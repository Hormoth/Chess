"""
chess_bot.py

A bot client that behaves like a player:
- Logs in via API key
- Joins the lobby
- Can chat in lobby and game
- Queues for matchmaking
- Plays moves (using Stockfish or custom logic)

The bot has the same capabilities as a human player client.
"""

import os
import sys
import time
import random
import threading
from typing import Optional, Callable
import chess
import chess.engine

from .api_client import APIClient


class ChessBot:
    """
    A bot client that acts like a player.

    All chat is manual - call lobby_chat() or game_chat() when you want to send messages.
    Override on_lobby_message() and on_game_update() to handle incoming data.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        stockfish_path: Optional[str] = None,
        skill_level: int = 10,
        think_time_ms: int = 500,
    ):
        self.api = APIClient(base_url)
        self.api_key = api_key
        self.stockfish_path = stockfish_path
        self.skill_level = max(0, min(20, skill_level))
        self.think_time_ms = think_time_ms

        # State
        self.running = False
        self.in_game = False
        self.current_game_id: Optional[int] = None
        self.last_lobby_message_id = 0

        # Callbacks (override these or set them)
        self.on_lobby_message: Optional[Callable[[dict], None]] = None
        self.on_game_start: Optional[Callable[[dict], None]] = None
        self.on_game_end: Optional[Callable[[dict], None]] = None
        self.on_opponent_move: Optional[Callable[[dict, str], None]] = None

        # Threads
        self._lobby_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None

    @property
    def player_id(self) -> Optional[int]:
        return self.api.player_id

    @property
    def name(self) -> Optional[str]:
        return self.api.name

    # ---- Authentication ----

    def login(self) -> dict:
        """Log in with API key."""
        info = self.api.bot_login(self.api_key)
        print(f"[BOT] Logged in as: {info['name']} (id={info['player_id']})")
        return info

    # ---- Lobby ----

    def join_lobby(self) -> dict:
        """Join the lobby (mark as online)."""
        result = self.api.join_lobby()
        print(f"[BOT] Joined lobby")
        return result

    def leave_lobby(self) -> dict:
        """Leave the lobby (mark as offline)."""
        result = self.api.leave_lobby()
        print(f"[BOT] Left lobby")
        return result

    def lobby_chat(self, text: str) -> dict:
        """Send a message to the lobby."""
        return self.api.lobby_chat(text)

    def get_lobby_messages(self, since_id: int = 0) -> list:
        """Get lobby messages since a given ID."""
        return self.api.get_lobby_messages(since_id=since_id)

    def get_online_players(self, include_bots: bool = True) -> list:
        """Get list of online players in lobby."""
        return self.api.get_online_players(include_bots=include_bots)

    # ---- Matchmaking ----

    def queue(self, ranked: bool = False, vs_system: bool = False) -> dict:
        """Queue for a game."""
        return self.api.queue(ranked=ranked, vs_system=vs_system)

    def get_matchmaking_status(self) -> dict:
        """Check current matchmaking status."""
        # Re-queue returns current status
        return self.api.queue(ranked=False, vs_system=False)

    # ---- Game ----

    def get_game(self, game_id: int) -> dict:
        """Get game state."""
        return self.api.get_game(game_id)

    def move(self, game_id: int, uci: str) -> dict:
        """Make a move in UCI format (e.g., 'e2e4')."""
        return self.api.move(game_id, uci)

    def game_chat(self, game_id: int, text: str) -> dict:
        """Send a chat message in a game."""
        return self.api.chat(game_id, text)

    # ---- Move Generation ----

    def get_stockfish_move(self, fen: str) -> Optional[str]:
        """Get a move from Stockfish engine."""
        if not self.stockfish_path:
            return None

        try:
            board = chess.Board() if (not fen or fen == "startpos") else chess.Board(fen)

            with chess.engine.SimpleEngine.popen_uci(self.stockfish_path) as engine:
                engine.configure({"Skill Level": self.skill_level})
                result = engine.play(
                    board,
                    chess.engine.Limit(time=self.think_time_ms / 1000.0)
                )
                return result.move.uci() if result.move else None

        except FileNotFoundError:
            print(f"[BOT] Stockfish not found at: {self.stockfish_path}")
            return None
        except Exception as e:
            print(f"[BOT] Stockfish error: {e}")
            return None

    def get_random_move(self, fen: str) -> str:
        """Get a random legal move."""
        board = chess.Board() if (not fen or fen == "startpos") else chess.Board(fen)
        moves = list(board.legal_moves)
        if not moves:
            return ""
        return random.choice(moves).uci()

    def get_best_move(self, fen: str) -> str:
        """Get best move (Stockfish if available, else random)."""
        move = self.get_stockfish_move(fen)
        if move:
            return move
        return self.get_random_move(fen)

    def is_my_turn(self, game_data: dict) -> bool:
        """Check if it's the bot's turn."""
        turn = game_data.get("meta", {}).get("turn")
        my_id = self.api.player_id
        return (
            (turn == "white" and my_id == game_data.get("white_id")) or
            (turn == "black" and my_id == game_data.get("black_id"))
        )

    # ---- Background Tasks ----

    def _heartbeat_loop(self):
        """Send periodic heartbeats to stay online."""
        while self.running:
            try:
                self.api.lobby_heartbeat()
            except Exception as e:
                print(f"[BOT] Heartbeat error: {e}")
            time.sleep(30)

    def _lobby_monitor_loop(self):
        """Monitor lobby chat for new messages."""
        while self.running and not self.in_game:
            try:
                messages = self.api.get_lobby_messages(since_id=self.last_lobby_message_id)
                for msg in messages:
                    self.last_lobby_message_id = max(self.last_lobby_message_id, msg['id'])
                    # Skip own messages
                    if msg['player_id'] != self.api.player_id and self.on_lobby_message:
                        self.on_lobby_message(msg)
            except Exception as e:
                print(f"[BOT] Lobby monitor error: {e}")
            time.sleep(2)

    def start_background_tasks(self):
        """Start heartbeat and lobby monitoring."""
        self.running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        self._lobby_thread = threading.Thread(target=self._lobby_monitor_loop, daemon=True)
        self._lobby_thread.start()

    def stop_background_tasks(self):
        """Stop background tasks."""
        self.running = False

    # ---- Game Loop ----

    def wait_for_match(self, ranked: bool = False, vs_system: bool = False) -> int:
        """Queue and wait until matched. Returns game_id."""
        print(f"[BOT] Queuing (ranked={ranked}, vs_system={vs_system})")

        q = self.queue(ranked=ranked, vs_system=vs_system)
        game_id = q.get("game_id")

        while self.running and not game_id:
            time.sleep(1)
            q = self.queue(ranked=ranked, vs_system=vs_system)
            game_id = q.get("game_id")

        print(f"[BOT] Matched! Game ID: {game_id}")
        return game_id

    def play_game(self, game_id: int, auto_move: bool = True):
        """
        Play a game.

        Args:
            game_id: The game to play
            auto_move: If True, automatically play moves using Stockfish/random
        """
        self.in_game = True
        self.current_game_id = game_id

        # Wait for game to be active
        while self.running:
            game = self.get_game(game_id)
            if game.get("status") == "active":
                break
            if game.get("status") == "ended":
                print(f"[BOT] Game ended before starting")
                self.in_game = False
                return
            time.sleep(0.5)

        if self.on_game_start:
            self.on_game_start(game)

        print(f"[BOT] Game started - White: {game.get('white_id')}, Black: {game.get('black_id')}")

        last_fen = None

        while self.running:
            try:
                game = self.get_game(game_id)

                if game.get("status") != "active":
                    print(f"[BOT] Game ended: {game.get('result')} ({game.get('end_reason')})")
                    if self.on_game_end:
                        self.on_game_end(game)
                    break

                current_fen = game.get("fen", "startpos")

                # Detect opponent move
                if current_fen != last_fen and last_fen is not None:
                    if self.on_opponent_move:
                        self.on_opponent_move(game, current_fen)

                last_fen = current_fen

                # Auto-move if enabled and it's our turn
                if auto_move and self.is_my_turn(game):
                    uci = self.get_best_move(current_fen)
                    if uci:
                        self.move(game_id, uci)
                        print(f"[BOT] Played: {uci}")

                time.sleep(0.5)

            except Exception as e:
                print(f"[BOT] Game error: {e}")
                time.sleep(1)

        self.in_game = False
        self.current_game_id = None

    # ---- Simple Run Loop ----

    def run(self, ranked: bool = False, vs_system: bool = False, continuous: bool = True):
        """
        Simple run loop: login, join lobby, play games.

        Args:
            ranked: Play ranked games
            vs_system: If no opponent, play vs system bot
            continuous: Keep playing games (False = play one and stop)
        """
        self.login()
        self.join_lobby()
        self.start_background_tasks()

        try:
            while self.running:
                game_id = self.wait_for_match(ranked=ranked, vs_system=vs_system)
                if game_id:
                    self.play_game(game_id)

                if not continuous:
                    break

                time.sleep(2)

        except KeyboardInterrupt:
            print("\n[BOT] Interrupted")
        finally:
            self.stop_background_tasks()
            self.leave_lobby()
            print("[BOT] Stopped")


def main():
    """Run bot with environment variable config."""
    base_url = os.getenv("CHESS_ARENA_URL", "http://127.0.0.1:8001")
    api_key = os.getenv("BOT_API_KEY", "")
    stockfish_path = os.getenv("STOCKFISH_PATH", "")
    skill_level = int(os.getenv("BOT_SKILL_LEVEL", "10"))
    think_time = int(os.getenv("BOT_THINK_TIME_MS", "500"))
    ranked = os.getenv("BOT_RANKED", "false").lower() == "true"
    vs_system = os.getenv("BOT_MODE", "pvp").lower() == "system"
    continuous = os.getenv("BOT_CONTINUOUS", "true").lower() == "true"

    if not api_key:
        print("ERROR: Set BOT_API_KEY environment variable")
        print("\nEnvironment variables:")
        print("  CHESS_ARENA_URL    - Server URL (default: http://127.0.0.1:8001)")
        print("  BOT_API_KEY        - Bot's API key (required)")
        print("  STOCKFISH_PATH     - Path to Stockfish executable")
        print("  BOT_SKILL_LEVEL    - Stockfish skill 0-20 (default: 10)")
        print("  BOT_THINK_TIME_MS  - Think time in ms (default: 500)")
        print("  BOT_RANKED         - true/false (default: false)")
        print("  BOT_MODE           - pvp/system (default: pvp)")
        print("  BOT_CONTINUOUS     - true/false (default: true)")
        sys.exit(1)

    bot = ChessBot(
        base_url=base_url,
        api_key=api_key,
        stockfish_path=stockfish_path if stockfish_path else None,
        skill_level=skill_level,
        think_time_ms=think_time,
    )

    bot.run(ranked=ranked, vs_system=vs_system, continuous=continuous)


if __name__ == "__main__":
    main()
