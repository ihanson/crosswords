from dataclasses import dataclass
from typing import Sequence
from crossword import FormattableText

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