# widgets/__init__.py

from .chess_board_widget import ChessBoardWidget, SquareWidget, CapturedPiecesWidget
from .chat_widget import ChatWidget
from .move_history_widget import MoveHistoryWidget

__all__ = [
    'ChessBoardWidget',
    'SquareWidget', 
    'CapturedPiecesWidget',
    'ChatWidget',
    'MoveHistoryWidget',
]
