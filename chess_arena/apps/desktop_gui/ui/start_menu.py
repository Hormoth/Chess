from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox, QFrame, QHBoxLayout
)
from PySide6.QtCore import Qt

from .login_dialog import LoginDialog
from .create_account_dialog import CreateAccountDialog
from .lobby import Lobby
from .game_window import GameWindow


class StartMenu(QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Chess Arena")
        self.setMinimumSize(560, 360)

        self.lobby = None
        self.game = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # ---------- Header ----------
        header = QFrame()
        header.setObjectName("Card")
        h = QHBoxLayout(header)
        h.setContentsMargins(16, 14, 16, 14)

        self.title = QLabel("Chess Arena")
        self.title.setObjectName("Title")
        h.addWidget(self.title)

        h.addStretch()

        self.account_status = QLabel("Not logged in")
        self.account_status.setObjectName("Subtitle")
        self.account_status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(self.account_status)

        root.addWidget(header)

        # ---------- Auth Card (Login/Create) ----------
        self.auth_card = QFrame()
        self.auth_card.setObjectName("Card")
        a = QVBoxLayout(self.auth_card)
        a.setContentsMargins(16, 16, 16, 16)
        a.setSpacing(10)

        auth_msg = QLabel("Login or create an account to play ranked or online.")
        auth_msg.setObjectName("Subtitle")
        auth_msg.setWordWrap(True)
        a.addWidget(auth_msg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_login = QPushButton("Login")
        self.btn_create = QPushButton("Create Account")
        self.btn_login.clicked.connect(self.login)
        self.btn_create.clicked.connect(self.create)

        btn_row.addWidget(self.btn_login)
        btn_row.addWidget(self.btn_create)
        a.addLayout(btn_row)

        root.addWidget(self.auth_card)

        # ---------- Lobby Container (hidden until logged in) ----------
        self.lobby_card = QFrame()
        self.lobby_card.setObjectName("Card")
        self.lobby_layout = QVBoxLayout(self.lobby_card)
        self.lobby_layout.setContentsMargins(16, 16, 16, 16)
        self.lobby_layout.setSpacing(10)
        self.lobby_card.hide()

        root.addWidget(self.lobby_card, stretch=1)

        # If already logged in (token saved in this run), show lobby
        if self.api.token:
            self.show_lobby()

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

        # Update header status
        self.account_status.setText(
            f"{me['name']} • {me['rating']:.0f} • W/L/D {me['wins']}/{me['losses']}/{me['draws']}"
        )

        # Hide auth UI, show lobby UI
        self.auth_card.hide()
        self.lobby_card.show()

        # Replace lobby widget if it exists
        if self.lobby:
            self.lobby.setParent(None)
            self.lobby.deleteLater()
            self.lobby = None

        self.lobby = Lobby(self.api, self.open_game, self)
        self.lobby_layout.addWidget(self.lobby)

    def open_game(self, game_id: int):
        self.game = GameWindow(self.api, game_id, None)
        self.game.resize(980, 720)
        self.game.show()
