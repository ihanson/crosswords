import datetime
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
	if any(is_rebus(cell) for cell in cells):
		for cell in cells:
			if "moreAnswers" in cell:
				print(" ".join(f"[{answer}]" for answer in [cell["answer"], *cell["moreAnswers"]["valid"]]))
	else:
		print("There are no rebuses in this puzzle.")

def is_rebus(cell: nyt_json.Cell | nyt_json.BlackCell) -> bool:
	return (
		"answer" in cell and (
			cell["answer"] not in string.ascii_uppercase
			or "moreAnswers" in cell
		)
	)

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