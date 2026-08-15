from PIL import Image, ImageDraw, ImageFont
import crossword

from lib import Color, SquareSide

Black = Color(0x00, 0x00, 0x00)
White = Color(0xff, 0xff, 0xff)
Gray = Color(0x80, 0x80, 0x80)

def square_color(square: crossword.Square) -> Color:
	return (
		(square.color or White) if isinstance(square, crossword.WhiteSquare)
		else Black
	)

def draw_grid(
	grid: crossword.Grid,
	file_path: str,
	size: int = 60
):
	SCALE = 2
	SIZE_FACTOR = 0.8
	size *= SCALE
	FONT_NAME = "arial.ttf"
	width = size * grid.cols() + 1
	height = size * grid.rows() + 1
	image = Image.new("RGBA", (width, height))
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
			outline=Gray.to_pixel(),
			fill=square_color(square).to_pixel(),
			width=SCALE
		)
		if isinstance(square, crossword.WhiteSquare) and square.is_circled:
			draw.ellipse(
				xy=xy,
				outline=Black.to_pixel(),
				width=SCALE
			)
		if isinstance(square, crossword.WhiteSquare):
			if square.answer is not None:
				text_width = font.getlength(square.answer)
				draw.text(
					xy=(
						col * size + (size / 2),
						row * size + (size / 2)
					),
					text=square.answer,
					fill = Black.to_pixel(),
					font = (
						font if text_width <= size * SIZE_FACTOR
						else ImageFont.truetype(
							FONT_NAME, int((size * SIZE_FACTOR) ** 2 / text_width)
						)
					),
					anchor = "mm"
				)
			for side in SquareSide:
				if side in square.bars:
					bars.append(border_line(xy, side))

	for xy in bars:
		draw.line(
			xy,
			fill=Black.to_pixel(),
			width=4 * SCALE
		)
	x = image.resize((width // SCALE, height // SCALE)) # type: ignore
	x.save(file_path, "PNG")

def border_line(
	corners_xy: tuple[tuple[float, float], tuple[float,float]],
	side: SquareSide
) -> tuple[tuple[float, float], tuple[float, float]]:
	((x1, y1), (x2, y2)) = corners_xy
	match side:
		case SquareSide.TOP:
			return ((x1, y1), (x2, y1))
		case SquareSide.RIGHT:
			return ((x2, y1), (x2, y2))
		case SquareSide.BOTTOM:
			return ((x1, y2), (x2, y2))
		case SquareSide.LEFT:
			return ((x1, y1), (x1, y2))