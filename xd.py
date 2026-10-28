from dataclasses import dataclass
import re
from typing import Iterator, NamedTuple, TypeVar

from bs4 import BeautifulSoup

from crossword import Grid, BlackSquare, Puzzle, WhiteSquare, SquareSide
from lib import Color, FormattableText

section_expr = re.compile(r"## (?P<header>[^\n]++)\n(?P<value>(?:[^\n]|\n(?!\n## ))*+)")
clue_expr = re.compile(r"(?P<num>\w++)\.\s(?P<clueans>.*)")
clue_meta_expr = re.compile(r"(?P<num>\w++)\s\^(?P<keyval>.*+)")
clue_num_expr = re.compile(r"(?P<group>\w)(?P<number>\d+)")
bracket_expr = re.compile(r"(?P<symbol>.)(?P<contents>.*)(?P=symbol)", re.DOTALL)
style_expr = re.compile(r"<style>(?P<styles>.*?)</style>", re.DOTALL)
rule_expr = re.compile(r"(?P<selector>\w)\s*+\{(?P<properties>[^}]*+)\}")
blank_chars = {" ", ".", "#"}

T = TypeVar("T")
def some(value: T | None) -> T:
	if value is None:
		raise ValueError("Value is None")
	return value

@dataclass
class XDCrossword:
	metadata: XDMetadata
	grid: list[list[str]]
	clues: XDClues
	design: XDDesign | None
	note: XDText | None
	other_sections: dict[str, str]

	@staticmethod
	def parse(xd: str) -> XDCrossword:
		sections = {
			some(match["header"]).lower():
				some(match["value"]).strip("\n")
			for match in section_expr.finditer(xd)
		}
		metadata = XDMetadata.parse(sections.pop("metadata"))
		grid = [
			list(line)
			for line in sections.pop("grid").splitlines()
		]
		clues = XDClues.parse(sections.pop("clues"))
		design_section = sections.pop("design", None)
		design = (
			XDDesign.parse(design_section)
			if design_section is not None
			else None
		)
		help_section = sections.pop("help", None)
		note = (
			XDText.parse(help_section)
			if help_section is not None
			else None
		)
		return XDCrossword(metadata, grid, clues, design, note, sections)

	def designed_cells(self) -> list[list[tuple[str, XDStyleRules]]]:
		design = self.design or XDDesign({}, self.grid)
		return [
			[
				(grid_cell, design.styles.get(design_cell, XDStyleRules({})))
				for (grid_cell, design_cell) in zip(grid_row, design_row)
			]
			for (grid_row, design_row) in zip(self.grid, design.grid)
		]

	def to_puzzle(self) -> Puzzle:
		rebuses = self.metadata.rebuses()
		cells = self.designed_cells()
		grid = Grid([
			[
				WhiteSquare(
					answer=(
						rebuses.get(cell, cell)
						if cell != "*"
						else None
					),
					color=style.background_light(),
					is_circled=style.is_circled(),
					bars=style.bars()
				)
				if cell not in blank_chars
				else BlackSquare()
				for (cell, style) in row
			]
			for row in cells
		])
		date = (
			self.metadata.values.get("copyright")
			or self.metadata.values.get("date")
		)
		return Puzzle(
			grid=grid,
			across_clues=self.clues.clues_in_direction("A"),
			down_clues=self.clues.clues_in_direction("D"),
			title=FormattableText(self.metadata.values["title"]),
			author=FormattableText(self.metadata.values["author"]),
			copyright=FormattableText(date) if date else None,
			note=FormattableText(html=self.note.to_soup()) if self.note else None,
			show_note_on_open=self.note is not None
		)

@dataclass
class XDMetadata:
	values: dict[str, str]

	@staticmethod
	def parse(metadata: str) -> XDMetadata:
		return XDMetadata({
			key: value
			for [key, value] in (
				split2(line, ":")
				for line in metadata.splitlines()
			)
		})

	def rebuses(self) -> dict[str, str]:
		rebus_meta = self.values.get("rebus")
		return (
			{
				key: value
				for [key, value] in (
					split2(rebus, "=")
					for rebus in rebus_meta.split(" ")
				)
			}
			if rebus_meta is not None
			else {}
		)

