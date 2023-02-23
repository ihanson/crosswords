import datetime
import requests
import crossword
import acrostic
import string
import re
import json
import base64
import urllib.parse
import os
import sys
import jpz

WHITE_SQUARE = 1
CIRCLED_SQUARE = 2
SHADED_SQUARE = 3
CIRCLED_SHADED_SQUARE = 4
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def puzzles_for_dates(
	start_date: datetime.date,
	end_date: datetime.date,
	format_type: str | None = None,
	publish_type: str | None = None,
	nyt_s: str | None = None
) -> list:
	return requests.get(
		"https://edge.games.nyti.nyt.net/svc/crosswords/v3/puzzles.json",
		params={
			"format_type": format_type,
			"publish_type": publish_type,
			"date_start": start_date.isoformat(),
			"date_end": end_date.isoformat()
		}, headers={
			"nyt-s": nyt_s
		} if nyt_s is not None else None
	).json()["results"] or []

def dict_to_square(obj: dict) -> crossword.Square:
	if "type" in obj:
		cell_type = obj["type"]
		return crossword.WhiteSquare(
			answer=obj["answer"],
			is_shaded=cell_type == SHADED_SQUARE or cell_type == CIRCLED_SHADED_SQUARE,
			is_circled=cell_type == CIRCLED_SQUARE or cell_type == CIRCLED_SHADED_SQUARE
		)
	else:
		return crossword.BlackSquare()

def dict_to_clue(obj: dict) -> crossword.Clue:
	return crossword.Clue(
		obj["text"][0]["plain"],
		obj["text"][0].get("formatted")
	)

def format_date(date: datetime.date):
	return f"{date.strftime('%A, %B')} {date.day}, {date.year}"

def download_puzzle(date: datetime.date, publish_type: str, nyt_s: str) -> crossword.Puzzle:
	obj = requests.get(
		f"https://www.nytimes.com/svc/crosswords/v6/puzzle/{publish_type}/{date.isoformat()}.json",
		cookies={
			"NYT-S": nyt_s
		}
	).json()
	puzzle_dict = obj["body"][0]
	width = puzzle_dict["dimensions"]["width"]
	height = puzzle_dict["dimensions"]["height"]
	
	return crossword.Puzzle(
		grid=crossword.Grid([
			[dict_to_square(puzzle_dict["cells"][row * width + col]) for col in range(width)]
			for row in range(height)
		]),
		across={
			int(puzzle_dict["clues"][i]["label"]): dict_to_clue(puzzle_dict["clues"][i])
			for i in puzzle_dict["clueLists"][0]["clues"]
		},
		down={
			int(puzzle_dict["clues"][i]["label"]): dict_to_clue(puzzle_dict["clues"][i])
			for i in puzzle_dict["clueLists"][1]["clues"]
		},
		title=obj.get("title"),
		author=", ".join(obj["constructors"]) if "constructors" in obj else None,
		copyright=format_date(datetime.date.fromisoformat(obj["publicationDate"])),
		note=obj["notes"][0]["text"] if "notes" in obj else None
	)

def download_acrostic(date: datetime.date, nyt_s: str) -> acrostic.Acrostic:
	html_data = requests.get(
		f"https://www.nytimes.com/puzzles/acrostic/{date.year:0>4}/{date.month:0>2}/{date.day:0>2}",
		cookies={
			"NYT-S": nyt_s
		}
	).text
	b64_data = json.loads(re.search(r"window\.gameData\s+=\s+(\".*?\")", html_data)[1])
	game_data = json.loads(urllib.parse.unquote(base64.b64decode(b64_data).decode("ascii")))
	puzzle_data = game_data["puzzle_data"].split("\n")
	letter_line = puzzle_data[0]
	length = len(letter_line) // 3
	letters = list(zip(
		letter_line[:length],
		letter_line[length:length * 2],
		letter_line[length * 2:]
	))
	clues = puzzle_data[1].strip("|").split("|")
	return acrostic.Acrostic(
		squares=[
			acrostic.LetterSquare(
				char,
				ord(clue_index) - 65,
				ord(word_index) - 65
			) if char in string.ascii_uppercase
			else acrostic.PunctuationSquare(char)
			for (char, clue_index, word_index) in letters
		],
		clues=clues,
		quote_text=puzzle_data[3],
		quote_author=puzzle_data[4],
		quote_work=puzzle_data[5],
		title=game_data["puzzle_meta"]["title"],
		author=game_data["puzzle_meta"]["author"],
		copyright=game_data["puzzle_meta"]["displayDate"]
	)

