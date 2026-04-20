# Project Overview: getcomics.info

A Python-based CLI tool designed to search for and sequentially download comics from [getcomics.info](https://getcomics.info). It provides a robust interface for filtering results by date, issue numbers, and confirming downloads before saving.

## Core Technologies
- **Python**: Core programming language.
- **Requests**: For HTTP requests and file streaming.
- **BeautifulSoup4**: For parsing HTML and scraping download links.
- **Rich**: For advanced terminal formatting, progress bars, and status indicators.
- **Argparse**: For CLI argument parsing.

## Architecture
- **`main.py`**: Entry point. Handles CLI argument parsing, date validation, and the high-level execution loop.
- **`query.py`**: Contains the `Query` class which encapsulates:
    - Search result discovery (`find_pages`).
    - Download link extraction (`get_download_links`).
    - File downloading with progress tracking (`download_file`).
    - Filename sanitization and collision handling.

## Building and Running

### Prerequisites
- Python 3.x
- `pip`

### Setup
```bash
pip install -r requirements.txt
```

### Running
```bash
# Basic search and download
python main.py "Comic Name"

# Search with date filter
python main.py "Comic Name" -date 2023-11-21

# Range-based search (Issue 70 to 73)
python main.py "Comic Name" -min 70 -max 73

# Test mode (shows links without downloading)
python main.py "Comic Name" -test
```

## Development Conventions
- **Date Parsing**: The project uses a custom, robust date parsing function (`is_date` in `main.py`) that handles various formats (e.g., `DD/MM/YYYY`, `YYYY-MM-DD`).
- **Scraping Logic**: The tool looks for specific anchor tags (`title="Download Now"`, `title="DOWNLOAD NOW"`, or text "Main Server") to identify download links.
- **Mediafire Support**: If a native link isn't found, it falls back to Mediafire links, which are reported to the user for manual download.
- **Progress Tracking**: Uses `rich.progress` for visual feedback during downloads.
- **Safety**: Includes a `safe_filename` utility to ensure compatibility across different operating systems by removing invalid characters.
