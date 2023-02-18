from typing import Tuple
import xml.etree.ElementTree as ET
from lxml import html as lxml_html, etree as lxml_etree
import html
import crossword
import acrostic
import image
import string

NUM_COLS = 3
GRID_WORD_ID = "1000"
ATTRIB_WORD_ID = "1001"

def element_with_raw_html(tag: str, raw_html: str | None, alternative_text: str):
	html_str = f"<{tag}>{raw_html}</{tag}>"
	if raw_html is not None:	
		try:
			return ET.fromstring(lxml_etree.tostring(lxml_html.fromstring(html_str)))
		except:
			pass
	element = ET.Element(tag)
	element.text = alternative_text
	return element

def clue_element(clue: crossword.Clue, word_id: int, clue_number: int):
	element = element_with_raw_html("clue", clue.clue_html, clue.clue)
	element.attrib = {
		"word": str(word_id),
		"number": str(clue_number)
	}
	return element

def save_crossword_jpz(puzzle: crossword.Puzzle, file_path: str, shade=image.Color(0xff, 0xff, 0x00)):
	root = ET.Element("crossword-compiler-applet", {
		"xmlns": "http://crossword.info/xml/crossword-compiler"
	})
	puzzle_el = ET.SubElement(root, "rectangular-puzzle", {
		"xmlns": "http://crossword.info/xml/rectangular-puzzle",
		"alphabet": "ABCDEFGHIJIKLMNOPQRSTUVWXYZ"
	})
	metadata = ET.SubElement(puzzle_el, "metadata")
	if puzzle.title is not None:
		ET.SubElement(metadata, "title").text = puzzle.title
	if puzzle.author is not None:
		ET.SubElement(metadata, "creator").text = puzzle.author
	if puzzle.copyright is not None:
		ET.SubElement(metadata, "copyright").text = puzzle.copyright
	if puzzle.note is not None:
		note_html = html.escape(puzzle.note).replace("\n", "<br>")
		metadata.append(element_with_raw_html("description", note_html, puzzle.note))
	
	crossword_el = ET.SubElement(puzzle_el, "crossword")
	grid = ET.SubElement(crossword_el, "grid", {
		"width": str(puzzle.grid.cols),
		"height": str(puzzle.grid.rows)
	})
	ET.SubElement(grid, "grid-look", {
		"hide-lines": "true"
	})
	word_count = 0
	clue_count = 0
	across_clues = ET.Element("clues", {
		"ordering": "normal"
	})
	ET.SubElement(across_clues, "title").text = "Across"
	down_clues = ET.Element("clues", {
		"ordering": "normal"
	})
	ET.SubElement(down_clues, "title").text = "Down"
	for row in range(puzzle.grid.rows):
		for col in range(puzzle.grid.cols):
			square = puzzle.grid[row, col]
			cell = ET.SubElement(grid, "cell", {
				"x": str(col + 1),
				"y": str(row + 1)
			})
			if isinstance(square, crossword.WhiteSquare):
				if square.answer is not None:
					cell.attrib["solution"] = square.answer
				if square.is_circled:
					cell.attrib["background-shape"] = "circle"
				if square.is_shaded:
					cell.attrib["background-color"] = shade.hex()
			else:
				cell.attrib["type"] = "block"
			is_across = puzzle.grid.is_across_start(row, col)
			is_down = puzzle.grid.is_down_start(row, col)
			if is_across or is_down:
				clue_count += 1
				cell.attrib["number"] = str(clue_count)
				if is_across:
					word_count += 1
					word = ET.SubElement(crossword_el, "word", {
						"id": str(word_count)
					})
					acr_col = col
					while puzzle.grid.can_enter(row, acr_col):
						ET.SubElement(word, "cells", {
							"x": str(acr_col + 1),
							"y": str(row + 1)
						})
						acr_col += 1
					across_clues.append(clue_element(puzzle.across_clues[clue_count], word_count, clue_count))
				if is_down:
					word_count += 1
					word = ET.SubElement(crossword_el, "word", {
						"id": str(word_count)
					})
					down_row = row
					while puzzle.grid.can_enter(down_row, col):
						ET.SubElement(word, "cells", {
							"x": str(col + 1),
							"y": str(down_row + 1)
						})
						down_row += 1
					down_clues.append(clue_element(puzzle.down_clues[clue_count], word_count, clue_count))
	crossword_el.append(across_clues)
	crossword_el.append(down_clues)
	ET.ElementTree(root).write(file_path, xml_declaration=True, encoding="utf-8")

