from enum import Enum
from typing import Self
import math
from PIL import Image, ImageDraw, ImageFont
import crossword

class Shade(Enum):
	BLACK = 0,
	WHITE = 1,
	SHADED = 2

Pixel = tuple[int, int, int, int]

class Color(object):
	def __init__(self, red: int, green: int, blue: int):
		self.__red = red
		self.__green = green
		self.__blue = blue
	
	@staticmethod
	def from_pixel(pixel: Pixel):
		(red, green, blue, _) = pixel
		return Color(red, green, blue)
	
	def to_pixel(self):
		return (self.__red, self.__green, self.__blue, 0xff)

	def __str__(self):
		return f"({self.__red}, {self.__green}, {self.__blue})"

	def distance(self, other: Self):
		return math.sqrt(
			(self.__red - other.__red) ** 2
			+ (self.__green - other.__green) ** 2
			+ (self.__blue - other.__blue) ** 2
		)

	def hex(self):
		return f"#{self.__red:0>2x}{self.__green:0>2x}{self.__blue:0>2x}"

def shaded_square(shade: Shade, answer: str | None):
	return (
		crossword.BlackSquare() if shade == Shade.BLACK
		else crossword.WhiteSquare(answer, is_shaded = (shade == Shade.SHADED))
	)

def square_to_shade(square: crossword.Square):
	return (
		Shade.BLACK if isinstance(square, crossword.BlackSquare)
		else Shade.SHADED if isinstance(square, crossword.WhiteSquare) and square.is_shaded
		else Shade.WHITE
	)

class ColorMap(object):
	def __init__(self, black: Color, white: Color, shaded: Color):
		self.__colors = {
			Shade.BLACK: black,
			Shade.WHITE: white,
			Shade.SHADED: shaded
		}

	def map_pixel(self, color: Color, answer: str | None, tolerance: float = 0.05):
		distances = [
			(shade, def_color.distance(color))
			for (shade, def_color) in self.__colors.items()
		]
		(closest_shade, closest_dist) = min(distances, key=lambda dist: dist[1])
		if closest_dist / 0xff > tolerance:
			raise Exception(f"Unrecognized color: {color} (distance = {closest_dist})")
		return shaded_square(closest_shade, answer)

	def __getitem__(self, square: Shade):
		return self.__colors[square]

def read_image(
	file_path: str,
	start_coord: tuple[int, int],
	square_width: float,
	square_height: float,
	rows: int,
	cols: int,
	colors: ColorMap,
	answer: list[str]
) -> crossword.Grid:
	(start_x, start_y) = start_coord
	with Image.open(file_path) as image:
		return crossword.Grid([
			[
				colors.map_pixel(
					Color.from_pixel(
						get_pixel(
							image,
							int(start_x + square_width * col),
							int(start_y + square_height * row)
						)
					),
					answer[row][col] if answer[row][col] != " " else None
				) for col in range(cols)
			] for row in range(rows)
		])

def get_pixel(image: Image.Image, x: int, y: int) -> Pixel:
	pixel = image.getpixel((x, y))
	assert isinstance(pixel, tuple)
	assert len(pixel) == 4
	return pixel

def draw_grid(
	grid: crossword.Grid,
	file_path: str,
	size: int = 30,
	colors: ColorMap = ColorMap(
		Color(0x00, 0x00, 0x00),
		Color(0xff, 0xff, 0xff),
		Color(0xc0, 0xc0, 0xc0)
	)
):
	SIZE_FACTOR = 0.8
	FONT_NAME = "arial.ttf"
	image = Image.new("RGBA", (size * grid.cols + 1, size * grid.rows + 1))
	draw = ImageDraw.Draw(image)
	font = ImageFont.truetype(FONT_NAME, int(size * SIZE_FACTOR))
	for row in range(grid.rows):
		for col in range(grid.cols):
			square = grid[row, col]
			xy = [
				(col * size, row * size),
				((col + 1) * size, (row + 1) * size)
			]
			draw.rectangle(
				xy=xy,
				outline=colors[Shade.BLACK].to_pixel(),
				fill=colors[square_to_shade(square)].to_pixel()
			)
			if isinstance(square, crossword.WhiteSquare) and square.is_circled:
				draw.ellipse(
					xy=xy,
					outline=colors[Shade.BLACK].to_pixel()
				)
			if isinstance(square, crossword.WhiteSquare) and square.answer is not None:
				width = font.getlength(square.answer)
				draw.text(
					xy=(
						col * size + (size / 2),
						row * size + (size / 2)
					),
					text=square.answer,
					fill = colors[Shade.BLACK].to_pixel(),
					font = (
						font if width <= size * SIZE_FACTOR
						else ImageFont.truetype(
							FONT_NAME, int((size * SIZE_FACTOR) ** 2 / width)
						)
					),
					anchor = "mm"
				)
	image.save(file_path, "PNG")