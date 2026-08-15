import json
from lzstring import LZString
from typing import Any, Literal, TypedDict
import webbrowser
import crossword
from lib import SquareSide
import acrostic
import jpz

def open_puzzle(puzzle: crossword.Puzzle | acrostic.Acrostic):
	webbrowser.open(puzzle_url(puzzle.to_jpz()))

def puzzle_url(puzzle: jpz.JPZPuzzle) -> str:
	return f"https://crosswordnexus.com/solve/#{
		LZString.compressToEncodedURIComponent(
			json.dumps(clear_nones(to_js_puzzle(puzzle)))
		)
	}"

class JSPuzzle(TypedDict):
	metadata: Metadata
	cells: list[BlockCell | LetterCell | ClueCell | VoidCell]
	words: list[Word]
	clues: list[ClueSet]

class Metadata(TypedDict):
	title: str | None
	author: str | None
	copyright: str | None
	description: str | None
	intro: str | None
	completion_message: str | None
	fakeclues: bool
	realwords: bool
	autofill: bool
	crossword_type: Literal["crossword"] | Literal["acrostic"]
	has_reveal: bool
	width: int
	height: int

class BlockCell(TypedDict):
	x: int
	y: int
	type: Literal["block"]
	is_void: Literal[False]
	clue: Literal[False]

class VoidCell(TypedDict):
	x: int
	y: int
	type: Literal["void"]
	is_void: Literal[True]
	clue: Literal[False]

LetterCell = TypedDict("LetterCell", {
	"x": int,
	"y": int,
	"solution": str | None,
	"number": str | None,
	"top_right_number": str | None,
	"is_void": Literal[False],
	"clue": Literal[False],
	"top-bar": bool | None,
	"bottom-bar": bool | None,
	"left-bar": bool | None,
	"right-bar": bool | None,
	"background-color": str | None,
	"background-shape": str | None
})

ClueCell = TypedDict("ClueCell", {
	"x": int,
	"y": int,
	"type": Literal["clue"],
	"solution": str | None,
	"is_void": Literal[False],
	"clue": Literal[True],
	"letter": str | None
})

class Word(TypedDict):
	id: str
	cells: list[tuple[int, int]]

class ClueSet(TypedDict):
	title: str
	clue: list[Clue]

class Clue(TypedDict):
	text: str
	word: str
	number: str | None

def to_js_puzzle(puzzle: jpz.JPZPuzzle) -> JSPuzzle:
	metadata = Metadata(
		title=puzzle.title and str(puzzle.title.html),
		author=puzzle.creator and str(puzzle.creator.html),
		copyright=puzzle.copyright and str(puzzle.copyright.html),
		description=puzzle.note and str(puzzle.note.text.html),
		intro=(
			str(puzzle.note.text.html)
			if puzzle.note and puzzle.note.show_on_open
			else None
		),
		completion_message=puzzle.completion_message and str(puzzle.completion_message.html),
		fakeclues=False,
		realwords=False,
		autofill=False,
		crossword_type=puzzle.puzzle_type,
		has_reveal=True,
		width=puzzle.width(),
		height=puzzle.height()
	)
	cells = [
		(
			LetterCell({
				"x": coord.col,
				"y": coord.row,
				"solution": cell.solution,
				"number": cell.number,
				"top_right_number": cell.top_right_number,
				"is_void": False,
				"clue": False,
				"top-bar": (SquareSide.TOP in cell.bars) or None,
				"bottom-bar": (SquareSide.BOTTOM in cell.bars) or None,
				"left-bar": (SquareSide.LEFT in cell.bars) or None,
				"right-bar": (SquareSide.RIGHT in cell.bars) or None,
				"background-color": cell.color.hex() if cell.color else None,
				"background-shape": "circle" if cell.is_circled else None
			}) if isinstance(cell, jpz.EntryCell)
			else ClueCell({
				"x": coord.col,
				"y": coord.row,
				"type": "clue",
				"clue": True,
				"is_void": False,
				"solution": cell.text,
				"letter": cell.text
			}) if isinstance(cell, jpz.ClueCell)
			else BlockCell(
				x=coord.col,
				y=coord.row,
				type="block",
				is_void=False,
				clue=False
			) if isinstance(cell, jpz.BlockCell)
			else VoidCell(
				x=coord.col,
				y=coord.row,
				type="void",
				is_void=True,
				clue=False
			)
		)
		for (coord, cell) in puzzle.grid.items()
	]
	words = [
		Word(
			id=word.word_id,
			cells=[
				(coord.col, coord.row)
				for coord in word.cells
			]
		)
		for word in puzzle.words
	]
	clues = [
		ClueSet(
			title=clue_set.title,
			clue=[
				Clue(
					number=clue.number,
					text=str(clue.text.html),
					word=clue.word_id
				)
				for clue in clue_set.clues
			]
		)
		for clue_set in puzzle.clues
	]
	return JSPuzzle(
		metadata=metadata,
		cells=cells,
		words=words,
		clues=clues,
	)

def clear_nones(obj: Any) -> Any:
	if isinstance(obj, dict):
		return {
			key: clear_nones(value)
			for (key, value) in obj.items() # type: ignore
			if value is not None
		}
	elif isinstance(obj, list):
		return [
			clear_nones(value)
			for value in obj # type: ignore
			if value is not None
		]
	else:
		return obj