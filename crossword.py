from dataclasses import dataclass
import string.templatelib
import copy
from enum import Enum
from typing import Generator, Iterator, NamedTuple
from bs4 import BeautifulSoup
import image

class SquareSide(Enum):
	TOP = 0
	RIGHT = 1
	BOTTOM = 2
	LEFT = 3

@dataclass
class Square:
	pass

@dataclass
class BlackSquare(Square):
	pass

@dataclass
class WhiteSquare(Square):
	answer: str | None = None
	color: image.Color | None = None
	is_circled: bool = False
	bars: frozenset[SquareSide] = frozenset()

@dataclass
class Grid:
	squares: list[list[Square]]
	def __post_init__(self):
		if len(self.squares) == 0 or len(self.squares[0]) == 0:
			raise Exception("Empty grid")
		if any(
			len(row) != len(self.squares[0])
			for row in self.squares
		):
			raise Exception("Ragged grid")

	def __getitem__(self, index: GridCoord) -> Square:
		(row, col) = index
		if (
			0 <= row < self.rows
			and 0 <= col < self.cols
		):
			return self.squares[row][col]
		return BlackSquare()
	
	@property
	def rows(self):
		return len(self.squares)
	
	@property
	def cols(self):
		return len(self.squares[0])
	
	def __iter__(self) -> Iterator[tuple[GridCoord, Square]]:
		for row in range(self.rows):
			for col in range(self.cols):
				coord = GridCoord(row, col)
				yield (coord, self[coord])

	def word_continues_right(self, coord: GridCoord) -> bool:
		square1 = self[coord]
		square2 = self[coord.right()]
		return (
			isinstance(square1, WhiteSquare)
			and isinstance(square2, WhiteSquare)
			and SquareSide.RIGHT not in square1.bars
			and SquareSide.LEFT not in square2.bars
		)
	
	def word_continues_down(self, coord: GridCoord) -> bool:
		square1 = self[coord]
		square2 = self[coord.down()]
		return (
			isinstance(square1, WhiteSquare)
			and isinstance(square2, WhiteSquare)
			and SquareSide.BOTTOM not in square1.bars
			and SquareSide.TOP not in square2.bars
		)

	def is_across_start(self, coord: GridCoord):
		return (
			not self.word_continues_right(coord.left())
			and self.word_continues_right(coord)
		)

	def is_down_start(self, coord: GridCoord):
		return (
			not self.word_continues_down(coord.up())
			and self.word_continues_down(coord)
		)
	
	def across_word_cells(self, coord: GridCoord) -> Generator[GridCoord]:
		if not self.is_across_start(coord):
			return
		yield coord
		while self.word_continues_right(coord):
			yield (coord := coord.right())
	
	def down_word_cells(self, coord: GridCoord) -> Generator[GridCoord]:
		if not self.is_down_start(coord):
			return
		yield coord
		while self.word_continues_down(coord):
			yield (coord := coord.down())

class Puzzle(object):
	def __init__(
		self,
		grid: Grid,
		across: dict[int, FormattableText],
		down: dict[int, FormattableText],
		title: FormattableText | None = None,
		author: FormattableText | None = None,
		copyright: FormattableText | None = None,
		note: FormattableText | None = None,
		show_note_on_open: bool = False
	):
		self.__grid = grid
		self.__across = across
		self.__down = down
		self.__title = title
		self.__author = author
		self.__copyright = copyright
		self.__note = note
		self.__show_note_on_open = show_note_on_open

	@property
	def grid(self):
		return self.__grid
	
	@property
	def title(self):
		return self.__title

	@property
	def author(self):
		return self.__author

	@property
	def copyright(self):
		return self.__copyright

	@property
	def note(self):
		return self.__note
	
	@property
	def show_note_on_open(self):
		return self.__show_note_on_open
	
	@property
	def across_clues(self):
		return self.__across
	
	@property
	def down_clues(self):
		return self.__down

class FormattableText(object):
	def __init__(self, text: str | None = None, html: BeautifulSoup | str | None = None):
		html = BeautifulSoup(html, "html.parser") if isinstance(html, str) else html
		if text is not None and html is None:
			self.__text = text
			self.__html = BeautifulSoup()
			for (i, line) in enumerate(text.split("\n")):
				if i > 0:
					self.__html.append(self.__html.new_tag("br"))
				self.__html.append(line)
		elif text is None and html is not None:
			self.__html = html
			self.__text = self.__html.getText()
		elif text is not None and html is not None:
			self.__html = html
			self.__text = text
		else:
			raise ValueError("Expected one non-None value")

	def __repr__(self) -> str:
		return f"FormattableText({self.text!r})"

	@property
	def html(self) -> BeautifulSoup:
		return self.__html

	@property
	def text(self) -> str:
		return self.__text

	@staticmethod
	def from_template(template: string.templatelib.Template) -> FormattableText:
		soup = BeautifulSoup()
		text = ""
		for item in template:
			if isinstance(item, str):
				soup.append(item)
				text += item
			else:
				value = item.value
				if not isinstance(value, FormattableText):
					raise TypeError(f"Interpolated value {value} is not a FormattableText object")
				soup.append(copy.copy(value.html))
				text += value.text
		return FormattableText(text, soup)

class GridCoord(NamedTuple):
	row: int
	col: int

	def up(self):
		return GridCoord(self.row - 1, self.col)

	def down(self):
		return GridCoord(self.row + 1, self.col)

	def left(self):
		return GridCoord(self.row, self.col - 1)

	def right(self):
		return GridCoord(self.row, self.col + 1)