@dataclass
class XDClues:
	clues: dict[XDClueNumber, XDClue]

	@staticmethod
	def parse(clues: str) -> XDClues:
		clue_dict: dict[XDClueNumber, tuple[XDText, str | None]] = {}
		meta_dict: dict[XDClueNumber, dict[str, XDText]] = {}

		for line in (
			line.strip() for line in clues.splitlines()
			if len(line) > 0 and not line.isspace()
		):
			if clue_match := clue_expr.fullmatch(line):
				num = XDClueNumber.parse(some(clue_match["num"]))
				clueans = some(clue_match["clueans"])
				[clue, answer] = (
					split2(clueans, "~", True)
					if "~" in clueans
					else (clueans.strip(), None)
				)
				clue_dict[num] = (XDText.parse(clue), answer)
			elif meta_match := clue_meta_expr.fullmatch(line):
				num = XDClueNumber.parse(some(meta_match["num"]))
				[key, value] = split2(meta_match["keyval"], ":")
				meta_dict.setdefault(num, {})
				meta_dict[num][key] = XDText.parse(value)
			else:
				raise XDParseError(f"Invalid clue line: {line}")
		return XDClues({
			num: XDClue(text, answer, meta_dict.get(num, {}))
			for (num, (text, answer)) in clue_dict.items()
		})

	def clues_in_direction(self, clueset: str) -> dict[int, FormattableText]:
		return {
			number.number: FormattableText(html=clue.text.to_soup())
			for (number, clue) in self.clues.items()
			if number.clueset == clueset
		}

class XDClueNumber(NamedTuple):
	clueset: str
	number: int

	@staticmethod
	def parse(number: str) -> XDClueNumber:
		clue = some(clue_num_expr.fullmatch(number))
		return XDClueNumber(clue["group"], int(clue["number"]))

@dataclass
class XDClue:
	text: XDText
	answer: str | None
	meta: dict[str, XDText]

@dataclass
class XDText:
	pieces: list[str | XDContent]

	@staticmethod
	def parse(text: str) -> XDText:
		pieces: list[str | XDContent] = []
		char_iter = iter(text)
		for char in char_iter:
			if char == "{":
				bracketed = advance_to_close(char_iter)
				pieces.append(XDText.parse_brackets(bracketed))
			else:
				if len(pieces) > 0 and isinstance(pieces[-1], str):
					pieces[-1] += char
				else:
					pieces.append(char)
		return XDText(pieces)

	@staticmethod
	def parse_brackets(bracketed: str) -> XDContent:
		m = bracket_expr.fullmatch(bracketed)
		if m is None:
			raise XDParseError(f"Invalid format expression: {{{bracketed}}}")
		match some(m["symbol"]):
			case "@":
				return XDLink.parse(m["contents"])
			case "!":
				return XDImage.parse(m["contents"])
			case "#":
				return XDColorText.parse(m["contents"])
			case _:
				return XDFormattedText.parse(m["symbol"], m["contents"])
		

	def to_soup(self) -> BeautifulSoup:
		soup = BeautifulSoup()
		for piece in self.pieces:
			if isinstance(piece, XDContent):
				soup.append(piece.to_soup())
			else:
				soup.append(soup.new_string(piece))
		return soup

class XDContent:
	def to_soup(self) -> BeautifulSoup:
		raise NotImplementedError()

@dataclass
class XDFormattedText(XDContent):
	format_char: str
	contents: XDText

	@staticmethod
	def parse(symbol: str, text: str) -> XDFormattedText:
		return XDFormattedText(symbol, XDText.parse(text))

	def to_soup(self) -> BeautifulSoup:
		match self.format_char:
			case "/":
				return tag("span", self.contents.to_soup(), {"font-style": "italic"})
			case "_":
				return tag("span", self.contents.to_soup(), {"text-decoration": "underline"})
			case "*":
				return tag("span", self.contents.to_soup(), {"font-weight": "bold"})
			case "-":
				return tag("span", self.contents.to_soup(), {"text-decoration": "line-through"})
			case "~":
				return tag("sub", self.contents.to_soup())
			case "^":
				return tag("sup", self.contents.to_soup())
			case _:
				raise ValueError(f"Unknown symbol {self.format_char}")

@dataclass
class XDColorText(XDContent):
	light_mode_color: Color
	dark_mode_color: Color
	text: XDText

	@staticmethod
	def parse(color: str) -> XDColorText:
		(text_light, dark) = split2(color, "|", True)
		(text, light) = split2(text_light, "|", True)
		return XDColorText(
			Color.from_hex(light),
			Color.from_hex(dark),
			XDText.parse(text)
		)

	def to_soup(self) -> BeautifulSoup:
		return tag(
			"span",
			self.text.to_soup(),
			style={
				"color": self.light_mode_color.hex()
			}
		)

