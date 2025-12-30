import json
import threading
import websocket  # NOTE: we avoid extra deps by using websockets in python, but PySide threading is easier with websocket-client

# We won't add websocket-client to requirements by default. Instead we use `websockets` in a thread in game_window.
# This module remains as a placeholder for future improvements.
