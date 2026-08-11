from typing import Generator
import xml.etree.ElementTree as ET
import crossword
from crossword import FormattableText, GridCoord
import acrostic
import string
import puzzle as generic_puzzle

def element_with_raw_html(tag: str, text: crossword.FormattableText, attrs: dict[str, str] = {}):
	xml_ish = f"<{tag}>{text.html}</{tag}>"
	element = ET.fromstring(xml_ish)
	for (attr, value) in attrs.items():
		element.set(attr, value)
	return element

def to_jpz_puzzle(xword: crossword.Puzzle) -> generic_puzzle.Puzzle:
	grid: dict[GridCoord, generic_puzzle.Cell] = {}
	across_clues: list[generic_puzzle.Clue] = []
	down_clues: list[generic_puzzle.Clue] = []
	words: list[generic_puzzle.Word] = []
	word_count = 0
	clue_count = 0
	for (coord, xword_cell) in xword.grid:
		is_across = xword.grid.is_across_start(coord)
		is_down = xword.grid.is_down_start(coord)
		number = (
			(clue_count := clue_count + 1)
			if is_across or is_down
			else None
		)
		cell = (
			generic_puzzle.EntryCell(
				solution=xword_cell.answer,
				number=str(number) if number is not None else None,
				is_circled=xword_cell.is_circled,
				color=xword_cell.color,
				bars=xword_cell.bars
			)
			if isinstance(xword_cell, crossword.WhiteSquare)
			else generic_puzzle.BlockCell()
		)
		grid[coord] = cell
		if number is not None:
			for (is_start, clue_dict, gen, clue_list) in [
				(is_across, xword.across_clues, xword.grid.across_word_cells, across_clues),
				(is_down, xword.down_clues, xword.grid.down_word_cells, down_clues)
			]:
				if is_start:
					word_id = str(word_count := word_count + 1)
					words.append(generic_puzzle.Word(
						word_id=word_id,
						cells=list(gen(coord))
					))
					clue_list.append(generic_puzzle.Clue(
						word_id=word_id,
						number=str(number),
						text=clue_dict[number]
					))
	return generic_puzzle.Puzzle(
		title=xword.title,
		creator=xword.author,
		copyright=xword.copyright,
		note=(
			generic_puzzle.Note(
				text=xword.note,
				show_on_open=xword.show_note_on_open
			)
			if xword.note
			else None
		),
		grid=grid,
		words=words,
		clues=[
			generic_puzzle.ClueList(
				title="Across",
				clues=across_clues
			),
			generic_puzzle.ClueList(
				title="Down",
				clues=down_clues
			)
		]
	)