def pdf_data(date: datetime.date, publish_type: str, answer: bool, nyt_s: str) -> bytes:
	date_str = MONTHS[date.month - 1] + date.strftime("%d%y")
	publish_ext = ".2" if publish_type == "Variety" else ".3" if publish_type == "Assorted" else ""
	answer_ext = ".ans" if answer else ""
	url = f"https://www.nytimes.com/svc/crosswords/v2/puzzle/print/{date_str}{publish_ext}{answer_ext}.pdf"
	response = requests.get(url, cookies = {
		"nyt-s": nyt_s
	})
	if response.status_code != 200:
		raise Exception(f"Could not download {url}")
	return response.content

def safe_filename(name: str) -> str:
	return re.sub(r"[^\w. -]", "_", name.strip())

def download_puzzles(destination: str, start_year: int, end_year: int, nyt_s: str):
	for year in range(start_year, end_year + 1):
		year_start = datetime.date(year, 1, 1)
		year_end = datetime.date(year, 12, 31)
		puzzles = (
			puzzles_for_dates(year_start, year_end, publish_type="bonus", nyt_s=nyt_s)
			+ puzzles_for_dates(year_start, year_end, format_type="acrostic", nyt_s=nyt_s)
			+ puzzles_for_dates(year_start, year_end, format_type="pdf,normal,diagramless", publish_type="variety,assorted", nyt_s=nyt_s)
		)
		for puzzle in puzzles:
			print_date = datetime.date.fromisoformat(puzzle["print_date"])
			format_type = puzzle["format_type"]
			publish_type = puzzle["publish_type"]
			title = puzzle["title"]
			is_pdf = format_type == "PDF" or format_type == "Diagramless"
			path = os.path.join(
				destination,
				"PDF" if is_pdf else "Solved" if puzzle["solved"] else "Unsolved",
				"Bonus" if publish_type == "Bonus" else safe_filename(title),
				f"{print_date.year}"
			)
			try:
				os.makedirs(path, exist_ok=True)
				if format_type == "Normal":
					jpz.save_crossword_jpz(
						download_puzzle(print_date, publish_type.lower(), nyt_s),
						os.path.join(path, f"{print_date.isoformat()} {safe_filename(title)}.jpz")
					)
				elif format_type == "PDF":
					with open(os.path.join(path, f"{print_date.isoformat()} {safe_filename(title)}.pdf"), "wb") as f:
						f.write(pdf_data(print_date, publish_type, False, nyt_s))
					try:
						answer_data = pdf_data(print_date, publish_type, True, nyt_s)
						with open(os.path.join(path, f"{print_date.isoformat()} {safe_filename(title)} Answer.pdf"), "wb") as f:
							f.write(answer_data)
					except: pass
				elif format_type == "Acrostic":
					jpz.save_acrostic_jpz(
						download_acrostic(print_date, nyt_s),
						os.path.join(path, f"{print_date.isoformat()} {safe_filename(title)}.jpz")
					)
			except Exception as e:
				sys.stderr.write(f"Error downloading puzzle {title} for {print_date.isoformat()}: {e}\n")

def token() -> str:
	with open("nyt-s.txt", encoding="utf-8") as f:
		return f.read()

if __name__ == "__main__":
	download_puzzles("puzzles\\New York Times", 1997, 2023, token())