from PIL import Image, ImageDraw, ImageFont
import crossword

Pixel = tuple[int, int, int, int]

class Color(object):
	def __init__(self, red: int, green: int, blue: int):
		self.__red = red
		self.__green = green
		self.__blue = blue
	
	def to_pixel(self):
		return (self.__red, self.__green, self.__blue, 0xff)

	def __str__(self):
		return f"({self.__red}, {self.__green}, {self.__blue})"

	def hex(self):
		return f"#{self.__red:0>2x}{self.__green:0>2x}{self.__blue:0>2x}"

	Black: Color
	White: Color
	Gray: Color

Color.Black = Color(0x00, 0x00, 0x00)
Color.White = Color(0xff, 0xff, 0xff)
Color.Gray = Color(0x80, 0x80, 0x80)

def square_color(square: crossword.Square) -> Color:
	return (
		(square.color or Color.White) if isinstance(square, crossword.WhiteSquare)
		else Color.Black
	)

def draw_grid(
	grid: crossword.Grid,
	file_path: str,
	size: int = 60
):
	SIZE_FACTOR = 0.8
	FONT_NAME = "arial.ttf"
	image = Image.new("RGBA", (size * grid.cols + 1, size * grid.rows + 1))
	draw = ImageDraw.Draw(image)
	font = ImageFont.truetype(FONT_NAME, int(size * SIZE_FACTOR))
	bars: list[tuple[tuple[float, float], tuple[float,float]]] = []
	for ((row, col), square) in grid:
		xy = (
			(col * size, row * size),
			((col + 1) * size, (row + 1) * size)
		)
		draw.rectangle(
			xy=xy,
			outline=Color.Gray.to_pixel(),
			fill=square_color(square).to_pixel()
		)
		if isinstance(square, crossword.WhiteSquare) and square.is_circled:
			draw.ellipse(
				xy=xy,
				outline=Color.Black.to_pixel()
			)
		if isinstance(square, crossword.WhiteSquare):
			if square.answer is not None:
				width = font.getlength(square.answer)
				draw.text(
					xy=(
						col * size + (size / 2),
						row * size + (size / 2)
					),
					text=square.answer,
					fill = Color.Black.to_pixel(),
					font = (
						font if width <= size * SIZE_FACTOR
						else ImageFont.truetype(
							FONT_NAME, int((size * SIZE_FACTOR) ** 2 / width)
						)
					),
					anchor = "mm"
				)
			for side in crossword.SquareSide:
				if square.has_bar(side):
					bars.append(border_line(xy, side))

	for xy in bars:
		draw.line(
			xy,
			fill=Color.Black.to_pixel(),
			width=4
		)
	image.save(file_path, "PNG")

def border_line(
	corners_xy: tuple[tuple[float, float], tuple[float,float]],
	side: crossword.SquareSide
) -> tuple[tuple[float, float], tuple[float, float]]:
	((x1, y1), (x2, y2)) = corners_xy
	match side:
		case crossword.SquareSide.TOP:
			return ((x1, y1), (x2, y1))
		case crossword.SquareSide.RIGHT:
			return ((x2, y1), (x2, y2))
		case crossword.SquareSide.BOTTOM:
			return ((x1, y2), (x2, y2))
		case crossword.SquareSide.LEFT:
			return ((x1, y1), (x1, y2))