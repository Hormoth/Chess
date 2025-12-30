from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
import secrets

class Base(DeclarativeBase):
    pass

class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    api_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    # Glicko-2 fields
    rating: Mapped[float] = mapped_column(Float, default=1500.0)
    rd: Mapped[float] = mapped_column(Float, default=350.0)
    vol: Mapped[float] = mapped_column(Float, default=0.06)

    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def ensure_api_key(self):
        if not self.api_key:
            self.api_key = secrets.token_hex(32)

class Game(Base):
    __tablename__ = "games"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ranked: Mapped[bool] = mapped_column(Boolean, default=False)
    time_control: Mapped[str] = mapped_column(String(20), default="10+0")
    white_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    black_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    fen: Mapped[str] = mapped_column(Text, default="startpos")
    pgn: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="waiting")  # waiting/active/ended
    result: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 1-0, 0-1, 1/2-1/2
    end_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
