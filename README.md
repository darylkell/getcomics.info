# getcomics.info
Sequentially download files from getcomics.info, plays nicely on Linux and Windows.

```
usage: main.py [-h] [-d DATE] [-o DOWNLOAD_PATH] [-min MIN] [-max MAX] [-p] [-r RESULTS] [-t] [-v] query

Search for and/or download content from getcomics.info.

Note: If -min or -max is set, an integer will be included as part of the performed search query.

positional arguments:
  query                 Search term for comics

options:
  -h, --help            show this help message and exit
  -d DATE, --date DATE  Return results as new as this date (inclusive), eg: 2023-11-21 (optional)
  -o DOWNLOAD_PATH, --output DOWNLOAD_PATH
                        Destination directory (default: "./")
  -min MIN, --min MIN   Search for issues including newer ones from issue number X (default: None)
  -max MAX, --max MAX   Search for issues up to issue number X (default: None)
  -p, --prompt          Confirm download before saving (default: False)
  -r RESULTS, --results RESULTS
                        Number of results to retrieve (default: 0, for infinite)
  -t, --test            Enable test mode (default: False)
  -v, --verbose         Verbosity level (default: False)
```

# Examples:
### Download all 'Stalking Dead Deluxe' comics to be found
```
python main.py "Stalking Dead Deluxe"

[1/41] 'The Stalking Dead Deluxe #135' downloaded.
[2/41] The Stalking Dead Deluxe 133 (2026) (Digital) (Zone-Empire).cbr 00:04 ━━━━━╸━━━━━━━━━━━━━━ 27.6% • 28.7/104.3 MiB • 21.8 MB/s
...etc
```

### Download issues 73 and newer of 'Stalking Dead Deluxe', to a maximum of 10 results
```
python main.py "Stalking Dead Deluxe" -min 73 -results 10
```

### Download issues up to issue #73 of 'Stalking Dead Deluxe'
```
python main.py "Stalking Dead Deluxe" -max 73
```

### Download issues #70 to #73 of 'Stalking Dead Deluxe'
```
python main.py "Stalking Dead Deluxe" -min 70 -max 73
```

### Do a test run at a maximum of 3 search results for 'huffy 4' - essentially runs the search without downloading
```
python main.py "huffy 4" -t -r 3                                                    

Search Results for 'huffy 4'                                                                                                                             │
│ ├── 1) huffy – The Last Vampire Player #4 (2023)                                                                                                         │
│ │   https://getcomics.org/other-comics/huffy-the-last-vampire-Player-4-2023/                                                                             │
│ │   ├── huffy – The Last Vampire Player #4 (SD-Digital) (DIRECT:                                                                                         │
│ │   │   https://fs2.comicfiles.ru/2023.11.01/huffy%20the%20Last%20Vampire%20Player%20004%20%282023%29%20%28Digital%29%20%28Kileko-Empire%29.cbz)         │
│ │   ├── huffy – The Last Vampire Player #4 (SD-Digital) (TERABOX: https://teraboxapp.com/s/1F9a2Awg2zSwEz2ziLwSKEA)                                      │
│ │   ├── huffy – The Last Vampire Player #4 (SD-Digital) (MEGA: https://mega.nz/file/LfJAXYYQ#shSu9BlceVT_RnMcGLd0Yj_BhjgTSSuQ6KWZAWw-jwM)                │
│ │   ├── huffy – The Last Vampire Player #4 (SD-Digital) (MEDIAFIRE:                                                                                      │
│ │   │   https://www.mediafire.com/file_premium/27mw90sza11kfyd/huffy_the_Last_Vampire_Player_004_%25282023%2529_%2528Digital%2529_%2528Kileko-Empire%252 │
│ │   │   9.cbz/file)                                                                                                                                      │
│ │   └── huffy – The Last Vampire Player #4 (SD-Digital) (READ ONLINE: https://readcomicsonline.ru/comic/huffy-the-last-vampire-Player-2023/4)            │
│ ├── 2) huffy The Last Vampire Player #4 (2022)                                                                                                           │
│ │   https://getcomics.org/other-comics/huffy-the-last-vampire-Player-4-2022/                                                                             │
│ │   ├── huffy The Last Vampire Player #4 (DIRECT:                                                                                                        │
│ │   │   https://fs1.comicfiles.ru/2022.03.09/Update/huffy%20the%20Last%20Vampire%20Player%20004%20%282022%29%20%28Digital%29%20%28Kileko-Empire%29.cbz)  │
│ │   ├── huffy The Last Vampire Player #4 (UFILE: https://getcomics.ufile.io/v1kqjm61)                                                                    │
│ │   ├── huffy The Last Vampire Player #4 (MEGA: https://mega.nz/file/Sg9GTDDa#BH8RfzsJiX4teg-X2tQ9_3AW_S_BV5rZx-5PCkcGaaM)                               │
│ │   ├── huffy The Last Vampire Player #4 (MEDIAFIRE:                                                                                                     │
│ │   │   https://www.mediafire.com/file/35blsuv7m5v6iit/huffy_the_Last_Vampire_Player_004_%25282022%2529_%2528Digital%2529_%2528Kileko-Empire%2529.cbz/fi │
│ │   │   le)                                                                                                                                              │
│ │   ├── huffy The Last Vampire Player #4 (ZIPPYSHARE: https://www75.zippyshare.com/v/OUfEHKzY/file.html)                                                 │
│ │   └── huffy The Last Vampire Player #4 (READ ONLINE: https://readcomicsonline.ru/comic/huffy-the-last-vampire-Player-2021/4)
...etc
```

