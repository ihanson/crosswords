class Cell {
	constructor(white, circle, {onArrow, onToggle, onCircle}) {
		this.#div = document.createElement("div");
		this.setWhite(white);
		this.setCircle(circle);
		this.#div.setAttribute("tabindex", "0");
		this.#div.addEventListener("keydown", (e) => {
			if (["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"].includes(e.key)) {
				onArrow(e.key);
				e.preventDefault();
				e.stopPropagation();
			} else if (e.key === " ") {
				onToggle(!this.isWhite(), this);
				e.preventDefault();
				e.stopPropagation();
			} else if (e.key === "o") {
				onCircle(!this.isCircle(), this);
				e.preventDefault();
				e.stopPropagation();
			}
		});
		this.#numberDiv	 = document.createElement("div");
		this.#numberDiv.classList.add("number");
		this.#number = null;
		this.#div.appendChild(this.#numberDiv);
	}

	setWhite(white) {
		this.#white = white;
		this.#div.classList.toggle("white", this.#white);
	}

	setCircle(circle) {
		this.#circle = circle;
		this.#div.classList.toggle("circle", this.#circle);
	}

	isCircle() {
		return this.#circle;
	}

	setNumber(number) {
		this.#number = number;
		this.#numberDiv.innerText = Number.isInteger(number) ? number.toLocaleString() : "";
	}

	number() {
		return this.#number;
	}
	
	focus() {
		this.#div.focus();
	}

	isWhite() {
		return this.#white;
	}

	static fromStateStr(stateStr, events) {
		return new Cell(stateStr !== " ", stateStr === "o", events);
	}

	stateStr() {
		return !this.isWhite() ? " " : (this.isCircle() ? "o" : " ");
	}

	appendToParent(parent) {
		parent.appendChild(this.#div);
	}

	#div;
	#numberDiv;
	#number;
	#white;
	#circle;
}

class Grid {
	constructor() {
		this.#cells = [];
		const state = globalThis.localStorage.getItem("grid")?.split("\n");
		for (let row = 0; row < 15; row++) {
			const rowCells = [];
			for (let col = 0; col < 15; col++) {
				const cell = Cell.fromStateStr(
					state?.[row]?.[col] ?? ".",
					{
						onArrow: ((row, col) => (dir) => {
							this.#cellInDir(row, col, dir).focus();
						})(row, col),
						onToggle: (white, target) => {
							target.setWhite(white);
							this.#oppositeCell(row, col).setWhite(white);
							this.#afterChangeState();
						},
						onCircle: (circle, target) => {
							target.setCircle(circle);
							this.#afterChangeState();
						}
					}
				);
				rowCells.push(cell);
			}
			this.#cells.push(rowCells);
		}
		this.#afterChangeState();
	}

	#cellInDir(row, col, dir) {
		switch (dir) {
			case "ArrowLeft":
				return this.cellAt(row, col > 0 ? col - 1 : this.numCols() - 1);
			case "ArrowRight":
				return this.cellAt(row, col < this.numCols() - 1 ? col + 1 : 0);
			case "ArrowUp":
				return this.cellAt(row > 0 ? row - 1 : this.numRows() - 1, col);
			case "ArrowDown":
				return this.cellAt(row < this.numRows() - 1 ? row + 1 : 0, col);
			default:
				throw new Exception("Invalid direction");
		}
	}

	reset() {
		for (const row of this.#cells) {
			for (const cell of row) {
				cell.setWhite(true);
				cell.setCircle(false);
			}
		}
		this.#afterChangeState();
	}

	numRows() {
		return this.#cells.length;
	}

	numCols() {
		return this.#cells[0].length;
	}

	#oppositeCell(row, col) {
		return this.cellAt(
			this.numRows() - row - 1,
			this.numCols() - col - 1
		);
	}

	#afterChangeState() {
		globalThis.localStorage.setItem("grid", this.gridStr());
		const [across, down] = this.#countCells();
		document.getElementById("result").innerText = `Total entries: ${(across + down).toLocaleString()}`;
	}

	#countCells() {
		let numAcross = 0;
		let numDown = 0;
		let nextNumber = 1;
		for (let row = 0; row < this.numRows(); row++) {
			for (let col = 0; col < this.numCols(); col++) {
				const isAcross = this.#isAcrossStart(row, col);
				const isDown = this.#isDownStart(row, col);
				if (isAcross) {
					numAcross++;
				}
				if (isDown) {
					numDown++;
				}
				this.cellAt(row, col).setNumber(
					isDown || isAcross ? nextNumber++ : ""
				);
			}
		}
		return [numAcross, numDown];
	}

	#isAcrossStart(row, col) {
		const cell = this.cellAt(row, col);
		const before = this.cellAt(row, col - 1);
		const after = this.cellAt(row, col + 1);
		return cell?.isWhite() && !before?.isWhite() && after?.isWhite();
	}

	#isDownStart(row, col) {
		const cell = this.cellAt(row, col);
		const before = this.cellAt(row - 1, col);
		const after = this.cellAt(row + 1, col);
		return cell?.isWhite() && !before?.isWhite() && after?.isWhite();
	}

	gridStr() {
		return this.#cells.map((row) =>
			row.map((cell) =>
				cell.isWhite()
					? (cell.isCircle() ? "o" : ".")
					: " "
			).join("")
		).join("\n");
	}

	appendToParent(parent) {
		const gridDiv = document.createElement("div");
		gridDiv.classList.add("grid");
		for (let row = 0; row < this.numRows(); row++) {
			const rowDiv = document.createElement("div");
			for (let col = 0; col < this.numCols(); col++) {
				this.cellAt(row, col).appendToParent(rowDiv);
			}
			gridDiv.appendChild(rowDiv);
		}
		parent.appendChild(gridDiv);
		this.cellAt(0, 0)?.focus();
	}

	cellAt(row, col) {
		return this.#cells[row]?.[col] ?? null;
	}

	#cells;
}

const grid = new Grid();
grid.appendToParent(document.getElementById("entry"));
document.getElementById("reset").addEventListener("click", () => {
	if (prompt("Are you sure you want to reset? Type yes") === "yes") {
		grid.reset();
	}
});
document.getElementById("copy").addEventListener("click", async () => {
	try {
		await navigator.clipboard.writeText(grid.gridStr())
		alert("Grid copied to clipboard");
	} catch {
		alert("Failed to copy the grid");
	}
});