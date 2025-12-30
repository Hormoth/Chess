import os
import time
import chess
from .api_client import APIClient

BASE_URL = os.getenv("CHESS_ARENA_URL", "http://127.0.0.1:8001")
API_KEY = os.getenv("BOT_API_KEY", "")

# ---- BOT MODE ----
# "pvp"        -> bot plays other players
# "system"     -> bot plays Stockfish
BOT_MODE = os.getenv("BOT_MODE", "pvp").lower()
RANKED = os.getenv("BOT_RANKED", "false").lower() == "true"


def pick_random_legal_move(fen: str) -> str:
    b = chess.Board() if (not fen or fen == "startpos") else chess.Board(fen)
    moves = list(b.legal_moves)
    if not moves:
        return ""
    return moves[0].uci()


def main():
    if not API_KEY:
        raise SystemExit("Set BOT_API_KEY env var.")

    api = APIClient(BASE_URL)
    info = api.bot_login(API_KEY)

    print(f"Logged in as bot: {info['name']} (id={info['player_id']})")
    print(f"Mode: {BOT_MODE} | Ranked: {RANKED}")

    vs_system = BOT_MODE == "system"

    # ---- Queue ----
    q = api.queue(ranked=RANKED, vs_system=vs_system)
    print("Queue response:", q)

    game_id = q.get("game_id")

    # If waiting (PvP), poll until matched
    while not game_id:
        time.sleep(1)
        q = api.queue(ranked=RANKED, vs_system=vs_system)
        print("Queue update:", q)
        game_id = q.get("game_id")

    print("Matched into game:", game_id)

    # ---- Wait for game start ----
    while True:
        g = api.get_game(game_id)
        if g.get("status") == "active":
            break
        time.sleep(0.5)

    print("Game active:",
          "White:", g.get("white_id"),
          "Black:", g.get("black_id"))

    # ---- Main loop ----
    while True:
        g = api.get_game(game_id)

        if g.get("status") != "active":
            print("Game ended:", g.get("result"), g.get("end_reason"))
            break

        turn = g.get("meta", {}).get("turn")
        my_id = api.player_id

        my_turn = (
            (turn == "white" and my_id == g.get("white_id")) or
            (turn == "black" and my_id == g.get("black_id"))
        )

        if my_turn:
            uci = pick_random_legal_move(g.get("fen", "startpos"))
            if uci:
                api.move(game_id, uci)
                print("Played:", uci)

        time.sleep(0.5)


if __name__ == "__main__":
    main()
