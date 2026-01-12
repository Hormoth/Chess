"""
lobby_service.py

Handles lobby chat and online presence for players.
Messages and presence are stored in memory (not persisted).
"""

import html
import threading
from datetime import datetime, timezone
from collections import deque
from dataclasses import dataclass, asdict
from typing import Dict


@dataclass
class LobbyMessage:
    id: int
    player_id: int
    player_name: str
    text: str
    timestamp: str
    is_bot: bool = False


@dataclass
class OnlinePlayer:
    player_id: int
    player_name: str
    rating: int
    is_bot: bool
    joined_at: str
    last_seen: str


class LobbyService:
    def __init__(self, max_messages: int = 100):
        self._lock = threading.Lock()
        self._messages: deque[LobbyMessage] = deque(maxlen=max_messages)
        self._next_id = 1
        # Online presence tracking
        self._online_players: Dict[int, OnlinePlayer] = {}
    
    def send_message(self, player_id: int, player_name: str, text: str, is_bot: bool = False) -> dict:
        """Send a message to the lobby."""
        # Sanitize inputs to prevent XSS
        safe_name = html.escape(player_name[:50])
        safe_text = html.escape(text[:500])

        with self._lock:
            msg = LobbyMessage(
                id=self._next_id,
                player_id=player_id,
                player_name=safe_name,
                text=safe_text,
                timestamp=datetime.now(timezone.utc).isoformat(),
                is_bot=is_bot
            )
            self._next_id += 1
            self._messages.append(msg)
            return asdict(msg)
    
    def get_messages(self, since_id: int = 0, limit: int = 50) -> list[dict]:
        """Get messages since a given ID."""
        with self._lock:
            messages = [
                asdict(m) for m in self._messages 
                if m.id > since_id
            ]
            return messages[-limit:]
    
    def get_recent(self, limit: int = 20) -> list[dict]:
        """Get most recent messages."""
        with self._lock:
            messages = list(self._messages)
            return [asdict(m) for m in messages[-limit:]]

    # ---- Online Presence Methods ----

    def join_lobby(self, player_id: int, player_name: str, rating: int, is_bot: bool = False) -> dict:
        """Mark a player as online in the lobby."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._online_players[player_id] = OnlinePlayer(
                player_id=player_id,
                player_name=html.escape(player_name[:50]),
                rating=rating,
                is_bot=is_bot,
                joined_at=now,
                last_seen=now
            )
            return asdict(self._online_players[player_id])

    def leave_lobby(self, player_id: int) -> bool:
        """Remove a player from online list."""
        with self._lock:
            if player_id in self._online_players:
                del self._online_players[player_id]
                return True
            return False

    def heartbeat(self, player_id: int) -> bool:
        """Update last_seen timestamp for a player."""
        with self._lock:
            if player_id in self._online_players:
                self._online_players[player_id].last_seen = datetime.now(timezone.utc).isoformat()
                return True
            return False

    def get_online_players(self, include_bots: bool = True) -> list[dict]:
        """Get list of online players."""
        with self._lock:
            players = list(self._online_players.values())
            if not include_bots:
                players = [p for p in players if not p.is_bot]
            return [asdict(p) for p in players]

    def get_online_count(self) -> dict:
        """Get count of online players (humans and bots separately)."""
        with self._lock:
            humans = sum(1 for p in self._online_players.values() if not p.is_bot)
            bots = sum(1 for p in self._online_players.values() if p.is_bot)
            return {"humans": humans, "bots": bots, "total": humans + bots}

    def is_online(self, player_id: int) -> bool:
        """Check if a player is online."""
        with self._lock:
            return player_id in self._online_players


# Singleton instance
lobby = LobbyService()
