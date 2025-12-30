import asyncio
import threading
import json
import chess
import websockets

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QMessageBox
from PySide6.QtCore import Qt, Signal

from .widgets.chess_board_widget import ChessBoardWidget
from .widgets.chat_widget import ChatWidget


def ws_url(http_base: str, game_id: int) -> str:
    base = http_base.replace("http://", "ws://").replace("https://", "wss://")
    return f"{base}/games/ws/{game_id}"


class GameWindow(QWidget):
    # Thread-safe signals for websocket updates
    wsChat = Signal(str)
    wsMove = Signal()

    def __init__(self, api, game_id: int, parent=None):
        super().__init__(parent)
        self.api = api
        self.game_id = game_id
        self.setWindowTitle(f"Game #{game_id}")

        self.selected: str | None = None
        self.current_fen: str = "startpos"
        self.current_pgn: str = ""

        # destinations for the currently selected square
        self._legal_to: set[str] = set()

        # Root layout
        root = QHBoxLayout(self)

        # Left: board + chat
        left = QVBoxLayout()
        self.board = ChessBoardWidget()
        self.board.squareClicked.connect(self.on_square_clicked)
        left.addWidget(self.board, stretch=3)

        self.chat = ChatWidget()
        self.chat.sendChat.connect(self.send_chat)
        left.addWidget(self.chat, stretch=1)

        root.addLayout(left, stretch=2)

        # Right: player info + status
        right = QVBoxLayout()
        self.player_info = QLabel("Player Info:\nLoading...")
        self.player_info.setAlignment(Qt.AlignTop)
        right.addWidget(self.player_info)

        self.status = QLabel("Game Status:\nLoading...")
        self.status.setAlignment(Qt.AlignTop)
        right.addWidget(self.status)

        root.addLayout(right, stretch=1)

        # Hook websocket signals
        self.wsChat.connect(self.chat.append)
        self.wsMove.connect(self.refresh)

        # Initial load
        self.refresh()

        # Websocket thread
        self._stop = False
        self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
        self._ws_thread.start()

    # ---------- Helpers ----------
    def _board_obj(self) -> chess.Board:
        fen = self.current_fen
        if not fen or fen == "startpos":
            return chess.Board()
        return chess.Board(fen)

    def _clear_selection_ui(self):
        self.selected = None
        self._legal_to.clear()
        if hasattr(self.board, "clear_highlights"):
            self.board.clear_highlights()

    def _highlight_legal(self, frm: str, legal_to: set[str]):
        if not legal_to:
            return

        if hasattr(self.board, "highlight_squares"):
            self.board.highlight_squares(frm, sorted(legal_to))
        else:
            self.chat.append(f"[legal] {frm} -> {', '.join(sorted(legal_to))}")

    # ---------- UI actions ----------
    def refresh(self):
        try:
            g = self.api.get_game(self.game_id)
            me = self.api.me()
            my_id = me.get("id")

            white_id = g.get("white_id")
            black_id = g.get("black_id")

            if my_id == white_id:
                my_color = "White"
            elif my_id == black_id:
                my_color = "Black"
            else:
                my_color = "Spectator/Unknown"

            meta = g.get("meta", {})
            turn = meta.get("turn")

            # Update cached board state + render
            self.current_fen = g.get("fen", "startpos")
            self.current_pgn = g.get("pgn", "")
            self.board.set_fen(self.current_fen)

            # Player info (IDs for now; later you can add /players/{id} to show names)
            self.player_info.setText(
                f"You: {me.get('name')} (#{my_id}) • {me.get('rating', 0):.0f}\n"
                f"White: {white_id}\n"
                f"Black: {black_id}"
            )

            status_msg = [
                f"Status: {g.get('status')}",
                f"Ranked: {g.get('ranked')}",
                f"You are: {my_color}",
                f"Turn: {turn}",
            ]
            if meta.get("in_check"):
                status_msg.append("CHECK!")
            if g.get("result"):
                status_msg.append(f"Result: {g.get('result')} ({g.get('end_reason')})")

            self.status.setText("\n".join(status_msg))

            # Clear selection after any refresh (prevents stale highlights after opponent moves)
            self._clear_selection_ui()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def on_square_clicked(self, sq: str):
        # Build board from cached fen
        try:
            board = self._board_obj()
        except Exception as e:
            self.chat.append(f"[fen error] {e}")
            self._clear_selection_ui()
            return

        # First click: select a piece square
        if self.selected is None:
            piece = board.piece_at(chess.parse_square(sq))
            if piece is None:
                self.chat.append(f"[select] {sq} (empty)")
                return

            self.selected = sq

            frm_sq = chess.parse_square(sq)
            legal_to = set()
            for mv in board.legal_moves:
                if mv.from_square == frm_sq:
                    legal_to.add(chess.square_name(mv.to_square))

            self._legal_to = legal_to
            self.chat.append(f"[select] {sq}")
            self._highlight_legal(sq, legal_to)
            return

        # Second click: destination
        frm = self.selected
        to = sq

        if to == frm:
            self.chat.append(f"[cancel] {frm}")
            self._clear_selection_ui()
            return

        # Cosmetic filter only (server is authoritative)
        if self._legal_to and to not in self._legal_to:
            self.chat.append(f"[illegal] {frm}{to} (not legal)")
            self._clear_selection_ui()
            return

        self._clear_selection_ui()

        uci = f"{frm}{to}"
        try:
            self.api.move(self.game_id, uci)
            # ws will also refresh, but do it now for snappy fee
        except Exception as e:
            self.chat.append(f"[move rejected] {uci} -> {e}")

    def send_chat(self, text: str):
        try:
            self.api.chat(self.game_id, text)
        except Exception as e:
            self.chat.append(f"[chat error] {e}")

    def closeEvent(self, event):
        self._stop = True
        super().closeEvent(event)

    # ---------- Websocket loop ----------
    def _ws_loop(self):
        async def run():
            url = ws_url(self.api.base_url, self.game_id)
            try:
                async with websockets.connect(url) as ws:
                    async def ping_loop():
                        while not self._stop:
                            try:
                                await ws.send("ping")
                            except Exception:
                                break
                            await asyncio.sleep(10)

                    ping_task = asyncio.create_task(ping_loop())

                    while not self._stop:
                        msg = await ws.recv()

                        # robustness
                        if isinstance(msg, (bytes, bytearray)):
                            msg = msg.decode("utf-8", errors="ignore")

                        data = json.loads(msg)

                        if data.get("type") == "chat":
                            pid = data.get("player_id")
                            txt = data.get("text")
                            self.wsChat.emit(f"{pid}: {txt}")

                        elif data.get("type") == "move":
                            self.current_fen = data.get("fen", self.current_fen)
                            self.current_pgn = data.get("pgn", self.current_pgn)
                            self.wsMove.emit()

                    ping_task.cancel()
            except Exception as e:
                self.wsChat.emit(f"[ws closed] {e}")

        asyncio.run(run())
