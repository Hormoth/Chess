# game_window.py - Enhanced Game Window

import asyncio
import threading
import json
import chess
import websockets

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QMessageBox, 
    QFrame, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from .widgets.chess_board_widget import ChessBoardWidget
from .widgets.chat_widget import ChatWidget
from .widgets.move_history_widget import MoveHistoryWidget


def ws_url(http_base: str, game_id: int) -> str:
    base = http_base.replace("http://", "ws://").replace("https://", "wss://")
    return f"{base}/games/ws/{game_id}"


class PlayerInfoWidget(QFrame):
    """Displays player information with name, rating, and status."""
    
    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = color  # 'white' or 'black'
        self.setObjectName("Card")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        
        # Color indicator
        indicator = QLabel("●")
        indicator.setStyleSheet(f"""
            font-size: 16px;
            color: {'#ffffff' if color == 'white' else '#1a1a1a'};
        """)
        layout.addWidget(indicator)
        
        # Player info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.name_label = QLabel("Waiting...")
        self.name_label.setObjectName("PlayerName")
        info_layout.addWidget(self.name_label)
        
        self.rating_label = QLabel("")
        self.rating_label.setObjectName("Rating")
        info_layout.addWidget(self.rating_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Turn indicator
        self.turn_indicator = QLabel("")
        self.turn_indicator.setStyleSheet("""
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        """)
        layout.addWidget(self.turn_indicator)
    
    def set_player(self, name: str, rating: int, is_you: bool = False):
        display_name = f"{name} (You)" if is_you else name
        self.name_label.setText(display_name)
        self.rating_label.setText(f"Rating: {rating:.0f}")
    
    def set_turn(self, is_their_turn: bool):
        if is_their_turn:
            self.turn_indicator.setText("● Their turn")
            self.turn_indicator.setStyleSheet("""
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                background: #2d6a4f;
                color: #ffffff;
            """)
        else:
            self.turn_indicator.setText("")
            self.turn_indicator.setStyleSheet("padding: 4px 10px;")


class GameWindow(QWidget):
    """Main game window with board, chat, and move history."""
    
    # Thread-safe signals for websocket updates
    wsChat = Signal(str)
    wsMove = Signal()
    
    def __init__(self, api, game_id: int, parent=None):
        super().__init__(parent)
        self.api = api
        self.game_id = game_id
        self.setWindowTitle(f"Chess Arena - Game #{game_id}")
        self.setMinimumSize(1100, 750)
        
        self.selected: str | None = None
        self.current_fen: str = "startpos"
        self.current_pgn: str = ""
        self._legal_to: set[str] = set()
        
        # Player info cache
        self.white_info = None
        self.black_info = None
        self.my_id = None
        self.my_color = None
        
        self._setup_ui()
        self._connect_signals()
        
        # Initial load
        self.refresh()
        
        # Websocket thread
        self._stop = False
        self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
        self._ws_thread.start()
    
    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)
        
        # ==========================================
        # LEFT COLUMN: Board + Chat below
        # ==========================================
        left_column = QVBoxLayout()
        left_column.setSpacing(12)
        
        # Black player info (top)
        self.black_player = PlayerInfoWidget('black')
        left_column.addWidget(self.black_player)
        
        # Chess board (center)
        self.board = ChessBoardWidget()
        self.board.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_column.addWidget(self.board, stretch=3)
        
        # White player info
        self.white_player = PlayerInfoWidget('white')
        left_column.addWidget(self.white_player)
        
        # Chat (below board)
        self.chat = ChatWidget("Game Chat")
        self.chat.setMaximumHeight(180)
        left_column.addWidget(self.chat)
        
        root.addLayout(left_column, stretch=3)
        
        # ==========================================
        # RIGHT COLUMN: Moves + Status + Controls
        # ==========================================
        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        
        # Game status
        self.status_panel = QFrame()
        self.status_panel.setObjectName("Card")
        status_layout = QVBoxLayout(self.status_panel)
        status_layout.setContentsMargins(12, 12, 12, 12)
        status_layout.setSpacing(8)
        
        status_header = QLabel("Game Status")
        status_header.setObjectName("SectionHeader")
        status_layout.addWidget(status_header)
        
        self.status_label = QLabel("Loading...")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        self.turn_label = QLabel("")
        self.turn_label.setObjectName("TurnIndicator")
        status_layout.addWidget(self.turn_label)
        
        right_column.addWidget(self.status_panel)
        
        # Move history
        self.move_history = MoveHistoryWidget()
        self.move_history.setObjectName("MovesPanel")
        right_column.addWidget(self.move_history, stretch=1)
        
        # Game controls
        controls = QFrame()
        controls.setObjectName("Card")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(12, 12, 12, 12)
        controls_layout.setSpacing(8)
        
        self.resign_btn = QPushButton("Resign")
        self.resign_btn.setObjectName("DangerButton")
        self.resign_btn.clicked.connect(self._on_resign)
        controls_layout.addWidget(self.resign_btn)
        
        self.draw_btn = QPushButton("Offer Draw")
        self.draw_btn.clicked.connect(self._on_offer_draw)
        controls_layout.addWidget(self.draw_btn)
        
        right_column.addWidget(controls)
        
        root.addLayout(right_column, stretch=1)
    
    def _connect_signals(self):
        self.board.squareClicked.connect(self.on_square_clicked)
        self.chat.sendChat.connect(self.send_chat)
        self.wsChat.connect(self._handle_ws_chat)
        self.wsMove.connect(self.refresh)
    
    def _handle_ws_chat(self, msg: str):
        self.chat.append(msg)
    
    # ---------- Helpers ----------
    def _board_obj(self) -> chess.Board:
        fen = self.current_fen
        if not fen or fen == "startpos":
            return chess.Board()
        return chess.Board(fen)
    
    def _clear_selection_ui(self):
        self.selected = None
        self._legal_to.clear()
        self.board.clear_highlights()
    
    def _fetch_player_info(self, player_id: int) -> dict:
        """Fetch player info from API."""
        try:
            # Try to get player info - adjust endpoint as needed
            import httpx
            r = httpx.get(f"{self.api.base_url}/players/{player_id}", timeout=5)
            if r.status_code == 200:
                return r.json()
        except:
            pass
        return {"name": f"Player #{player_id}", "rating": 1500}
    
    # ---------- UI actions ----------
    def refresh(self):
        try:
            g = self.api.get_game(self.game_id)
            me = self.api.me()
            self.my_id = me.get("id")
            
            white_id = g.get("white_id")
            black_id = g.get("black_id")
            
            # Determine my color
            if self.my_id == white_id:
                self.my_color = "white"
            elif self.my_id == black_id:
                self.my_color = "black"
            else:
                self.my_color = "spectator"
            
            meta = g.get("meta", {})
            turn = meta.get("turn")
            
            # Update cached board state + render
            self.current_fen = g.get("fen", "startpos")
            self.current_pgn = g.get("pgn", "")
            self.board.set_fen(self.current_fen)
            
            # Update move history
            self.move_history.set_pgn(self.current_pgn)
            
            # Update player info panels
            # White player
            if white_id == self.my_id:
                self.white_player.set_player(me.get("name", "You"), me.get("rating", 1500), is_you=True)
            else:
                white_info = self._fetch_player_info(white_id) if white_id else {"name": "Waiting...", "rating": 0}
                self.white_player.set_player(white_info.get("name", f"#{white_id}"), white_info.get("rating", 1500))
            
            # Black player
            if black_id == self.my_id:
                self.black_player.set_player(me.get("name", "You"), me.get("rating", 1500), is_you=True)
            else:
                black_info = self._fetch_player_info(black_id) if black_id else {"name": "Waiting...", "rating": 0}
                self.black_player.set_player(black_info.get("name", f"#{black_id}"), black_info.get("rating", 1500))
            
            # Update turn indicators
            self.white_player.set_turn(turn == "white" and self.my_color != "white")
            self.black_player.set_turn(turn == "black" and self.my_color != "black")
            
            # Update status
            status_lines = [f"Status: {g.get('status')}"]
            if g.get('ranked'):
                status_lines.append("Ranked Game")
            
            if meta.get("in_check"):
                status_lines.append("⚠️ CHECK!")
            
            if g.get("result"):
                status_lines.append(f"Result: {g.get('result')}")
                status_lines.append(f"Reason: {g.get('end_reason')}")
            
            self.status_label.setText("\n".join(status_lines))
            
            # Your turn indicator
            is_my_turn = (turn == self.my_color)
            if g.get("status") == "active":
                if is_my_turn:
                    self.turn_label.setText("Your Turn!")
                    self.turn_label.setStyleSheet("""
                        padding: 8px 16px;
                        border-radius: 6px;
                        font-size: 14px;
                        font-weight: 700;
                        background: #2d6a4f;
                        color: #ffffff;
                    """)
                else:
                    self.turn_label.setText("Opponent's Turn")
                    self.turn_label.setStyleSheet("""
                        padding: 8px 16px;
                        border-radius: 6px;
                        font-size: 14px;
                        font-weight: 600;
                        background: #1f2a3a;
                        color: #8fa4bf;
                    """)
            else:
                self.turn_label.setText("Game Over")
                self.turn_label.setStyleSheet("""
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 600;
                    background: #742a2a;
                    color: #ffffff;
                """)
            
            # Clear selection after any refresh
            self._clear_selection_ui()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def on_square_clicked(self, sq: str):
        try:
            board = self._board_obj()
        except Exception as e:
            self.chat.append_system(f"FEN error: {e}")
            self._clear_selection_ui()
            return
        
        # First click: select a piece square
        if self.selected is None:
            piece = board.piece_at(chess.parse_square(sq))
            if piece is None:
                return
            
            self.selected = sq
            frm_sq = chess.parse_square(sq)
            legal_to = set()
            for mv in board.legal_moves:
                if mv.from_square == frm_sq:
                    legal_to.add(chess.square_name(mv.to_square))
            
            self._legal_to = legal_to
            self.board.highlight_squares(sq, sorted(legal_to))
            return
        
        # Second click: destination
        frm = self.selected
        to = sq
        
        if to == frm:
            self._clear_selection_ui()
            return
        
        if self._legal_to and to not in self._legal_to:
            self.chat.append_system(f"Illegal move: {frm}{to}")
            self._clear_selection_ui()
            return
        
        self._clear_selection_ui()
        
        uci = f"{frm}{to}"
        try:
            self.api.move(self.game_id, uci)
            self.board.set_last_move(frm, to)
        except Exception as e:
            self.chat.append_system(f"Move rejected: {e}")
    
    def send_chat(self, text: str):
        try:
            self.api.chat(self.game_id, text)
        except Exception as e:
            self.chat.append_system(f"Chat error: {e}")
    
    def _on_resign(self):
        reply = QMessageBox.question(
            self, "Resign", 
            "Are you sure you want to resign?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                # Call resign endpoint if available
                self.chat.append_system("You resigned.")
            except Exception as e:
                self.chat.append_system(f"Error: {e}")
    
    def _on_offer_draw(self):
        self.chat.append_system("Draw offer sent (not implemented yet)")
    
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
                            except:
                                break
                            await asyncio.sleep(10)
                    
                    ping_task = asyncio.create_task(ping_loop())
                    
                    while not self._stop:
                        msg = await ws.recv()
                        
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
