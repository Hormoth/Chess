from collections import defaultdict
from fastapi import WebSocket

class Hub:
    def __init__(self):
        self.rooms = defaultdict(set)  # game_id -> set[WebSocket]

    async def join(self, game_id: int, ws: WebSocket):
        await ws.accept()
        self.rooms[game_id].add(ws)

    async def leave(self, game_id: int, ws: WebSocket):
        self.rooms[game_id].discard(ws)
        try:
            await ws.close()
        except Exception:
            pass

        # Optional: cleanup empty rooms
        if not self.rooms[game_id]:
            self.rooms.pop(game_id, None)

    async def broadcast(self, game_id: int, payload: dict):
        dead = []
        for ws in list(self.rooms.get(game_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.leave(game_id, ws)

hub = Hub()
