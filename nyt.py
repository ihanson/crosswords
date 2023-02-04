import datetime
import requests
import crossword
import image
import re
import json
import base64
import urllib.parse
import jpz

WHITE_SQUARE = 1
CIRCLED_SQUARE = 2
SHADED_SQUARE = 3
CIRCLED_SHADED_SQUARE = 4

def puzzles_for_dates(
	start_date: datetime.date,
	end_date: datetime.date,
	format_type: str | None = None,
	puzzle_type: str | None = None,
	nyt_s: str | None = None
) -> dict:
	return requests.get(
		"https://edge.games.nyti.nyt.net/svc/crosswords/v3/puzzles.json",
		params={
			"format_type": format_type,
			"publish_type": puzzle_type,
			"date_start": start_date.isoformat(),
			"date_end": end_date.isoformat()
		}, headers={
			"nyt-s": nyt_s
		} if nyt_s is not None else None
	).json()

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

def puzzle(date: datetime.date, puzzle_type: str, nyt_s: str) -> crossword.Puzzle:
	obj = requests.get(
		f"https://www.nytimes.com/svc/crosswords/v6/puzzle/{puzzle_type}/{date.isoformat()}.json",
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
		author=obj["constructors"][0] if "constructors" in obj else None,
		copyright=obj.get("copyright"),
		note=obj["notes"][0]["text"] if "notes" in obj else None
	)

def acrostic_data(date: datetime.date, nyt_s: str) -> dict:
	html_data = requests.get(
		f"https://www.nytimes.com/puzzles/acrostic/{date.year:0>4}/{date.month:0>2}/{date.day:0>2}",
		cookies={
			"NYT-S": nyt_s
		}
	).text
	b64_data = json.loads(re.search(r"window\.gameData\s+=\s+(\".*?\")", html_data)[1])
	json_data = urllib.parse.unquote(base64.b64decode(b64_data).decode("ascii"))
	return json.loads(json_data)

if __name__ == "__main__":
	with open("nyt-s.txt", encoding="utf-8") as f:
		nyt_s = f.read()
	p = puzzle(datetime.date(2022, 7, 17), "daily", nyt_s)
	image.draw_grid(p.grid, "puzzles\\daily.png")
	jpz.save_jpz(p, "puzzles\\daily.jpz")
