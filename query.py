import re
import shutil
import tempfile
import textwrap

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
		self.comic_links = {} # actual links to comics, dict[str, str]: url, title
		self.successful_downloads = []
		self.skipped_downloads = []
		self.mediafire_links = []
		
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

	def _fetch_links_from_page(self, url, title):
		"""Helper for parallel link fetching"""
		try:
			if self.verbose: console.print(f"Opening page {url}")
			response = self.session.get(url)
		except Exception as e:
			console.print(f"Error contacting URL: {url}")
			console.print(e)
			return

		soup = BeautifulSoup(response.text, "html.parser")
		native_download_a_tags = soup.findAll("a", {"title": "Download Now"})
		native_download_a_tags += soup.findAll("a", {"title": "DOWNLOAD NOW"})
		main_server_a_tags = soup.findAll("a", text="Main Server")
		mediafire_download_a_tags = soup.findAll("a", {"title": "MEDIAFIRE"})

		if not native_download_a_tags and not main_server_a_tags:
			if self.verbose: console.print(f"Couldn't find a native download link on page {url}")
			if mediafire_download_a_tags:
				# prepend URL so we know it is MEDIAFIRE
				for tag in mediafire_download_a_tags:
					self.comic_links[f"_MEDIAFIRE_{tag['href']}"] = title
		if native_download_a_tags:
			for tag in native_download_a_tags:
				self.comic_links[tag["href"]] = title
		if main_server_a_tags:
			for tag in main_server_a_tags:
				self.comic_links[tag["href"]] = title
		if not native_download_a_tags and not main_server_a_tags and not mediafire_download_a_tags:
			if self.verbose: console.print(f"No download links found on {url}")

	def get_download_links(self):
		"""
		From the page results, gets download links in parallel.
		"""
		with ThreadPoolExecutor(max_workers=5) as executor:
			executor.map(lambda p: self._fetch_links_from_page(*p), self.page_links.items())

	def download_comics(self, prompt=False):
		"""
		Downloads comics that have been found 
		"""        
		total = len(self.comic_links)
		for i, (url, title) in enumerate(self.comic_links.items()):
			prefix = f"[{i+1}/{total}]"
			if url.startswith("_MEDIAFIRE_"):
				self.mediafire_links.append((title, url[url.index('http'):]))
				continue
			
			if self.verbose: console.print(f"{prefix} Downloading {title} from {url}")

			# if url doesn't look like a direct file link (some are encoded) try and get file name from the redirect
			if "." not in url.rpartition("/")[-1]:
				url = self.session.head(url, allow_redirects=True).url
			
			file_name = self.safe_filename(unquote(url.rpartition("/")[-1]))
			file_name = self.create_file_name(str(self.download_path / file_name))
			
			if prompt and "n" in input(f"{prefix} Download '{title}'? (Y/n) ").lower():
				self.skipped_downloads.append(title)
				continue

			self.download_file(
				url, 
				filename=Path(file_name),
				verbose=True, 
				transient=True,
				prefix=prefix
			)
			self.successful_downloads.append(title)
			console.print(f"{prefix} [green]'{title}' downloaded.[/green]")

	def download_file(self, url, filename=None, chunk_size=1024, verbose=False, transient=False, prefix=""):
		"""
		url (str): url to download
		filename (Path): path to save as
		verbose (bool): whether or not to display the progress bar
		transient: make the progress bar disappear on completion
		prefix (str): string to prepend to the progress bar description
		
		Downloads file to OS temp directory, then renames to the final given destination
		"""
		response = self.session.get(url, stream=True)

		# check if a redirect occurred because it could affect the file name being saved (issue #13)
		if response.history:
			filename = Path(unquote(Path(response.url).name))
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
						visible=not self.verbose
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
		"""Returns the filename with characters like \:*?"<>| removed."""
		return re.sub(r"[\/\\\:\*\?\"\<\>\|]", "", filename)

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
		if not any([self.successful_downloads, self.skipped_downloads, self.mediafire_links]):
			return

		summary_elements = []
		if self.successful_downloads:
			summary_elements.append(f"[green]Successfully downloaded {len(self.successful_downloads)} comics.[/green]")
		if self.skipped_downloads:
			summary_elements.append(f"[yellow]Skipped {len(self.skipped_downloads)} comics.[/yellow]")
		
		# Combine status counts
		status_text = "\n".join(summary_elements)
		
		if self.mediafire_links:
			table = Table(title="Manual Downloads Required (Mediafire)", show_header=True, header_style="bold magenta", expand=True)
			table.add_column("Comic Title", style="dim")
			table.add_column("URL", style="blue")
			for title, link in self.mediafire_links:
				table.add_row(title, link)
			
			console.print()
			if status_text:
				console.print(Panel(status_text, title="Download Status", expand=False))
			console.print(table)
		else:
			if status_text:
				console.print(Panel(status_text, title="Summary", expand=False))
