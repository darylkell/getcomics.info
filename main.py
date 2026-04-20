import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.tree import Tree

from query import Query

console = Console(highlight=False)


def parse_arguments():
	"""
	Parse arguments, but exit early if an output directory doesn't resolve properly.
	"""

	parser = argparse.ArgumentParser(
		description="Search for and/or download content from getcomics.info.\n\n" \
			"Note: If -min or -max is set, an integer will be included as part of the performed search query."
		)
	
	# Mandatory argument
	parser.add_argument("query", type=str, help="Search term for comics")

	# Optional argument for date
	parser.add_argument("-d", "--date", dest='date', type=str, default=None,
		help="Return results as new as this date (inclusive), eg: 2023-11-21 (optional)"
	)

	# Optional argument for download location
	parser.add_argument("-o", "--output", dest="download_path", type=str, default="./",
		help='Destination directory (default: "./")'
	)

	# Optional argument for newer issues
	parser.add_argument("-min", "--min", dest="min", type=int, default=None,
		help="Search for issues including newer ones from issue number X (default: None)"
	)

	# Optional argument for newer issues
	parser.add_argument("-max", "--max", dest="max", type=int, default=None,
		help="Search for issues up to issue number X (default: None)"
	)

	# Optional argument for prompting before saving
	parser.add_argument("-p", "--prompt", dest="prompt", action="store_true", default=False,
		help="Confirm download before saving (default: False)"
	)
	
	# Optional argument for the number of results
	parser.add_argument("-r", "--results", dest="results", type=int, default=0, # treat 0 as infinite
		help="Number of results to retrieve (default: 0, for infinite)"
	)

	# Optional argument for testing
	parser.add_argument("-t", "--test", dest="test", action="store_true", default=False,
		help="Enable test mode (default: False)"
	)

	# Optional argument for verbosity
	parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False,
		help="Verbosity level (default: False)"
	)

	args = parser.parse_args()

	args.download_path = Path(args.download_path).expanduser()
	if not args.download_path.exists():
		args.download_path.mkdir(parents=True, exist_ok=True)
	elif not args.download_path.is_dir():
		console.print(f"[red]Error: '{args.download_path}' is not a valid directory.[/red]")
		sys.exit(1)

	if args.date:
		args.date = is_date(args.date, return_datetime=True)
		if args.verbose:
			console.print(f"Searching for comics released on/since {args.date.strftime('%d-%B-%Y')}")
	
	if args.min and args.max:
		if args.max < args.min:
			console.print("[red]You must specify -max argument as a number greater than -min argument.[/red]")
			sys.exit(1)
	if args.max and not args.min:
		args.min = 0  # give the search a place to start

	return args


def is_date(date, return_datetime=False) -> [bool, datetime]:  
	"""
	date (str) - date to check if valid
	return_datetime (bool or str) - if True, returns True/False if date is valid
		if str is passed, returns datetime/strftime of the date in the requested string format (ie "%d-%m-%Y" etc)
	the function returns (boolean or datetime object) depending on return_datetime argument
	"""
	if not isinstance(return_datetime, str):
		if not isinstance(return_datetime, bool):
			raise TypeError("Argument 'return_datetime' must be boolean, or a datetime formatting (ie '%d-%m-%Y' etc)")
	if isinstance(return_datetime, str):
		try:
			datetime.today().strftime(return_datetime)
		except:
			raise TypeError("Argument 'return_datetime': invalid format string (ie should be '%d-%m-%Y' etc)")
	
	for char in ["/", ".", "-", "\\"]:
		date = date.replace(char, "-")
	
	if "-" in date:
		date_split = date.split("-")
	elif " " in date:
		date_split = date.split()
	date_split_original = date_split[:]

	if len(date_split) != 3:
		return False

	date = {}
	# determine year
	for i, part in enumerate(date_split):
		# if its larger than 32 
		if part.isdigit() and 31 < int(part) < 9999:
			date["year"] = int(date_split.pop(i))
			break
	
	# determine day/month if year known
	for i, part in enumerate(date_split):
		# if all digits are the same, that makes life easy
		if all([num == date_split[0] for num in date_split]):
			date["day"] = int(date_split.pop())
			date["month"] = int(date_split.pop())
			if not date.get("year"):
				date["year"] = int(date_split.pop())
			break
		
		if date.get("year"):
			# if year is known, and only one of the remaining numbers is between 13-31
			if part.isdigit() and 32 > int(part) > 12 and len([num for num in date_split if num.isdigit() and 32 > int(num) > 12]) == 1: 
				date["day"] = int(date_split.pop(i))
				date["month"] = int(date_split.pop())
				break
			# if year is known and both numbers are the same < 13, take month as the second given value, day as the first
			if len([num for num in date_split if num.isdigit() and int(num) < 13]) == 2:
				date["day"] = int(date_split.pop())
				date["month"] = int(date_split.pop())
				break

		# if year is not known, and at least two highest numbers are between 13-31, take the second index as month
		if not date.get("year"):
			if len([num for num in date_split if num.isdigit() and 32 > int(num) > 12]) >= 2:
				date["month"] = int(date_split.pop(1))
				date["year"] = int(date_split.pop(date_split.index(max(date_split)))) # next highest as year
				date["day"] = int(date_split.pop())
				break

	# determine month
	months = {
		"january": 1,
		"february": 2,
		"march": 3,
		"april": 4,
		"june": 6,
		"july": 7,
		"august": 8,
		"september": 9,
		"october": 10, 
		"november": 11,
		"december": 12,
		"jan": 1,
		"feb": 2,
		"mar": 3,
		"apr": 4,
		"may": 5,
		"jun": 6,
		"jul": 7,
		"aug": 8,
		"sep": 9,
		"oct": 10,
		"nov": 11,
		"dec": 12
	}
	for i, part in enumerate(date_split):
		# if we already determined the month, skip this
		if date.get("month"):
			break
		# if its a string and matches a month name
		if not part.isdigit() and months.get(part.lower()):
			date_split.pop(i)
			date["month"] = months.get(part.lower())
			continue  # don't break, in case there are 2 strings we'll fail later
		# if year and day are known, it is the remaining item
		if date.get("year") and date.get("day") and date_split:
			date["month"] = int(date_split.pop(i))
			break
	
	# revisit the day now we may know year and month
	for i, part in enumerate(date_split):
		#if year and month are known, it is the remaining item
		if date.get("year") and date.get("month") and date_split:
			date["month"] = int(date_split.pop(i))
			break
	
	# revisit the year now we may know month and day
	for i, part in enumerate(date_split):
		if date.get("month") and date.get("day") and part.isdigit():
			date["year"] = int(date_split.pop(i))
	
	# check that years are formatted correctly
	if len(date_split_original[2]) == 2:
		date_split_original[2] = "20" + date_split_original[2]  # assume 21st century
	if date.get("year") and len(str(date["year"])) == 2:
		date["year"] = int(f"20{date['year']}")

	# try to make a datetime object in australian formatting if we haven't already
	# been able to work out the date
	try:
		dt = datetime(
			date.get("year") or int(date_split_original[2]),
			date.get("month") or int(date_split_original[1]),
			date.get("day") or int(date_split_original[0])
		)
		if return_datetime is True:
			return dt
		elif isinstance(return_datetime, str):
			return dt.strftime(return_datetime)
		return True
	except Exception as err:
		return False