def save_puzzle_jpz(puzzle: generic_puzzle.Puzzle, file_path: str):
	root = ET.Element("crossword-compiler-applet", {
		"xmlns": "http://crossword.info/xml/crossword-compiler"
	})
	settings_el = ET.SubElement(root, "applet-settings")
	if puzzle.completion_message:
		settings_el.append(element_with_raw_html(
			"completion",
			puzzle.completion_message,
			{
				"only-if-correct": "true"
			}
		))
	actions_el = ET.SubElement(settings_el, "actions")
	ET.SubElement(actions_el, "reveal-word")
	ET.SubElement(actions_el, "reveal-letter")
	ET.SubElement(actions_el, "solution")
	puzzle_el = ET.SubElement(root, "rectangular-puzzle", {
		"xmlns": "http://crossword.info/xml/rectangular-puzzle",
		"alphabet": "ABCDEFGHIJIKLMNOPQRSTUVWXYZ"
	})
	metadata = ET.SubElement(puzzle_el, "metadata")
	for (tag, text) in [
		("title", puzzle.title),
		("creator", puzzle.creator),
		("copyright", puzzle.copyright)
	]:
		if text is not None:
			metadata.append(element_with_raw_html(tag, text))
	if puzzle.note:
		note_tag = (
			"description" if puzzle.note.show_on_open
			else "instructions"
		)
		metadata.append(element_with_raw_html(note_tag, puzzle.note.text))
	
	crossword_el = ET.SubElement(puzzle_el, puzzle.puzzle_type)
	grid = ET.SubElement(crossword_el, "grid", {
		"width": str(puzzle.width()),
		"height": str(puzzle.height())
	})
	ET.SubElement(grid, "grid-look", {
		"hide-lines": "true"
	})
	for (coord, cell) in sorted(puzzle.grid.items()):
		cell_el = ET.SubElement(grid, "cell", {
			"x": str(coord.col + 1),
			"y": str(coord.row + 1)
		})
		if isinstance(cell, generic_puzzle.EntryCell):
			if cell.solution is not None:
				cell_el.attrib["solution"] = cell.solution
			if cell.number is not None:
				cell_el.attrib["number"] = cell.number
			if cell.top_right_number is not None:
				cell_el.attrib["top-right-number"] = cell.top_right_number
			if cell.is_circled:
				cell_el.attrib["background-shape"] = "circle"
			if cell.color:
				cell_el.attrib["background-color"] = cell.color.hex()
			for side in crossword.SquareSide:
				if side in cell.bars:
					cell_el.attrib[bar_attribute(side)] = "true"
		elif isinstance(cell, generic_puzzle.ClueCell):
			cell_el.attrib["type"] = "clue"
			cell_el.attrib["solution"] = cell.text
			cell_el.attrib["solve-state"] = cell.text
		elif isinstance(cell, generic_puzzle.BlockCell):
			cell_el.attrib["type"] = "block"
		else:
			cell_el.attrib["type"] = "void"
	for word in puzzle.words:
		word_el = ET.SubElement(crossword_el, "word", {
			"id": word.word_id
		})
		for coord in word.cells:
			ET.SubElement(word_el, "cells", {
				"x": str(coord.col + 1),
				"y": str(coord.row + 1)
			})
	for clue_set in puzzle.clues:
		clues_el = ET.Element("clues", {
			"ordering": "normal"
		})
		ET.SubElement(clues_el, "title").text = clue_set.title
		for clue in clue_set.clues:
			clue_el = element_with_raw_html("clue", clue.text, {
				"word": clue.word_id
			})
			if clue.number is not None:
				clue_el.attrib["number"] = clue.number
			clues_el.append(clue_el)
		crossword_el.append(clues_el)
	ET.ElementTree(root).write(file_path, xml_declaration=True, encoding="utf-8")

def bar_attribute(side: crossword.SquareSide) -> str:
	match side:
		case crossword.SquareSide.TOP:
			return "top-bar"
		case crossword.SquareSide.RIGHT:
			return "right-bar"
		case crossword.SquareSide.BOTTOM:
			return "bottom-bar"
		case crossword.SquareSide.LEFT:
			return "left-bar"

def clue_letters(
	rev: dict[tuple[int, int], tuple[str, int]],
	clue_index: int
) -> Generator[tuple[int, tuple[str, int]]]:
	letter_index = 0
	while (clue_index, letter_index) in rev:
		yield (letter_index, rev[clue_index, letter_index])
		letter_index += 1

