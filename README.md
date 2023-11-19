# getcomics.info
Sequentially download files from getcomics.info, should play nicely on Linux and Windows.

```
usage: main.py [-h] [-output DOWNLOAD_PATH] [-newer NEWER] [-results RESULTS] [-test] [-verbose] query

Get comics from a search term.

positional arguments:
  query                 Search term for comics

options:
  -h, --help            show this help message and exit
  -output DOWNLOAD_PATH, --o DOWNLOAD_PATH
                        Destination directory (default: "./")
  -newer NEWER, --n NEWER
                        Search for issues including newer ones, requires an integer argument (default: False)
  -results RESULTS, --r RESULTS
                        Number of results to retrieve, requires an integer argument (default: 1, 0 for infinite)
  -test, --t            Enable test mode (default: False)
  -verbose, --v         Verbosity level (default: False)
```

Examples:
```
# Download all 'Stalking Dead Deluxe' comics to be found
python main.py "Stalking Dead Deluxe"
```

```
# Download issues 73 and newer of 'Stalking Dead Deluxe'
python main.py "Stalking Dead Deluxe" -newer 73
```

```
# Download a maximum of 10 'Stalking Dead Deluxe' search results
python main.py "Stalking Dead Deluxe" -results 10
```

```
# Do a test run at a maximum of 3 search results for 'Stalking Dead Deluxe' - essentially runs the search without downloading
python main.py "Stalking Dead Deluxe" -results 3 -test                                                              

Page links found:
1) The Stalking Dead Deluxe #77 (2023): https://getcomics.org/other-comics/the-stalking-dead-deluxe-77-2023/
2) The Stalking Dead Deluxe #76 (2023): https://getcomics.org/other-comics/the-stalking-dead-deluxe-76-2023/
3) The Stalking Dead Deluxe #75 (2023): https://getcomics.org/other-comics/the-stalking-dead-deluxe-75-2023/

Comic links found:
1) The Stalking Dead Deluxe #77 (2023): https://fs2.comicfiles.ru/2023.11.15/Update/The%20Stalking%20Dead%20Deluxe%20077%20%282023%29%20%28Digital%29%20%28Li%27l-Empire%29.cbr
2) The Stalking Dead Deluxe #76 (2023): https://fs2.comicfiles.ru/2023.11.01/The%20Stalking%20Dead%20Deluxe%20076%20%282023%29%20%28Digital%29%20%28Li_l-Empire%29.cbr
3) The Stalking Dead Deluxe #75 (2023): https://fs2.comicfiles.ru/2023.10.25/Update%202/The%20Stalking%20Dead%20Deluxe%20075%20%282023%29%20%28Digital%29%20%28%20Li%27l-Empire%29.cbr
```

Notes:

* Where a 'native' download cannot be found, but a Mediarefire download is available, the Mediafire link will be shown, the URL prepended by '_MEDIAFIRE_' (will require a manual download)
* Script relies on a 'Download Now' button or 'Main Server' button(s) to find a download link.
* As the query is made via a Python object, query.Query could be imported to a bespoke script and searches could be written out to file etc.
<br>
Requirements:

This script has been tested with the following requirements:

* rich                 13.3.4
* beautifulsoup4       4.12.2
* requests             2.28.2 
