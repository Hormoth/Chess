from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton
from PySide6.QtCore import Signal
import chess

PIECE_TO_UNICODE = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}

class ChessBoardWidget(QWidget):
    squareClicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChessBoardWidget")

        self.grid = QGridLayout(self)
        self.grid.setSpacing(0)
        self.grid.setContentsMargins(0, 0, 0, 0)

        self.buttons: dict[str, QPushButton] = {}
        self._selected: str | None = None
        self._destinations: set[str] = set()

        # Better board colors (readable with both piece colors)
        self.light_sq = "#f0d9b5"   # classic light
        self.dark_sq  = "#b58863"   # classic dark

        for r in range(8):
            for c in range(8):
                btn = QPushButton("")
                btn.setFixedSize(56, 56)
                btn.setFlat(True)

                sq = chess.square(c, 7 - r)
                name = chess.square_name(sq)

                btn.clicked.connect(lambda _, n=name: self.squareClicked.emit(n))

                is_light = (r + c) % 2 == 0
                btn.setProperty("light", is_light)

                self.buttons[name] = btn
                self.grid.addWidget(btn, r, c)

        self._refresh_styles()  # sets initial colors

    # ---------- Public API ----------
    def clear_highlights(self):
        self._selected = None
        self._destinations = set()
        self._refresh_styles()

    def highlight_squares(self, selected: str, destinations: list[str] | set[str]):
        self._selected = selected
        self._destinations = set(destinations)
        self._refresh_styles()

    def set_fen(self, fen: str):
        board = chess.Board() if fen in ("", "startpos") else chess.Board(fen)

        for sq_name, btn in self.buttons.items():
            sq = chess.parse_square(sq_name)
            piece = board.piece_at(sq)

            if piece:
                btn.setText(PIECE_TO_UNICODE.get(piece.symbol(), ""))
                # Explicit per-piece color
                btn.setProperty("pieceColor", "white" if piece.color == chess.WHITE else "black")
            else:
                btn.setText("")
                btn.setProperty("pieceColor", "none")

        self._refresh_styles()

    # ---------- Internal ----------
    def _refresh_styles(self):
        # One place to build the style so colors ALWAYS apply correctly
        for name, btn in self.buttons.items():
            is_light = bool(btn.property("light"))
            bg = self.light_sq if is_light else self.dark_sq

            border = "none"
            if self._selected and name == self._selected:
                border = "3px solid #22c55e"  # green
            elif name in self._destinations:
                border = "3px solid #f59e0b"  # amber

            piece_color_prop = btn.property("pieceColor")
            if piece_color_prop == "white":
                fg = "#ffffff"
            elif piece_color_prop == "black":
                # not pure black so it reads on dark squares too
                fg = "#111827"  # gray-900
            else:
                fg = "#00000000"  # transparent-ish; irrelevant when no text

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {fg};
                    border: {border};
                    font-size: 30px;
                    padding: 0px;
                    margin: 0px;
                }}
                QPushButton:hover {{
                    border: 1px solid rgba(0,0,0,0.25);
                }}
            """)
