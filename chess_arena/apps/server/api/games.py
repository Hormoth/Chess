from fastapi import APIRouter, Depends, HTTPException, WebSocket, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import Game, Player
from ..realtime.ws_hub import hub
from ..services.rating_glicko2 import update_after_game
from ..services.stockfish_service import stockfish
from ..api.players import get_player_from_auth

from chess_arena.packages.chesslib.rules import apply_uci_move, status_flags, board_from_fen_or_start



router = APIRouter(prefix="/games", tags=["games"])


# --------- Request Models (NO player_id; token is identity) ---------

class MoveReq(BaseModel):
    uci: str


class ChatReq(BaseModel):
    text: str


# --------- Helpers ---------

def end_game_if_needed(db: Session, g: Game) -> dict:
    meta = status_flags(g.fen)

    if meta["is_checkmate"]:
        b = board_from_fen_or_start(g.fen)
        g.status = "ended"
        # side to move is checkmated => other side won
        g.result = "0-1" if b.turn else "1-0"
        g.end_reason = "checkmate"

    elif meta["is_stalemate"]:
        g.status = "ended"
        g.result = "1/2-1/2"
        g.end_reason = "stalemate"

    elif meta["insufficient"]:
        g.status = "ended"
        g.result = "1/2-1/2"
        g.end_reason = "insufficient_material"

    return meta


def maybe_rate(db: Session, g: Game):
    if g.ranked and g.status == "ended" and g.white_id and g.black_id and g.result:
        w = db.get(Player, g.white_id)
        b = db.get(Player, g.black_id)
        if w and b:
            update_after_game(w, b, g.result)


def _random_legal_move_uci(fen: str) -> str:
    import random
    b = board_from_fen_or_start(fen)
    moves = list(b.legal_moves)
    if not moves:
        return ""
    return random.choice(moves).uci()


async def maybe_play_system_move(db: Session, g: Game):
    """
    If it's a bot's turn, play a move.
    Stockfish is preferred; if unavailable, fallback to a random legal move.
    This function may chain if the engine/bot gets multiple turns (rare).
    """
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

    # Try Stockfish; fallback to random move so vs_system never freezes
    try:
        uci = stockfish.best_move_uci(g.fen, think_ms=150)
    except Exception:
        uci = _random_legal_move_uci(g.fen)

    if not uci:
        return

    try:
        new_fen, san = apply_uci_move(g.fen, uci)
    except ValueError:
        # If engine gave an illegal move (rare), fallback random once
        uci = _random_legal_move_uci(g.fen)
        if not uci:
            return
        new_fen, san = apply_uci_move(g.fen, uci)

    g.fen = new_fen
    g.pgn += (san + " ")
    meta = end_game_if_needed(db, g)
    maybe_rate(db, g)
    db.commit()

    await hub.broadcast(
        g.id,
        {"type": "move", "game_id": g.id, "fen": g.fen, "pgn": g.pgn, "meta": meta, "uci": uci},
    )

    # Chain (rare) — safe and non-recursive explosion due to board.turn flipping normally
    if g.status == "active":
        await maybe_play_system_move(db, g)


# --------- Routes ---------

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
async def move(
    game_id: int,
    req: MoveReq,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    p = get_player_from_auth(db, authorization)

    g = db.get(Game, game_id)
    if not g or g.status != "active":
        raise HTTPException(404, "Game not active")

    b = board_from_fen_or_start(g.fen)
    is_white_turn = b.turn

    # Token identity + turn is the truth
    if is_white_turn and p.id != g.white_id:
        raise HTTPException(403, "Not your turn")
    if (not is_white_turn) and p.id != g.black_id:
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

    # If opponent is system/bot, respond
    if g.status == "active":
        await maybe_play_system_move(db, g)

    return payload


@router.post("/{game_id}/chat")
async def chat(
    game_id: int,
    req: ChatReq,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    p = get_player_from_auth(db, authorization)

    g = db.get(Game, game_id)
    if not g:
        raise HTTPException(404, "Game not found")

    await hub.broadcast(game_id, {"type": "chat", "player_id": p.id, "text": req.text})
    return {"ok": True}


@router.websocket("/ws/{game_id}")
async def ws_game(ws: WebSocket, game_id: int):
    await hub.join(game_id, ws)
    try:
        while True:
            # client can send pings; we ignore content
            await ws.receive_text()
    finally:
        await hub.leave(game_id, ws)

