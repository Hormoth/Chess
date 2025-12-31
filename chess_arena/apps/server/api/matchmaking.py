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
    # ❌ REMOVED: player_id (use token instead)


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