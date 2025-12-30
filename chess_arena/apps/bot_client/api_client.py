import httpx


class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None
        self.player_id: int | None = None
        self.name: str | None = None

    # ------------- helpers -------------

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

    # ------------- auth -------------

    def bot_login(self, api_key: str):
        # Server expects Header(...): x-api-key (case-insensitive)
        r = httpx.post(
            f"{self.base_url}/auth/bot/login",
            headers={"X-API-Key": api_key},
            timeout=30,
        )
        self._raise(r)

        data = r.json()
        self.token = data.get("token")
        self.player_id = data.get("player_id")
        self.name = data.get("name")
        return data

    # ------------- matchmaking / games -------------

    def queue(self, ranked: bool = True, vs_system: bool = False):
        # Token identity is source of truth now; DO NOT send player_id
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
        # Token identity is source of truth now; DO NOT send player_id
        r = httpx.post(
            f"{self.base_url}/games/{game_id}/move",
            json={"uci": uci},
            headers=self._auth_headers(),
            timeout=30,
        )
        self._raise(r)
        return r.json()

    def chat(self, game_id: int, text: str):
        # Token identity is source of truth now; DO NOT send player_id
        r = httpx.post(
            f"{self.base_url}/games/{game_id}/chat",
            json={"text": text},
            headers=self._auth_headers(),
            timeout=30,
        )
        self._raise(r)
        return r.json()
