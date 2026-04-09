import datetime
import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Any, Iterable, Iterator, TypeVar
import crossword
import crossword_nexus

js_expr = re.compile(r"window.__PRELOADED_STATE__ = (?P<json>.*);")
section_expr = re.compile(r"## (?P<header>[^\n]+)\n\n(?P<value>(?:[^\n]|\n(?!\n##))*)")
metadata_expr = re.compile(r"(?P<key>[^:]+): (?P<value>.*)")
clue_expr = re.compile(r"(?P<direction>[AD])(?P<number>\d+)\. (?P<clue>.*) ~ [A-Z]*")
bracket_expr = re.compile(r"\{(?P<symbol>.)(?P<contents>.*)(?P=symbol)\}")
cssish_expr = re.compile(r"(?P<tag>\w) \{(?P<properties>[^}]*)\}")

def puzzle_url(date: datetime.date, puzzle_type: str = "crossword"):
	return f"https://www.newyorker.com/puzzles-and-games-dept/{puzzle_type}/{date.year:04}/{date.month:02}/{date.day:02}"

def download_puzzle(
	url: str,
) -> crossword.Puzzle:
	page = BeautifulSoup(
		requests.get(url).text,
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
	puzzle_data: str = puzzle["data"]
	sections: dict[str, str] = {
		match.group("header"): match.group("value")
		for match in section_expr.finditer(puzzle_data)
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
		clues: list[tuple[str, int, crossword.FormattableText]] = [
			(
				match.group("direction"),
				int(match.group("number")),
				crossword.FormattableText(html=parse_clue(match.group("clue")))
			)
			for match in (
				clue_expr.fullmatch(line)
				for line in sections["Clues"].split("\n")
			)
			if match is not None
		]
		is_barred = metadata.get("form") == "barred"
		design = GridDesign(
			sections["Design"] if is_barred
			else None
		)
	except KeyError, ValueError:
		raise ValueError("Could not parse the New Yorker puzzle")
	
	grid = crossword.Grid([
		[
			crossword.BlackSquare() if char == "."
			else crossword.WhiteSquare(char, bars=design.bars(y, x))
			for (x, char) in enumerate(row)
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
		across=clues_by_dir["A"],
		down=clues_by_dir["D"],
		title=crossword.FormattableText(metadata["title"]),
		author=crossword.FormattableText(metadata["author"]),
		copyright=crossword.FormattableText(date) if date else None,
		note=crossword.FormattableText(html=note) if note else None,
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
		case [_, {}, *rest]:
			return first_not_none(
				find_game_id(tag)
				for tag in rest
			)
		case [_, *rest]:
			return first_not_none(
				find_game_id(tag)
				for tag in rest
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
	contents: str = match.group("contents")
	soup = BeautifulSoup()
	try:
		(prop, val) = {
			"/": ("font-style", "italic"),
			"_": ("text-decoration", "underline"),
			"*": ("font-weight", "bold")
		}[symbol]
	except KeyError:
		raise ValueError(f"Unknown symbol {symbol}")
	node = soup.new_tag("span")
	node["style"] = f"{prop}:{val}"
	node.append(parse_clue(contents))
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

class GridDesign(object):
	def __init__(self, design: str | None):
		self.__grid__ = (
			GridDesign.__parse_design__(design)
			if design is not None
			else None
		)
	
	def bars(self, row: int, col: int) -> frozenset[crossword.SquareSide]:
		return (
			self.__grid__[row][col]
			if self.__grid__ is not None
			else frozenset()
		)

	@staticmethod
	def __parse_design__(design: str):
		[style_html, grid] = design.strip().split("\n\n")
		style_soup = BeautifulSoup(style_html, features="html.parser")
		style = GridDesign.__parse_cssish__(
			assert_not_none(style_soup.find("style")).text
		)
		bar_map = {
			tag: frozenset([
				GridDesign.__direction__(prop)
				for (prop, value) in rules.items()
				if value == "true"
			])
			for (tag, rules) in style
		}
		empty: frozenset[crossword.SquareSide] = frozenset()
		return [
			[
				bar_map.get(cell, empty)
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
	def __direction__(property: str) -> crossword.SquareSide:
		match property:
			case "bar-top":
				return crossword.SquareSide.TOP
			case "bar-right":
				return crossword.SquareSide.RIGHT
			case "bar-bottom":
				return crossword.SquareSide.BOTTOM
			case "bar-left":
				return crossword.SquareSide.LEFT
			case _:
				raise ValueError(f"Unknown property {property}")

def daily_puzzle(date: datetime.date | None = None):
	date = date or datetime.date.today()
	puzzle_type = "mini-crossword" if date.weekday() >= 3 else "crossword"
	return download_puzzle(f"https://www.newyorker.com/puzzles-and-games-dept/{puzzle_type}/{date.year:04}/{date.month:02}/{date.day:02}")

T = TypeVar("T")
def assert_not_none(value: T | None) -> T:
	if value is None:
		raise ValueError("Value is None")
	return value

if __name__ == "__main__":
	crossword_nexus.open_puzzle(daily_puzzle())