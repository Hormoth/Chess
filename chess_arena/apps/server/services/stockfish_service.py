import os
import chess
import chess.engine

from chess_arena.packages.chesslib.rules import board_from_fen_or_start


class StockfishService:
    def __init__(self):
        self.path = os.environ.get("STOCKFISH_PATH")

    def best_move_uci(self, fen: str, think_ms: int = 200) -> str:
        if not self.path or not os.path.exists(self.path):
            raise FileNotFoundError(
                f"Stockfish executable not found. STOCKFISH_PATH='{self.path}'"
            )

        b = board_from_fen_or_start(fen)
        with chess.engine.SimpleEngine.popen_uci(self.path) as engine:
            limit = chess.engine.Limit(time=think_ms / 1000.0)
            result = engine.play(b, limit)
            return result.move.uci()


stockfish = StockfishService()
