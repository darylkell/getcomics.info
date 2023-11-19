import math
import tempfile
from pathlib import Path
from urllib.parse import quote_plus, unquote

import requests
from bs4 import BeautifulSoup
from rich.progress import track

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

    def find_pages(self):
        """
        Uses the search query to find pages that can later be parsed for download links.
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
            posts = soup.findAll("h1", {"class": "post-title"})
            if len(posts) == 0:
                return

            for post in posts:
                tags = post.findAll("a")
                for tag in tags:
                    # don't get any more if we've passed our desired number
                    if self.num_results_desired != 0 and len(self.page_links) == self.num_results_desired:
                        continue
                    self.page_links[tag["href"]] = tag.text
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

    def download_comics(self):
        """
        Downloads comics that have been found 
        """        
        for i, (url, title) in enumerate(self.comic_links.items()):
            if url.startswith("_MEDIAFIRE_"):
                print(f"Please download from the following Mediafire link:\n{url[url.index('http'):]}")
                continue
            
            if self.verbose: print(f"Downloading {title} from {url}")
            file_name = unquote(url.rpartition("/")[-1])
            file_name = self.create_file_name(str(Path(self.download_path / file_name)))
            self.download_file(
                url, 
                filename=file_name,
                verbose=True, 
                transient=True
            )

    def download_file(self, url, filename=None, chunk_size=1024, verbose=False, transient=False):
        """
        url (str): url to download
        filename (str): path to save as
        verbose (bool): whether or not to display the progress bar
        transient: make the progress bar disappear on completion
        
        Downloads file to OS temp directory, then renames to the final given destination
        """
        destination = filename
        
        filename = url.rpartition("/")[-1] if filename is None else filename
        temp_file = Path(tempfile.gettempdir()) / filename
                
        response = requests.get(url, stream=True)
        with open(temp_file, "wb") as file:
            total_size_in_bytes = int(response.headers.get('content-length', 0))
            for chunk in track(
                response.iter_content(chunk_size=chunk_size), 
                description=f"Downloading '{filename}' ({self.format_bytes(total_size_in_bytes) if total_size_in_bytes else 'Unknown size'})", 
                transient=transient,
                total=math.ceil(total_size_in_bytes / 1024),
                disable=not verbose
            ):
                file.write(chunk)
        temp_file.replace(destination)

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

    def format_bytes(self, size: [int, float]) -> str:
        """
        :param size: (int) bytes to determine a readable size from
        :return: (string) readable size
        """
        orig_size = size
        # 2**10 = 1024
        power = 2**10
        n = 0
        power_labels = {0 : ' B', 1: ' KB', 2: ' MB', 3: ' GB', 4: ' TB', 5: ' PB', 6: ' EB', 7: ' ZB', 8: ' YB'}
        while size > power:
            size /= power
            n += 1
        try:
            return f"{round(size, 2)}{power_labels[n]}"
        except KeyError:
            raise TypeError(f"Input {orig_size:,} is too large (yottabyte is largest calculable)")