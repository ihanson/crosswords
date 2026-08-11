from dataclasses import dataclass
from typing import Literal, Optional

from crossword import FormattableText, GridCoord, SquareSide
from image import Color

@dataclass
class Puzzle:
	grid: dict[GridCoord, Cell]
	words: list[Word]
	clues: list[ClueList]
	title: Optional[FormattableText] = None
	creator: Optional[FormattableText] = None
	copyright: Optional[FormattableText] = None
	note: Optional[Note] = None
	completion_message: Optional[FormattableText] = None
	puzzle_type: Literal["crossword"] | Literal["acrostic"] = "crossword"

	def width(self) -> int:
		return max(coord.col for coord in self.grid.keys()) + 1

	def height(self) -> int:
		return max(coord.row for coord in self.grid.keys()) + 1

@dataclass
class Note:
	text: FormattableText
	show_on_open: bool = False

@dataclass
class Cell:
	pass

@dataclass
class EntryCell(Cell):
	solution: Optional[str] = None
	number: Optional[str] = None
	top_right_number: Optional[str] = None
	is_circled: bool = False
	color: Optional[Color] = None
	bars: frozenset[SquareSide] = frozenset()

@dataclass
class ClueCell(Cell):
	text: str

@dataclass
class BlockCell(Cell):
	pass

@dataclass
class VoidCell(Cell):
	pass

@dataclass
class Word:
	word_id: str
	cells: list[GridCoord]

@dataclass
class ClueList:
	title: str
	clues: list[Clue]

@dataclass
class Clue:
	text: FormattableText
	word_id: str
	number: Optional[str] = None