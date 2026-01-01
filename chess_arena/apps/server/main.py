import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path as _Path

# -----------------------------------------------------------------------------
# Robust path setup for local "packages/*" imports
# This file is: <ROOT>/chess_arena/apps/server/main.py
# ROOT is 3 parents up from this file's directory.
# -----------------------------------------------------------------------------
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[3]          # ...\Chess
PACKAGES_DIR = PROJECT_ROOT / "packages"

# Put ROOT and PACKAGES on sys.path (front of list)
for p in (str(PROJECT_ROOT), str(PACKAGES_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# -----------------------------------------------------------------------------
# App imports
# -----------------------------------------------------------------------------
from .db.models import Base
from .db.session import engine
from .api.auth import router as auth_router
from .api.players import router as players_router
from .api.matchmaking import router as mm_router
from .api.games import router as games_router
from .api.lobby import router as lobby_router


# Ensure storage dir exists for sqlite file
_Path("storage").mkdir(parents=True, exist_ok=True)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chess Arena API")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Standardize error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

# Dev CORS (tighten in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(players_router)
app.include_router(mm_router)
app.include_router(games_router)
app.include_router(lobby_router)

@app.get("/")
def root():
    return {"ok": True, "service": "chess_arena"}


if __name__ == "__main__":
    # Prefer CLI for reload:
    # python -m uvicorn chess_arena.apps.server.main:app --reload --host 127.0.0.1 --port 8000
    uvicorn.run(
        "chess_arena.apps.server.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )