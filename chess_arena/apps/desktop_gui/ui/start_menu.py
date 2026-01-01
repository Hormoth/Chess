# start_menu.py - Enhanced Start Menu

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox, 
    QFrame, QHBoxLayout
)
from PySide6.QtCore import Qt

from .login_dialog import LoginDialog
from .create_account_dialog import CreateAccountDialog
from .lobby import Lobby
from .game_window import GameWindow


class StartMenu(QWidget):
    """Main entry point with login and lobby access."""
    
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Chess Arena")
        self.setMinimumSize(1200, 800)
        
        self.lobby = None
        self.game = None
        
        self._setup_ui()
        
        # If already logged in, show lobby
        if self.api.token:
            self.show_lobby()
    
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)
        
        # ==========================================
        # HEADER
        # ==========================================
        header = QFrame()
        header.setObjectName("Card")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        
        # Logo / Title
        title_section = QVBoxLayout()
        
        title = QLabel("♟ Chess Arena")
        title.setObjectName("Title")
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: 2px;
        """)
        title_section.addWidget(title)
        
        subtitle = QLabel("Online Multiplayer Chess")
        subtitle.setObjectName("Subtitle")
        title_section.addWidget(subtitle)
        
        header_layout.addLayout(title_section)
        header_layout.addStretch()
        
        # Account status
        self.account_section = QVBoxLayout()
        self.account_section.setAlignment(Qt.AlignRight)
        
        self.account_name = QLabel("Not logged in")
        self.account_name.setObjectName("PlayerName")
        self.account_name.setAlignment(Qt.AlignRight)
        self.account_section.addWidget(self.account_name)
        
        self.account_stats = QLabel("")
        self.account_stats.setObjectName("Subtitle")
        self.account_stats.setAlignment(Qt.AlignRight)
        self.account_section.addWidget(self.account_stats)
        
        header_layout.addLayout(self.account_section)
        
        root.addWidget(header)
        
        # ==========================================
        # AUTH CARD (shown when not logged in)
        # ==========================================
        self.auth_card = QFrame()
        self.auth_card.setObjectName("Card")
        auth_layout = QVBoxLayout(self.auth_card)
        auth_layout.setContentsMargins(40, 40, 40, 40)
        auth_layout.setSpacing(20)
        
        # Welcome message
        welcome = QLabel("Welcome to Chess Arena")
        welcome.setStyleSheet("font-size: 24px; font-weight: 700; color: #ffffff;")
        welcome.setAlignment(Qt.AlignCenter)
        auth_layout.addWidget(welcome)
        
        welcome_sub = QLabel("Login or create an account to start playing")
        welcome_sub.setObjectName("Subtitle")
        welcome_sub.setAlignment(Qt.AlignCenter)
        auth_layout.addWidget(welcome_sub)
        
        auth_layout.addSpacing(20)
        
        # Auth buttons
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        
        self.btn_login = QPushButton("Login")
        self.btn_login.setMinimumSize(150, 50)
        self.btn_login.clicked.connect(self.login)
        btn_container.addWidget(self.btn_login)
        
        btn_container.addSpacing(16)
        
        self.btn_create = QPushButton("Create Account")
        self.btn_create.setObjectName("PrimaryButton")
        self.btn_create.setMinimumSize(180, 50)
        self.btn_create.clicked.connect(self.create)
        btn_container.addWidget(self.btn_create)
        
        btn_container.addStretch()
        auth_layout.addLayout(btn_container)
        
        root.addWidget(self.auth_card, stretch=1)
        
        # ==========================================
        # LOBBY CONTAINER (shown when logged in)
        # ==========================================
        self.lobby_card = QFrame()
        self.lobby_card.setObjectName("Card")
        self.lobby_layout = QVBoxLayout(self.lobby_card)
        self.lobby_layout.setContentsMargins(16, 16, 16, 16)
        self.lobby_layout.setSpacing(0)
        self.lobby_card.hide()
        
        root.addWidget(self.lobby_card, stretch=1)
    
    def login(self):
        dlg = LoginDialog(self.api, self)
        if dlg.exec():
            self.show_lobby()
    
    def create(self):
        dlg = CreateAccountDialog(self.api, self)
        if dlg.exec():
            self.show_lobby()
    
    def show_lobby(self):
        try:
            me = self.api.me()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        
        # Update header
        self.account_name.setText(me.get("name", "Player"))
        self.account_stats.setText(
            f"Rating: {me.get('rating', 1500):.0f}  •  "
            f"W: {me.get('wins', 0)}  L: {me.get('losses', 0)}  D: {me.get('draws', 0)}"
        )
        
        # Hide auth, show lobby
        self.auth_card.hide()
        self.lobby_card.show()
        
        # Replace lobby widget
        if self.lobby:
            self.lobby.setParent(None)
            self.lobby.deleteLater()
            self.lobby = None
        
        self.lobby = Lobby(self.api, self.open_game, self)
        self.lobby_layout.addWidget(self.lobby)
    
    def open_game(self, game_id: int):
        self.game = GameWindow(self.api, game_id, None)
        self.game.resize(1200, 850)
        self.game.show()
