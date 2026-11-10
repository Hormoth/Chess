from pydantic import BaseModel
import os
import warnings

class Settings(BaseModel):
    jwt_secret: str = os.getenv("JWT_SECRET", "CHANGE_ME_DEV_SECRET")
    jwt_alg: str = "HS256"
    jwt_exp_minutes: int = 60 * 24
    db_url: str = os.getenv("DATABASE_URL", "sqlite:///storage/dev.db")
    stockfish_path: str = os.getenv("STOCKFISH_PATH", "stockfish")  # set env to .exe on Windows
    default_time_control: str = os.getenv("DEFAULT_TIME_CONTROL", "10+0")
    # CORS: comma-separated list of allowed origins, or "*" for all (dev only)
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from environment variable."""
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

# Security warnings at module load
if settings.jwt_secret == "CHANGE_ME_DEV_SECRET":
    warnings.warn(
        "JWT_SECRET is using the default development value. "
        "Set the JWT_SECRET environment variable in production!",
        UserWarning,
        stacklevel=1,
    )

if settings.cors_origins == "*":
    warnings.warn(
        "CORS_ORIGINS is set to '*' (allow all). "
        "Set CORS_ORIGINS to specific origins in production!",
        UserWarning,
        stacklevel=1,
    )
