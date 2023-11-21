import re
import shutil
import tempfile
import textwrap

from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, unquote

import requests
from bs4 import BeautifulSoup
from rich.progress import Progress, BarColumn, DownloadColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn


BASE_URL = "https://getcomics.info"

class Query:
	"""
	Object to take a user's search string and provide an interface to getcomics.info results 
	"""
	def __init__(self, query: str, results: str, verbose: bool, download_path: str):
		self.query = query
		self.num_results_desired = results
		self.verbose = verbose
		self.download_path = download_path
		self.page_links = {}  # pages hosting comics, dict[str, str]: url, title
		self.comic_links = {} # actual links to comics, dict[str, str]: url, title

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
				if self.verbose: print(f"Opening page {url}")
				response = requests.get(url)
			except Exception as e:
				print(f"Error contacting URL: {url}")
				print(e)
			
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
			print(f"{len(self.page_links):,} pages found containing matching comics.")

	def get_download_links(self):
		"""
		From the page results, gets download links.
		If a page does not have a native link but has mediafire, it will record that link instead,
		prepending the url with '_MEDIAFIRE_'
		
		TODO: Does not yet handle a page that has multiple links, such as:
			https://getcomics.org/other-comics/buffy-the-vampire-slayer-season-8-library-edition-vol-1-4-2012-2013/
		
		"""
		for url, title in self.page_links.items():
			try:
				if self.verbose: print(f"Opening page {url}")
				response = requests.get(url)
			except Exception as e:
				print(f"Error contacting URL: {url}")
				print(e)

			soup = BeautifulSoup(response.text, "html.parser")
			native_download_a_tag = soup.find("a", {"title": "Download Now"})
			main_server_a_tags = soup.findAll("a", text="Main Server")
			mediafire_download_a_tag = soup.find("a", {"title": "MEDIAFIRE"})

			if not native_download_a_tag and not main_server_a_tags:
				if self.verbose: print(f"Couldn't find a native download link on page {url}")
				if mediafire_download_a_tag:
					# prepend URL so we know it is MEDIAFIRE
					self.comic_links[f"_MEDIAFIRE_{mediafire_download_a_tag['href']}"] = title
			elif native_download_a_tag:
				self.comic_links[native_download_a_tag["href"]] = title
			elif main_server_a_tags:
				for tag in main_server_a_tags:
					self.comic_links[tag["href"]] = title
			else:
				print("No download links found.")

	def download_comics(self, prompt=False):
		"""
		Downloads comics that have been found 
		"""        
		for i, (url, title) in enumerate(self.comic_links.items()):
			if url.startswith("_MEDIAFIRE_"):
				print(f"{title}:\nPlease download from the following Mediafire link:\n{url[url.index('http'):]}")
				continue
			
			if self.verbose: print(f"Downloading {title} from {url}")
			file_name = self.safe_filename(unquote(url.rpartition("/")[-1]))
			file_name = self.create_file_name(str(Path(self.download_path / file_name)))
			
			if prompt and "n" in input(f"Download '{title}'? (Y/n) ").lower():
				continue

			self.download_file(
				url, 
				filename=Path(file_name),
				verbose=True, 
				transient=True
			)
			print(f"'{title}' downloaded.")

	def download_file(self, url, filename=None, chunk_size=1024, verbose=False, transient=False):
		"""
		url (str): url to download
		filename (Path): path to save as
		verbose (bool): whether or not to display the progress bar
		transient: make the progress bar disappear on completion
		
		Downloads file to OS temp directory, then renames to the final given destination
		"""
		destination = filename
		temp_file = Path(tempfile.gettempdir()) / filename.name

		response = requests.get(url, stream=True)
		total_size_in_bytes = int(response.headers.get('content-length', 0))
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
					description=destination.name,
					total=total_size_in_bytes,
					visible=not self.verbose
				)
				for chunk in response.iter_content(chunk_size=chunk_size):
					# set up the progress bar so it has the best chance to be displayed nicely, allowing for terminal resizing
					columns_width = 60 # generally, the Text/TimeRemaining/Bar/Download/TransferSpeed Columns take up this much room
					terminal_width = shutil.get_terminal_size().columns
					max_length = max(terminal_width - columns_width, 10)
					file_name_divided = "\n".join(textwrap.wrap(destination.name, width=max_length))

					file.write(chunk)
					progress.update(task_id, description=file_name_divided, advance=chunk_size)
		temp_file.replace(destination)

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