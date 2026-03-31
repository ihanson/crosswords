import datetime
import requests
from bs4 import BeautifulSoup
import re
import json
import os.path
from typing import Iterator, TypeVar
import crossword
from nyt import format_date
import jpz

js_expr = re.compile(r"window.__PRELOADED_STATE__ = (?P<json>.*);")
section_expr = re.compile(r"## (?P<header>[^\n]+)\n\n(?P<value>(?:[^\n]|\n(?!\n##))*)")
metadata_expr = re.compile(r"(?P<key>[^:]+): (?P<value>.*)")
clue_expr = re.compile(r"(?P<direction>[AD])(?P<number>\d+)\. (?P<clue>.*) ~ [A-Z]*")
bracket_expr = re.compile(r"\{(?P<symbol>.)(?P<contents>.*)(?P=symbol)\}")
						
def download_puzzle(date: datetime.date) -> crossword.Puzzle:
	page = BeautifulSoup(
		requests.get(
			f"https://www.newyorker.com/puzzles-and-games-dept/crossword/{date.year:04}/{date.month:02}/{date.day:02}"
		).text,
		features="html.parser"
	)
	script_tags = page.find_all("script")
	results = (js_expr.fullmatch(tag.text) for tag in script_tags)
	try:
		jsons = [assert_not_none(match.group("json")) for match in results if match]
		[state_json] = jsons
		state = json.loads(state_json)
		[_, [_, embed]] = state["transformed"]["article"]["body"]
		puzzle_id = embed["props"]["id"]
	except IndexError, ValueError, KeyError, TypeError:
		raise ValueError("Could not find the New Yorker puzzle")
	puzzle_data: str = requests.get(
		f"https://puzzles-games-api.gp-prod.conde.digital/api/v1/games/{puzzle_id}",
		headers={
			"User-Agent": "Mozilla/5.0"
		}
	).json()["data"]
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
		}
		clues: list[tuple[str, int, BeautifulSoup]] = [
			(
				match.group("direction"),
				int(match.group("number")),
				parse_clue(match.group("clue"))
			)
			for match in (
				clue_expr.fullmatch(line)
				for line in sections["Clues"].split("\n")
			)
			if match is not None
		]
	except KeyError, ValueError:
		raise ValueError("Could not parse the New Yorker puzzle")
	grid = crossword.Grid([
		[
			crossword.BlackSquare() if char == "."
			else crossword.WhiteSquare(char)
			for char in row
		] for row in sections["Grid"].split("\n")
	])
	clues_by_dir = {
		direction: {
			number: crossword.Clue(clue.text, str(clue))
			for (clue_dir, number, clue)
			in clues
			if clue_dir == direction
		}
		for direction in ["A", "D"]
	}
	return crossword.Puzzle(
		grid=grid,
		across=clues_by_dir["A"],
		down=clues_by_dir["D"],
		title=metadata["title"],
		author=metadata["author"],
		copyright=metadata.get("copyright") or metadata.get("date") or format_date(date)
	)

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
	tag = {
		"/": "i"
	}[symbol]
	node = soup.new_tag(tag)
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

T = TypeVar("T")
def assert_not_none(value: T | None) -> T:
	if value is None:
		raise ValueError("Value is None")
	return value

if __name__ == "__main__":
	date = datetime.date(2026, 3, 23)
	puzzle = download_puzzle(date)
	jpz.save_crossword_jpz(puzzle, os.path.join("puzzles", f"tny {date.isoformat()}.jpz"))