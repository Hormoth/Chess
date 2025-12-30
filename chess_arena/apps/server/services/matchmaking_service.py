from collections import deque
import random
import threading

from ..db.models import Game, Player
from ..settings import settings


class MatchmakingService:
    def __init__(self):
        self._lock = threading.Lock()
        self.ranked_q = deque()
        self.free_q = deque()

    def enqueue(self, db, player_id: int, ranked: bool, vs_system: bool) -> dict:
        """
        Returns JSON-safe dict only.
        matched: {"status":"active","game_id":...,"ranked":...,"vs_system":...}
        waiting: {"status":"waiting","ranked":...,"vs_system":...}
        """

        # ---- vs_system: immediate game creation (player vs Stockfish bot account) ----
        if vs_system:
            bot = db.query(Player).filter(Player.is_bot == True).first()
            if not bot:
                # auto-create a system bot
                from passlib.context import CryptContext
                pwd = CryptContext(schemes=["argon2"], deprecated="auto")

                bot = Player(
                    email="system@local",
                    name="Stockfish",
                    password_hash=pwd.hash("system-bot-password"),
                    is_bot=True,
                )
                bot.ensure_api_key()
                db.add(bot)
                db.commit()
                db.refresh(bot)

            white, black = (player_id, bot.id) if random.random() < 0.5 else (bot.id, player_id)
            g = Game(
                ranked=ranked,
                time_control=settings.default_time_control,
                white_id=white,
                black_id=black,
                fen="startpos",
                status="active",
            )
            db.add(g)
            db.commit()
            db.refresh(g)

            return {"game_id": g.id, "status": g.status, "ranked": ranked, "vs_system": True}

        # ---- PvP queue (in-memory) ----
        q = self.ranked_q if ranked else self.free_q

        with self._lock:
            # Prevent same player being queued twice
            if player_id in q:
                return {"status": "waiting", "ranked": ranked, "vs_system": False}

            q.append(player_id)

            if len(q) >= 2:
                p1 = q.popleft()
                p2 = q.popleft()
                white, black = (p1, p2) if random.random() < 0.5 else (p2, p1)

                g = Game(
                    ranked=ranked,
                    time_control=settings.default_time_control,
                    white_id=white,
                    black_id=black,
                    fen="startpos",
                    status="active",
                )
                db.add(g)
                db.commit()
                db.refresh(g)

                return {"game_id": g.id, "status": g.status, "ranked": ranked, "vs_system": False}

        # Not enough players yet
        return {"status": "waiting", "ranked": ranked, "vs_system": False}

    def status(self, db, player_id: int, ranked: bool) -> dict:
        """
        Returns:
          - {"status":"waiting","ranked":ranked} if still queued
          - {"status":"active","game_id":...,"ranked":...} if matched
          - {"status":"idle","ranked":ranked} if not queued and no active game found
        """
        q = self.ranked_q if ranked else self.free_q

        with self._lock:
            if player_id in q:
                return {"status": "waiting", "ranked": ranked}

        # Not queued anymore → see if an active game exists for this player
        g = (
            db.query(Game)
            .filter(
                Game.status == "active",
                ((Game.white_id == player_id) | (Game.black_id == player_id)),
            )
            .order_by(Game.id.desc())
            .first()
        )
        if not g:
            return {"status": "idle", "ranked": ranked}

        return {"status": "active", "game_id": g.id, "ranked": g.ranked}


mm = MatchmakingService()
