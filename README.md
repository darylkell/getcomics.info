# getcomics.info
Sequentially download files from getcomics.info, plays nicely on Linux and Windows.

```
usage: main.py [-h] [-date DATE] [-output DOWNLOAD_PATH] [-min MIN] [-max MAX] [-prompt] [-results RESULTS] [-test]
               [-verbose]
               query

Search for and/or download content from getcomics.info. Note: If -min or -max is set, an integer will be included as
part of the performed search query.

positional arguments:
  query                 Search term for comics

options:
  -h, --help            show this help message and exit
  -date DATE, --d DATE  Return results as new as this date (inclusive), eg: 2023-11-21 (optional)
  -output DOWNLOAD_PATH, --o DOWNLOAD_PATH
                        Destination directory (default: "./")
  -min MIN              Search for issues including newer ones from issue number X (default: None)
  -max MAX              Search for issues up to issue number X (default: None)
  -prompt, --p          Confirm download before saving (default: False)
  -results RESULTS, --r RESULTS
                        Number of results to retrieve (default: 0, for infinite)
  -test, --t            Enable test mode (default: False)
  -verbose, --v         Verbosity level (default: False)
```

# Examples:
### Download all 'Stalking Dead Deluxe' comics to be found
```
python main.py "Stalking Dead Deluxe"

The Stalking Dead Deluxe 076 (2023).cbr 00:02 ━━━━━━━━━━━━━━╸━━━━━ 73.5% • 18.9/25.8 MiB • 5.4 MB/s
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
python main.py "buffy 4" -t -r 3                                                    

                                                                        huffy 4

1) Huffy – The Last Layer #4 (2023)
Page: https://getcomics.org/other-comics/huffy-the-last-layer-4-2023/
Comic links on page:
  • https://fs2.comicfiles.ru/2023.11.01/Huffy%20the%20Last%20Layer%20004%20%282023%29%20%28Digital%29%20%28Kileko-Empire%29.cbz

2) Huffy The Last Layer #4 (2022)
Page: https://getcomics.org/other-comics/huffy-the-last-layer-4-2022/
Comic links on page:
  • https://fs1.comicfiles.ru/2022.03.09/Update/Huffy%20the%20Last%20Layer%20004%20%282022%29%20%28Digital%29%20%28Kileko-Empire%29.cbz

3) Huffy the Layer Season 8 – Library Edition Vol. 1 – 4 (2012-2013)
Page: https://getcomics.org/other-comics/huffy-the-layer-season-8-library-edition-vol-1-4-2012-2013/
Comic links on page:
  • https://twlv.comicfiles.ru/Weekly/2021.10.06/Update/Huffy%20the%20Layer%20Season%208%20-%20Library%20Edition%20v01%20%282012%29%20%28digital%29%20%28Son%20of%20Ultron%20II-Empire%29.cbr
  • https://twlv.comicfiles.ru/Weekly/2021.10.06/Update/Huffy%20the%20Layer%20Season%208%20-%20Library%20Edition%20v02%20%282012%29%20%28digital%29%20%28Son%20of%20Ultron%20II-Empire%29.cbr
  • https://twlv.comicfiles.ru/Weekly/2021.10.06/Update/Huffy%20the%20Layer%20Season%208%20-%20Library%20Edition%20v03%20%282012%29%20%28digital%29%20%28Son%20of%20Ultron%20II-Empire%29.cbr
  • https://twlv.comicfiles.ru/Weekly/2021.10.06/Update/Huffy%20the%20Layer%20Season%208%20-%20Library%20Edition%20v04%20%282013%29%20%28digital%29%20%28Lynx-Empire%29.cbr
```

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

### Notes:
* Where a 'native' download cannot be found, but a Mediafire download is available, the Mediafire link will be shown, the URL prepended by '_MEDIAFIRE_' (will require a manual download)
* Script relies on a 'Download Now' button or 'Main Server' button(s) to find a download link.
* As the query is made via a Python object, query.Query could be imported to a bespoke script and searches could be written out to file etc.
* Can combo with a text file containing series' you want to download, and in the case of PowerShell use something like: `cat ~\Documents\comics.txt | foreach { python main.py $_ -date 2023-11-18 -output ~\Downloads}`, incrementing your date each time to the last date you ran the script so you pick up any new uploads.

