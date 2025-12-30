from pydantic import BaseModel
import os

class Settings(BaseModel):
    jwt_secret: str = os.getenv("JWT_SECRET", "CHANGE_ME_DEV_SECRET")
    jwt_alg: str = "HS256"
    jwt_exp_minutes: int = 60 * 24
    db_url: str = os.getenv("DATABASE_URL", "sqlite:///storage/dev.db")
    stockfish_path: str = os.getenv("STOCKFISH_PATH", "stockfish")  # set env to .exe on Windows
    default_time_control: str = os.getenv("DEFAULT_TIME_CONTROL", "10+0")

settings = Settings()