In the terminal, the supported links are highlighted - these would be attempted for downloaded in non-test execution (no -t flag).
The tree identifies each result: the title of the page is shown, followed by the url for the page, and then download links for the comic.

### Prompt before downloading a file, and save to the desktop
```
python main.py "Stalking Dead Deluxe 75" -output ~\Desktop -prompt                                                                                ─╯
Download 'The Stalking Dead Deluxe #75 (2023)'? (Y/n)
```


## Installation
* Install Python from https://python.org
* Download this repository, or git clone it.
* Install the requirements - from the program's directory: `pip install -r requirements.txt`
* Run with `python main.py "search term"`
  
### Requirements
This script has been tested with the following requirements:
* rich                 13.3.4
* beautifulsoup4       4.12.2
* requests             2.28.2

### Features & Updates:
* **Automated Downloads:** In addition to 'native' servers, the script now automatically resolves and downloads from **Mediafire** and **Pixeldrain**.
* **Smart Filtering:** Automatically ignores non-comic links such as 7-Zip, YAC Reader, and site meta-pages (Contact, Sitemap).
* **Mirror Deduplication:** Intelligently groups multiple download sources for the same comic and picks the best one (prioritizing direct servers), preventing duplicate downloads.
* **Improved Title Detection:** Advanced HTML parsing to extract clean comic titles, even when pages use generic "Download Now" headers.
* **Progress Visibility:** High-quality download progress bars powered by `rich`, which remain visible even in verbose mode.
* **Content-Disposition Support:** Correctly identifies original filenames and extensions for API-based downloads.

### Notes:
* Where an automated download cannot be performed (e.g., Mega, Terabox, Rootz), the links will be displayed in a summary table at the end for manual download.
* As the query is made via a Python object, query.Query could be imported to a bespoke script and searches could be written out to file etc.
* Can combo with a text file containing series' you want to download, and in the case of PowerShell use something like: `cat ~\Documents\comics.txt | foreach { python main.py $_ -date 2023-11-18 -output ~\Downloads}`, incrementing your date each time to the last date you ran the script so you pick up any new uploads.

### Security Warning
------
Please properly vet anything you download from the internet, including this script. It could do anything.
