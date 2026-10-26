import datetime
import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Any, Iterable, Iterator, NamedTuple, TypeVar
import crossword
import crossword_nexus
import sys

from lib import Color, FormattableText, GridCoord, SquareSide

js_expr = re.compile(r"window.__PRELOADED_STATE__ = (?P<json>.*);")
section_expr = re.compile(r"## (?P<header>[^\n]+)\n\n(?P<value>(?:[^\n]|\n(?!\n##))*)")
metadata_expr = re.compile(r"(?P<key>[^:]+): (?P<value>.*)")
clue_expr = re.compile(r"(?P<direction>[AD])(?P<number>\d+)\. (?P<clue>.*) ~ [A-Z]*")
bracket_expr = re.compile(r"\{(?P<symbol>.)(?P<contents>.*)(?P=symbol)\}")
cssish_expr = re.compile(r"(?P<tag>\w) \{(?P<properties>[^}]*)\}")

def puzzle_url(date: datetime.date, puzzle_type: str = "crossword"):
	return f"https://www.newyorker.com/puzzles-and-games-dept/{puzzle_type}/{date.year:04}/{date.month:02}/{date.day:02}"

def download_puzzle(
	url: str
) -> crossword.Puzzle:
	text = requests.get(url).text
	page = BeautifulSoup(
		text,
		features="html.parser"
	)
	script_tags = page.find_all("script")
	results = (js_expr.fullmatch(tag.text) for tag in script_tags)
	try:
		jsons = [assert_not_none(match.group("json")) for match in results if match]
		[state_json] = jsons
		state = json.loads(state_json)
		puzzle_id = assert_not_none(
			find_game_id(state["transformed"]["article"]["body"])
		)
	except IndexError, ValueError, KeyError, TypeError:
		raise ValueError("Could not find the New Yorker puzzle")
	puzzle = requests.get(
		f"https://puzzles-games-api.gp-prod.conde.digital/api/v1/games/{puzzle_id}",
		headers={
			"User-Agent": "Mozilla/5.0"
		}
	).json()
	if puzzle["gameType"] != "crossword":
		raise ValueError("Not a crossword puzzle")
	return parse_xd(puzzle["data"])

def parse_xd(xd: str) -> crossword.Puzzle:
	sections: dict[str, str] = {
		match.group("header"): match.group("value")
		for match in section_expr.finditer(xd)
	}
	try:
		metadata = {
			data.group("key"): data.group("value")
			for data in (
				assert_not_none(metadata_expr.fullmatch(line))
				for line in sections["Metadata"].split("\n")
			)
			if data.group("value")
		}
		rebus_str: str | None = metadata.get("rebus")
		rebuses = (
			{
				key: value
				for [key, value] in (
					rebus.split("=", 1)
					for rebus in rebus_str.split(" ")
				)
			}
			if rebus_str is not None
			else {}
		)
		clues: list[tuple[str, int, FormattableText]] = [
			(
				match.group("direction"),
				int(match.group("number")),
				FormattableText(html=parse_clue(match.group("clue")))
			)
			for match in (
				clue_expr.fullmatch(line)
				for line in sections["Clues"].split("\n")
			)
			if match is not None
		]
		design = GridDesign(sections.get("Design"))
	except KeyError, ValueError:
		raise ValueError("Could not parse the New Yorker puzzle")
	
	grid = crossword.Grid([
		[
			crossword.BlackSquare() if char == "."
			else crossword.WhiteSquare(
				answer=(
					None if char == "*"
					else rebuses[char] if char in rebuses
					else char
				),
				color=d.color,
				is_circled=d.is_circled,
				bars=d.bars
			)
			for (d, char) in (
				(design[GridCoord(y, x)], char) for (x, char) in enumerate(row)
			)
		] for (y, row) in enumerate(sections["Grid"].split("\n"))
	])
	clues_by_dir = {
		direction: {
			number: clue
			for (clue_dir, number, clue)
			in clues
			if clue_dir == direction
		}
		for direction in ["A", "D"]
	}
	note = sections.get("Help")
	date = metadata.get("copyright") or metadata.get("date")
	return crossword.Puzzle(
		grid=grid,
		across_clues=clues_by_dir["A"],
		down_clues=clues_by_dir["D"],
		title=FormattableText(metadata["title"]),
		author=FormattableText(metadata["author"]),
		copyright=FormattableText(date) if date else None,
		note=FormattableText(html=note) if note else None,
		show_note_on_open=note is not None
	)

