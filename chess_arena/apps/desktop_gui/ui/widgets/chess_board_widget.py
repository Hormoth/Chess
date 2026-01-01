# chess_board_widget.py - Enhanced Chess Board with Captured Pieces

import chess
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QBrush, QPen

from ..theme import BOARD_COLORS, PIECE_SYMBOLS


class SquareWidget(QLabel):
    """Individual chess square that can be clicked."""
    
    clicked = Signal(str)  # Emits square name like 'e4'
    
    def __init__(self, square_name: str, is_light: bool, parent=None):
        super().__init__(parent)
        self.square_name = square_name
        self.is_light = is_light
        self.piece = None
        self.is_highlighted = False
        self.is_legal_target = False
        self.is_last_move = False
        self.is_check = False
        
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(60, 60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        
        self._update_style()
    
    def _update_style(self):
        base_color = BOARD_COLORS['light'] if self.is_light else BOARD_COLORS['dark']
        
        if self.is_check:
            base_color = BOARD_COLORS['check']
        elif self.is_highlighted:
            base_color = BOARD_COLORS['highlight']
        elif self.is_last_move:
            base_color = BOARD_COLORS['last_move']
        
        # Piece color - white pieces are lighter, black pieces are darker
        piece_color = "#1a1a1a" if self.piece and self.piece.islower() else "#ffffff"
        text_shadow = "1px 1px 2px rgba(0,0,0,0.5)" if self.piece and self.piece.isupper() else "none"
        
        style = f"""
            background-color: {base_color};
            color: {piece_color};
            font-size: 42px;
            font-weight: bold;
            border: none;
        """
        
        if self.is_legal_target:
            # Add dot indicator for legal moves
            if self.piece:
                # Capture indicator - ring around piece
                style += f"border: 3px solid {BOARD_COLORS['legal']};"
            else:
                # Empty square - will draw dot in paintEvent
                pass
        
        self.setStyleSheet(style)
    
    def set_piece(self, piece: str | None):
        self.piece = piece
        if piece:
            self.setText(PIECE_SYMBOLS.get(piece, piece))
        else:
            self.setText("")
        self._update_style()
    
    def set_highlighted(self, highlighted: bool):
        self.is_highlighted = highlighted
        self._update_style()
    
    def set_legal_target(self, is_legal: bool):
        self.is_legal_target = is_legal
        self._update_style()
        self.update()
    
    def set_last_move(self, is_last: bool):
        self.is_last_move = is_last
        self._update_style()
    
    def set_check(self, is_check: bool):
        self.is_check = is_check
        self._update_style()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        # Draw legal move indicator dot for empty squares
        if self.is_legal_target and not self.piece:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            color = QColor(BOARD_COLORS['legal'])
            color.setAlpha(180)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            
            # Draw centered dot
            size = min(self.width(), self.height())
            dot_size = size // 4
            x = (self.width() - dot_size) // 2
            y = (self.height() - dot_size) // 2
            painter.drawEllipse(x, y, dot_size, dot_size)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.square_name)
        super().mousePressEvent(event)


class CapturedPiecesWidget(QWidget):
    """Displays captured pieces for one side."""
    
    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = color  # 'white' or 'black'
        self.captured = []
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)
        
        self.pieces_label = QLabel("")
        self.pieces_label.setStyleSheet(f"""
            font-size: 22px;
            color: {'#ffffff' if color == 'white' else '#1a1a1a'};
            background: transparent;
        """)
        layout.addWidget(self.pieces_label)
        layout.addStretch()
        
        # Material advantage
        self.advantage_label = QLabel("")
        self.advantage_label.setStyleSheet("font-size: 14px; color: #8fa4bf; font-weight: 600;")
        layout.addWidget(self.advantage_label)
    
    def set_captured(self, pieces: list[str], advantage: int = 0):
        """pieces is a list of piece characters that were captured from this side."""
        self.captured = pieces
        
        # Sort by value (Q, R, B, N, P)
        order = {'q': 0, 'r': 1, 'b': 2, 'n': 3, 'p': 4, 'Q': 0, 'R': 1, 'B': 2, 'N': 3, 'P': 4}
        sorted_pieces = sorted(pieces, key=lambda p: order.get(p, 5))
        
        # Convert to symbols
        symbols = ''.join(PIECE_SYMBOLS.get(p, p) for p in sorted_pieces)
        self.pieces_label.setText(symbols)
        
        # Show advantage
        if advantage > 0:
            self.advantage_label.setText(f"+{advantage}")
            self.advantage_label.setStyleSheet("font-size: 14px; color: #40916c; font-weight: 600;")
        elif advantage < 0:
            self.advantage_label.setText(str(advantage))
            self.advantage_label.setStyleSheet("font-size: 14px; color: #c53030; font-weight: 600;")
        else:
            self.advantage_label.setText("")


