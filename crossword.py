from typing import Optional

class Square(object):
	pass

class BlackSquare(Square):
	pass

class WhiteSquare(Square):
	def __init__(self, answer: Optional[str] = None, is_shaded = False, is_circled = False):
		self.__answer = answer
		self.__is_shaded = is_shaded
		self.__is_circled = is_circled

	@property
	def answer(self):
		return self.__answer

	@property
	def is_shaded(self):
		return self.__is_shaded

	@property
	def is_circled(self):
		return self.__is_circled

class Clue(object):
	def __init__(self, clue: str, is_special: bool = False):
		self.__clue = clue
		self.__is_special = is_special

	@property
	def clue(self):
		return self.__clue

	@property
	def is_special(self):
		return self.__is_special

class Grid(object):
	def __init__(self, squares: list[list[Square]]):
		if len(squares) == 0 or len(squares[0]) == 0:
			raise Exception("Empty grid")
		if any(len(row) != len(squares[0]) for row in squares):
			raise Exception("Ragged grid")
		self.__squares = squares

	def __getitem__(self, index: tuple[int, int]):
		(row, col) = index
		return self.__squares[row][col]
	
	@property
	def rows(self):
		return len(self.__squares)
	
	@property
	def cols(self):
		return len(self.__squares[0])

	def can_enter(self, row, col):
		return (
			0 <= row < self.rows
			and 0 <= col < self.cols
			and isinstance(self[row, col], WhiteSquare)
		)

	def is_across_start(self, row: int, col: int):
		return (
			self.can_enter(row, col)
			and not self.can_enter(row, col - 1)
			and self.can_enter(row, col + 1)
		)

	def is_down_start(self, row: int, col: int):
		return (
			self.can_enter(row, col)
			and not self.can_enter(row - 1, col)
			and self.can_enter(row + 1, col)
		)

class Puzzle(object):
	def __init__(
		self, grid: Grid, across: dict[int, Clue], down: dict[int, Clue],
		title: Optional[str] = None, author: Optional[str] = None,
		copyright: Optional[str] = None, note: Optional[str] = None
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