# lobby.py - Enhanced Lobby with Waiting Players, Chat & Leaderboard

import threading
import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QMessageBox, QCheckBox, QFrame, QListWidget, QListWidgetItem,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer

from .widgets.chat_widget import ChatWidget


class LeaderboardWidget(QFrame):
    """Top 10 players leaderboard."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LeaderboardPanel")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header with trophy
        header = QLabel("🏆 Top 10 Players")
        header.setObjectName("SectionHeader")
        header.setStyleSheet("color: #d4af37; border-bottom: 1px solid #d4af37;")
        layout.addWidget(header)
        
        # Leaderboard list
        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 6px 8px;
            }
        """)
        layout.addWidget(self.list)
    
    def set_players(self, players: list[dict]):
        """Set leaderboard data. Each dict has: rank, name, rating, wins, losses"""
        self.list.clear()
        
        for i, player in enumerate(players[:10]):
            rank = i + 1
            name = player.get("name", "Unknown")
            rating = player.get("rating", 1500)
            wins = player.get("wins", 0)
            losses = player.get("losses", 0)
            
            # Medal for top 3
            if rank == 1:
                medal = "🥇"
                style = "color: #d4af37; font-weight: 700;"
            elif rank == 2:
                medal = "🥈"
                style = "color: #a8a8a8; font-weight: 600;"
            elif rank == 3:
                medal = "🥉"
                style = "color: #cd7f32; font-weight: 600;"
            else:
                medal = f"#{rank}"
                style = "color: #8fa4bf;"
            
            item = QListWidgetItem(f"{medal}  {name}  •  {rating:.0f}  ({wins}W/{losses}L)")
            self.list.addItem(item)
    
    def refresh(self, api):
        """Fetch and update leaderboard from API."""
        try:
            import httpx
            r = httpx.get(f"{api.base_url}/players/leaderboard", timeout=5)
            if r.status_code == 200:
                self.set_players(r.json())
        except:
            # Fallback sample data
            self.set_players([
                {"name": "GrandMaster42", "rating": 2150, "wins": 156, "losses": 34},
                {"name": "ChessWizard", "rating": 2080, "wins": 142, "losses": 48},
                {"name": "KnightRider", "rating": 1950, "wins": 98, "losses": 52},
                {"name": "BishopSlayer", "rating": 1890, "wins": 87, "losses": 63},
                {"name": "RookMaster", "rating": 1820, "wins": 76, "losses": 54},
            ])


