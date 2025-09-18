import datetime
from collections.abc import Generator
import nyt
import nyt_json
import string

def main():
	try:
		date = prompt_date("Puzzle date (yyyy-mm-dd): ")
		puzzle = nyt.download_json(date, "daily", token())
	except KeyboardInterrupt:
		return
	cells = puzzle["body"][0]["cells"]
	white_cells: Generator[nyt_json.Cell] = (cell for cell in cells if "answer" in cell)
	rebuses = [cell for cell in white_cells if is_rebus(cell)]
	if len(rebuses) > 0:
		for cell in rebuses:
			moreAnswers = cell["moreAnswers"]["valid"] if "moreAnswers" in cell else []
			print(" ".join(f"[{answer}]" for answer in [cell["answer"], *moreAnswers]))
	else:
		print("There are no rebuses in this puzzle.")

uppercase = list(string.ascii_uppercase)

def is_rebus(cell: nyt_json.Cell) -> bool:
	return cell["answer"] not in uppercase or "moreAnswers" in cell

def token() -> str:
	try:
		return nyt.token()
	except FileNotFoundError:
		token = input("NYT-S cookie: ")
		with open("nyt-s.txt", "w", encoding="utf-8") as f:
			f.write(token)
		return token

def prompt_date(prompt: str) -> datetime.date:
	while True:
		try:
			return datetime.date.fromisoformat(input(prompt))
		except ValueError:
			pass

if __name__ == "__main__":
	main()