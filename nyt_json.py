from typing import NotRequired, TypedDict, Any

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

class Cell(TypedDict):
	answer: str
	clues: list[int]
	label: str
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
	relatedContent: RelatedContent