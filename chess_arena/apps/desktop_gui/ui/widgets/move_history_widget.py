# move_history_widget.py - Displays game moves in algebraic notation

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame
)
from PySide6.QtCore import Qt


class MoveHistoryWidget(QWidget):
    """Displays the move history in standard algebraic notation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.moves = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("Moves")
        header.setObjectName("SectionHeader")
        layout.addWidget(header)
        
        # Scroll area for moves
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.moves_container = QWidget()
        self.moves_layout = QVBoxLayout(self.moves_container)
        self.moves_layout.setContentsMargins(0, 0, 0, 0)
        self.moves_layout.setSpacing(4)
        self.moves_layout.addStretch()
        
        scroll.setWidget(self.moves_container)
        layout.addWidget(scroll, stretch=1)
    
    def set_pgn(self, pgn: str):
        """Parse and display moves from PGN move text."""
        # Clear existing moves
        while self.moves_layout.count() > 1:
            item = self.moves_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not pgn or not pgn.strip():
            return
        
        # Parse PGN moves (simplified - handles "1. e4 e5 2. Nf3 Nc6" format)
        tokens = pgn.split()
        
        current_move_num = 0
        white_move = None
        
        for token in tokens:
            # Skip move numbers and result
            if token.endswith('.'):
                try:
                    current_move_num = int(token.rstrip('.'))
                except ValueError:
                    pass
                continue
            
            if token in ('1-0', '0-1', '1/2-1/2', '*'):
                continue
            
            if white_move is None:
                white_move = token
            else:
                # We have both moves, add the row
                self._add_move_row(current_move_num, white_move, token)
                white_move = None
        
        # Handle odd number of moves (white's last move without black response)
        if white_move is not None:
            self._add_move_row(current_move_num, white_move, "")
        
        # Scroll to bottom
        self.moves_layout.parentWidget().parentWidget().verticalScrollBar().setValue(
            self.moves_layout.parentWidget().parentWidget().verticalScrollBar().maximum()
        )
    
    def _add_move_row(self, move_num: int, white_move: str, black_move: str):
        """Add a single move pair row."""
        row = QFrame()
        row.setStyleSheet("""
            QFrame {
                background: #12181f;
                border-radius: 4px;
                padding: 4px;
            }
            QFrame:hover {
                background: #1a2332;
            }
        """)
        
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 6, 8, 6)
        row_layout.setSpacing(12)
        
        # Move number
        num_label = QLabel(f"{move_num}.")
        num_label.setObjectName("MoveNumber")
        num_label.setFixedWidth(28)
        row_layout.addWidget(num_label)
        
        # White's move
        white_label = QLabel(white_move)
        white_label.setObjectName("WhiteMove")
        white_label.setFixedWidth(60)
        row_layout.addWidget(white_label)
        
        # Black's move
        black_label = QLabel(black_move)
        black_label.setObjectName("BlackMove")
        row_layout.addWidget(black_label)
        
        row_layout.addStretch()
        
        # Insert before the stretch at the end
        self.moves_layout.insertWidget(self.moves_layout.count() - 1, row)
    
    def add_move(self, move_num: int, san: str, is_white: bool):
        """Add a single move (for real-time updates)."""
        if is_white:
            self._add_move_row(move_num, san, "")
        else:
            # Update the last row to add black's move
            if self.moves_layout.count() > 1:
                last_row = self.moves_layout.itemAt(self.moves_layout.count() - 2).widget()
                if last_row:
                    black_label = last_row.layout().itemAt(2).widget()
                    if black_label:
                        black_label.setText(san)
    
    def clear(self):
        """Clear all moves."""
        while self.moves_layout.count() > 1:
            item = self.moves_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
