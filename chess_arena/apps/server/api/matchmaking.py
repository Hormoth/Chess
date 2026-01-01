from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services.matchmaking_service import mm
from ..api.players import get_player_from_auth

router = APIRouter(prefix="/matchmaking", tags=["matchmaking"])


class QueueReq(BaseModel):
    ranked: bool = True
    vs_system: bool = False


@router.post("/queue")
def queue(
    req: QueueReq,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    """Queue for matchmaking using token authentication."""
    p = get_player_from_auth(db, authorization)
    try:
        return mm.enqueue(db, p.id, ranked=req.ranked, vs_system=req.vs_system)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/status")
def status(
    ranked: bool = True,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    """Get matchmaking status using token authentication."""
    p = get_player_from_auth(db, authorization)
    return mm.status(db, p.id, ranked=ranked)


@router.get("/waiting")
def get_waiting_players(
    ranked: bool | None = None,
    db: Session = Depends(get_db),
):
    """Get list of players waiting in queue."""
    return mm.get_waiting_players(db, ranked=ranked)


@router.post("/cancel")
def cancel_queue(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    """Cancel matchmaking and leave the queue."""
    p = get_player_from_auth(db, authorization)
    was_queued = mm.cancel(p.id)
    return {"success": True, "was_queued": was_queued}
