import argparse
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

from query import Query


def parse_arguments():
	"""
	Parse arguments, but exit early if an output directory doesn't resolve properly.
	"""

	parser = argparse.ArgumentParser(description="Search for and/or download content from getcomics.info")
	
	# Mandatory argument
	parser.add_argument("query", type=str, help="Search term for comics")

	# Optional argument for date
	parser.add_argument("-date", "--d", dest='date', type=str, default=None,
		help="Return results as new as this date (inclusive), eg: 2023-11-21 (optional)"
	)

	# Optional argument for download location
	parser.add_argument("-output", "--o", dest="download_path", type=str, default="./",
		help='Destination directory (default: "./")'
	)

	# Optional argument for newer issues
	parser.add_argument("-newer", "--n", dest="newer", type=int, default=False,
		help="Search for issues including newer ones, requires an integer in the search (default: False)"
	)

	# Optional argument for prompting before saving
	parser.add_argument("-prompt", "--p", dest="prompt", action="store_true", default=False,
		help="Confirm download before saving (default: False)"
	)
	
	# Optional argument for the number of results
	parser.add_argument("-results", "--r", dest="results", type=int, default=0, # treat 0 as infinite
		help="Number of results to retrieve (default: 0, for infinite)"
	)

	# Optional argument for testing
	parser.add_argument("-test", "--t", dest="test", action="store_true", default=False,
		help="Enable test mode (default: False)"
	)

	# Optional argument for verbosity
	parser.add_argument("-verbose", "--v", dest="verbose", action="store_true", default=False,
		help="Verbosity level (default: False)"
	)

	args = parser.parse_args()

	args.download_path = Path(args.download_path).expanduser()
	if not args.download_path.exists() or not args.download_path.is_dir():
		print(f"Please enter a valid output directory.")
		print(f"'{args.download_path}' does not exist or is not a valid directory.")
		sys.exit(1)

	if args.date:
		args.date = is_date(args.date, return_datetime=True)
		if args.verbose:
			print(f"Searching for comics released on/since {args.date.strftime('%d-%B-%Y')}")
	
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


def main():
	args = parse_arguments()
	console = Console()

	try:
		i = -1
		failed_to_find_comics = 0
		while True: # loop used to continue searching for issues until one cannot be found, if args.newer set
			if args.newer:
				i += 1
				query_string = f"{args.query} {args.newer + i}"
				query = Query(query_string, args.results, args.verbose, args.download_path)
			else:
				query_string = args.query
				query = Query(query_string, args.results, args.verbose, args.download_path)
			
			with console.status("Querying getcomics.info for search results...") as status:
				query.find_pages(date=args.date)
			with console.status(f"Querying {len(query.page_links):,} search results for download links...") as status:
				query.get_download_links()

			if args.test and query.page_links:
				console.print(Markdown(f"## {query_string}"))
				for page_index, (page_url, page_title) in enumerate(query.page_links.items(), start=1):
					print(f"\n{page_index}) {page_title}\nPage: {page_url}\nComic links on page:")
					for comic_url, comic_title in query.comic_links.items():
						if comic_title == page_title:
							print(f"  • {comic_url}")
			elif not query.page_links:
				print(f"No results found for query '{query_string}'")
			else:
				query.download_comics(args.prompt)

			if args.newer:
				# break if it is 3 or -results times in a row that we've failed to find comics
				if not query.comic_links:
					failed_to_find_comics += 1
					if failed_to_find_comics == max(3, args.results):
						break
				else:
					failed_to_find_comics = 0
			else:
				break
	except KeyboardInterrupt:
		sys.exit(1)


if __name__ == "__main__":
	main()




