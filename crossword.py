from dataclasses import dataclass
from typing import Generator, Iterator
import jpz
from lib import Color, FormattableText, GridCoord, SquareSide

@dataclass
class Square:
	pass

@dataclass
class BlackSquare(Square):
	pass

@dataclass
class WhiteSquare(Square):
	answer: str | None = None
	color: Color | None = None
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
			0 <= row < self.rows()
			and 0 <= col < self.cols()
		):
			return self.squares[row][col]
		return BlackSquare()
	
	def rows(self):
		return len(self.squares)
	
	def cols(self):
		return len(self.squares[0])
	
	def __iter__(self) -> Iterator[tuple[GridCoord, Square]]:
		for row in range(self.rows()):
			for col in range(self.cols()):
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

@dataclass
class Puzzle:
	grid: Grid
	across_clues: dict[int, FormattableText]
	down_clues: dict[int, FormattableText]
	title: FormattableText | None = None
	author: FormattableText | None = None
	copyright: FormattableText | None = None
	note: FormattableText | None = None
	show_note_on_open: bool = False
	completion_message: FormattableText | None = None

	def to_jpz(self) -> jpz.JPZPuzzle:
		grid: dict[GridCoord, jpz.Cell] = {}
		across_clues: list[jpz.Clue] = []
		down_clues: list[jpz.Clue] = []
		words: list[jpz.Word] = []
		word_count = 0
		clue_count = 0
		for (coord, xword_cell) in self.grid:
			is_across = self.grid.is_across_start(coord)
			is_down = self.grid.is_down_start(coord)
			number = (
				(clue_count := clue_count + 1)
				if is_across or is_down
				else None
			)
			cell = (
				jpz.EntryCell(
					solution=xword_cell.answer,
					number=str(number) if number is not None else None,
					is_circled=xword_cell.is_circled,
					color=xword_cell.color,
					bars=xword_cell.bars
				)
				if isinstance(xword_cell, WhiteSquare)
				else jpz.BlockCell()
			)
			grid[coord] = cell
			if number is not None:
				for (is_start, clue_dict, gen, clue_list) in [
					(is_across, self.across_clues, self.grid.across_word_cells, across_clues),
					(is_down, self.down_clues, self.grid.down_word_cells, down_clues)
				]:
					if is_start:
						word_id = str(word_count := word_count + 1)
						words.append(jpz.Word(
							word_id=word_id,
							cells=list(gen(coord))
						))
						clue_list.append(jpz.Clue(
							word_id=word_id,
							number=str(number),
							text=clue_dict[number]
						))
		return jpz.JPZPuzzle(
			title=self.title,
			creator=self.author,
			copyright=self.copyright,
			note=(
				jpz.Note(
					text=self.note,
					show_on_open=self.show_note_on_open
				)
				if self.note
				else None
			),
			completion_message=self.completion_message,
			grid=grid,
			words=words,
			clues=[
				jpz.ClueList(
					title="Across",
					clues=across_clues
				),
				jpz.ClueList(
					title="Down",
					clues=down_clues
				)
			]
		)