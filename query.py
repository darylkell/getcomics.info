import re
import shutil
import tempfile
import textwrap
import time

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, unquote

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, DownloadColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn


BASE_URL = "https://getcomics.info"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
console = Console(highlight=False)

class Query:
	"""
	Object to take a user's search string and provide an interface to getcomics.info results 
	"""
	def __init__(self, query: str, results: str, verbose: bool, download_path: Path):
		self.query = query
		self.num_results_desired = results
		self.verbose = verbose
		self.download_path = download_path
		self.page_links = {}  # pages hosting comics, dict[str, str]: url, title
		self.comic_links = {} # actual links to comics, dict[str, str]: url, metadata dict
		self.successful_downloads = []
		self.skipped_downloads = []
		self.unsupported_mirrors = [] # list of dicts: {title, provider, url, parent_page}
		
		self.session = requests.Session()
		self.session.headers.update({"User-Agent": USER_AGENT})

	def find_pages(self, date=None):
		"""
		Uses the search query to find pages that can later be parsed for download links.

		date (None | datetime): date to look for in search results, or newer
		"""
		# treat 0 as infinite desired results
		page = 0
		while self.num_results_desired == 0 or len(self.page_links) < self.num_results_desired:
			page += 1
			url = f"{BASE_URL}/page/{page}?s={quote_plus(self.query)}"
			try:
				if self.verbose: console.print(f"Opening page {url}")
				response = self.session.get(url)
			except Exception as e:
				console.print(f"Error contacting URL: {url}")
				console.print(e)
			
			soup = BeautifulSoup(response.text, "html.parser")
			articles = soup.findAll("article")
			if len(articles) == 0:
				return

			for article in articles:
				title_tag = article.find("h1", {"class": "post-title"})
				title = title_tag.text
				link = title_tag.find("a")["href"]
				article_time = article.find("time")["datetime"]
				
				if date:
					year, month, day = article_time.split("-")  # should be in the format "2023-10-08" for Oct 8 2023
					if datetime(year=int(year), month=int(month), day=int(day)) < date:
						return  # don't bother looking at more articles because the articles are sorted by date
				self.page_links[link] = title

		if self.verbose:
			console.print(f"{len(self.page_links):,} pages found containing matching comics.")

	def _get_response(self, url, method="GET", **kwargs):
		"""Robust request handler with retries"""
		for attempt in range(2):
			try:
				if method == "GET":
					response = self.session.get(url, timeout=15, **kwargs)
				else:
					response = self.session.head(url, timeout=15, **kwargs)
				
				if response.status_code == 200:
					return response
			except Exception as e:
				if self.verbose: console.print(f"[dim]Attempt {attempt+1} failed for {url}: {e}[/dim]")
		return None

	def _resolve_mediafire(self, url):
		"""Extracts direct download link from Mediafire landing page"""
		try:
			response = self._get_response(url)
			if not response: return url
			soup = BeautifulSoup(response.text, "html.parser")
			download_button = soup.find("a", {"id": "downloadButton"})
			if download_button:
				return download_button.get("href")
			
			# regex fallback
			match = re.search(r'https?://download\d+\.mediafire\.com/[^"\'>]+', response.text)
			if match:
				return match.group(0)
		except Exception as e:
			if self.verbose: console.print(f"[red]Failed to resolve Mediafire link {url}: {e}[/red]")
		return url

	def _resolve_pixeldrain(self, url):
		"""Converts Pixeldrain landing page URL to direct API download link"""
		# URL format: https://pixeldrain.com/u/ID
		# API format: https://pixeldrain.com/api/file/ID?download
		if "/u/" in url:
			return url.replace("/u/", "/api/file/") + "?download"
		return url

	def _resolve_indirect_link(self, url):
		"""Routes to provider-specific resolvers"""
		if "mediafire.com" in url:
			return self._resolve_mediafire(url)
		if "pixeldrain.com" in url:
			return self._resolve_pixeldrain(url)
		return url

	def _get_item_title(self, tag, page_title):
		"""Attempts to find a specific title for a link by looking at preceding headers/bold text"""
		# Traverse backwards to find the nearest title-like tag
		generic_keywords = ["DOWNLOAD", "MAIN SERVER", "MIRROR", "CONTACT", "SITEMAP", "HOW TO", "READ ONLINE", "SERVER"]
		
		curr = tag
		while curr:
			# Look for siblings before this one
			for sibling in curr.previous_siblings:
				if hasattr(sibling, "name") and sibling.name:
					# If it's a direct title tag
					if sibling.name in ["h1", "h2", "h3", "h4", "strong", "b"]:
						text = sibling.get_text().strip()
						if text and len(text) > 3 and not any(k in text.upper() for k in generic_keywords):
							return text
					
					# If it's a container that might have a title in it (like <p><strong>TITLE</strong></p>)
					target = sibling.find(["strong", "b", "h2", "h3", "h4"])
					if target:
						text = target.get_text().strip()
						if text and len(text) > 3 and not any(k in text.upper() for k in generic_keywords):
							return text
						
			curr = curr.parent
			if curr and curr.name in ["section", "article"]: # don't go outside post-contents
				break
		return page_title

	def _fetch_links_from_page(self, url, title, depth=0, origin_url=None):
		"""Exhaustive link discovery and classification"""
		if not origin_url:
			origin_url = url
			
		response = self._get_response(url)
		if not response:
			if self.verbose: console.print(f"Could not load page {url}")
			return

		soup = BeautifulSoup(response.text, "html.parser")
		
		# Try multiple common content wrappers
		post_contents = soup.find("section", {"class": "post-contents"}) or \
						soup.find("div", {"class": "post-contents"}) or \
						soup.find("div", {"class": "entry-content"}) or \
						soup.find("article")
		
		if not post_contents:
			if self.verbose: console.print(f"Post contents not found for {url}")
			return

		links_found_on_page = False
		# Known providers and mirrors
		providers = ["MEDIAFIRE", "MEGA", "TERABOX", "PIXELDRAIN", "ROOTZ", "VIKINGFILE", 
					 "DROPAPK", "USERSCLOUD", "GOOGLE DRIVE", "SHARER.PW", "TORRENT", "MAGNET", "READ ONLINE"]
		
		# Software and sites to ignore (often found in "Reading Guide" or footer)
		blacklist = [
			"yacreader.com", "comicrack.cyolito.com", "cdisplayex.com", "7-zip.org", "win-rar.com", 
			"adobe.com", "facebook.com", "twitter.com", "x.com", "instagram.com", "reddit.com", 
			"paypal.com", "patreon.com", "jdownloader.org", "utorrent.com", "bittorrent.com",
			"/contact", "/sitemap", "/how-to-download"
		]

		found_links = post_contents.find_all("a")
		for a in found_links:
			href = a.get("href")
			if not href or href.startswith("#") or "how-to-download" in href:
				continue
			
			# Filter out blacklisted domains
			if any(domain in href.lower() for domain in blacklist):
				continue

			link_text = a.get_text().strip().upper()
			link_title = (a.get("title") or "").upper()
			
			# Normalize for provider search
			search_space = f"{link_text} {link_title}"
			
			# 1. Direct Links (Known file extensions or labeled as Main Server/Download Now)
			is_direct = any(href.lower().endswith(ext) for ext in [".cbz", ".cbr", ".zip", ".pdf"]) or \
						any(x in search_space for x in ["DOWNLOAD NOW", "MAIN SERVER"])
			
			if is_direct:
				item_title = self._get_item_title(a, title)
				self.comic_links[href] = {
					"title": item_title, 
					"provider": "DIRECT", 
					"type": "DIRECT",
					"origin_url": origin_url
				}
				links_found_on_page = True

			# 2. Resolvable Mirrors (Mediafire, Pixeldrain)
			elif "MEDIAFIRE" in search_space or "mediafire.com" in href or "pixeldrain.com" in href:
				item_title = self._get_item_title(a, title)
				provider = "MEDIAFIRE" if "mediafire" in href.lower() or "MEDIAFIRE" in search_space else "PIXELDRAIN"
				self.comic_links[href] = {
					"title": item_title, 
					"provider": provider, 
					"type": "RESOLVABLE",
					"origin_url": origin_url
				}
				links_found_on_page = True

			# 3. Internal index links (Weekly Packs) - follow depth=0 only
			elif depth == 0 and link_text == "DOWNLOAD" and any(x in href for x in ["getcomics.info", "getcomics.org"]):
				if self.verbose: console.print(f"Following internal link: {href}")
				self._fetch_links_from_page(href, title, depth=1, origin_url=origin_url)
				links_found_on_page = True

			# 4. Known Mirrors (Manual)
			elif any(x in search_space for x in providers) or any(x in href.lower() for x in ["terabox", "mega.nz", "pixeldrain"]):
				# Find which provider matched
				provider = "MIRROR"
				for p in providers:
					if p in search_space:
						provider = p
						break
				if provider == "MIRROR": # Fallback to URL-based detection
					if "terabox" in href.lower(): provider = "TERABOX"
					elif "mega.nz" in href.lower(): provider = "MEGA"
					elif "pixeldrain" in href.lower(): provider = "PIXELDRAIN"

				item_title = self._get_item_title(a, title)
				self.unsupported_mirrors.append({
					"title": item_title,
					"provider": provider,
					"url": href,
					"parent_page": url
				})
				self.comic_links[href] = {
					"title": item_title, 
					"provider": provider, 
					"type": "MANUAL",
					"origin_url": origin_url
				}
				links_found_on_page = True
			
			# 5. Catch-all for other potentially useful links
			elif link_title or len(link_text) > 2:
				if any(x in href.lower() for x in ["download", "file", "share", "comic"]):
					item_title = self._get_item_title(a, title)
					provider = link_text if 0 < len(link_text) < 15 else "MIRROR"
					self.unsupported_mirrors.append({
						"title": item_title,
						"provider": provider,
						"url": href,
						"parent_page": url
					})
					self.comic_links[href] = {
						"title": item_title, 
						"provider": provider, 
						"type": "MANUAL",
						"origin_url": origin_url
					}
					links_found_on_page = True

		if not links_found_on_page and self.verbose:
			console.print(f"No workable links found on {url}")

	def get_download_links(self):
		"""
		From the page results, gets download links in parallel.
		"""
		executor = ThreadPoolExecutor(max_workers=3)
		futures = [executor.submit(self._fetch_links_from_page, url, title) for url, title in self.page_links.items()]
		try:
			while any(not f.done() for f in futures):
				time.sleep(0.1)
		except KeyboardInterrupt:
			for f in futures:
				f.cancel()
			executor.shutdown(wait=False, cancel_futures=True)
			raise
		finally:
			executor.shutdown(wait=False)

	def download_comics(self, prompt=False):
		"""
		Downloads comics that have been found 
		"""        
		# Filter out manual-only links for the automated download loop
		automatable_links = {u: m for u, m in self.comic_links.items() if m["type"] in ["DIRECT", "RESOLVABLE"]}
		
		# Group by (origin_url, title) to avoid downloading mirrors
		grouped_items = {}
		for url, metadata in automatable_links.items():
			key = (metadata["origin_url"], metadata["title"])
			if key not in grouped_items:
				grouped_items[key] = []
			grouped_items[key].append((url, metadata))
		
		# For each item, pick the best link (Prefer DIRECT over RESOLVABLE)
		final_links = []
		for key, links in grouped_items.items():
			# Sort by type: DIRECT (0) before RESOLVABLE (1)
			links.sort(key=lambda x: 0 if x[1]["type"] == "DIRECT" else 1)
			final_links.append(links[0])

		total = len(final_links)
		for i, (url, metadata) in enumerate(final_links):
			prefix = f"[{i+1}/{total}]"
			title = metadata["title"]
			
			# Resolve indirect links (e.g. Mediafire)
			download_url = self._resolve_indirect_link(url)
			
			if self.verbose: console.print(f"\n{prefix} Downloading {title} from {download_url}")

			# Start the request to get headers
			response = self.session.get(download_url, stream=True)
			
			# Try to get filename from Content-Disposition header
			content_disp = response.headers.get("Content-Disposition")
			if content_disp and "filename=" in content_disp:
				# Extract filename from header: filename="comic.cbz" or filename=comic.cbz
				fname_match = re.search(r'filename=["\']?([^"\']+)["\']?', content_disp)
				if fname_match:
					file_name = self.safe_filename(unquote(fname_match.group(1)))
				else:
					file_name = self.safe_filename(unquote(download_url.rpartition("/")[-1].replace("?download", "")))
			else:
				# Fallback to URL-based filename
				file_name = self.safe_filename(unquote(download_url.rpartition("/")[-1].replace("?download", "")))
			
			# If still no extension or generic name, fallback to title + best guess or .zip
			if "." not in file_name or len(file_name) < 5:
				file_name = f"{self.safe_filename(title)}.zip"

			file_path = self.create_file_name(str(self.download_path / file_name))
			
			if prompt and "n" in input(f"{prefix} Download '{title}'? (Y/n) ").lower():
				self.skipped_downloads.append(title)
				continue

			try:
				self.download_file_stream(
					response, 
					filename=Path(file_path),
					verbose=True, 
					transient=True,
					prefix=prefix
				)
				self.successful_downloads.append(title)
				console.print(f"{prefix} [green]'{title}' downloaded.[/green]")
			except Exception as e:
				console.print(f"{prefix} [red]Failed to download '{title}': {e}[/red]")

	def download_file_stream(self, response, filename=None, chunk_size=1024, verbose=False, transient=False, prefix=""):
		"""
		Downloads an already started response stream to a file
		"""
		destination = filename
		temp_file = Path(tempfile.gettempdir()) / filename.name
		
		total_size_in_bytes = int(response.headers.get('content-length', 0))
		try:
			with open(temp_file, "wb") as file:
				progress = Progress(
					TextColumn("[progress.description]{task.description}"),
					TimeRemainingColumn(compact=True),
					BarColumn(bar_width=20),
					"[progress.percentage]{task.percentage:>3.1f}%",
					"•",
					DownloadColumn(binary_units=True),
					"•",
					TransferSpeedColumn(),
					disable=not verbose,
					transient=transient
				)
				with progress:
					task_id = progress.add_task(
						description=f"{prefix} {destination.name}",
						total=total_size_in_bytes,
						visible=True
					)
					for chunk in response.iter_content(chunk_size=chunk_size):
						# set up the progress bar so it has the best chance to be displayed nicely, allowing for terminal resizing
						columns_width = 70
						terminal_width = shutil.get_terminal_size().columns
						max_length = max(terminal_width - columns_width, 10)
						file_name_divided = "\n".join(textwrap.wrap(f"{prefix} {destination.name}", width=max_length))

						file.write(chunk)
						progress.update(task_id, description=file_name_divided, advance=chunk_size)
			temp_file.replace(destination)
		except KeyboardInterrupt:
			if temp_file.exists():
				temp_file.unlink(missing_ok=True)
			raise

	def safe_filename(self, filename: str) -> str:
		r"""Returns the filename with characters like \:*?"<>| removed."""
		return re.sub(r'[\\/:*?"<>|]', "", filename)

	def create_file_name(self, filename: str) -> str:
		""" 
		Checks to see if a file already exists.
		If it does, returns a string path with a unique name that does not exist
		as per the Windows standard ("temp.py" when exists returns "temp (0).py")
		
		:Parameters:
		filename (str) - path to be checked
		
		:Returns:
		filename (str) - unique filename
		"""
		filename = filename.replace("\\", "/")
		if not Path(filename).exists():
			return filename
		
		# account for "." in directory structure
		if "/" in filename:
			directories, _, filename = filename.rpartition("/") 
			directories += "/"
		else:
			directories = ""
		
		# break down the filename into its parts
		if "." in filename:
			stem, _, suffix = filename.rpartition(".")
			suffix = "." + suffix
		else:
			stem, suffix = filename, ""

		num = 0
		while Path(f"{directories}{stem} ({num}){suffix}").exists():
			num += 1
		return f"{directories}{stem} ({num}){suffix}"

	def print_summary(self):
		if not any([self.successful_downloads, self.skipped_downloads, self.unsupported_mirrors]):
			return

		summary_elements = []
		if self.successful_downloads:
			summary_elements.append(f"[green]Successfully downloaded {len(self.successful_downloads)} comics.[/green]")
		if self.skipped_downloads:
			summary_elements.append(f"[yellow]Skipped {len(self.skipped_downloads)} comics.[/yellow]")
		
		# Combine status counts
		status_text = "\n".join(summary_elements)
		
		# Filter out mirrors for comics that were already successfully downloaded
		downloaded_titles = set(self.successful_downloads)
		filtered_mirrors = [m for m in self.unsupported_mirrors if m["title"] not in downloaded_titles]

		if filtered_mirrors:
			table = Table(title="Discovered Mirrors (Manual Download Required)", show_header=True, header_style="bold magenta", expand=True)
			table.add_column("Comic / Item", style="white")
			table.add_column("Provider", style="bold cyan")
			table.add_column("URL", style="blue")
			for mirror in filtered_mirrors:
				table.add_row(mirror["title"], mirror["provider"], mirror["url"])
			
			console.print()
			if status_text:
				console.print(Panel(status_text, title="Download Status", expand=False))
			console.print(table)
		else:
			if status_text:
				console.print(Panel(status_text, title="Summary", expand=False))