class WaitingPlayersWidget(QFrame):
    """Shows players waiting for a match."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WaitingPanel")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header
        header_row = QHBoxLayout()
        header = QLabel("Players in Queue")
        header.setObjectName("SectionHeader")
        header_row.addWidget(header)
        
        self.count_label = QLabel("0 waiting")
        self.count_label.setStyleSheet("color: #6b7d99; font-size: 12px;")
        header_row.addWidget(self.count_label)
        header_row.addStretch()
        
        layout.addLayout(header_row)
        
        # Player list
        self.list = QListWidget()
        layout.addWidget(self.list)
    
    def set_players(self, players: list[dict]):
        """Update waiting players list."""
        self.list.clear()
        self.count_label.setText(f"{len(players)} waiting")
        
        for player in players:
            name = player.get("name", "Unknown")
            rating = player.get("rating", 1500)
            queue_type = "Ranked" if player.get("ranked") else "Free"
            
            item_text = f"⏳ {name}  •  {rating:.0f}  ({queue_type})"
            item = QListWidgetItem(item_text)
            self.list.addItem(item)
    
    def refresh(self, api):
        """Fetch waiting players from API."""
        try:
            import httpx
            r = httpx.get(f"{api.base_url}/matchmaking/waiting", timeout=5)
            if r.status_code == 200:
                self.set_players(r.json())
        except:
            pass


class Lobby(QWidget):
    """Enhanced lobby with queue, waiting players, chat, and leaderboard."""
    
    gameReady = Signal(int)  # Emits game_id when matched
    
    def __init__(self, api, on_game_ready, parent=None):
        super().__init__(parent)
        self.api = api
        self.on_game_ready = on_game_ready
        self.open_game_cb = on_game_ready  # Backwards compatibility
        
        self._polling = False
        self._poll_timer = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        
        # ==========================================
        # LEFT SIDE: Queue Controls + Waiting Players
        # ==========================================
        left = QVBoxLayout()
        left.setSpacing(12)
        
        # Queue controls card
        queue_card = QFrame()
        queue_card.setObjectName("Card")
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(16, 16, 16, 16)
        queue_layout.setSpacing(12)
        
        queue_title = QLabel("Find a Match")
        queue_title.setObjectName("Title")
        queue_layout.addWidget(queue_title)
        
        self.info = QLabel("Choose your game mode and start playing!")
        self.info.setObjectName("Subtitle")
        self.info.setWordWrap(True)
        queue_layout.addWidget(self.info)
        
        # Options
        options_row = QHBoxLayout()
        self.ranked = QCheckBox("Ranked Game")
        self.ranked.setChecked(True)
        self.ranked.setToolTip("Ranked games affect your rating")
        options_row.addWidget(self.ranked)
        options_row.addStretch()
        queue_layout.addLayout(options_row)
        
        # Queue buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        self.btn_pvp = QPushButton("⚔️  Play Online")
        self.btn_pvp.setObjectName("PrimaryButton")
        self.btn_pvp.setMinimumHeight(50)
        self.btn_pvp.clicked.connect(self.queue_pvp)
        btn_row.addWidget(self.btn_pvp)
        
        self.btn_sys = QPushButton("🤖  Play vs Bot")
        self.btn_sys.setMinimumHeight(50)
        self.btn_sys.clicked.connect(self.queue_system)
        btn_row.addWidget(self.btn_sys)
        
        queue_layout.addLayout(btn_row)
        
        # Cancel button (hidden by default)
        self.btn_cancel = QPushButton("Cancel Search")
        self.btn_cancel.setObjectName("DangerButton")
        self.btn_cancel.clicked.connect(self.cancel_queue)
        self.btn_cancel.hide()
        queue_layout.addWidget(self.btn_cancel)
        
        left.addWidget(queue_card)
        
        # Waiting players
        self.waiting_players = WaitingPlayersWidget()
        left.addWidget(self.waiting_players, stretch=1)
        
        root.addLayout(left, stretch=1)
        
        # ==========================================
        # CENTER: Lobby Chat
        # ==========================================
        center = QVBoxLayout()
        center.setSpacing(0)
        
        self.chat = ChatWidget("Lobby Chat")
        self.chat.sendChat.connect(self.send_lobby_chat)
        center.addWidget(self.chat)
        
        root.addLayout(center, stretch=2)
        
        # ==========================================
        # RIGHT: Leaderboard
        # ==========================================
        self.leaderboard = LeaderboardWidget()
        self.leaderboard.setFixedWidth(280)
        root.addWidget(self.leaderboard)
        
        # Initial data load
        self._refresh_lobby_data()
        
        # Periodic refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_lobby_data)
        self._refresh_timer.start(10000)  # Refresh every 10 seconds
    
    def _refresh_lobby_data(self):
        """Refresh waiting players and leaderboard."""
        self.waiting_players.refresh(self.api)
        self.leaderboard.refresh(self.api)
    
    def queue_pvp(self):
        """Queue for PvP matchmaking."""
        try:
            q = self.api.queue(ranked=self.ranked.isChecked(), vs_system=False)
            
            if q.get("status") == "waiting":
                self.info.setText("🔍 Searching for opponent...")
                self.info.setStyleSheet("color: #d4af37; font-weight: 600;")
                self.btn_pvp.setEnabled(False)
                self.btn_sys.setEnabled(False)
                self.btn_cancel.show()
                self._start_polling(q.get("queue_id"))
                return
            
            self.on_game_ready(q["game_id"])
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def queue_system(self):
        """Queue to play vs System/Stockfish."""
        try:
            q = self.api.queue(ranked=self.ranked.isChecked(), vs_system=True)
            
            if q.get("status") == "waiting":
                self.info.setText("Starting game vs bot...")
                return
            
            self.on_game_ready(q["game_id"])
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def cancel_queue(self):
        """Cancel matchmaking."""
        self._polling = False
        self.info.setText("Search cancelled")
        self.info.setStyleSheet("")
        self.btn_pvp.setEnabled(True)
        self.btn_sys.setEnabled(True)
        self.btn_cancel.hide()
        
        # Call cancel endpoint if available
        try:
            import httpx
            httpx.post(f"{self.api.base_url}/matchmaking/cancel", 
                      json={"player_id": self.api.player_id}, timeout=5)
        except:
            pass
    
    def _start_polling(self, queue_id=None):
        """Poll for match updates."""
        self._polling = True
        
        def poll():
            while self._polling:
                try:
                    q = self.api.queue(ranked=self.ranked.isChecked(), vs_system=False)
                    if q.get("game_id"):
                        self._polling = False
                        # Use signal to call on_game_ready in main thread
                        self.gameReady.emit(q["game_id"])
                        return
                except:
                    pass
                time.sleep(1)
        
        self.gameReady.connect(self._on_matched)
        threading.Thread(target=poll, daemon=True).start()
    
    def _on_matched(self, game_id: int):
        """Called when matched (in main thread)."""
        self.info.setText("Match found!")
        self.info.setStyleSheet("color: #40916c; font-weight: 600;")
        self.btn_pvp.setEnabled(True)
        self.btn_sys.setEnabled(True)
        self.btn_cancel.hide()
        self.on_game_ready(game_id)
    
    def send_lobby_chat(self, text: str):
        """Send message to lobby chat."""
        try:
            # Call lobby chat endpoint if available
            import httpx
            httpx.post(f"{self.api.base_url}/lobby/chat",
                      json={"player_id": self.api.player_id, "text": text}, timeout=5)
            # Add locally for now
            me = self.api.me()
            self.chat.append_player(me.get("name", "You"), text)
        except Exception as e:
            self.chat.append_system(f"Chat error: {e}")
