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
venv\Scripts\activate
pip install -r requirements.txt
```

## Stockfish
Install Stockfish on your machine and set:
```bat
setx STOCKFISH_PATH "C:\path\to\stockfish.exe"
```
Or edit `apps/server/settings.py`.

## Run backend
```bat
venv\Scripts\activate
python apps\server\main.py
```

Backend runs at http://127.0.0.1:8000

## Run GUI
```bat
venv\Scripts\activate
python apps\desktop_gui\main.py
```

## Run Bot Client (example)
1) Create a bot account in GUI or via API `/auth/register` with `is_bot=true`.
2) Copy the returned `api_key` from `/players/me` or DB.
3) Run:
```bat
venv\Scripts\activate
set BOT_API_KEY=...your key...
python apps\bot_client\agamemnon_bot.py
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
