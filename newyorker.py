import datetime
import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Any, Iterable, TypeVar
import crossword
import crossword_nexus
import sys

import xd

js_expr = re.compile(r"window.__PRELOADED_STATE__ = (?P<json>.*);")
section_expr = re.compile(r"## (?P<header>[^\n]+)\n\n(?P<value>(?:[^\n]|\n(?!\n##))*)")
metadata_expr = re.compile(r"(?P<key>[^:]+): (?P<value>.*)")
clue_expr = re.compile(r"(?P<direction>[AD])(?P<number>\d+)\. (?P<clue>.*) ~ [A-Z]*")
bracket_expr = re.compile(r"\{(?P<symbol>.)(?P<contents>.*)(?P=symbol)\}")
cssish_expr = re.compile(r"(?P<tag>\w) \{(?P<properties>[^}]*)\}")

def puzzle_url(date: datetime.date, puzzle_type: str = "crossword"):
	return f"https://www.newyorker.com/puzzles-and-games-dept/{puzzle_type}/{date.year:04}/{date.month:02}/{date.day:02}"

class DownloadError(Exception):
	pass

def download_preloaded_state(url: str) -> Any:
	req = requests.get(url)
	if req.status_code != 200:
		raise DownloadError(f"Got HTTP code {req.status_code} when downloading {url}")
	text = requests.get(url).text
	page = BeautifulSoup(text, features="html.parser")
	script_tags = page.find_all("script")
	results = (js_expr.fullmatch(tag.text) for tag in script_tags)
	jsons = [assert_not_none(match.group("json")) for match in results if match]
	[state_json] = jsons
	return json.loads(state_json)

def download_puzzle_xd(url: str) -> str:
	state = download_preloaded_state(url)
	try:
		puzzle_id = assert_not_none(
			find_game_id(state["transformed"]["article"]["body"])
		)
	except IndexError, ValueError, KeyError, TypeError:
		raise ValueError("Could not find the New Yorker puzzle")
	data_url = f"https://puzzles-games-api.gp-prod.conde.digital/api/v1/games/{puzzle_id}"
	data_req = requests.get(data_url, headers={
		"User-Agent": "Mozilla/5.0"
	})
	if data_req.status_code != 200:
		raise DownloadError(f"Got HTTP code {data_req.status_code} when downloading {url}")
	puzzle = data_req.json()
	if puzzle["gameType"] != "crossword":
		raise ValueError("Not a crossword puzzle")
	return puzzle["data"]

def download_puzzle(
	url: str
) -> crossword.Puzzle:
	return parse_xd(download_puzzle_xd(url))


def parse_xd(xd_text: str) -> crossword.Puzzle:
	return xd.XDCrossword.parse(xd_text).to_puzzle()

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