@dataclass
class XDLink(XDContent):
	href: str
	text: XDText

	@staticmethod
	def parse(link: str) -> XDLink:
		[text, href] = split2(link, "|", True)
		return XDLink(href, XDText.parse(text))

	def to_soup(self) -> BeautifulSoup:
		return tag("a", self.text.to_soup(), attrs={
			"href": self.href
		})

@dataclass
class XDImage(XDContent):
	src: str
	alt: str | None = None
	height: int | None = None
	width: int | None = None
	is_block: bool = False

	@staticmethod
	def parse(img: str) -> XDImage:
		(block, img) = (
			(True, img[1:-1])
			if img.startswith("!") and img.endswith("!")
			else (False, img)
		)
		match img.split("|"):
			case [src]:
				return XDImage(src, is_block=block)
			case [src, alt]:
				return XDImage(src, alt, is_block=block)
			case [src, alt, width]:
				return XDImage(src, alt, int(width), is_block=block)
			case [src, alt, width, height]:
				return XDImage(src, alt, int(width), int(height), is_block=block)
			case _:
				raise XDParseError(f"Invalid image specification {img}")

	def to_soup(self) -> BeautifulSoup:
		(width, height) = XDImage.normalize_size(self.width, self.height, 64)
		return tag(
			"span",
			style={
				"display": "block" if self.is_block else "inline-block",
				"width": f"{width}px",
				"height": f"{height}px",
				"background-image": f"url({self.src})",
				"background-size": f"{width}px, {height}px"
			}
		)

	@staticmethod
	def normalize_size(width: int | None, height: int | None, norm_size: int) -> tuple[int, int]:
		if height is None or width is None:
			return (height or norm_size, width or norm_size)
		return (
			(width, height) if height <= norm_size
			else (
				round(width * (norm_size / height)),
				round(height * (norm_size / height))
			)
		)

@dataclass
class XDDesign:
	styles: dict[str, XDStyleRules]
	grid: list[list[str]]

	@staticmethod
	def parse(design: str) -> XDDesign:
		styles: dict[str, dict[str, str]] = {}
		for (selector, prop, val) in (
			(some(rule["selector"]), prop, val)
			for ruleset in style_expr.finditer(design)
			for rule in rule_expr.finditer(ruleset["styles"])
			for (prop, val) in (
				split2(decl, ":")
				for decl in rule["properties"].split(";")
			)
		):
			styles.setdefault(selector, {})
			styles[selector][prop] = val
		grid = [
			list(line)
			for line in style_expr.sub("", design).strip("\n").splitlines()
		]
		return XDDesign({
			selector: XDStyleRules(rules)
			for (selector, rules) in styles.items()
		}, grid)

@dataclass
class XDStyleRules:
	styles: dict[str, str]

	def background_light(self) -> Color | None:
		color = self.styles.get("background-light")
		if color is None:
			return None
		return Color.from_hex(color)

	def is_circled(self) -> bool:
		return self.styles.get("background") == "circle"

	def bars(self) -> frozenset[SquareSide]:
		return frozenset(
			side
			for (side, prop) in [
				(SquareSide.TOP, "bar-top"),
				(SquareSide.LEFT, "bar-left")
			]
			if self.styles.get(prop) == "true"
		)

def advance_to_close(char_iter: Iterator[str]) -> str:
	depth = 1
	result: list[str] = []
	for char in char_iter:
		result.append(char)
		if char == "{":
			depth += 1
		elif char == "}":
			depth -= 1
			if depth == 0:
				return "".join(result[:-1])
	raise XDParseError("Unclosed bracket")

class XDParseError(Exception):
	pass


def tag(
	element: str,
	contents: BeautifulSoup | None = None,
	style: dict[str, str] = {},
	attrs: dict[str, str] | None = None
) -> BeautifulSoup:
	soup = BeautifulSoup()
	node = soup.new_tag(element, attrs=attrs)
	if len(style) > 0:
		node["style"] = "".join(
			f"{prop}:{value};"
			for (prop, value) in style.items()
		)
	if contents:
		node.append(contents)
	soup.append(node)
	return soup

def split2(string: str, split_at: str, split_right: bool = False) -> tuple[str, str]:
	index = string.rfind(split_at) if split_right else string.find(split_at)
	if index == -1:
		raise ValueError(f"String does not contain separator {split_at}")
	return (string[:index].strip(), string[index + 1:].strip())