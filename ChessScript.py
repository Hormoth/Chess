#!/usr/bin/env python3
"""
bootstrap_chess_arena.py

Creates an online-multiplayer chess platform scaffold:
- FastAPI backend (accounts, JWT, bot API-key login, matchmaking, games, chat, websockets)
- Shared chess rules via python-chess
- Glicko-2 rating updates
- Stockfish-based "play system" (bot account + server-side engine move)
- Minimal PySide6 desktop GUI (login/register, queue ranked/free, board, last-6 moves, chat)
- Bot client example (Agamemnon-style)

USAGE:
  python bootstrap_chess_arena.py chess_arena
  cd chess_arena
  python -m venv venv
  venv\\Scripts\\activate
  pip install -r requirements.txt
  # install stockfish binary and set STOCKFISH_PATH env var or edit apps/server/settings.py
  python apps/server/main.py
  python apps/desktop_gui/main.py

NOTES:
- This is a working v1 scaffold. You will want to harden auth, add email verification,
  improve matchmaking, implement draw claims, clocks, resign/draw offers, PGN export, etc.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from textwrap import dedent

REQUIREMENTS = dedent(
    """
    fastapi>=0.110
    uvicorn[standard]>=0.27
    sqlalchemy>=2.0
    pydantic>=2.6
    python-jose[cryptography]>=3.3
    passlib[bcrypt]>=1.7
    python-chess>=1.999
    glicko2>=2.1
    httpx>=0.27
    websockets>=12.0
    pyside6>=6.6
    """
).strip() + "\n"


def write_file(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python bootstrap_chess_arena.py <project_dir>")
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)

    # -------------------------
    # Top-level files
    # -------------------------
    write_file(root, "requirements.txt", REQUIREMENTS)

    write_file(
        root,
        "README.md",
        dedent(
            f"""
            # Chess Arena (v1 scaffold)

            Online multiplayer chess with:
            - Accounts (email + password)
            - Bot accounts via API key (Agamemnon-friendly)
            - Ranked / Free play queues
            - Glicko-2 ratings for ranked games
            - Real-time moves + chat over WebSockets
            - Stockfish-based "Play System"

            ## Setup (Windows)
            ```bat
            python -m venv venv
            venv\\Scripts\\activate
            pip install -r requirements.txt
            ```

            ## Stockfish
            Install Stockfish on your machine and set:
            ```bat
            setx STOCKFISH_PATH "C:\\path\\to\\stockfish.exe"
            ```
            Or edit `apps/server/settings.py`.

            ## Run backend
            ```bat
            venv\\Scripts\\activate
            python apps\\server\\main.py
            ```

            Backend runs at http://127.0.0.1:8000

            ## Run GUI
            ```bat
            venv\\Scripts\\activate
            python apps\\desktop_gui\\main.py
            ```

            ## Run Bot Client (example)
            1) Create a bot account in GUI or via API `/auth/register` with `is_bot=true`.
            2) Copy the returned `api_key` from `/players/me` or DB.
            3) Run:
            ```bat
            venv\\Scripts\\activate
            set BOT_API_KEY=...your key...
            python apps\\bot_client\\agamemnon_bot.py
            ```

            ## Dev DB
            SQLite database: `storage/dev.db`

            ## Next improvements you’ll likely want
            - clocks (10+0 now, add increments + timeout)
            - draw claims endpoints (threefold, 50-move)
            - resign / offer draw flow
            - promotion chooser UI
            - matchmaking by rating bands
            - reconnect + spectators
            - email verification + password reset
            """
        ).strip()
        + "\n",
    )

    # -------------------------
    # Shared chess library
    # -------------------------
    write_file(
        root,
        "packages/chesslib/__init__.py",
        "from .rules import *\n",
    )

    write_file(
        root,
        "packages/chesslib/rules.py",
        dedent(
            """
            import chess

            def board_from_fen_or_start(fen: str) -> chess.Board:
                if not fen or fen == "startpos":
                    return chess.Board()
                return chess.Board(fen)

            def apply_uci_move(fen: str, uci: str) -> tuple[str, str]:
                b = board_from_fen_or_start(fen)
                move = chess.Move.from_uci(uci)
                if move not in b.legal_moves:
                    raise ValueError("Illegal move")
                san = b.san(move)
                b.push(move)
                return b.fen(), san

            def status_flags(fen: str) -> dict:
                b = board_from_fen_or_start(fen)
                return {
                    "turn": "white" if b.turn else "black",
                    "in_check": b.is_check(),
                    "is_checkmate": b.is_checkmate(),
                    "is_stalemate": b.is_stalemate(),
                    "insufficient": b.is_insufficient_material(),
                    "can_claim_threefold": b.can_claim_threefold_repetition(),
                    "can_claim_fifty": b.can_claim_fifty_moves(),
                    "halfmove_clock": b.halfmove_clock,
                    "fullmove_number": b.fullmove_number,
                }

            def uci_to_from_to(uci: str) -> tuple[str, str, str | None]:
                # "e2e4" or "e7e8q"
                uci = uci.strip()
                if len(uci) < 4:
                    raise ValueError("Bad UCI")
                frm = uci[0:2]
                to = uci[2:4]
                promo = uci[4:5] if len(uci) >= 5 else None
                return frm, to, promo
            """
        ).strip()
        + "\n",
    )

    # -------------------------
    # Server
    # -------------------------
    write_file(
        root,
        "apps/server/settings.py",
        dedent(
            """
            from pydantic import BaseModel
            import os

            class Settings(BaseModel):
                jwt_secret: str = os.getenv("JWT_SECRET", "CHANGE_ME_DEV_SECRET")
                jwt_alg: str = "HS256"
                jwt_exp_minutes: int = 60 * 24
                db_url: str = os.getenv("DATABASE_URL", "sqlite:///storage/dev.db")
                stockfish_path: str = os.getenv("STOCKFISH_PATH", "stockfish")  # set env to .exe on Windows
                default_time_control: str = os.getenv("DEFAULT_TIME_CONTROL", "10+0")

            settings = Settings()
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/server/db/session.py",
        dedent(
            """
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from ...server.settings import settings

            # sqlite needs check_same_thread=False
            connect_args = {"check_same_thread": False} if settings.db_url.startswith("sqlite") else {}
            engine = create_engine(settings.db_url, echo=False, future=True, connect_args=connect_args)
            SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

            def get_db():
                db = SessionLocal()
                try:
                    yield db
                finally:
                    db.close()
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/server/db/models.py",
        dedent(
            """
            from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, Text, Float
            from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
            from datetime import datetime
            import secrets

            class Base(DeclarativeBase):
                pass

            class Player(Base):
                __tablename__ = "players"
                id: Mapped[int] = mapped_column(Integer, primary_key=True)
                email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
                name: Mapped[str] = mapped_column(String(40), unique=True, index=True)
                password_hash: Mapped[str] = mapped_column(String(255))
                is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
                api_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

                # Glicko-2 fields
                rating: Mapped[float] = mapped_column(Float, default=1500.0)
                rd: Mapped[float] = mapped_column(Float, default=350.0)
                vol: Mapped[float] = mapped_column(Float, default=0.06)

                wins: Mapped[int] = mapped_column(Integer, default=0)
                losses: Mapped[int] = mapped_column(Integer, default=0)
                draws: Mapped[int] = mapped_column(Integer, default=0)

                created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

                def ensure_api_key(self):
                    if not self.api_key:
                        self.api_key = secrets.token_hex(32)

            class Game(Base):
                __tablename__ = "games"
                id: Mapped[int] = mapped_column(Integer, primary_key=True)
                ranked: Mapped[bool] = mapped_column(Boolean, default=False)
                time_control: Mapped[str] = mapped_column(String(20), default="10+0")
                white_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
                black_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
                fen: Mapped[str] = mapped_column(Text, default="startpos")
                pgn: Mapped[str] = mapped_column(Text, default="")
                status: Mapped[str] = mapped_column(String(20), default="waiting")  # waiting/active/ended
                result: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 1-0, 0-1, 1/2-1/2
                end_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
                created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/server/realtime/ws_hub.py",
        dedent(
            """
            from collections import defaultdict
            from fastapi import WebSocket

            class Hub:
                def __init__(self):
                    self.rooms = defaultdict(set)  # game_id -> set[WebSocket]

                async def join(self, game_id: int, ws: WebSocket):
                    await ws.accept()
                    self.rooms[game_id].add(ws)

                def leave(self, game_id: int, ws: WebSocket):
                    self.rooms[game_id].discard(ws)

                async def broadcast(self, game_id: int, payload: dict):
                    dead = []
                    for ws in list(self.rooms[game_id]):
                        try:
                            await ws.send_json(payload)
                        except Exception:
                            dead.append(ws)
                    for ws in dead:
                        self.leave(game_id, ws)

            hub = Hub()
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/server/services/rating_glicko2.py",
        dedent(
            """
            from glicko2 import Player as GPlayer

            def update_after_game(white, black, result: str):
                w = GPlayer(rating=white.rating, rd=white.rd, vol=white.vol)
                b = GPlayer(rating=black.rating, rd=black.rd, vol=black.vol)

                if result == "1-0":
                    w.update_player([b.rating], [b.rd], [1])
                    b.update_player([w.rating], [w.rd], [0])
                    white.wins += 1; black.losses += 1
                elif result == "0-1":
                    w.update_player([b.rating], [b.rd], [0])
                    b.update_player([w.rating], [w.rd], [1])
                    white.losses += 1; black.wins += 1
                else:
                    w.update_player([b.rating], [b.rd], [0.5])
                    b.update_player([w.rating], [w.rd], [0.5])
                    white.draws += 1; black.draws += 1

                white.rating, white.rd, white.vol = w.rating, w.rd, w.vol
                black.rating, black.rd, black.vol = b.rating, b.rd, b.vol
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/server/services/stockfish_service.py",
        dedent(
            """
            import chess
            import chess.engine
            from ..settings import settings
            from ....packages.chesslib.rules import board_from_fen_or_start

            class StockfishService:
                def __init__(self):
                    self.path = settings.stockfish_path

                def best_move_uci(self, fen: str, think_ms: int = 200) -> str:
                    b = board_from_fen_or_start(fen)
                    with chess.engine.SimpleEngine.popen_uci(self.path) as engine:
                        limit = chess.engine.Limit(time=think_ms / 1000.0)
                        result = engine.play(b, limit)
                        return result.move.uci()

            stockfish = StockfishService()
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/server/services/matchmaking_service.py",
        dedent(
            """
            from collections import deque
            import random
            from ..db.models import Game, Player
            from ..settings import settings

            class MatchmakingService:
                def __init__(self):
                    self.ranked_q = deque()
                    self.free_q = deque()
                    self.system_q_ranked = deque()
                    self.system_q_free = deque()

                def enqueue(self, db, player_id: int, ranked: bool, vs_system: bool) -> Game:
                    # vs_system pairs player with a bot (is_bot=True) if available.
                    if vs_system:
                        # Find (or create) a single system bot account
                        bot = db.query(Player).filter(Player.is_bot == True).first()
                        if not bot:
                            raise ValueError("No bot account exists. Register a bot (is_bot=true).")
                        white, black = (player_id, bot.id) if random.random() < 0.5 else (bot.id, player_id)
                        g = Game(ranked=ranked, time_control=settings.default_time_control,
                                 white_id=white, black_id=black, fen="startpos", status="active")
                        db.add(g); db.commit(); db.refresh(g)
                        return g

                    q = self.ranked_q if ranked else self.free_q
                    q.append(player_id)

                    if len(q) >= 2:
                        p1 = q.popleft(); p2 = q.popleft()
                        white, black = (p1, p2) if random.random() < 0.5 else (p2, p1)
                        g = Game(ranked=ranked, time_control=settings.default_time_control,
                                 white_id=white, black_id=black, fen="startpos", status="active")
                        db.add(g); db.commit(); db.refresh(g)
                        return g

                    # waiting placeholder (optional)
                    g = Game(ranked=ranked, time_control=settings.default_time_control,
                             white_id=player_id, status="waiting", fen="startpos")
                    db.add(g); db.commit(); db.refresh(g)
                    return g

            mm = MatchmakingService()
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/server/api/auth.py",
        dedent(
            """
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
            pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/server/api/players.py",
        dedent(
            """
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
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/server/api/matchmaking.py",
        dedent(
            """
            from fastapi import APIRouter, Depends, HTTPException
            from pydantic import BaseModel
            from sqlalchemy.orm import Session
            from ..db.session import get_db
            from ..services.matchmaking_service import mm

            router = APIRouter(prefix="/matchmaking", tags=["matchmaking"])

            class QueueReq(BaseModel):
                player_id: int
                ranked: bool = True
                vs_system: bool = False

            @router.post("/queue")
            def queue(req: QueueReq, db: Session = Depends(get_db)):
                try:
                    game = mm.enqueue(db, req.player_id, ranked=req.ranked, vs_system=req.vs_system)
                except ValueError as e:
                    raise HTTPException(400, str(e))
                return {"game_id": game.id, "status": game.status, "ranked": game.ranked, "vs_system": req.vs_system}
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/server/api/games.py",
        dedent(
            """
            from fastapi import APIRouter, Depends, HTTPException, WebSocket
            from pydantic import BaseModel
            from sqlalchemy.orm import Session

            from ..db.session import get_db
            from ..db.models import Game, Player
            from ..realtime.ws_hub import hub
            from ..services.rating_glicko2 import update_after_game
            from ..services.stockfish_service import stockfish
            from ....packages.chesslib.rules import apply_uci_move, status_flags, board_from_fen_or_start

            router = APIRouter(prefix="/games", tags=["games"])

            class MoveReq(BaseModel):
                player_id: int
                uci: str

            class ChatReq(BaseModel):
                player_id: int
                text: str

            def end_game_if_needed(db: Session, g: Game) -> dict:
                meta = status_flags(g.fen)
                if meta["is_checkmate"]:
                    # side to move is checkmated
                    b = board_from_fen_or_start(g.fen)
                    g.status = "ended"
                    g.result = "0-1" if b.turn else "1-0"  # if white to move and checkmated => black won => 0-1
                    g.end_reason = "checkmate"
                elif meta["is_stalemate"]:
                    g.status = "ended"; g.result = "1/2-1/2"; g.end_reason = "stalemate"
                elif meta["insufficient"]:
                    g.status = "ended"; g.result = "1/2-1/2"; g.end_reason = "insufficient_material"
                return meta

            def maybe_rate(db: Session, g: Game):
                if g.ranked and g.status == "ended" and g.white_id and g.black_id and g.result:
                    w = db.get(Player, g.white_id)
                    b = db.get(Player, g.black_id)
                    if w and b:
                        update_after_game(w, b, g.result)

            async def maybe_play_system_move(db: Session, g: Game):
                # If one side is a bot, make engine move when it's bot's turn.
                if g.status != "active" or not g.white_id or not g.black_id:
                    return
                white = db.get(Player, g.white_id)
                black = db.get(Player, g.black_id)
                if not white or not black:
                    return

                b = board_from_fen_or_start(g.fen)
                bot_to_move = (b.turn and white.is_bot) or ((not b.turn) and black.is_bot)
                if not bot_to_move:
                    return

                uci = stockfish.best_move_uci(g.fen, think_ms=150)
                new_fen, san = apply_uci_move(g.fen, uci)
                g.fen = new_fen
                g.pgn += (san + " ")
                meta = end_game_if_needed(db, g)
                maybe_rate(db, g)
                db.commit()

                await hub.broadcast(g.id, {"type": "move", "game_id": g.id, "fen": g.fen, "pgn": g.pgn, "meta": meta, "uci": uci})
                if g.status == "active":
                    # allow chain (rare) but safe
                    await maybe_play_system_move(db, g)

            @router.get("/{game_id}")
            def get_game(game_id: int, db: Session = Depends(get_db)):
                g = db.get(Game, game_id)
                if not g:
                    raise HTTPException(404, "Game not found")
                return {
                    "id": g.id,
                    "ranked": g.ranked,
                    "time_control": g.time_control,
                    "fen": g.fen,
                    "pgn": g.pgn,
                    "white_id": g.white_id,
                    "black_id": g.black_id,
                    "status": g.status,
                    "result": g.result,
                    "end_reason": g.end_reason,
                    "meta": status_flags(g.fen),
                }

            @router.post("/{game_id}/move")
            async def move(game_id: int, req: MoveReq, db: Session = Depends(get_db)):
                g = db.get(Game, game_id)
                if not g or g.status != "active":
                    raise HTTPException(404, "Game not active")

                b = board_from_fen_or_start(g.fen)
                is_white_turn = b.turn
                if is_white_turn and req.player_id != g.white_id:
                    raise HTTPException(403, "Not your turn")
                if (not is_white_turn) and req.player_id != g.black_id:
                    raise HTTPException(403, "Not your turn")

                try:
                    new_fen, san = apply_uci_move(g.fen, req.uci)
                except ValueError as e:
                    raise HTTPException(400, str(e))

                g.fen = new_fen
                g.pgn += (san + " ")
                meta = end_game_if_needed(db, g)
                maybe_rate(db, g)
                db.commit()

                payload = {"type": "move", "game_id": g.id, "fen": g.fen, "pgn": g.pgn, "meta": meta, "uci": req.uci}
                await hub.broadcast(g.id, payload)

                # If system/bot is opponent, let it respond
                if g.status == "active":
                    await maybe_play_system_move(db, g)

                return payload

            @router.post("/{game_id}/chat")
            async def chat(game_id: int, req: ChatReq, db: Session = Depends(get_db)):
                g = db.get(Game, game_id)
                if not g:
                    raise HTTPException(404, "Game not found")
                await hub.broadcast(game_id, {"type": "chat", "player_id": req.player_id, "text": req.text})
                return {"ok": True}

            @router.websocket("/ws/{game_id}")
            async def ws_game(ws: WebSocket, game_id: int):
                await hub.join(game_id, ws)
                try:
                    while True:
                        # client can send pings; we ignore content
                        await ws.receive_text()
                finally:
                    hub.leave(game_id, ws)
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/server/main.py",
        dedent(
            """
            import os
            from pathlib import Path
            import uvicorn
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware

            from .db.models import Base
            from .db.session import engine
            from .api.auth import router as auth_router
            from .api.players import router as players_router
            from .api.matchmaking import router as mm_router
            from .api.games import router as games_router

            # Ensure storage dir exists for sqlite file
            Path("storage").mkdir(parents=True, exist_ok=True)

            # Create tables
            Base.metadata.create_all(bind=engine)

            app = FastAPI(title="Chess Arena API")

            # Dev CORS (tighten in prod)
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            app.include_router(auth_router)
            app.include_router(players_router)
            app.include_router(mm_router)
            app.include_router(games_router)

            @app.get("/")
            def root():
                return {"ok": True, "service": "chess_arena"}

            if __name__ == "__main__":
                uvicorn.run("apps.server.main:app", host="127.0.0.1", port=8000, reload=False)
            """
        ).strip()
        + "\n",
    )

    # -------------------------
    # Bot client (Agamemnon-style)
    # -------------------------
    write_file(
        root,
        "apps/bot_client/api_client.py",
        dedent(
            """
            import os
            import httpx

            class APIClient:
                def __init__(self, base_url: str):
                    self.base_url = base_url.rstrip("/")
                    self.token = None
                    self.player_id = None

                def bot_login(self, api_key: str):
                    r = httpx.post(f"{self.base_url}/auth/bot/login", headers={"X-API-Key": api_key}, timeout=30)
                    r.raise_for_status()
                    data = r.json()
                    self.token = data["token"]
                    self.player_id = data["player_id"]
                    return data

                def queue(self, ranked: bool = True, vs_system: bool = False):
                    r = httpx.post(f"{self.base_url}/matchmaking/queue",
                                   json={"player_id": self.player_id, "ranked": ranked, "vs_system": vs_system},
                                   timeout=30)
                    r.raise_for_status()
                    return r.json()

                def get_game(self, game_id: int):
                    r = httpx.get(f"{self.base_url}/games/{game_id}", timeout=30)
                    r.raise_for_status()
                    return r.json()

                def move(self, game_id: int, uci: str):
                    r = httpx.post(f"{self.base_url}/games/{game_id}/move",
                                   json={"player_id": self.player_id, "uci": uci},
                                   timeout=30)
                    r.raise_for_status()
                    return r.json()
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/bot_client/agamemnon_bot.py",
        dedent(
            """
            import os
            import time
            import chess
            from .api_client import APIClient

            BASE_URL = os.getenv("CHESS_ARENA_URL", "http://127.0.0.1:8000")
            API_KEY = os.getenv("BOT_API_KEY", "")

            def pick_random_legal_move(fen: str) -> str:
                b = chess.Board() if fen in ("", "startpos") else chess.Board(fen)
                moves = list(b.legal_moves)
                if not moves:
                    return ""
                return moves[0].uci()

            def main():
                if not API_KEY:
                    raise SystemExit("Set BOT_API_KEY env var.")
                api = APIClient(BASE_URL)
                info = api.bot_login(API_KEY)
                print("Logged in as bot:", info["name"], "player_id:", info["player_id"])

                # Join free-play queue for demo (or ranked)
                q = api.queue(ranked=False, vs_system=False)
                game_id = q["game_id"]
                print("Queued. game_id:", game_id, "status:", q["status"])
                # If status waiting, you need a second player to join.
                while True:
                    g = api.get_game(game_id)
                    if g["status"] == "active":
                        break
                    time.sleep(1)

                print("Game active. White:", g["white_id"], "Black:", g["black_id"])
                while True:
                    g = api.get_game(game_id)
                    if g["status"] != "active":
                        print("Game ended:", g["result"], g["end_reason"])
                        break
                    turn = g["meta"]["turn"]
                    my_turn = (turn == "white" and api.player_id == g["white_id"]) or (turn == "black" and api.player_id == g["black_id"])
                    if my_turn:
                        uci = pick_random_legal_move(g["fen"])
                        if not uci:
                            time.sleep(0.5)
                            continue
                        api.move(game_id, uci)
                        print("Played:", uci)
                    time.sleep(0.5)

            if __name__ == "__main__":
                main()
            """
        ).strip()
        + "\n",
    )

    # -------------------------
    # Desktop GUI (minimal)
    # -------------------------
    write_file(
        root,
        "apps/desktop_gui/client/api_client.py",
        dedent(
            """
            import httpx

            class APIClient:
                def __init__(self, base_url: str):
                    self.base_url = base_url.rstrip("/")
                    self.token = None
                    self.player_id = None
                    self.name = None

                def register(self, email: str, name: str, password: str, is_bot: bool = False):
                    r = httpx.post(f"{self.base_url}/auth/register",
                                   json={"email": email, "name": name, "password": password, "is_bot": is_bot},
                                   timeout=30)
                    r.raise_for_status()
                    data = r.json()
                    self.token = data["token"]
                    self.player_id = data["player_id"]
                    self.name = data["name"]
                    return data

                def login(self, email: str, password: str):
                    r = httpx.post(f"{self.base_url}/auth/login",
                                   json={"email": email, "password": password},
                                   timeout=30)
                    r.raise_for_status()
                    data = r.json()
                    self.token = data["token"]
                    self.player_id = data["player_id"]
                    self.name = data["name"]
                    return data

                def me(self):
                    r = httpx.get(f"{self.base_url}/players/me",
                                  headers={"Authorization": f"Bearer {self.token}"},
                                  timeout=30)
                    r.raise_for_status()
                    return r.json()

                def queue(self, ranked: bool, vs_system: bool):
                    r = httpx.post(f"{self.base_url}/matchmaking/queue",
                                   json={"player_id": self.player_id, "ranked": ranked, "vs_system": vs_system},
                                   timeout=30)
                    r.raise_for_status()
                    return r.json()

                def get_game(self, game_id: int):
                    r = httpx.get(f"{self.base_url}/games/{game_id}", timeout=30)
                    r.raise_for_status()
                    return r.json()

                def move(self, game_id: int, uci: str):
                    r = httpx.post(f"{self.base_url}/games/{game_id}/move",
                                   json={"player_id": self.player_id, "uci": uci},
                                   timeout=30)
                    r.raise_for_status()
                    return r.json()

                def chat(self, game_id: int, text: str):
                    r = httpx.post(f"{self.base_url}/games/{game_id}/chat",
                                   json={"player_id": self.player_id, "text": text},
                                   timeout=30)
                    r.raise_for_status()
                    return r.json()
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/desktop_gui/client/ws_client.py",
        dedent(
            """
            import json
            import threading
            import websocket  # NOTE: we avoid extra deps by using websockets in python, but PySide threading is easier with websocket-client

            # We won't add websocket-client to requirements by default. Instead we use `websockets` in a thread in game_window.
            # This module remains as a placeholder for future improvements.
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/desktop_gui/ui/widgets/chess_board_widget.py",
        dedent(
            """
            from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton
            from PySide6.QtCore import Signal
            import chess

            PIECE_TO_UNICODE = {
                "P":"♙","N":"♘","B":"♗","R":"♖","Q":"♕","K":"♔",
                "p":"♟","n":"♞","b":"♝","r":"♜","q":"♛","k":"♚",
            }

            class ChessBoardWidget(QWidget):
                squareClicked = Signal(str)  # algebraic like "e2"

                def __init__(self, parent=None):
                    super().__init__(parent)
                    self.grid = QGridLayout(self)
                    self.grid.setSpacing(0)
                    self.buttons = {}
                    for r in range(8):
                        for c in range(8):
                            btn = QPushButton("")
                            btn.setFixedSize(56, 56)
                            sq = chess.square(c, 7 - r)  # map row to rank
                            name = chess.square_name(sq)
                            btn.clicked.connect(lambda _, n=name: self.squareClicked.emit(n))
                            self.buttons[name] = btn
                            # light styling
                            is_light = (r + c) % 2 == 0
                            btn.setStyleSheet(f"font-size: 26px; background: {'#EEE' if is_light else '#888'};")
                            self.grid.addWidget(btn, r, c)

                def set_fen(self, fen: str):
                    board = chess.Board() if fen in ("", "startpos") else chess.Board(fen)
                    for sq_name, btn in self.buttons.items():
                        sq = chess.parse_square(sq_name)
                        piece = board.piece_at(sq)
                        btn.setText(PIECE_TO_UNICODE.get(piece.symbol(), "") if piece else "")

                def highlight_squares(self, squares: set[str]):
                    # optional: implement later
                    pass
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/desktop_gui/ui/widgets/move_list_widget.py",
        dedent(
            """
            from PySide6.QtWidgets import QListWidget

            class MoveListWidget(QListWidget):
                def set_last_moves(self, pgn_text: str, last_n: int = 6):
                    moves = [m for m in pgn_text.strip().split() if m]
                    self.clear()
                    for m in moves[-last_n:]:
                        self.addItem(m)
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/desktop_gui/ui/widgets/chat_widget.py",
        dedent(
            """
            from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QLineEdit, QPushButton
            from PySide6.QtCore import Signal

            class ChatWidget(QWidget):
                sendChat = Signal(str)

                def __init__(self, parent=None):
                    super().__init__(parent)
                    layout = QVBoxLayout(self)

                    self.log = QTextEdit()
                    self.log.setReadOnly(True)
                    layout.addWidget(self.log)

                    row = QHBoxLayout()
                    self.input = QLineEdit()
                    self.btn = QPushButton("Send")
                    self.btn.clicked.connect(self._send)
                    self.input.returnPressed.connect(self._send)
                    row.addWidget(self.input)
                    row.addWidget(self.btn)
                    layout.addLayout(row)

                def _send(self):
                    text = self.input.text().strip()
                    if not text:
                        return
                    self.input.clear()
                    self.sendChat.emit(text)

                def append(self, line: str):
                    self.log.append(line)
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/desktop_gui/ui/login_dialog.py",
        dedent(
            """
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QHBoxLayout

            class LoginDialog(QDialog):
                def __init__(self, api, parent=None):
                    super().__init__(parent)
                    self.api = api
                    self.setWindowTitle("Login")

                    layout = QVBoxLayout(self)
                    layout.addWidget(QLabel("Email"))
                    self.email = QLineEdit()
                    layout.addWidget(self.email)

                    layout.addWidget(QLabel("Password"))
                    self.password = QLineEdit()
                    self.password.setEchoMode(QLineEdit.Password)
                    layout.addWidget(self.password)

                    row = QHBoxLayout()
                    self.btn = QPushButton("Login")
                    self.btn.clicked.connect(self.do_login)
                    row.addWidget(self.btn)
                    layout.addLayout(row)

                def do_login(self):
                    try:
                        self.api.login(self.email.text().strip(), self.password.text())
                        QMessageBox.information(self, "OK", f"Logged in as {self.api.name}")
                        self.accept()
                    except Exception as e:
                        QMessageBox.critical(self, "Error", str(e))
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/desktop_gui/ui/create_account_dialog.py",
        dedent(
            """
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QCheckBox

            class CreateAccountDialog(QDialog):
                def __init__(self, api, parent=None):
                    super().__init__(parent)
                    self.api = api
                    self.setWindowTitle("Create Account")

                    layout = QVBoxLayout(self)

                    layout.addWidget(QLabel("Email"))
                    self.email = QLineEdit()
                    layout.addWidget(self.email)

                    layout.addWidget(QLabel("Name"))
                    self.name = QLineEdit()
                    layout.addWidget(self.name)

                    layout.addWidget(QLabel("Password"))
                    self.password = QLineEdit()
                    self.password.setEchoMode(QLineEdit.Password)
                    layout.addWidget(self.password)

                    self.is_bot = QCheckBox("Create as Bot account (gives API key)")
                    layout.addWidget(self.is_bot)

                    self.btn = QPushButton("Create")
                    self.btn.clicked.connect(self.do_create)
                    layout.addWidget(self.btn)

                def do_create(self):
                    try:
                        data = self.api.register(
                            self.email.text().strip(),
                            self.name.text().strip(),
                            self.password.text(),
                            is_bot=self.is_bot.isChecked()
                        )
                        msg = f"Created account: {data['name']}"
                        if data.get("api_key"):
                            msg += f"\\nBot API Key: {data['api_key']}"
                        QMessageBox.information(self, "OK", msg)
                        self.accept()
                    except Exception as e:
                        QMessageBox.critical(self, "Error", str(e))
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/desktop_gui/ui/lobby.py",
        dedent(
            """
            from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox, QHBoxLayout, QCheckBox

            class Lobby(QWidget):
                def __init__(self, api, on_game_ready, parent=None):
                    super().__init__(parent)
                    self.api = api
                    self.on_game_ready = on_game_ready

                    layout = QVBoxLayout(self)
                    self.info = QLabel("Queue for a match")
                    layout.addWidget(self.info)

                    self.ranked = QCheckBox("Ranked")
                    self.ranked.setChecked(True)
                    layout.addWidget(self.ranked)

                    row = QHBoxLayout()
                    self.btn_pvp = QPushButton("Play Player (Online)")
                    self.btn_sys = QPushButton("Play System (Stockfish)")
                    self.btn_pvp.clicked.connect(self.queue_pvp)
                    self.btn_sys.clicked.connect(self.queue_system)
                    row.addWidget(self.btn_pvp)
                    row.addWidget(self.btn_sys)
                    layout.addLayout(row)

                def queue_pvp(self):
                    try:
                        q = self.api.queue(ranked=self.ranked.isChecked(), vs_system=False)
                        self.on_game_ready(q["game_id"])
                    except Exception as e:
                        QMessageBox.critical(self, "Error", str(e))

                def queue_system(self):
                    try:
                        q = self.api.queue(ranked=self.ranked.isChecked(), vs_system=True)
                        self.on_game_ready(q["game_id"])
                    except Exception as e:
                        QMessageBox.critical(self, "Error", str(e))
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/desktop_gui/ui/game_window.py",
        dedent(
            """
            import asyncio
            import threading
            import websockets
            from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QMessageBox
            from PySide6.QtCore import Qt

            from .widgets.chess_board_widget import ChessBoardWidget
            from .widgets.move_list_widget import MoveListWidget
            from .widgets.chat_widget import ChatWidget

            def ws_url(http_base: str, game_id: int) -> str:
                # http://127.0.0.1:8000 -> ws://127.0.0.1:8000
                base = http_base.replace("http://", "ws://").replace("https://", "wss://")
                return f"{base}/games/ws/{game_id}"

            class GameWindow(QWidget):
                def __init__(self, api, game_id: int, parent=None):
                    super().__init__(parent)
                    self.api = api
                    self.game_id = game_id
                    self.setWindowTitle(f"Game #{game_id}")

                    self.selected = None  # square name like "e2"
                    self.current_fen = "startpos"
                    self.current_pgn = ""

                    root = QHBoxLayout(self)

                    # Left column: last 6 moves (top), board (middle), chat (bottom)
                    left = QVBoxLayout()
                    self.moves_label = QLabel("Last 6 moves")
                    left.addWidget(self.moves_label)

                    self.moves = MoveListWidget()
                    left.addWidget(self.moves)

                    self.board = ChessBoardWidget()
                    self.board.squareClicked.connect(self.on_square_clicked)
                    left.addWidget(self.board)

                    self.chat = ChatWidget()
                    self.chat.sendChat.connect(self.send_chat)
                    left.addWidget(self.chat)

                    root.addLayout(left, 2)

                    # Right column: status
                    right = QVBoxLayout()
                    self.status = QLabel("Loading...")
                    self.status.setAlignment(Qt.AlignTop)
                    right.addWidget(self.status)
                    root.addLayout(right, 1)

                    # initial load
                    self.refresh()

                    # start websocket listener in a thread
                    self._stop = False
                    self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
                    self._ws_thread.start()

                def refresh(self):
                    try:
                        g = self.api.get_game(self.game_id)
                        self.current_fen = g["fen"]
                        self.current_pgn = g["pgn"]
                        self.board.set_fen(self.current_fen)
                        self.moves.set_last_moves(self.current_pgn, last_n=6)

                        meta = g.get("meta", {})
                        msg = []
                        msg.append(f"Status: {g['status']}")
                        msg.append(f"Ranked: {g['ranked']}")
                        msg.append(f"Turn: {meta.get('turn')}")
                        if meta.get("in_check"):
                            msg.append("CHECK!")
                        if g.get("result"):
                            msg.append(f"Result: {g['result']} ({g.get('end_reason')})")
                        self.status.setText("\\n".join(msg))
                    except Exception as e:
                        QMessageBox.critical(self, "Error", str(e))

                def on_square_clicked(self, sq: str):
                    # simple from-to click move (no highlight, no promotion chooser yet)
                    if self.selected is None:
                        self.selected = sq
                        self.chat.append(f"[select] {sq}")
                        return
                    frm = self.selected
                    to = sq
                    self.selected = None
                    uci = f"{frm}{to}"
                    try:
                        self.api.move(self.game_id, uci)
                        # server will push ws updates; but refresh quick too
                        self.refresh()
                    except Exception as e:
                        self.chat.append(f"[illegal] {uci} -> {e}")

                def send_chat(self, text: str):
                    try:
                        self.api.chat(self.game_id, text)
                    except Exception as e:
                        self.chat.append(f"[chat error] {e}")

                def closeEvent(self, event):
                    self._stop = True
                    super().closeEvent(event)

                def _ws_loop(self):
                    async def run():
                        url = ws_url(self.api.base_url, self.game_id)
                        try:
                            async with websockets.connect(url) as ws:
                                # keep alive ping
                                async def ping_loop():
                                    while not self._stop:
                                        try:
                                            await ws.send("ping")
                                        except:
                                            break
                                        await asyncio.sleep(10)

                                ping_task = asyncio.create_task(ping_loop())

                                while not self._stop:
                                    msg = await ws.recv()
                                    # websockets gives JSON as str; FastAPI sends JSON object
                                    # but in this minimal setup, ws.send_json -> ws.recv str; parse with eval-safe
                                    import json
                                    data = json.loads(msg)
                                    if data.get("type") == "chat":
                                        pid = data.get("player_id")
                                        self.chat.append(f"{pid}: {data.get('text')}")
                                    elif data.get("type") == "move":
                                        self.current_fen = data.get("fen", self.current_fen)
                                        self.current_pgn = data.get("pgn", self.current_pgn)
                                        # UI updates must happen on main thread; simplest is to call refresh indirectly
                                        # We use a queued call via singleShot
                                        from PySide6.QtCore import QTimer
                                        QTimer.singleShot(0, self.refresh)

                                ping_task.cancel()
                        except Exception as e:
                            from PySide6.QtCore import QTimer
                            QTimer.singleShot(0, lambda: self.chat.append(f"[ws closed] {e}"))

                    asyncio.run(run())
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/desktop_gui/ui/start_menu.py",
        dedent(
            """
            from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
            from .login_dialog import LoginDialog
            from .create_account_dialog import CreateAccountDialog
            from .lobby import Lobby
            from .game_window import GameWindow

            class StartMenu(QWidget):
                def __init__(self, api, parent=None):
                    super().__init__(parent)
                    self.api = api
                    self.setWindowTitle("Chess Arena - Start")

                    layout = QVBoxLayout(self)
                    self.label = QLabel("Chess Arena")
                    layout.addWidget(self.label)

                    self.btn_login = QPushButton("Login")
                    self.btn_create = QPushButton("Create Account")
                    layout.addWidget(self.btn_login)
                    layout.addWidget(self.btn_create)

                    self.btn_login.clicked.connect(self.login)
                    self.btn_create.clicked.connect(self.create)

                    self.lobby = None
                    self.game = None

                def login(self):
                    dlg = LoginDialog(self.api, self)
                    if dlg.exec():
                        self.show_lobby()

                def create(self):
                    dlg = CreateAccountDialog(self.api, self)
                    if dlg.exec():
                        self.show_lobby()

                def show_lobby(self):
                    try:
                        me = self.api.me()
                        self.label.setText(f"Logged in: {me['name']} | Rating: {me['rating']:.0f} | W/L/D: {me['wins']}/{me['losses']}/{me['draws']}")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", str(e))
                        return

                    if self.lobby:
                        self.lobby.setParent(None)

                    self.lobby = Lobby(self.api, self.open_game, self)
                    self.layout().addWidget(self.lobby)

                def open_game(self, game_id: int):
                    # Open game window; keep start menu open for now.
                    self.game = GameWindow(self.api, game_id, self)
                    self.game.resize(900, 700)
                    self.game.show()
            """
        ).strip()
        + "\n",
    )

    write_file(
        root,
        "apps/desktop_gui/main.py",
        dedent(
            """
            import os
            import sys
            from PySide6.QtWidgets import QApplication
            from .client.api_client import APIClient
            from .ui.start_menu import StartMenu

            def main():
                base_url = os.getenv("CHESS_ARENA_URL", "http://127.0.0.1:8000")
                app = QApplication(sys.argv)
                api = APIClient(base_url)
                w = StartMenu(api)
                w.resize(420, 260)
                w.show()
                sys.exit(app.exec())

            if __name__ == "__main__":
                main()
            """
        ).strip()
        + "\n",
    )

    # Ensure storage directory exists
    (root / "storage").mkdir(parents=True, exist_ok=True)

    print(f"✅ Project created at: {root}")
    print("Next:")
    print(f"  cd {root}")
    print("  python -m venv venv")
    print("  venv\\Scripts\\activate")
    print("  pip install -r requirements.txt")
    print("  (install stockfish and set STOCKFISH_PATH)")
    print("  python apps\\server\\main.py")
    print("  python apps\\desktop_gui\\main.py")


if __name__ == "__main__":
    main()
