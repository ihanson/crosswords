from dataclasses import dataclass
from typing import Literal, Optional
import xml.etree.ElementTree as ET
from lib import Color, FormattableText, GridCoord, SquareSide

@dataclass
class JPZPuzzle:
	grid: dict[GridCoord, Cell]
	words: list[Word]
	clues: list[ClueList]
	title: Optional[FormattableText] = None
	creator: Optional[FormattableText] = None
	copyright: Optional[FormattableText] = None
	note: Optional[Note] = None
	completion_message: Optional[FormattableText] = None
	puzzle_type: Literal["crossword"] | Literal["acrostic"] = "crossword"

	def width(self) -> int:
		return max(coord.col for coord in self.grid.keys()) + 1

	def height(self) -> int:
		return max(coord.row for coord in self.grid.keys()) + 1

	def save(self, file_path: str):
		root = ET.Element("crossword-compiler-applet", {
			"xmlns": "http://crossword.info/xml/crossword-compiler"
		})
		settings_el = ET.SubElement(root, "applet-settings")
		if self.completion_message:
			settings_el.append(element_with_raw_html(
				"completion",
				self.completion_message,
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
			("title", self.title),
			("creator", self.creator),
			("copyright", self.copyright)
		]:
			if text is not None:
				metadata.append(element_with_raw_html(tag, text))
		if self.note:
			note_tag = (
				"description" if self.note.show_on_open
				else "instructions"
			)
			metadata.append(element_with_raw_html(note_tag, self.note.text))
		
		crossword_el = ET.SubElement(puzzle_el, self.puzzle_type)
		grid = ET.SubElement(crossword_el, "grid", {
			"width": str(self.width()),
			"height": str(self.height())
		})
		ET.SubElement(grid, "grid-look", {
			"hide-lines": "true"
		})
		for (coord, cell) in sorted(self.grid.items()):
			cell_el = ET.SubElement(grid, "cell", {
				"x": str(coord.col + 1),
				"y": str(coord.row + 1)
			})
			if isinstance(cell, EntryCell):
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
				for side in SquareSide:
					if side in cell.bars:
						cell_el.attrib[bar_attribute(side)] = "true"
			elif isinstance(cell, ClueCell):
				cell_el.attrib["type"] = "clue"
				cell_el.attrib["solution"] = cell.text
				cell_el.attrib["solve-state"] = cell.text
			elif isinstance(cell, BlockCell):
				cell_el.attrib["type"] = "block"
			else:
				cell_el.attrib["type"] = "void"
		for word in self.words:
			word_el = ET.SubElement(crossword_el, "word", {
				"id": word.word_id
			})
			for coord in word.cells:
				ET.SubElement(word_el, "cells", {
					"x": str(coord.col + 1),
					"y": str(coord.row + 1)
				})
		for clue_set in self.clues:
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

@dataclass
class Note:
	text: FormattableText
	show_on_open: bool = False

@dataclass
class Cell:
	pass

@dataclass
class EntryCell(Cell):
	solution: Optional[str] = None
	number: Optional[str] = None
	top_right_number: Optional[str] = None
	is_circled: bool = False
	color: Optional[Color] = None
	bars: frozenset[SquareSide] = frozenset()

@dataclass
class ClueCell(Cell):
	text: str

@dataclass
class BlockCell(Cell):
	pass

@dataclass
class VoidCell(Cell):
	pass

@dataclass
class Word:
	word_id: str
	cells: list[GridCoord]

@dataclass
class ClueList:
	title: str
	clues: list[Clue]

@dataclass
class Clue:
	text: FormattableText
	word_id: str
	number: Optional[str] = None

def element_with_raw_html(tag: str, text: FormattableText, attrs: dict[str, str] = {}):
	xml_ish = f"<{tag}>{text.html}</{tag}>"
	element = ET.fromstring(xml_ish)
	for (attr, value) in attrs.items():
		element.set(attr, value)
	return element

def bar_attribute(side: SquareSide) -> str:
	match side:
		case SquareSide.TOP:
			return "top-bar"
		case SquareSide.RIGHT:
			return "right-bar"
		case SquareSide.BOTTOM:
			return "bottom-bar"
		case SquareSide.LEFT:
			return "left-bar"