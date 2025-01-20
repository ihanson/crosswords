import datetime
import requests
import os
import json
import html
import string
import re
from bs4 import BeautifulSoup
import crossword
import jpz
import acrostic
import lzstring

def download_puzzle(type: str, date: datetime.date) -> crossword.Puzzle:
	soup = BeautifulSoup(
		requests.get(
			f"https://www.xwordinfo.com/{type}?date={format_date(date)}"
		).text,
		"html.parser"
	)
	notepad = soup.find("div", class_="notepad")
	return crossword.Puzzle(
		grid=crossword.Grid([
			[
				crossword.BlackSquare() if has_class(td, ["black", "shape"])
				else crossword.WhiteSquare(
					answer=(
						td.find("div", class_="letter")
						or td.find("div", class_="subst")
					).get_text(),
					is_shaded=has_class(td, ["shade"]),
					is_circled=has_class(td, ["bigcircle"])
				)
				for td in tr.find_all("td", recursive=False)
			]
			for tr in soup.find("table", id="PuzTable").find_all("tr", recursive=False)
		]),
		across=clues_dict(
			soup.find("div", id="ACluesPan")
			or soup.find("div", id="CPHContent_ACluesPan")
		),
		down=clues_dict(
			soup.find("div", id="DCluesPan")
			or soup.find("div", id="CPHContent_DCluesPan")
		),
		title=soup.find("h1").get_text(),
		author=soup.find("div", class_="aegrid").find_all("div", recursive=False)[1].get_text(),
		copyright=soup.find("span", id="CPHContent_Copyright").get_text(),
		note="".join([
			text for text in (
				text_node.strip()
				for text_node in notepad.find_all(string=True, recursive=False)
			) if len(text) > 0
		]) if notepad else None
	)

def has_class(element, classes) -> bool:
	return (
		element.has_attr("class")
		and any(class_name in element["class"] for class_name in classes)
	)

def format_date(date: datetime.date) -> str:
	return f"{date.month}/{date.day}/{date.year}"

def clues_dict(div) -> dict[int, crossword.Clue]:
	return {
		number: crossword.Clue(clue, clue_html)
		for (number, clue, clue_html) in clue_tuples(
			div.find("div", class_="numclue")
		)
	}

def clue_tuples(clue_div):
	for i in range(0, len(clue_div.contents), 2):
		clue_nodes = clue_div.contents[i + 1].contents[:-1]
		yield (
			int(clue_div.contents[i].get_text()),
			"".join(node.text for node in clue_nodes)[:-3],
			"".join(str(node) for node in clue_nodes)[:-3]
		)

def save_variety(date: datetime.date):
	os.makedirs("puzzles", exist_ok=True)
	jpz.save_crossword_jpz(
		download_puzzle("Variety", date),
		f"puzzles\\Variety_{date.isoformat()}.jpz"
	)

def download_acrostic(date: datetime.date) -> acrostic.Acrostic:
	page_url = f"https://www.xwordinfo.com/Acrostic?date={format_date(date)}"
	soup = BeautifulSoup(
		requests.get(
			page_url
		).text,
		"html.parser"
	)
	title = soup.find("h1").get_text()
	author = re.match(r"^by (.*?), edited", soup.find_all("h2")[0].get_text())[1]
	data = json.loads(
		lzstring.LZString().decompressFromEncodedURIComponent(
			json.loads(
				requests.get(
					f"https://www.xwordinfo.com/JSON/AcrosticData.ashx?date={format_date(date)}",
					headers={"Referer": page_url}
				).text
			)["data"]
		)
	)
	quote_with_attr = html.unescape(data["quote"])
	if match := re.match(r"^(.*?)\s*[,:]\s*(.*?)\s*(?:--?|\u2014)\s*([\s\S]*)$", quote_with_attr):
		quote_author = match[1]
		quote_work = match[2]
		quote_text = match[3]
	elif match := re.match(r"^(.*?)\s*(?:--?|\u2014)\s*([\s\S]*)$", quote_with_attr):
		quote_author = None
		quote_work = match[1]
		quote_text = match[2]
	else:
		quote_author = None
		quote_work = None
		quote_text = quote_with_attr
	return acrostic.Acrostic(
		squares=[
			(
				acrostic.LetterSquare(
					answer=answer_letter,
					clue_index=string.ascii_uppercase.index(grid_letter),
					clue_word_index=clue_word_index
				) if grid_letter in string.ascii_uppercase
				else acrostic.PunctuationSquare(answer_letter)
			) for (answer_letter, grid_letter, clue_word_index) in zip(
				data["answerKey"],
				data["gridLetters"],
				(i - 1 if i > 0 else None for i in data["cluePos"])
			)
		],
		clues=[html.unescape(clue) for clue in data["clues"]],
		quote_text=quote_text,
		quote_author=quote_author,
		quote_work=quote_work,
		title=title,
		author=author,
		copyright=data["copyright"]
	)

if __name__ == "__main__":
	import jpz
	date = datetime.date(2025, 1, 19)
	jpz.save_crossword_jpz(download_puzzle("Variety", date), f"puzzles\\Variety {date.isoformat()}.jpz")