def find_game_id(root: list[Any]) -> str | None:
	match root:
		case ["inline-embed", {
			"type": "game",
			"props": {
				"id": game_id
			}
		}]:
			return game_id
		case [_, {}, *rest] | [_, *rest]:
			return first_not_none(
				find_game_id(child) # type: ignore
				for child in rest
				if isinstance(child, list)
			)
		case _:
			raise ValueError("Unexpected pattern")

def first_not_none(iterable: Iterable[T | None]) -> T | None:
	for value in iterable:
		if value is not None:
			return value
	return None

def parse_clue(clue: str) -> BeautifulSoup:
	result = BeautifulSoup()
	char_iter = iter(clue)
	for char in char_iter:
		if char == "{":
			bracketed = advance_to_close(char_iter)
			result.append(parse_brackets(bracketed))
		else:
			result.append(result.new_string(char))
	return result

def parse_brackets(bracketed: str) -> BeautifulSoup:
	match = assert_not_none(bracket_expr.fullmatch(bracketed))
	symbol: str = match.group("symbol")
	contents = assert_not_none(match.group("contents"))
	match symbol:
		case "/":
			return tag("span", parse_clue(contents), {"font-style": "italic"})
		case "_":
			return tag("span", parse_clue(contents), {"text-decoration": "underline"})
		case "*":
			return tag("span", parse_clue(contents), {"font-weight": "bold"})
		case "-":
			return tag("span", parse_clue(contents), {"text-decoration": "line-through"})
		case "~":
			return tag("sub", parse_clue(contents))
		case "^":
			return tag("sup", parse_clue(contents))
		case "@":
			[inner, href] = contents.split("|", 1)
			return tag("a", parse_clue(inner), attrs={
				"href": href
			})
		case "!":
			(is_block, rest) = (
				(True, contents[1:]) if contents.startswith("!")
				 else (False, contents)
			)
			(url, _, size) = parse_img(rest[1:-1].split("|"))
			(width, height) = normalize_size(size, 64)
			return tag(
				"span",
				style={
					"display": "block" if is_block else "inline-block",
					"width": f"{width}px",
					"height": f"{height}px",
					"background-image": f"url({url})",
					"background-size": f"{width}px, {height}px"
				}
			)
		case "#":
			[inner, color, _] = contents.split("|")
			return tag("span", parse_clue(inner), style={"color": color})
		case _:
			raise ValueError(f"Unknown symbol {symbol}")

def parse_img(img_props: list[str]) -> tuple[str, str | None, tuple[int, int] | None]:
	match img_props:
		case [url, alt, width, height, *_]:
			return (url, alt, (int(width), int(height)))
		case [url, alt, _] | [url, alt]:
			return (url, alt, None)
		case [url]:
			return (url, None, None)
		case _:
			raise ValueError("Image URL is required")

def normalize_size(size: tuple[int, int] | None, norm_height: int) -> tuple[int, int]:
	(width, height) = size or (norm_height, norm_height)
	return (
		(width, height) if height <= norm_height
		else (
			int(width * (norm_height / height)),
			int(height * (norm_height / height))
		)
	)

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

def advance_to_close(char_iter: Iterator[str]) -> str:
	depth = 1
	result: list[str] = ["{"]
	for char in char_iter:
		result.append(char)
		if char == "{":
			depth += 1
		elif char == "}":
			depth -= 1
			if depth == 0:
				return "".join(result)
	raise ValueError("Unclosed bracket")

