from fastapi import APIRouter, Depends, HTTPException, Header
from jose import jwt
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import Player
from ..settings import settings

router = APIRouter(prefix="/players", tags=["players"])

def get_player_from_auth(db: Session, authorization: str | None) -> Player:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
        pid = int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Invalid token")
    p = db.get(Player, pid)
    if not p:
        raise HTTPException(401, "Player not found")
    return p

@router.get("/me")
def me(db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    p = get_player_from_auth(db, authorization)
    return {
        "id": p.id,
        "email": p.email,
        "name": p.name,
        "is_bot": p.is_bot,
        "api_key": p.api_key,
        "rating": p.rating,
        "rd": p.rd,
        "vol": p.vol,
        "wins": p.wins,
        "losses": p.losses,
        "draws": p.draws,
    }
