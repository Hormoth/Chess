from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

from ..db.session import get_db
from ..db.models import Player
from ..settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])
pwd = CryptContext(schemes=["argon2"], deprecated="auto")


class RegisterReq(BaseModel):
    email: EmailStr
    name: str
    password: str
    is_bot: bool = False

class LoginReq(BaseModel):
    email: EmailStr
    password: str

class TokenRes(BaseModel):
    token: str
    player_id: int
    name: str
    is_bot: bool
    api_key: str | None = None

def make_token(player: Player) -> str:
    payload = {
        "sub": str(player.id),
        "name": player.name,
        "is_bot": player.is_bot,
        "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_exp_minutes)
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)

@router.post("/register", response_model=TokenRes)
def register(req: RegisterReq, db: Session = Depends(get_db)):
    if db.query(Player).filter((Player.email == req.email.lower()) | (Player.name == req.name.strip())).first():
        raise HTTPException(400, "Email or name already used.")

    p = Player(
        email=req.email.lower(),
        name=req.name.strip(),
        password_hash=pwd.hash(req.password),
        is_bot=req.is_bot
    )
    if p.is_bot:
        p.ensure_api_key()
    db.add(p); db.commit(); db.refresh(p)

    return TokenRes(
        token=make_token(p),
        player_id=p.id,
        name=p.name,
        is_bot=p.is_bot,
        api_key=p.api_key if p.is_bot else None
    )

@router.post("/login", response_model=TokenRes)
def login(req: LoginReq, db: Session = Depends(get_db)):
    p = db.query(Player).filter(Player.email == req.email.lower()).first()
    if not p or not pwd.verify(req.password, p.password_hash):
        raise HTTPException(401, "Invalid credentials.")
    return TokenRes(token=make_token(p), player_id=p.id, name=p.name, is_bot=p.is_bot, api_key=None)

@router.post("/bot/login", response_model=TokenRes)
def bot_login(x_api_key: str = Header(...), db: Session = Depends(get_db)):
    p = db.query(Player).filter(Player.api_key == x_api_key).first()
    if not p or not p.is_bot:
        raise HTTPException(401, "Invalid bot API key.")
    return TokenRes(token=make_token(p), player_id=p.id, name=p.name, is_bot=True, api_key=p.api_key)
