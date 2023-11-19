'''
	Inspired by:
	Taylor King
	telltaylor13@gmail.com
	https://github.com/Gink3/ComicScraper
'''

import argparse
import sys
from pathlib import Path

from query import Query


def parse_arguments():
	"""
	Parse arguments, but exit early if an output directory doesn't resolve properly.
	"""

	parser = argparse.ArgumentParser(description='Get comics from a search term.')
	
	# Mandatory argument
	parser.add_argument('query', type=str, help='Search term for comics')

	# Optional argument for download location
	parser.add_argument('-output', '--o', dest='download_path', type=str, default='./',
		help='Destination directory (default: "./")'
	)

	# Optional argument for the number of results
	parser.add_argument('-results', '--r', dest="results", type=int, default=0, # treat 0 as infinite
		help='Number of results to retrieve (default: 1, 0 for infinite)'
	)

	# Optional argument for testing
	parser.add_argument('-test', '--t', dest="test", action='store_true', default=False,
		help='Enable test mode (default: False)'
	)

	# Optional argument for verbosity
	parser.add_argument('-verbose', '--v', dest="verbose", action='store_true', default=False,
		help='Verbosity level (default: False)'
	)

	args = parser.parse_args()

	args.download_path = Path(args.download_path)
	if not args.download_path.exists() or not args.download_path.is_dir():
		print(f"Please enter a valid output directory.")
		print(f"'{args.download_path}' does not exist or is not a valid directory.")
		sys.exit(1)
	
	return args


def main():
	args = parse_arguments()

	query = Query(args.query, args.results, args.verbose, args.download_path)
	
	query.find_pages()
	if args.test:
		print("\nPage links found:")
		for i, (url, title) in enumerate(query.page_links.items(), start=1):
			print(f"{i}) {title}: {url}")
	
	query.get_download_links()
	if args.test:
		print("\nComic links found:")	
		for i, (url, title) in enumerate(query.comic_links.items(), start=1):
			print(f"{i}) {title}: {url}")
	
	if not args.test:
		query.download_comics()


if __name__ == "__main__":
	main()