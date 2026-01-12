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

    def _get_or_create_stockfish_bot(self, db) -> Player:
        """Get or create the Stockfish system bot."""
        bot = db.query(Player).filter(
            Player.is_bot == True,
            Player.email == "system@local"
        ).first()

        if not bot:
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

        return bot

    def _try_match_with_waiting_player(self, db, player_id: int, ranked: bool, requesting_is_bot: bool = False) -> Game | None:
        """
        Try to match with a waiting player.

        PRIORITY:
        1. If requesting player is human -> try to match with human first, then bot
        2. If requesting player is bot -> try to match with human first, then bot

        This ensures humans play humans when possible.
        Returns a Game if matched, None otherwise.
        Must be called while holding self._lock.
        """
        q = self.ranked_q if ranked else self.free_q

        # Separate waiting players into humans and bots
        waiting_humans = []
        waiting_bots = []

        for waiting_pid in list(q):
            if waiting_pid == player_id:
                continue
            p = db.query(Player).filter(Player.id == waiting_pid).first()
            if p:
                if p.is_bot:
                    waiting_bots.append(waiting_pid)
                else:
                    waiting_humans.append(waiting_pid)

        # Priority: humans first, then bots
        match_order = waiting_humans + waiting_bots

        for waiting_pid in match_order:
            # Found a match! Remove them from queue
            q.remove(waiting_pid)

            # Also remove ourselves if we were queued
            if player_id in q:
                q.remove(player_id)

            # Randomly assign colors
            white, black = (player_id, waiting_pid) if random.random() < 0.5 else (waiting_pid, player_id)

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

            return g

        return None

    def enqueue(self, db, player_id: int, ranked: bool, vs_system: bool) -> dict:
        """
        Enqueue a player for matchmaking.

        PRIORITY ORDER:
        1. First, try to match with a human player
        2. If no humans, try to match with a bot player
        3. Only if no players are waiting AND vs_system=True, create game vs Stockfish
        4. Otherwise, add to queue and wait

        Returns consistent JSON structure:
        {
            "status": "active" | "waiting",
            "game_id": int | None,
            "ranked": bool,
            "vs_system": bool
        }
        """
        # Check if requesting player is a bot
        requesting_player = db.query(Player).filter(Player.id == player_id).first()
        requesting_is_bot = requesting_player.is_bot if requesting_player else False

        with self._lock:
            # ---- PRIORITY 1: Try to match with waiting player (humans first) ----
            game = self._try_match_with_waiting_player(db, player_id, ranked, requesting_is_bot)
            if game:
                return {
                    "status": "active",
                    "game_id": game.id,
                    "ranked": ranked,
                    "vs_system": False
                }

            # ---- PRIORITY 2: If vs_system requested and no players waiting, play Stockfish ----
            if vs_system:
                bot = self._get_or_create_stockfish_bot(db)

                # Make sure we're not matching stockfish with itself
                if player_id != bot.id:
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

            # ---- PRIORITY 3: Add to queue and wait for another player ----
            q = self.ranked_q if ranked else self.free_q

            # Prevent duplicate queueing
            if player_id not in q:
                q.append(player_id)

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