def to_jpz_acrostic(
	puzzle: acrostic.Acrostic,
	num_cols: int = 3,
	min_width: int = 30
) -> generic_puzzle.Puzzle:
	quote = crossword.FormattableText.from_template(
		t"{puzzle.quote_text}\n\n\u2014 {puzzle.quote_author}, {puzzle.quote_work}" if puzzle.quote_author and puzzle.quote_work
		else t"{puzzle.quote_text}\n\n\u2014 {puzzle.quote_work}" if puzzle.quote_work
		else t"{puzzle.quote_text}\n\n\u2014 {puzzle.quote_author}" if puzzle.quote_author
		else t"{puzzle.quote_text}"
	)
	col_width = max(
		square.clue_word_index + 1
		for square in puzzle.squares
		if isinstance(square, acrostic.LetterSquare
	)) + 1
	width = max((col_width + 1) * num_cols - 1, min_width)
	quote_height = (len(puzzle.squares) - 1) // width + 1
	num_clues = len(puzzle.clues)
	clues_height = (num_clues // num_cols) + (1 if num_clues % num_cols > 0 else 0)
	cell_number = 0
	word_id = 0
	grid: dict[GridCoord, generic_puzzle.Cell] = {}
	rev: dict[tuple[int, int], tuple[str, int]] = {}
	words: list[generic_puzzle.Word] = []

	quote_word: list[GridCoord] = []
	for coord in (
		GridCoord(row, col)
		for row in range(quote_height)
		for col in range(width)
	):
		clue_index = coord.row * width + coord.col
		square = (
			puzzle.squares[clue_index] if clue_index < len(puzzle.squares)
			else acrostic.PunctuationSquare("")
		)
		if isinstance(square, acrostic.LetterSquare):
			grid[coord] = generic_puzzle.EntryCell(
				solution=square.answer,
				number=str(cell_number := cell_number + 1),
				top_right_number=string.ascii_uppercase[square.clue_index]
			)
			rev[square.clue_index, square.clue_word_index] = (square.answer, cell_number)
			quote_word.append(coord)
		elif isinstance(square, acrostic.PunctuationSquare):
			grid[coord] = (
				generic_puzzle.ClueCell(
					text=square.punctuation
				) if len(square.punctuation.strip()) > 0
				else generic_puzzle.BlockCell()
			)
	attrib_row = quote_height + 1
	first_clue_row = attrib_row + 2
	quote_word_id = str(word_id := word_id + 1)
	words.append(generic_puzzle.Word(
		word_id=quote_word_id,
		cells=quote_word
	))

	attrib_word: list[GridCoord] = []
	for clue_index in range(len(puzzle.clues)):
		(first_letter, first_letter_index) = rev[clue_index, 0]
		coord = GridCoord(attrib_row, clue_index)
		grid[coord] = generic_puzzle.EntryCell(
			solution=first_letter,
			number=str(first_letter_index)
		)
		attrib_word.append(coord)
	attrib_word_id = str(word_id := word_id + 1)
	words.append(generic_puzzle.Word(
		word_id=attrib_word_id,
		cells=attrib_word
	))

	clues: list[generic_puzzle.Clue] = []
	for (clue_index, clue) in enumerate(puzzle.clues):
		clue_number = string.ascii_uppercase[clue_index]
		clue_word_id = str(word_id := word_id + 1)
		label_coord = GridCoord(
			col=(col_width + 1) * (clue_index // clues_height),
			row=first_clue_row + (clue_index % clues_height)
		)
		grid[label_coord] = generic_puzzle.ClueCell(clue_number)
		clues.append(generic_puzzle.Clue(
			number=clue_number,
			text=clue,
			word_id=clue_word_id
		))

		clue_word: list[GridCoord] = []
		for (letter_index, (answer, number)) in clue_letters(rev, clue_index):
			coord = GridCoord(
				row=label_coord.row,
				col=label_coord.col + 1 + letter_index
			)
			clue_word.append(coord)
			grid[coord] = generic_puzzle.EntryCell(
				number=str(number),
				solution=answer
			)
		words.append(generic_puzzle.Word(
			word_id=clue_word_id,
			cells=clue_word
		))
	clues.append(generic_puzzle.Clue(
		word_id=quote_word_id,
		text=FormattableText(html="<i>[Quote]</i>")
	))
	clues.append(generic_puzzle.Clue(
		word_id=attrib_word_id,
		text=FormattableText(html="<i>[Attribution]</i>")
	))
	for coord in (
		GridCoord(row, col)
		for row in range(quote_height + 3 + clues_height)
		for col in range(width)
	):
		if coord not in grid:
			grid[coord] = generic_puzzle.VoidCell()
	return generic_puzzle.Puzzle(
		title=puzzle.title,
		creator=puzzle.author,
		copyright=puzzle.copyright,
		completion_message=quote,
		clues=[
			generic_puzzle.ClueList(
				title="Clues",
				clues=clues
			)
		],
		grid=grid,
		words=words,
		puzzle_type="acrostic"
	)