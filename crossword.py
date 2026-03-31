from enum import Enum
from typing import Generator

class Square(object):
	pass

class BlackSquare(Square):
	pass

class SquareSide(Enum):
	TOP = 0
	RIGHT = 1
	BOTTOM = 2
	LEFT = 3

class WhiteSquare(Square):
	def __init__(
			self,
			answer: str | None = None,
			is_shaded: bool = False,
			is_circled: bool = False,
			bars: frozenset[SquareSide] = frozenset()
		):
		self.__answer = answer
		self.__is_shaded = is_shaded
		self.__is_circled = is_circled
		self.__bars = frozenset(bars)

	@property
	def answer(self):
		return self.__answer

	@property
	def is_shaded(self):
		return self.__is_shaded

	@property
	def is_circled(self):
		return self.__is_circled
	
	def has_bar(self, bar: SquareSide):
		return bar in self.__bars

class Clue(object):
	def __init__(self, clue: str, clue_html: str | None = None):
		self.__clue = clue
		self.__clue_html = clue_html

	@property
	def clue(self):
		return self.__clue

	@property
	def clue_html(self):
		return self.__clue_html

class Grid(object):
	def __init__(self, squares: list[list[Square]]):
		if len(squares) == 0 or len(squares[0]) == 0:
			raise Exception("Empty grid")
		if any(len(row) != len(squares[0]) for row in squares):
			raise Exception("Ragged grid")
		self.__squares = squares

	def __getitem__(self, index: tuple[int, int]):
		(row, col) = index
		if (
			0 <= row < self.rows
			and 0 <= col < self.cols
		):
			return self.__squares[row][col]
		return BlackSquare()
	
	@property
	def rows(self):
		return len(self.__squares)
	
	@property
	def cols(self):
		return len(self.__squares[0])
	
	def word_continues_right(self, row: int, col: int) -> bool:
		square1 = self[row, col]
		square2 = self[row, col + 1]
		return (
			isinstance(square1, WhiteSquare)
			and isinstance(square2, WhiteSquare)
			and not square1.has_bar(SquareSide.RIGHT)
			and not square2.has_bar(SquareSide.LEFT)
		)
	
	def word_continues_down(self, row: int, col: int) -> bool:
		square1 = self[row, col]
		square2 = self[row + 1, col]
		return (
			isinstance(square1, WhiteSquare)
			and isinstance(square2, WhiteSquare)
			and not square1.has_bar(SquareSide.BOTTOM)
			and not square2.has_bar(SquareSide.TOP)
		)

	def is_across_start(self, row: int, col: int):
		return (
			not self.word_continues_right(row, col - 1)
			and self.word_continues_right(row, col)
		)

	def is_down_start(self, row: int, col: int):
		return (
			not self.word_continues_down(row - 1, col)
			and self.word_continues_down(row, col)
		)
	
	def across_word_cols(self, row: int, col: int) -> Generator[int]:
		if self.is_across_start(row, col):
			yield col
		while self.word_continues_right(row, col):
			col += 1
			yield col
	
	def down_word_rows(self, row: int, col: int) -> Generator[int]:
		if self.is_down_start(row, col):
			yield row
		while self.word_continues_down(row, col):
			row += 1
			yield row
		

class Puzzle(object):
	def __init__(
		self, grid: Grid, across: dict[int, Clue], down: dict[int, Clue],
		title: str | None = None, author: str | None = None,
		copyright: str | None = None, note: str | None = None
	):
		self.__grid = grid
		self.__across = across
		self.__down = down
		self.__title = title
		self.__author = author
		self.__copyright = copyright
		self.__note = note

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
	def across_clues(self):
		return self.__across
	
	@property
	def down_clues(self):
		return self.__down