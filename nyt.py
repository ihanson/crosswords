import datetime
from typing import Any, Literal, NotRequired, TypedDict
import requests
import babel
import babel.dates
import crossword
from lib import Color, FormattableText
import crossword_nexus

WHITE_SQUARE = 1
CIRCLED_SQUARE = 2
SHADED_SQUARE = 3
CIRCLED_SHADED_SQUARE = 4

class PuzzleResult(TypedDict):
	author: str
	editor: str
	format_type: str
	print_date: str
	publish_type: str
	puzzle_id: int
	title: str
	version: int
	percent_filled: int
	solved: bool
	star: str

class PuzzleList(TypedDict):
	status: str
	results: list[PuzzleResult]

class MoreAnswers(TypedDict):
	valid: list[str]

class Cell(TypedDict):
	answer: NotRequired[str]
	moreAnswers: NotRequired[MoreAnswers]
	clues: list[int]
	label: NotRequired[str]
	type: int

class BlackCell(TypedDict):
	pass

class ClueList(TypedDict):
	name: str
	clues: list[int]

class ClueText(TypedDict):
	plain: str
	formatted: NotRequired[str]

class Clue(TypedDict):
	cells: list[int]
	direction: str
	label: str
	text: list[ClueText]

class Dimensions(TypedDict):
	height: int
	width: int

class PuzzleBody(TypedDict):
	board: str
	cells: list[Cell | BlackCell]
	clueLists: list[ClueList]
	clues: list[Clue]
	dimensions: Dimensions
	SVG: dict[str, Any]

class Note(TypedDict):
	text: str

class RelatedContent(TypedDict):
	text: str
	url: str

class Puzzle(TypedDict):
	body: list[PuzzleBody]
	constructors: list[str]
	copyright: str
	editor: str
	id: int
	lastUpdated: str
	publicationDate: str
	title: NotRequired[str]
	notes: NotRequired[list[Note]]
	relatedContent: RelatedContent

def puzzles_for_dates(
	start_date: datetime.date,
	end_date: datetime.date,
	format_type: str | None = None,
	publish_type: str | None = None,
	nyt_s: str | None = None
) -> list[PuzzleResult]:
	puzzles: PuzzleList = requests.get(
		"https://edge.games.nyti.nyt.net/svc/crosswords/v3/puzzles.json",
		params={
			"format_type": format_type,
			"publish_type": publish_type,
			"date_start": start_date.isoformat(),
			"date_end": end_date.isoformat()
		}, headers={
			"nyt-s": nyt_s
		} if nyt_s is not None else None
	).json()
	return puzzles["results"] or []

def cell_to_square(cell: Cell | BlackCell) -> crossword.Square:
	if "type" in cell:
		cell_type = cell["type"]
		is_shaded = cell_type == SHADED_SQUARE or cell_type == CIRCLED_SHADED_SQUARE
		is_circled = cell_type == CIRCLED_SQUARE or cell_type == CIRCLED_SHADED_SQUARE
		return crossword.WhiteSquare(
			answer=cell.get("answer"),
			color=Color(0xdc, 0xdc, 0xdc) if is_shaded else None,
			is_circled=is_circled
		)
	else:
		return crossword.BlackSquare()

def dict_to_clue(clue: Clue) -> FormattableText:
	return FormattableText(
		text=clue["text"][0]["plain"],
		html=clue["text"][0].get("formatted")
	)

def download_json(date: datetime.date, publish_type: str, nyt_s: str) -> Puzzle:
	url = f"https://www.nytimes.com/svc/crosswords/v6/puzzle/{publish_type}/{date.isoformat()}.json"
	result = requests.get(
		url,
		cookies={
			"NYT-S": nyt_s
		}
	)
	if result.status_code != 200:
		raise Exception(f"Request to {url} returned HTTP {result.status_code} error")
	return result.json()

def download_today() -> crossword.Puzzle:
	return download_puzzle(datetime.date.today(), "daily", token())

def download_puzzle(
	date: datetime.date,
	publish_type: Literal["daily"] | Literal["mini"] | Literal["midi"] | Literal["bonus"],
	nyt_s: str
) -> crossword.Puzzle:
	puzzle = download_json(date, publish_type, nyt_s)
	puzzle_dict = puzzle["body"][0]
	width = puzzle_dict["dimensions"]["width"]
	height = puzzle_dict["dimensions"]["height"]
	
	return crossword.Puzzle(
		grid=crossword.Grid([
			[cell_to_square(puzzle_dict["cells"][row * width + col]) for col in range(width)]
			for row in range(height)
		]),
		across_clues={
			int(puzzle_dict["clues"][i]["label"]): dict_to_clue(puzzle_dict["clues"][i])
			for i in puzzle_dict["clueLists"][0]["clues"]
		},
		down_clues={
			int(puzzle_dict["clues"][i]["label"]): dict_to_clue(puzzle_dict["clues"][i])
			for i in puzzle_dict["clueLists"][1]["clues"]
		},
		title=FormattableText(puzzle.get("title", "The Crossword")),
		author=FormattableText(", ".join(puzzle["constructors"])) if "constructors" in puzzle else None,
		copyright=FormattableText(
			babel.dates.format_date(
				datetime.date.fromisoformat(puzzle["publicationDate"]),
				"full",
				babel.Locale("en", "US")
			)
		),
		note=puzzle_note(puzzle)
	)

def puzzle_note(puzzle: Puzzle) -> FormattableText | None:
	if "notes" not in puzzle:
		return None
	notes = puzzle["notes"]
	match notes:
		case [note, *_]:
			return FormattableText(note["text"])
		case _:
			return None

def token() -> str:
	with open("nyt-s.txt", encoding="utf-8") as f:
		return f.read()

if __name__ == "__main__":
	crossword_nexus.open_puzzle(download_today())