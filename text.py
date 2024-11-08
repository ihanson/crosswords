import crossword

def load_text(file_path: str) -> crossword.Puzzle:
	with open(file_path, "r", encoding="utf-8") as reader:
		title = reader.readline().strip("\r\n") or None
		author = reader.readline().strip("\r\n") or None
		copyright = reader.readline().strip("\r\n") or None
		note = reader.readline().strip("\r\n") or None
		grid_text = []
		while len(line := reader.readline().strip("\r\n")) > 0:
			grid_text.append(line)
		grid = crossword.Grid([
			[
				crossword.BlackSquare() if c == " " else crossword.WhiteSquare(c)
				for c in row
			] for row in grid_text
		])
		(across_nums, down_nums) = clue_nums(grid)
		across: dict[int, str] = {}
		down: dict[int, str] = {}
		for clue in across_nums:
			across[clue] = crossword.Clue(*p(reader.readline().strip("\r\n")))
		for clue in down_nums:
			down[clue] = crossword.Clue(*p(reader.readline().strip("\r\n")))
		return crossword.Puzzle(grid, across, down, title, author, copyright, note)

def p(text):
	return tuple(text.split("|"))

def save_text(puzzle: crossword.Puzzle, file_path: str):
	with open(file_path, "w", encoding="utf-8") as writer:
		writer.write(puzzle.title or "")
		writer.write("\n")
		writer.write(puzzle.author or "")
		writer.write("\n")
		writer.write(puzzle.copyright or "")
		writer.write("\n")
		writer.write(puzzle.note or "")
		writer.write("\n")
		for row in range(puzzle.grid.rows):
			for col in range(puzzle.grid.cols):
				writer.write("." if isinstance(puzzle.grid[row, col], crossword.WhiteSquare) else " ")
			writer.write("\n")
		writer.write("\n")
		for (_, clue) in sorted(puzzle.across_clues.items()):
			writer.write(clue.clue)
			writer.write("\n")
		for (_, clue) in sorted(puzzle.down_clues.items()):
			writer.write(clue.clue)
			writer.write("\n")

def clue_nums(grid: crossword.Grid) -> tuple[list[int], list[int]]:
	across = []
	down = []
	clue_num = 1
	for row in range(grid.rows):
		for col in range(grid.cols):
			is_across = grid.is_across_start(row, col)
			is_down = grid.is_down_start(row, col)
			if is_across or is_down:
				if is_across:
					across.append(clue_num)
				if is_down:
					down.append(clue_num)
				clue_num += 1
	return (across, down)

if __name__ == "__main__":
	import jpz
	jpz.save_crossword_jpz(load_text("puzzles/script.txt"), "puzzles/script.jpz")