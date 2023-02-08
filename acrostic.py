from typing import Tuple

class AcrosticSquare(object):
	pass

class PunctuationSquare(AcrosticSquare):
	def __init__(self, punctuation: str):
		self.__punctuation = punctuation
	
	@property
	def punctuation(self):
		return self.__punctuation

class LetterSquare(AcrosticSquare):
	def __init__(self, answer: str, clue_index: int, clue_word_index: int):
		self.__answer = answer
		self.__clue_index = clue_index
		self.__clue_word_index = clue_word_index
	
	@property
	def answer(self):
		return self.__answer
	
	@property
	def clue_index(self):
		return self.__clue_index
	
	@property
	def clue_word_index(self):
		return self.__clue_word_index

class Acrostic(object):
	def __init__(
			self, squares: list[AcrosticSquare], clues: list[str],
			quote_text: str, quote_author: str, quote_work: str,
			title: str, author: str, copyright: str
		):
		self.__squares = squares
		self.__clues = clues
		self.__quote_text = quote_text
		self.__quote_author = quote_author
		self.__quote_work = quote_work
		self.__title = title
		self.__author = author
		self.__copyright = copyright
	
	@property
	def squares(self):
		return self.__squares
	
	@property
	def clues(self):
		return self.__clues
	
	@property
	def quote_text(self):
		return self.__quote_text
	
	@property
	def quote_author(self):
		return self.__quote_author
	
	@property
	def quote_work(self):
		return self.__quote_work
	
	@property
	def title(self):
		return self.__title
	
	@property
	def author(self):
		return self.__author
	
	@property
	def copyright(self):
		return self.__copyright