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
