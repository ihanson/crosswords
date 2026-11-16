import datetime
import nyt
import string

def main():
	try:
		date = prompt_date("Puzzle date (yyyy-mm-dd): ")
		puzzle = nyt.download_json(date, "daily", token())
	except KeyboardInterrupt:
		return
	cells = puzzle["body"][0]["cells"]
	white_cells = (cell for cell in cells if "type" in cell)
	answers = (possible_answers(cell) for cell in white_cells)
	rebuses = [a for a in answers if is_rebus(a)]
	if len(rebuses) > 0:
		for rebus in rebuses:
			print(" ".join(f"[{answer}]" for answer in rebus))
	else:
		print("There are no rebuses in this puzzle.")

uppercase = set(string.ascii_uppercase)

def possible_answers(cell: nyt.Cell) -> list[str]:
	return [
		cell.get("answer", ""),
		*cell.get("moreAnswers", {"valid": []})["valid"]
	]

def is_rebus(answers: list[str]) -> bool:
	match answers:
		case [a]: return a not in uppercase
		case _: return True
		

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