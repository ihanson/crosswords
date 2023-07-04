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
		number: crossword.Clue(clue)
		for (number, clue) in clue_pairs(
			div.find("div", class_="numclue")
		)
	}

def clue_pairs(clue_div):
	for i in range(0, len(clue_div.contents), 2):
		yield (
			int(clue_div.contents[i].get_text()),
			clue_div.contents[i + 1].contents[0].get_text()[:-3]
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
		requests.get(
			f"https://www.xwordinfo.com/JSON/AcrosticData.ashx?date={format_date(date)}",
			headers={"Referer": page_url}
		).text
	)
	quote_with_attr = data["quote"]
	quote_match = re.match(r"^(.*?),\s*(.*?)\s*(?:--|\u2014)\s*(.*)$", html.unescape(quote_with_attr))
	if quote_match is None:
		raise Exception(f"Could not parse quote: {quote_with_attr}")
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
		quote_text=quote_match[3],
		quote_author=quote_match[1],
		quote_work=quote_match[2],
		title=title,
		author=author,
		copyright=data["copyright"]
	)
