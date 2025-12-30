from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox, QHBoxLayout, QCheckBox
)

class Lobby(QWidget):
    def __init__(self, api, on_game_ready, parent=None):
        super().__init__(parent)
        self.api = api
        self.on_game_ready = on_game_ready

        # ✅ Keep this attribute name because other code may expect it
        # (Your old snippet had: self.open_game_cb = open_game (bug: open_game not defined))
        # Here we point it at the callback you actually receive.
        self.open_game_cb = on_game_ready

        layout = QVBoxLayout(self)
        self.info = QLabel("Queue for a match")
        layout.addWidget(self.info)

        self.ranked = QCheckBox("Ranked")
        self.ranked.setChecked(True)
        layout.addWidget(self.ranked)

        row = QHBoxLayout()
        self.btn_pvp = QPushButton("Play Player (Online)")
        self.btn_sys = QPushButton("Play System (Stockfish)")

        # ✅ These methods exist now
        self.btn_pvp.clicked.connect(self.queue_pvp)
        self.btn_sys.clicked.connect(self.queue_system)

        row.addWidget(self.btn_pvp)
        row.addWidget(self.btn_sys)
        layout.addLayout(row)

    # ----------------------------
    # Queue handlers (DROP-IN)
    # ----------------------------

    def queue_pvp(self):
        """
        Queue for PvP matchmaking.
        Preserves your original behavior:
          - uses ranked checkbox
          - if waiting: update label and return
          - else: call on_game_ready(game_id)
        """
        try:
            q = self.api.queue(ranked=self.ranked.isChecked(), vs_system=False)

            if q.get("status") == "waiting":
                self.info.setText("Waiting for an opponent...")
                return

            self.on_game_ready(q["game_id"])

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def queue_system(self):
        """
        Queue to play the System/Stockfish.
        Preserves your original behavior:
          - uses ranked checkbox
          - if waiting: update label and return
          - else: call on_game_ready(game_id)
        """
        try:
            q = self.api.queue(ranked=self.ranked.isChecked(), vs_system=True)

            # vs_system should always return active+game_id, but keep it safe
            if q.get("status") == "waiting":
                self.info.setText("Waiting...")
                return

            self.on_game_ready(q["game_id"])

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ----------------------------
    # Optional helpers (safe)
    # ----------------------------

    def _handle_queue_response(self, resp, label="Game"):
        """
        Common handler for queue responses.
        Kept as a helper in case you later want to route both queue methods through it.
        Currently not required, but harmless to keep.
        """
        if not isinstance(resp, dict):
            self._show_error(f"{label} queue returned unexpected response: {resp!r}")
            return

        game_id = resp.get("game_id")
        if not game_id:
            self._show_error(f"{label} queue did not return a game_id: {resp}")
            return

        # Prefer the callback passed to Lobby(...)
        if callable(getattr(self, "on_game_ready", None)):
            self.on_game_ready(game_id)
            return

        # Fallbacks if another part of your app uses these names
        if callable(getattr(self, "open_game_cb", None)):
            self.open_game_cb(game_id)
            return

        self._show_error(f"{label} queued (game {game_id}), but no open-game callback is wired.")

    def _show_error(self, msg: str):
        # Keep it simple; swap to QMessageBox if you prefer.
        print(f"[Lobby] {msg}")
