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


# ---- Online Presence Endpoints ----

@router.post("/join")
def join_lobby(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    """Join the lobby (mark player as online)."""
    p = get_player_from_auth(db, authorization)
    return lobby.join_lobby(
        player_id=p.id,
        player_name=p.name,
        rating=p.rating,
        is_bot=p.is_bot
    )


@router.post("/leave")
def leave_lobby(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    """Leave the lobby (mark player as offline)."""
    p = get_player_from_auth(db, authorization)
    left = lobby.leave_lobby(p.id)
    return {"left": left}


@router.post("/heartbeat")
def lobby_heartbeat(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    """Update last_seen timestamp (call periodically to stay online)."""
    p = get_player_from_auth(db, authorization)
    updated = lobby.heartbeat(p.id)
    return {"updated": updated}


@router.get("/online")
def get_online_players(include_bots: bool = True):
    """Get list of players currently online in the lobby."""
    return lobby.get_online_players(include_bots=include_bots)


@router.get("/online/count")
def get_online_count():
    """Get count of online players (humans and bots)."""
    return lobby.get_online_count()