class ChessBoardWidget(QWidget):
    """Complete chess board with coordinates and captured pieces."""
    
    squareClicked = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChessBoardWidget")
        
        self.squares: dict[str, SquareWidget] = {}
        self.flipped = False
        self.last_move_from = None
        self.last_move_to = None
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        
        # Captured pieces for Black (pieces White captured) - shown at top
        self.captured_black = CapturedPiecesWidget('black')
        self.captured_black.setObjectName("CapturedPanel")
        main_layout.addWidget(self.captured_black)
        
        # Board container with edge styling
        board_container = QFrame()
        board_container.setObjectName("BoardEdge")
        board_layout = QVBoxLayout(board_container)
        board_layout.setContentsMargins(4, 4, 4, 4)
        board_layout.setSpacing(0)
        
        # Inner board frame
        inner_frame = QFrame()
        inner_frame.setObjectName("BoardFrame")
        inner_layout = QGridLayout(inner_frame)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)
        
        # Create board squares
        self._create_board(inner_layout)
        
        board_layout.addWidget(inner_frame)
        main_layout.addWidget(board_container, stretch=1)
        
        # Captured pieces for White (pieces Black captured) - shown at bottom
        self.captured_white = CapturedPiecesWidget('white')
        self.captured_white.setObjectName("CapturedPanel")
        main_layout.addWidget(self.captured_white)
    
    def _create_board(self, layout: QGridLayout):
        files = 'abcdefgh'
        ranks = '87654321'
        
        for row, rank in enumerate(ranks):
            # Rank label on left
            rank_label = QLabel(rank)
            rank_label.setAlignment(Qt.AlignCenter)
            rank_label.setFixedWidth(20)
            rank_label.setStyleSheet("color: #8fa4bf; font-size: 11px; font-weight: 600; background: transparent;")
            layout.addWidget(rank_label, row, 0)
            
            for col, file in enumerate(files):
                square_name = f"{file}{rank}"
                is_light = (row + col) % 2 == 0
                
                square = SquareWidget(square_name, is_light)
                square.clicked.connect(self.squareClicked.emit)
                
                self.squares[square_name] = square
                layout.addWidget(square, row, col + 1)
            
            # Rank label on right
            rank_label2 = QLabel(rank)
            rank_label2.setAlignment(Qt.AlignCenter)
            rank_label2.setFixedWidth(20)
            rank_label2.setStyleSheet("color: #8fa4bf; font-size: 11px; font-weight: 600; background: transparent;")
            layout.addWidget(rank_label2, row, 9)
        
        # File labels at bottom
        for col, file in enumerate(files):
            file_label = QLabel(file)
            file_label.setAlignment(Qt.AlignCenter)
            file_label.setFixedHeight(20)
            file_label.setStyleSheet("color: #8fa4bf; font-size: 11px; font-weight: 600; background: transparent;")
            layout.addWidget(file_label, 8, col + 1)
    
    def set_fen(self, fen: str):
        """Update board position from FEN string."""
        if not fen or fen == "startpos":
            board = chess.Board()
        else:
            board = chess.Board(fen)
        
        # Clear all squares first
        for sq in self.squares.values():
            sq.set_piece(None)
            sq.set_check(False)
        
        # Place pieces
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            square_name = chess.square_name(square)
            if square_name in self.squares:
                if piece:
                    self.squares[square_name].set_piece(piece.symbol())
                else:
                    self.squares[square_name].set_piece(None)
        
        # Highlight king if in check
        if board.is_check():
            king_square = board.king(board.turn)
            if king_square is not None:
                king_name = chess.square_name(king_square)
                if king_name in self.squares:
                    self.squares[king_name].set_check(True)
        
        # Update captured pieces
        self._update_captured(board)
    
    def _update_captured(self, board: chess.Board):
        """Calculate and display captured pieces."""
        # Starting piece counts
        start_counts = {'P': 8, 'N': 2, 'B': 2, 'R': 2, 'Q': 1, 'K': 1,
                       'p': 8, 'n': 2, 'b': 2, 'r': 2, 'q': 1, 'k': 1}
        
        # Current piece counts
        current_counts = {}
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                sym = piece.symbol()
                current_counts[sym] = current_counts.get(sym, 0) + 1
        
        # Calculate captured
        white_captured = []  # Black pieces that White captured
        black_captured = []  # White pieces that Black captured
        
        piece_values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0,
                       'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0}
        
        white_material = 0
        black_material = 0
        
        for piece, start_count in start_counts.items():
            current = current_counts.get(piece, 0)
            captured_count = start_count - current
            
            for _ in range(captured_count):
                if piece.isupper():
                    # White piece was captured by Black
                    black_captured.append(piece)
                    black_material += piece_values[piece]
                else:
                    # Black piece was captured by White
                    white_captured.append(piece)
                    white_material += piece_values[piece]
        
        advantage = white_material - black_material
        
        self.captured_black.set_captured(white_captured, advantage if advantage > 0 else 0)
        self.captured_white.set_captured(black_captured, -advantage if advantage < 0 else 0)
    
    def highlight_squares(self, selected: str, legal_targets: list[str]):
        """Highlight selected square and legal move targets."""
        self.clear_highlights()
        
        if selected in self.squares:
            self.squares[selected].set_highlighted(True)
        
        for target in legal_targets:
            if target in self.squares:
                self.squares[target].set_legal_target(True)
    
    def clear_highlights(self):
        """Clear all highlights."""
        for sq in self.squares.values():
            sq.set_highlighted(False)
            sq.set_legal_target(False)
    
    def set_last_move(self, from_sq: str | None, to_sq: str | None):
        """Highlight the last move played."""
        # Clear previous last move highlights
        if self.last_move_from and self.last_move_from in self.squares:
            self.squares[self.last_move_from].set_last_move(False)
        if self.last_move_to and self.last_move_to in self.squares:
            self.squares[self.last_move_to].set_last_move(False)
        
        # Set new last move
        self.last_move_from = from_sq
        self.last_move_to = to_sq
        
        if from_sq and from_sq in self.squares:
            self.squares[from_sq].set_last_move(True)
        if to_sq and to_sq in self.squares:
            self.squares[to_sq].set_last_move(True)
