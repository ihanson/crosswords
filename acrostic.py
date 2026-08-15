from dataclasses import dataclass
import string
from typing import Generator, Sequence
from lib import FormattableText, GridCoord
import jpz

@dataclass
class AcrosticSquare:
	pass

@dataclass
class PunctuationSquare(AcrosticSquare):
	punctuation: str

@dataclass
class LetterSquare(AcrosticSquare):
	answer: str
	clue_index: int
	clue_word_index: int

@dataclass
class Acrostic:
	squares: Sequence[AcrosticSquare]
	clues: Sequence[FormattableText]
	title: FormattableText
	author: FormattableText
	copyright: FormattableText
	quote_text: FormattableText
	quote_author: FormattableText | None = None
	quote_work: FormattableText | None = None

	def to_jpz(
		self,
		num_cols: int = 3,
		min_width: int = 30
	) -> jpz.JPZPuzzle:
		quote = FormattableText.from_template(
			t"{self.quote_text}\n\n\u2014 {self.quote_author}, {self.quote_work}" if self.quote_author and self.quote_work
			else t"{self.quote_text}\n\n\u2014 {self.quote_work}" if self.quote_work
			else t"{self.quote_text}\n\n\u2014 {self.quote_author}" if self.quote_author
			else t"{self.quote_text}"
		)
		col_width = max(
			square.clue_word_index + 1
			for square in self.squares
			if isinstance(square, LetterSquare
		)) + 1
		width = max((col_width + 1) * num_cols - 1, min_width)
		quote_height = (len(self.squares) - 1) // width + 1
		num_clues = len(self.clues)
		clues_height = (num_clues // num_cols) + (1 if num_clues % num_cols > 0 else 0)
		cell_number = 0
		word_id = 0
		grid: dict[GridCoord, jpz.Cell] = {}
		rev: dict[tuple[int, int], tuple[str, int]] = {}
		words: list[jpz.Word] = []

		quote_word: list[GridCoord] = []
		for coord in (
			GridCoord(row, col)
			for row in range(quote_height)
			for col in range(width)
		):
			clue_index = coord.row * width + coord.col
			square = (
				self.squares[clue_index] if clue_index < len(self.squares)
				else PunctuationSquare("")
			)
			if isinstance(square, LetterSquare):
				grid[coord] = jpz.EntryCell(
					solution=square.answer,
					number=str(cell_number := cell_number + 1),
					top_right_number=string.ascii_uppercase[square.clue_index]
				)
				rev[square.clue_index, square.clue_word_index] = (square.answer, cell_number)
				quote_word.append(coord)
			elif isinstance(square, PunctuationSquare):
				grid[coord] = (
					jpz.ClueCell(
						text=square.punctuation
					) if len(square.punctuation.strip()) > 0
					else jpz.BlockCell()
				)
		attrib_row = quote_height + 1
		first_clue_row = attrib_row + 2
		quote_word_id = str(word_id := word_id + 1)
		words.append(jpz.Word(
			word_id=quote_word_id,
			cells=quote_word
		))

		attrib_word: list[GridCoord] = []
		for clue_index in range(len(self.clues)):
			(first_letter, first_letter_index) = rev[clue_index, 0]
			coord = GridCoord(attrib_row, clue_index)
			grid[coord] = jpz.EntryCell(
				solution=first_letter,
				number=str(first_letter_index)
			)
			attrib_word.append(coord)
		attrib_word_id = str(word_id := word_id + 1)
		words.append(jpz.Word(
			word_id=attrib_word_id,
			cells=attrib_word
		))

		clues: list[jpz.Clue] = []
		for (clue_index, clue) in enumerate(self.clues):
			clue_number = string.ascii_uppercase[clue_index]
			clue_word_id = str(word_id := word_id + 1)
			label_coord = GridCoord(
				col=(col_width + 1) * (clue_index // clues_height),
				row=first_clue_row + (clue_index % clues_height)
			)
			grid[label_coord] = jpz.ClueCell(clue_number)
			clues.append(jpz.Clue(
				number=clue_number,
				text=clue,
				word_id=clue_word_id
			))

			clue_word: list[GridCoord] = []
			for (letter_index, (answer, number)) in clue_letters(rev, clue_index):
				coord = GridCoord(
					row=label_coord.row,
					col=label_coord.col + 1 + letter_index
				)
				clue_word.append(coord)
				grid[coord] = jpz.EntryCell(
					number=str(number),
					solution=answer
				)
			words.append(jpz.Word(
				word_id=clue_word_id,
				cells=clue_word
			))
		clues.append(jpz.Clue(
			word_id=quote_word_id,
			text=FormattableText(html="<i>[Quote]</i>")
		))
		clues.append(jpz.Clue(
			word_id=attrib_word_id,
			text=FormattableText(html="<i>[Attribution]</i>")
		))
		for coord in (
			GridCoord(row, col)
			for row in range(quote_height + 3 + clues_height)
			for col in range(width)
		):
			if coord not in grid:
				grid[coord] = jpz.VoidCell()
		return jpz.JPZPuzzle(
			title=self.title,
			creator=self.author,
			copyright=self.copyright,
			completion_message=quote,
			clues=[
				jpz.ClueList(
					title="Clues",
					clues=clues
				)
			],
			grid=grid,
			words=words,
			puzzle_type="acrostic"
		)

def clue_letters(
	rev: dict[tuple[int, int], tuple[str, int]],
	clue_index: int
) -> Generator[tuple[int, tuple[str, int]]]:
	letter_index = 0
	while (clue_index, letter_index) in rev:
		yield (letter_index, rev[clue_index, letter_index])
		letter_index += 1