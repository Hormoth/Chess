from PySide6.QtWidgets import QListWidget

class MoveListWidget(QListWidget):
    def set_last_moves(self, pgn_text: str, last_n: int = 6):
        moves = [m for m in pgn_text.strip().split() if m]
        self.clear()
        for m in moves[-last_n:]:
            self.addItem(m)
