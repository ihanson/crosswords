from io import BufferedReader
import struct
from unidecode import unidecode
from collections.abc import Callable
import crossword

ENCODING = "ISO-8859-1"
MAGIC_STRING = b"ACROSS&DOWN\x00"

class ByteGrid(object):
	def __init__(self, grid: bytes, width: int):
		self.__grid = grid
		self.__width = width

	@property
	def bytes(self):
		return self.__grid

	@property
	def width(self):
		return self.__width

	@property
	def height(self):
		return len(self.bytes) // self.width

	def __getitem__(self, index: tuple[int, int]):
		(row, col) = index
		return self.bytes[row * self.width + col]

class CString(object):
	def __init__(self, string: str | bytes):
		self.__bytes: bytes = (unidecode(string).encode(ENCODING) + b"\x00") if isinstance(string, str) else string
		if self.__bytes[-1] != 0:
			raise Exception("String is not null-terminated")

	@staticmethod
	def read(reader: BufferedReader):
		data = b""
		while True:
			byte = reader.read(1)
			data += byte
			if byte == b"\x00" or len(byte) == 0:
				break
		return CString(data)
		

	def __str__(self):
		return self.bytes[:-1].decode(ENCODING)

	def __repr__(self):
		return f"CString({self})"

	def __len__(self):
		return len(self.bytes) - 1

	@property
	def bytes(self):
		return self.__bytes

	def optional(self):
		return str(self) if len(self) > 0 else None

def read_extra_sections(reader: BufferedReader):
	sections: dict[bytes, bytes] = {}
	while len(title := reader.read(0x04)) > 0:
		(length, checksum) = struct.unpack("<HH", reader.read(0x04))
		data = reader.read(length)
		if cksum_region(data) != checksum:
			raise Exception("Invalid extra data checksum")
		if reader.read(1) != b"\x00":
			raise Exception("Extra data is not null-terminated")
		sections[title] = data
	return sections

def encode_extra_section(name: bytes, data: bytes):
	return struct.pack(
		"<4sHH",
		name, len(data), cksum_region(data)
	) + data + b"\x00"

def encode_circles(grid: crossword.Grid):
	data: list[int] = []
	num_circles = 0
	for row in range(grid.rows):
		for col in range(grid.cols):
			square = grid[row, col]
			if isinstance(square, crossword.WhiteSquare) and (square.is_circled or square.is_shaded):
				data.append(0x80)
				num_circles += 1
			else:
				data.append(0x00)
	return (num_circles, bytes(data))

def cksum_region(data: bytes, init: int = 0):
	checksum = init
	for byte in data:
		if checksum & 0x0001 == 1:
			checksum = (checksum >> 1) + 0x8000
		else:
			checksum = checksum >> 1
		checksum += byte
		checksum %= 0x10000
	return checksum

def string_checksum(
	title: CString, author: CString, copyright: CString,
	clues: list[CString], notes: CString,
	init: int = 0
):
	checksum = init
	if len(title) > 0:
		checksum = cksum_region(title.bytes, checksum)
	if len(author) > 0:
		checksum = cksum_region(author.bytes, checksum)
	if len(copyright) > 0:
		checksum = cksum_region(copyright.bytes, checksum)
	for clue in clues:
		checksum = cksum_region(clue.bytes[:-1], checksum)
	if len(notes) > 0:
		checksum = cksum_region(notes.bytes, checksum)
	return checksum

def overall_checksum(
	cib: bytes, solution: ByteGrid, state: ByteGrid,
	title: CString, author: CString, copyright: CString,
	clues: list[CString], notes: CString
):
	checksum = cksum_region(cib)
	checksum = cksum_region(solution.bytes, checksum)
	checksum = cksum_region(state.bytes, checksum)
	return string_checksum(title, author, copyright, clues, notes, checksum)

def masked_checksums(
	cib: bytes, solution: ByteGrid, state: ByteGrid,
	title: CString, author: CString, copyright: CString,
	clues: list[CString], notes: CString
):
	c_cib = cksum_region(cib)
	c_sol = cksum_region(solution.bytes)
	c_grid = cksum_region(state.bytes)
	c_part = string_checksum(title, author, copyright, clues, notes)
	return bytes([
		0x49 ^ (c_cib & 0xff),
		0x43 ^ (c_sol & 0xff),
		0x48 ^ (c_grid & 0xff),
		0x45 ^ (c_part & 0xff),
		0x41 ^ ((c_cib & 0xff00) >> 8),
		0x54 ^ ((c_sol & 0xff00) >> 8),
		0x45 ^ ((c_grid & 0xff00) >> 8),
		0x44 ^ ((c_part & 0xff00) >> 8)
	])

def read_rebuses(grbs: ByteGrid, rtbl: bytes) -> dict[tuple[int, int], str]:
	solutions = {
		int(key) + 1: value
		for [key, value] in (
			entry.split(":")
			for entry in rtbl.decode(ENCODING).split(";")
			if ":" in entry
		)
	}
	return {
		(row, col): solutions[grbs[row, col]]
		for col in range(grbs.width) for row in range(grbs.height)
		if grbs[row, col] != 0
	}

def load_clues(grid: crossword.Grid, clue_list: list[CString]):
	across: dict[int, crossword.Clue] = {}
	down: dict[int, crossword.Clue] = {}
	clue_queue = clue_list[::-1]
	clue_num = 1
	for row in range(grid.rows):
		for col in range(grid.cols):
			is_across = grid.is_across_start(row, col)
			is_down = grid.is_down_start(row, col)
			if is_across or is_down:
				if is_across:
					across[clue_num] = crossword.Clue(str(clue_queue.pop()))
				if is_down:
					down[clue_num] = crossword.Clue(str(clue_queue.pop()))
				clue_num += 1
	return (across, down)

