"""
lobby_service.py

Handles lobby chat for players waiting in queue.
Messages are stored in memory (not persisted).
"""

import threading
from datetime import datetime, timezone
from collections import deque
from dataclasses import dataclass, asdict


@dataclass
class LobbyMessage:
    id: int
    player_id: int
    player_name: str
    text: str
    timestamp: str
    is_bot: bool = False


class LobbyService:
    def __init__(self, max_messages: int = 100):
        self._lock = threading.Lock()
        self._messages: deque[LobbyMessage] = deque(maxlen=max_messages)
        self._next_id = 1
    
    def send_message(self, player_id: int, player_name: str, text: str, is_bot: bool = False) -> dict:
        """Send a message to the lobby."""
        with self._lock:
            msg = LobbyMessage(
                id=self._next_id,
                player_id=player_id,
                player_name=player_name,
                text=text[:500],  # Limit message length
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


# Singleton instance
lobby = LobbyService()
