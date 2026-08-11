import string
import requests
import pyperclip
import babel.dates
import json
import datetime
import urllib.parse
from typing import Any, TypedDict, NotRequired
from bs4 import BeautifulSoup
import crossword
import acrostic
import jpz

class NextData(TypedDict):
	props: NextDataProps

class NextDataProps(TypedDict):
	pageProps: NextDataPageProps

class NextDataPageProps(TypedDict):
	levelId: str

class CrosswordResponse(TypedDict):
	result: CrosswordResult

class CrosswordResult(TypedDict):
	data: CrosswordResultData

class CrosswordResultData(TypedDict):
	data: CrosswordData

class CrosswordData(TypedDict):
	title: str
	author: str
	date: str
	grid: list[list[GridCell]]
	clues: CrosswordClues

class GridCell(TypedDict):
	answer: str
	isBlack: NotRequired[bool]
	isCircled: NotRequired[bool]

class CrosswordClues(TypedDict):
	across: list[CrosswordClue]
	down: list[CrosswordClue]

class CrosswordClue(TypedDict):
	number: int
	text: str

class AcrosticData(TypedDict):
	copy: AcrosticCopy
	settings: AcrosticSettings
	celldata: str
	cluedata: str

AcrosticCopy = TypedDict(
	"AcrosticCopy",
	{
		"title": str,
		"description": str,
		"setter": str,
		"date-publish": str
	}
)

class AcrosticSettings(TypedDict):
	solution: str
	clues: list[AcrosticClue]

class AcrosticClue(TypedDict):
	id: str
	clue: str

def read_wsj_headers() -> Any:
	code = "copy(JSON.stringify({\"User-Agent\":navigator.userAgent,\"Accept-Language\":`${navigator.languages.join(\",\")};q=0.9`,Priority:\"u=0, i\",Cookie:document.cookie}))"
	pyperclip.copy(code)
	print("Paste to the console on the WSJ website, then paste the results here:")
	result = input("> ")
	with open("wsj.json", "w", encoding="utf-8") as f:
		f.write(result)
	return json.loads(result)

def wsj_headers() -> Any:
	try:
		with open("wsj.json", encoding="utf-8") as f:
			return json.load(f)
	except FileNotFoundError:
		return read_wsj_headers()

def wsj_get_with(url: str, headers: Any) -> requests.Response:
	return requests.get(url, headers=headers)

class WSJError(Exception): pass

def wsj_get(url: str) -> requests.Response:
	req = wsj_get_with(url, wsj_headers())
	if req.status_code == 200:
		return req
	req = wsj_get_with(url, read_wsj_headers())
	if req.status_code == 200:
		return req
	raise WSJError(f"Could not read URL {url}")

def puzzle_data(puzzle_id: str) -> CrosswordResponse:
	data: list[CrosswordResponse] = json.loads(requests.get(
		"https://api.puzzlr.net/trpc/crossword.getLevel",
		params={
			"batch": "1",
			"input": json.dumps({
				"0": {
					"tenant": "wsj",
					"shortId": puzzle_id
				}
			})
		}
	).text)
	return data[0]

def crossword_puzzle(url: str) -> crossword.Puzzle:
	soup = BeautifulSoup(wsj_get(url).text, "html.parser")
	script = soup.find(id="__NEXT_DATA__")
	if script is None:
		raise WSJError("Puzzle information not found")
	data: NextData = json.loads(script.get_text())
	puzzle_id = data["props"]["pageProps"]["levelId"]
	puzzle = puzzle_data(puzzle_id)["result"]["data"]["data"]

	return crossword.Puzzle(
		title=crossword.FormattableText(puzzle["title"]),
		author=crossword.FormattableText(puzzle["author"]),
		copyright=crossword.FormattableText(
			babel.dates.format_date(
				datetime.date.fromisoformat(puzzle["date"]),
				format="full"
			)
		),
		grid=crossword.Grid([
			[
				crossword.BlackSquare() if cell.get("isBlack", False)
				else crossword.WhiteSquare(
					answer=cell["answer"],
					is_circled=cell.get("isCircled", False)
				)
				for cell in row
			]
			for row in puzzle["grid"]
		]),
		across={
			clue["number"]: crossword.FormattableText(clue["text"])
			for clue in puzzle["clues"]["across"]
		},
		down={
			clue["number"]: crossword.FormattableText(clue["text"])
			for clue in puzzle["clues"]["down"]
		}
	)

def acrostic_puzzle(url: str) -> acrostic.Acrostic:
	soup = BeautifulSoup(wsj_get(url).text, "html.parser")
	iframe = soup.find(
		"iframe",
		class_=lambda c: c is not None and c.endswith("-PuzzleIframe")
	)
	if iframe is None:
		raise WSJError("Puzzle information not found")
	frame_url = iframe["src"]
	assert isinstance(frame_url, str)
	data_url = urllib.parse.urljoin(frame_url, "data.json")
	data: AcrosticData = json.loads(wsj_get(data_url).text)
	[source, quote] = data["copy"]["description"].split("\u2014", 1)
	return acrostic.Acrostic(
		title=crossword.FormattableText(data["copy"]["title"]),
		author=crossword.FormattableText(data["copy"]["setter"]),
		quote_text=crossword.FormattableText(quote),
		quote_author=crossword.FormattableText(source),
		copyright=crossword.FormattableText(data["copy"]["date-publish"]),
		squares=[
			acrostic.LetterSquare(
				answer=solution,
				clue_index=ord(cell) - 65,
				clue_word_index=ord(clue) - 65
			) if cell in string.ascii_uppercase
			else acrostic.PunctuationSquare(cell)
			for (cell, clue, solution) in zip(
				data["celldata"],
				data["cluedata"],
				data["settings"]["solution"]
			)
		],
		clues=[
			crossword.FormattableText(clue["clue"])
			for clue in data["settings"]["clues"]
		]
	)

def main():
	print("https://www.wsj.com/games/crosswords")
	url = input("Puzzle URL: ")
	puzzle = acrostic_puzzle(url)
	jpz.save_acrostic_jpz(puzzle, f"puzzles\\acrostic.jpz")
	#puzzle = crossword_puzzle(url)
	#crossword_nexus.open_puzzle(puzzle)

if __name__ == "__main__":
	main()