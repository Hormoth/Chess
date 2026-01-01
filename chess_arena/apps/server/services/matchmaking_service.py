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

    def get_waiting_players(self, db, ranked: bool = None) -> list[dict]:
        """Get list of players waiting in queue."""
        players = []
        
        with self._lock:
            if ranked is None or ranked is True:
                for pid in self.ranked_q:
                    p = db.query(Player).filter(Player.id == pid).first()
                    if p:
                        players.append({
                            "player_id": p.id,
                            "name": p.name,
                            "rating": p.rating,
                            "ranked": True,
                            "is_bot": p.is_bot
                        })
            
            if ranked is None or ranked is False:
                for pid in self.free_q:
                    p = db.query(Player).filter(Player.id == pid).first()
                    if p:
                        players.append({
                            "player_id": p.id,
                            "name": p.name,
                            "rating": p.rating,
                            "ranked": False,
                            "is_bot": p.is_bot
                        })
        
        return players

    def cancel(self, player_id: int) -> bool:
        """Remove a player from all queues."""
        with self._lock:
            was_queued = False
            if player_id in self.ranked_q:
                self.ranked_q.remove(player_id)
                was_queued = True
            if player_id in self.free_q:
                self.free_q.remove(player_id)
                was_queued = True
            return was_queued

    def enqueue(self, db, player_id: int, ranked: bool, vs_system: bool) -> dict:
        """
        Enqueue a player for matchmaking.
        
        Returns consistent JSON structure:
        {
            "status": "active" | "waiting",
            "game_id": int | None,
            "ranked": bool,
            "vs_system": bool
        }
        """
        # ---- vs_system: immediate game creation ----
        if vs_system:
            bot = db.query(Player).filter(Player.is_bot == True).first()
            if not bot:
                # Auto-create system bot
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

            return {
                "status": "active",
                "game_id": g.id,
                "ranked": ranked,
                "vs_system": True
            }

        # ---- PvP queue ----
        q = self.ranked_q if ranked else self.free_q

        with self._lock:
            # Prevent duplicate queueing
            if player_id in q:
                return {
                    "status": "waiting",
                    "game_id": None,
                    "ranked": ranked,
                    "vs_system": False
                }

            q.append(player_id)

            # Match if 2+ players
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

                return {
                    "status": "active",
                    "game_id": g.id,
                    "ranked": ranked,
                    "vs_system": False
                }

        # Still waiting
        return {
            "status": "waiting",
            "game_id": None,
            "ranked": ranked,
            "vs_system": False
        }

    def status(self, db, player_id: int, ranked: bool) -> dict:
        """
        Check matchmaking status for a player.
        
        Returns:
        {
            "status": "waiting" | "active" | "idle",
            "game_id": int | None,
            "ranked": bool
        }
        """
        q = self.ranked_q if ranked else self.free_q

        with self._lock:
            if player_id in q:
                return {
                    "status": "waiting",
                    "game_id": None,
                    "ranked": ranked
                }

        # Check for active game
        g = (
            db.query(Game)
            .filter(
                Game.status == "active",
                ((Game.white_id == player_id) | (Game.black_id == player_id)),
            )
            .order_by(Game.id.desc())
            .first()
        )
        
        if g:
            return {
                "status": "active",
                "game_id": g.id,
                "ranked": g.ranked
            }

        return {
            "status": "idle",
            "game_id": None,
            "ranked": ranked
        }


mm = MatchmakingService()
