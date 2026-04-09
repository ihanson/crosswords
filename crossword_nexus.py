import json
from lzstring import LZString
from typing import Any, Literal, TypedDict, NotRequired
import webbrowser
import crossword

def open_puzzle(puzzle: crossword.Puzzle):
	webbrowser.open(puzzle_url(puzzle))

def puzzle_url(puzzle: crossword.Puzzle) -> str:
	return f"https://crosswordnexus.github.io/html5-crossword-solver/#{
		LZString.compressToEncodedURIComponent(
			json.dumps(clear_nones(to_js_puzzle(puzzle)))
		)
	}"

class JSPuzzle(TypedDict):
	metadata: Metadata
	cells: list[BlockCell | LetterCell]
	words: list[Word]
	clues: list[ClueSet]

class Metadata(TypedDict):
	title: str | None
	author: str | None
	copyright: str | None
	description: str | None
	intro: str | None
	fakeclues: bool
	realwords: bool
	autofill: bool
	crossword_type: Literal["crossword"]
	has_reveal: bool
	width: int
	height: int

class BlockCell(TypedDict):
	x: int
	y: int
	type: Literal["block"]
	is_void: bool
	clue: bool

LetterCell = TypedDict("LetterCell", {
	"x": int,
	"y": int,
	"solution": str | None,
	"number": str | None,
	"is_void": bool,
	"clue": bool,
	"top-bar": bool | None,
	"bottom-bar": bool | None,
	"left-bar": bool | None,
	"right-bar": bool | None,
	"background-color": str | None,
	"background-shape": str | None
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
	number: str

class X(TypedDict):
	a: NotRequired[str]

def to_js_puzzle(puzzle: crossword.Puzzle) -> JSPuzzle:
	next_cell_number = 1
	cells: list[BlockCell | LetterCell] = []
	words: list[Word] = []
	across_clues: list[Clue] = []
	down_clues: list[Clue] = []
	for ((row, col), cell) in puzzle.grid:
		if isinstance(cell, crossword.WhiteSquare):
			is_across = puzzle.grid.is_across_start(row, col)
			is_down = puzzle.grid.is_down_start(row, col)
			if is_across or is_down:
				number = next_cell_number
				next_cell_number += 1
				if is_across:
					word_id = str(len(words))
					words.append(Word(
						id=word_id,
						cells=[
							(word_col, row)
							for word_col in puzzle.grid.across_word_cols(row, col)
						]
					))
					across_clues.append(Clue(
						text=str(puzzle.across_clues[number].html),
						word=word_id,
						number=str(number)
					))
				if is_down:
					word_id = str(len(words))
					words.append(Word(
						id=word_id,
						cells=[
							(col, word_row)
							for word_row in puzzle.grid.down_word_rows(row, col)
						]
					))
					down_clues.append(Clue(
						text=str(puzzle.down_clues[number].html),
						word=word_id,
						number=str(number)
					))
			else:
				number = None
			cells.append(LetterCell({
				"x": col,
				"y": row,
				"solution": cell.answer,
				"number": str(number) if number is not None else None,
				"is_void": False,
				"clue": False,
				"top-bar": cell.has_bar(crossword.SquareSide.TOP) or None,
				"bottom-bar": cell.has_bar(crossword.SquareSide.BOTTOM) or None,
				"left-bar": cell.has_bar(crossword.SquareSide.LEFT) or None,
				"right-bar": cell.has_bar(crossword.SquareSide.RIGHT) or None,
				"background-color": cell.color.hex() if cell.color else None,
				"background-shape": "circle" if cell.is_circled else None
			}))
		else:
			cells.append(BlockCell(
				x=col,
				y=row,
				type="block",
				is_void=False,
				clue=False
			))
	return JSPuzzle(
		metadata=Metadata(
			title=puzzle.title and str(puzzle.title.html),
			author=puzzle.author and str(puzzle.author.html),
			copyright=puzzle.copyright and str(puzzle.copyright.html),
			description=puzzle.note and str(puzzle.note.html),
			intro=(
				str(puzzle.note.html)
				if puzzle.note and puzzle.show_note_on_open
				else None
			),
			fakeclues=False,
			realwords=False,
			autofill=False,
			crossword_type="crossword",
			has_reveal=True,
			width=puzzle.grid.cols,
			height=puzzle.grid.rows
		),
		cells=cells,
		words=words,
		clues=[
			ClueSet(title="Across", clue=across_clues),
			ClueSet(title="Down", clue=down_clues)
		]
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