"""
lobby.py - Lobby chat API endpoints (SERVER)

This is the FastAPI router for lobby chat.
NOT the GUI widget - that's in desktop_gui/ui/lobby.py
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services.lobby_service import lobby
from .players import get_player_from_auth

router = APIRouter(prefix="/lobby", tags=["lobby"])


class ChatMessage(BaseModel):
    text: str


@router.post("/chat")
def send_lobby_message(
    msg: ChatMessage,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    """Send a message to the lobby chat."""
    p = get_player_from_auth(db, authorization)
    
    if not msg.text or not msg.text.strip():
        raise HTTPException(400, "Message cannot be empty")
    
    return lobby.send_message(
        player_id=p.id,
        player_name=p.name,
        text=msg.text.strip(),
        is_bot=p.is_bot
    )


@router.get("/chat")
def get_lobby_messages(
    since: int = 0,
    limit: int = 50,
):
    """Get lobby chat messages."""
    return lobby.get_messages(since_id=since, limit=limit)


@router.get("/chat/recent")
def get_recent_messages(limit: int = 20):
    """Get most recent lobby messages."""
    return lobby.get_recent(limit=limit)
