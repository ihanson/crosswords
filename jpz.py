import xml.etree.ElementTree as ET
from lxml import html as lxml_html, etree as lxml_etree
import html
import crossword
import image

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

def save_jpz(puzzle: crossword.Puzzle, file_path: str, shade=image.Color(0xff, 0xff, 0x00)):
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