import datetime
import requests
import os
from bs4 import BeautifulSoup
import crossword
import jpz

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