def save_acrostic_jpz(puzzle: acrostic.Acrostic, file_path: str):
	root = ET.Element("crossword-compiler-applet", {
		"xmlns": "http://crossword.info/xml/crossword-compiler"
	})
	settings_el = ET.SubElement(root, "applet-settings")
	ET.SubElement(settings_el, "completion", {
		"only-if-correct": "true"
	}).text = f"{puzzle.quote_text}\n\n\u2014 {puzzle.quote_author}, {puzzle.quote_work}"
	actions_el = ET.SubElement(settings_el, "actions")
	ET.SubElement(actions_el, "reveal-word")
	ET.SubElement(actions_el, "reveal-letter")
	ET.SubElement(actions_el, "solution")
	puzzle_el = ET.SubElement(root, "rectangular-puzzle", {
		"xmlns": "http://crossword.info/xml/rectangular-puzzle"
	})
	metadata_el = ET.SubElement(puzzle_el, "metadata")
	ET.SubElement(metadata_el, "title").text = puzzle.title
	ET.SubElement(metadata_el, "creator").text = puzzle.author
	ET.SubElement(metadata_el, "copyright").text = puzzle.copyright
	acrostic_el = ET.SubElement(puzzle_el, "acrostic")
	col_width = max(
		square.clue_word_index + 1 for square in puzzle.squares
		if isinstance(square, acrostic.LetterSquare
	)) + 1
	width = max((col_width + 1) * NUM_COLS - 1, 30)
	quote_height = (len(puzzle.squares) - 1) // width + 1
	clue_height = (len(puzzle.clues) // NUM_COLS) + (len(puzzle.clues) % NUM_COLS)
	height = quote_height + 3 + clue_height
	grid_el = ET.SubElement(acrostic_el, "grid", {
		"width": str(width),
		"height": str(height)
	})
	ET.SubElement(grid_el, "grid-look", {
		"numbering-scheme": "normal"
	})
	clues_el = ET.Element("clues")
	ET.SubElement(clues_el, "title").text = "Clues"
	count = 0
	cells: dict[Tuple[int, int], ET.Element] = {}
	rev: dict[Tuple[int, int], Tuple[str, int]] = {}
	grid_word: list[Tuple[int, int]] = []
	for y in range(quote_height):
		for x in range(width):
			clue_index = y * width + x
			square = (
				puzzle.squares[clue_index] if clue_index < len(puzzle.squares)
				else acrostic.PunctuationSquare(" ")
			)
			if isinstance(square, acrostic.LetterSquare):
				count += 1
				cells[(x, y)] = ET.Element("cell", {
					"solution": square.answer,
					"number": str(count),
					"top-right-number": string.ascii_uppercase[square.clue_index]
				})
				rev[(square.clue_index, square.clue_word_index)] = (square.answer, count)
				grid_word.append((x, y))
			elif isinstance(square, acrostic.PunctuationSquare):
				cells[(x, y)] = ET.Element("cell", {
					"type": "block"
				}) if square.punctuation == " " else ET.Element("cell", {
					"solution": square.punctuation,
					"type": "clue",
					"solve-state": square.punctuation
				})
	attrib_row = quote_height + 1
	first_clue_row = attrib_row + 2
	attrib_word_el = ET.SubElement(acrostic_el, "word", {
		"id": ATTRIB_WORD_ID
	})
	for clue_index in range(len(puzzle.clues)):
		(first_letter, first_letter_index) = rev[(clue_index, 0)]
		cells[(clue_index, attrib_row)] = ET.Element("cell", {
			"solution": first_letter,
			"number": str(first_letter_index)
		})
		ET.SubElement(attrib_word_el, "cells", {
			"x": str(clue_index + 1),
			"y": str(attrib_row + 1)
		})
		clue_x = (col_width + 1) * (clue_index // clue_height)
		clue_y = first_clue_row + (clue_index % clue_height)
		cells[(clue_x, clue_y)] = ET.Element("cell", {
			"solution": string.ascii_uppercase[clue_index],
			"type": "clue",
			"solve-state": string.ascii_uppercase[clue_index]
		})
		ET.SubElement(clues_el, "clue", {
			"word": str(clue_index),
			"number": string.ascii_uppercase[clue_index]
		}).text = puzzle.clues[clue_index]
		word_el = ET.SubElement(acrostic_el, "word", {
			"id": str(clue_index)
		})
		clue_word_index = 0
		while (clue_index, clue_word_index) in rev:
			(answer, letter_index) = rev[(clue_index, clue_word_index)]
			cells[(clue_x + clue_word_index + 1, clue_y)] = ET.Element("cell", {
				"solution": answer,
				"number": str(letter_index)
			})
			ET.SubElement(word_el, "cells", {
				"x": str(clue_x + clue_word_index + 2),
				"y": str(clue_y + 1)
			})
			clue_word_index += 1

	grid_word_el = ET.SubElement(acrostic_el, "word", {
		"id": GRID_WORD_ID
	})
	for y in range(height):
		for x in range(width):
			if (x, y) in cells:
				cell = cells[(x, y)]
				cell.attrib["x"] = str(x + 1)
				cell.attrib["y"] = str(y + 1)
				grid_el.append(cell)
			else:
				ET.SubElement(grid_el, "cell", {
					"x": str(x + 1),
					"y": str(y + 1),
					"type": "void"
				})
	for (x, y) in grid_word:
		ET.SubElement(grid_word_el, "cells", {
			"x": str(x + 1),
			"y": str(y + 1)
		})
	ET.SubElement(clues_el, "clue", {
		"word": GRID_WORD_ID,
		"number": ""
	}).text = "[Quote]"
	ET.SubElement(clues_el, "clue", {
		"word": ATTRIB_WORD_ID,
		"number": ""
	}).text = "[Author and title]"
	acrostic_el.append(clues_el)
	ET.ElementTree(root).write(file_path, xml_declaration=True, encoding="utf-8")