def all_clues(puzzle: crossword.Puzzle):
	clues: list[CString] = []
	clue_num = 1
	for row in range(puzzle.grid.rows):
		for col in range(puzzle.grid.cols):
			is_across = puzzle.grid.is_across_start(row, col)
			is_down = puzzle.grid.is_down_start(row, col)
			if is_across or is_down:
				if is_across:
					clues.append(CString(puzzle.across_clues[clue_num].clue))
				if is_down:
					clues.append(CString(puzzle.down_clues[clue_num].clue))
				clue_num += 1
	return clues

def encode_grid(grid: crossword.Grid, map_func: Callable[[crossword.Square], int]):
	result: list[int] = []
	for row in range(grid.rows):
		for col in range(grid.cols):
			result.append(map_func(grid[row, col]))
	return ByteGrid(bytes(result), grid.cols)

def load_puz(file_path: str) -> crossword.Puzzle:
	with open(file_path, "rb") as reader:
		(
			checksum, magic, cib_checksum, masked, _, _, _, _
		) = struct.unpack("<H12sH8s4sHH12s", reader.read(0x2c))
		cib = reader.read(0x8)
		(
			width, height, num_clues, _, scrambled
		) = struct.unpack("<BBH2sH", cib)
		solution = ByteGrid(reader.read(width * height), width)
		state = ByteGrid(reader.read(width * height), width)
		title = CString.read(reader)
		author = CString.read(reader)
		copyright = CString.read(reader)
		clues: list[CString] = []
		for _ in range(num_clues):
			clues.append(CString.read(reader))
		notes = CString.read(reader)
		extra_sections = read_extra_sections(reader)
	
	if magic != MAGIC_STRING:
		raise Exception("This is not a PUZ file")
	if cksum_region(cib) != cib_checksum:
		raise Exception("Invalid CIB checksum")
	if overall_checksum(
		cib, solution, state,
		title, author, copyright, clues, notes
	) != checksum:
		raise Exception("Invalid overall checksum")
	if masked_checksums(
		cib, solution, state,
		title, author, copyright, clues, notes
	) != masked:
		raise Exception("Invalid masked checksum")
	if scrambled != 0:
		raise Exception("Puzzle is scrambled")
	
	rebuses = read_rebuses(
		ByteGrid(extra_sections[b"GRBS"], width),
		extra_sections[b"RTBL"]
	) if b"GRBS" in extra_sections and b"RTBL" in extra_sections else {}
	circles = (
		ByteGrid(extra_sections[b"GEXT"], width)
	) if b"GEXT" in extra_sections else None

	grid = crossword.Grid([[
		crossword.BlackSquare() if solution[row, col] == 0x2e
		else crossword.WhiteSquare(
			answer=(
				rebuses[row, col] if (row, col) in rebuses
				else bytes([solution[row, col]]).decode(ENCODING)
			),
			is_circled=circles is not None and circles[row, col] & 0x80 != 0
		) for col in range(width)
	] for row in range(height)])
	(across, down) = load_clues(grid, clues)
	
	return crossword.Puzzle(
		grid, across, down,
		title.optional(), author.optional(), copyright.optional(), notes.optional()
	)

def save_puz(puzzle: crossword.Puzzle, file_path: str):
	num_clues = len(puzzle.across_clues) + len(puzzle.down_clues)
	cib = struct.pack(
		"<BBH2sH",
		puzzle.grid.cols, puzzle.grid.rows, num_clues,
		b"\x01\x00", 0
	)
	solution = encode_grid(
		puzzle.grid,
		lambda square: ((square.answer or " ").encode(ENCODING) if isinstance(square, crossword.WhiteSquare) else b".")[0]
	)
	state = encode_grid(
		puzzle.grid,
		lambda square: (b"-" if isinstance(square, crossword.WhiteSquare) else b".")[0]
	)
	title = CString(puzzle.title or "")
	author = CString(puzzle.author or "")
	copyright = CString(puzzle.copyright or "")
	clues = all_clues(puzzle)
	notes = CString(puzzle.note or "")
	rebus_grid: list[int] = []
	rebuses: list[tuple[int, str]] = []
	rebus_index = 0
	for row in range(puzzle.grid.rows):
		for col in range(puzzle.grid.cols):
			square = puzzle.grid[row, col]
			if isinstance(square, crossword.WhiteSquare) and square.answer is not None and len(square.answer) > 1:
				value = rebus_index + 1
				rebuses.append((rebus_index, square.answer))
				rebus_index += 1
			else:
				value = 0
			rebus_grid.append(value)
	extra_sections = b""
	if len(rebuses) > 0:
		extra_sections += encode_extra_section(
			b"GRBS",
			bytes(rebus_grid)
		)
		extra_sections += encode_extra_section(
			b"RTBL",
			";".join([f"{index: >2}:{rebus}" for (index, rebus) in rebuses] + [""]).encode(ENCODING)
		)
	(num_circles, circles) = encode_circles(puzzle.grid)
	if num_circles > 0:
		extra_sections += encode_extra_section(b"GEXT", circles)
	with open(file_path, "wb") as writer:
		writer.write(struct.pack(
			"<H12sH8s4sHH12s",
			overall_checksum(cib, solution, state, title, author, copyright, clues, notes),
			MAGIC_STRING, cksum_region(cib),
			masked_checksums(cib, solution, state, title, author, copyright, clues, notes),
			b"2.0\x00", 0, 0,
			b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		))
		writer.write(cib)
		writer.write(solution.bytes)
		writer.write(state.bytes)
		writer.write(title.bytes)
		writer.write(author.bytes)
		writer.write(copyright.bytes)
		for clue in clues:
			writer.write(clue.bytes)
		writer.write(notes.bytes)
		writer.write(extra_sections)