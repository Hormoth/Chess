import os
import sys

from PySide6.QtWidgets import QApplication

from chess_arena.apps.desktop_gui.client.api_client import APIClient
from chess_arena.apps.desktop_gui.ui.start_menu import StartMenu
from chess_arena.apps.desktop_gui.ui.theme import APP_QSS


def main():
    # Env var wins; fallback to local dev server
    base_url = os.environ.get("CHESS_ARENA_URL") or "http://127.0.0.1:8001"

    # Create Qt app first, then apply theme
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)

    # Create API client once
    api = APIClient(base_url)

    # Show start menu
    w = StartMenu(api)
    w.resize(520, 320)
    w.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
