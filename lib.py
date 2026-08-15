import copy
from enum import Enum
import re
import string.templatelib
from typing import NamedTuple

from bs4 import BeautifulSoup

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

class SquareSide(Enum):
	TOP = 0
	RIGHT = 1
	BOTTOM = 2
	LEFT = 3

class Color(NamedTuple):
	red: int
	green: int
	blue: int
	
	def to_pixel(self):
		return (self.red, self.green, self.blue, 0xff)

	def __str__(self):
		return f"({self.red}, {self.green}, {self.blue})"

	def hex(self):
		return f"#{self.red:0>2x}{self.green:0>2x}{self.blue:0>2x}"
	
	@staticmethod
	def from_hex(hex: str) -> Color:
		match = Color.__color_expr.match(hex)
		if match is None:
			raise ValueError(f"Invalid color: {hex}")
		(red, green, blue) = match.groups()
		return Color(
			int(red, 16),
			int(green ,16),
			int(blue, 16)
		)

	__color_expr = re.compile(r"#([\da-f]{2})([\da-f]{2})([\da-f]{2})", re.I)