def get_query_string(i, query, _min=None, _max=None):
	if _min or _max:
		return f"{query} {_min + i}"
	return query


def main():
	args = parse_arguments()

	try:
		i = -1
		failed_to_find_comics = 0
		overall_summary = Query("", 0, False, args.download_path)
		
		while True: # loop used to continue searching for issues until one cannot be found, if args.newer set
			i += 1
			if args.max and (args.min + i) > args.max:
				break

			query_string = get_query_string(i, args.query, _min=args.min, _max=args.max)
			query = Query(query_string, args.results, args.verbose, args.download_path)
			
			console.print()
			with console.status(f"Querying getcomics.info for search results for '{query_string}'...") as status:
				query.find_pages(date=args.date)
			with console.status(f"Querying {len(query.page_links):,} search results for download links...") as status:
				query.get_download_links()

			if (args.test or args.verbose) and query.page_links:
				tree = Tree(f"[bold blue]Search Results for '{query_string}'[/bold blue]")
				for page_index, (page_url, page_title) in enumerate(query.page_links.items(), start=1):
					page_node = tree.add(f"[bold]{page_index}) {page_title}[/bold]\n[dim]{page_url}[/dim]")
					links_found = False
					for comic_url, metadata in query.comic_links.items():
						# Associate links with the page they originated from
						if metadata.get("origin_url") == page_url:
							provider = metadata.get("provider", "UNKNOWN")
							link_type = metadata.get("type", "DIRECT")
							item_title = metadata.get("title", page_title)
							
							# If the item title is different from page title, show it (for collection pages)
							display_text = f"{provider}: {comic_url}"
							if item_title != page_title:
								display_text = f"[bold white]{item_title}[/bold white] ({display_text})"
								
							color = "green" if link_type != "MANUAL" else "yellow"
							page_node.add(f"[{color}]{display_text}[/{color}]")
							links_found = True
					if not links_found:
						page_node.add("[red]No download links found.[/red]")
				
				console.print(Panel(tree, expand=False))
			
			if not query.page_links:
				console.print(f"[yellow]No results found for query '{query_string}'[/yellow]")
			elif not args.test:
				query.download_comics(args.prompt)
				overall_summary.successful_downloads.extend(query.successful_downloads)
				overall_summary.skipped_downloads.extend(query.skipped_downloads)
				overall_summary.unsupported_mirrors.extend(query.unsupported_mirrors)

			if args.min or args.max:
				# break if it is (3 or -results) times in a row that we've failed to find comics
				if not query.page_links:
					failed_to_find_comics += 1
					if failed_to_find_comics == max(args.results, 3):
						break
				else:
					failed_to_find_comics = 0
			else:
				break
				
		if not args.test:
			overall_summary.print_summary()

	except KeyboardInterrupt:
		console.print("\n[yellow]Operation cancelled by user.[/yellow]")
		os._exit(1)


if __name__ == "__main__":
	main()