class CellDesign(NamedTuple):
	bars: frozenset[SquareSide]
	color: Color | None
	is_circled: bool

	@staticmethod
	def default():
		return CellDesign(
			bars=frozenset(),
			color=None,
			is_circled=False
		)

class GridDesign(object):
	def __init__(self, design: str | None):
		self.__grid__ = (
			GridDesign.__parse_design__(design)
			if design is not None
			else None
		)

	def __getitem__(self, index: GridCoord):
		(row, col) = index
		return (
			self.__grid__[row][col]
			if self.__grid__ is not None
			else CellDesign.default()
		)

	@staticmethod
	def __parse_design__(design: str) -> list[list[CellDesign]]:
		[style_html, grid] = design.strip().split("\n\n")
		style_soup = BeautifulSoup(style_html, features="html.parser")
		style = GridDesign.__parse_cssish__(
			assert_not_none(style_soup.find("style")).text
		)
		designs = {
			tag: GridDesign.__cell_design__(rules)
			for (tag, rules) in style
		}
		return [
			[
				designs.get(cell) or CellDesign.default()
				for cell in row
			]
			for row in grid.strip().split("\n")
		]
	
	@staticmethod
	def __parse_cssish__(cssish: str) -> list[tuple[str, dict[str, str]]]:
		lines = (
			assert_not_none(cssish_expr.fullmatch(line))
			for line in cssish.strip().split("\n")
		)
		return [
			(
				line.group("tag"),
				{
					prop.strip(): value.strip()
					for [prop, value] in (
						rule.split(":")
						for rule in line.group("properties").split(";")
					)
				}
			)
			for line in lines
		]
	
	@staticmethod
	def __cell_design__(rules: dict[str, str]) -> CellDesign:
		bars = frozenset([
			GridDesign.__direction__(prop)
			for (prop, value) in rules.items()
			if prop.startswith("bar-") and value == "true"
		])
		color_hex = rules.get("background-dark")
		color = (
			Color.from_hex(color_hex)
			if color_hex is not None
			else None
		)
		circle = rules.get("background") == "circle"
		return CellDesign(bars, color, circle)
	
	@staticmethod
	def __direction__(property: str) -> SquareSide:
		match property:
			case "bar-top":
				return SquareSide.TOP
			case "bar-right":
				return SquareSide.RIGHT
			case "bar-bottom":
				return SquareSide.BOTTOM
			case "bar-left":
				return SquareSide.LEFT
			case _:
				raise ValueError(f"Unknown property {property}")

def daily_puzzle(date: datetime.date | None = None, puzzle_type: str | None = None):
	date = date or datetime.date.today()
	url_type = puzzle_type or (
		"mini-crossword" if date.weekday() >= 3
		else "crossword"
	)
	return download_puzzle(f"https://www.newyorker.com/puzzles-and-games-dept/{url_type}/{date.year:04}/{date.month:02}/{date.day:02}")

T = TypeVar("T")
def assert_not_none(value: T | None) -> T:
	if value is None:
		raise ValueError("Value is None")
	return value

K = TypeVar("K")
def remove_nones(dictionary: dict[K, T | None]) -> dict[K, T]:
	return {
		key: value
		for (key, value) in dictionary.items()
		if value is not None
	}

def parse_args(argv: list[str]) -> tuple[datetime.date, str | None]:
	match argv:
		case [_, date, *rest]:
			try:
				date = datetime.date.fromisoformat(date)
				match rest:
					case [puzzle_type, *_]:
						return (date, puzzle_type)
					case _:
						return (date, None)
			except ValueError:
				return (datetime.date.today(), None)
		case [*_]:
			return (datetime.date.today(), None)

if __name__ == "__main__":
	(date, puzzle_type) = parse_args(sys.argv)
	crossword_nexus.open_puzzle(daily_puzzle(date, puzzle_type))