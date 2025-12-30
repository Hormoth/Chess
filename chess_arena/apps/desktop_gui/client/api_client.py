import os
import httpx


class APIClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (
            base_url
            or os.environ.get("CHESS_ARENA_URL")
            or "http://127.0.0.1:8001"
        ).rstrip("/")

        self.token: str | None = None
        self.player_id: int | None = None
        self.name: str | None = None

    # ----------------- helpers -----------------

    def _auth_headers(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _raise(self, r: httpx.Response):
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise httpx.HTTPStatusError(
                f"{e} | response={r.text}",
                request=e.request,
                response=e.response,
            )

    def logout(self):
        self.token = None
        self.player_id = None
        self.name = None

    # ----------------- auth -----------------

    def register(self, email: str, name: str, password: str, is_bot: bool = False):
        r = httpx.post(
            f"{self.base_url}/auth/register",
            json={
                "email": email,
                "name": name,
                "password": password,
                "is_bot": is_bot,
            },
            timeout=30,
        )
        self._raise(r)

        data = r.json()
        self.token = data.get("token")
        self.player_id = data.get("player_id")
        self.name = data.get("name")
        return data

    def login(self, email: str, password: str):
        r = httpx.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
        self._raise(r)

        data = r.json()
        self.token = data.get("token")
        self.player_id = data.get("player_id")
        self.name = data.get("name")
        return data

    # ----------------- player -----------------

    def me(self):
        r = httpx.get(
            f"{self.base_url}/players/me",
            headers=self._auth_headers(),
            timeout=30,
        )
        self._raise(r)

        data = r.json()

        # Keep local cache in sync for UI usage
        self.player_id = data.get("id", self.player_id)
        self.name = data.get("name", self.name)

        return data


    # ----------------- matchmaking / games -----------------

    def queue(self, ranked: bool, vs_system: bool):
        r = httpx.post(
            f"{self.base_url}/matchmaking/queue",
            json={"ranked": ranked, "vs_system": vs_system},
            headers=self._auth_headers(),
            timeout=30,
        )
        self._raise(r)
        return r.json()

    def get_game(self, game_id: int):
        r = httpx.get(
            f"{self.base_url}/games/{game_id}",
            headers=self._auth_headers(),
            timeout=30,
        )
        self._raise(r)
        return r.json()

    def move(self, game_id: int, uci: str):
        r = httpx.post(
            f"{self.base_url}/games/{game_id}/move",
            json={"uci": uci},
            headers=self._auth_headers(),
            timeout=30,
        )
        self._raise(r)
        return r.json()

    def chat(self, game_id: int, text: str):
        r = httpx.post(
            f"{self.base_url}/games/{game_id}/chat",
            json={"text": text},
            headers=self._auth_headers(),
            timeout=30,
        )
        self._raise(r)
        return r.json()
