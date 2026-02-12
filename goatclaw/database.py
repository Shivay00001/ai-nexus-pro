import asyncio
from datetime import datetime
from typing import Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, JSON, DateTime, Text, select
import os

# Define Base
class Base(DeclarativeBase):
    pass

# Memory Record Model (Relational persistence for MemoryAgent)
class MemoryRecordModel(Base):
    __tablename__ = "memory_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String)  # 'fact', 'pattern', 'interaction'
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    embedding_id: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Reference to vector DB
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default={})
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "embedding_id": self.embedding_id,
            "metadata": self.metadata_
        }

class TaskGraphModel(Base):
    __tablename__ = "task_graphs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String)
    state_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Phase 6 & 7: Security & Monetization Models
class SecretModel(Base):
    """Encrypted user API keys."""
    __tablename__ = "secrets"
    
    id: Mapped[str] = mapped_column(String, primary_key=True) # UUID
    user_id: Mapped[str] = mapped_column(String, index=True)
    provider: Mapped[str] = mapped_column(String) # 'openai', 'anthropic', etc.
    encrypted_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class UserAccountModel(Base):
    """User credits and platform subscription tier."""
    __tablename__ = "user_accounts"
    
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    balance_credits: Mapped[float] = mapped_column(default=0.0)
    tier: Mapped[str] = mapped_column(String, default="free") # 'free', 'pro', 'enterprise'
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DatabaseManager:
    """
    Async Database Manager using SQLAlchemy.
    For production, set DATABASE_URL env var.
    Defaults to SQLite for local dev/testing if not set.
    """
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", 
            f"sqlite+aiosqlite:///{os.path.abspath('memory.db')}"
        )
        self.engine = create_async_engine(self.database_url, echo=False)
        self.session_factory = async_sessionmaker(
            bind=self.engine, 
            expire_on_commit=False, 
            class_=AsyncSession
        )

    async def init_db(self):
        """Initialize database schema."""
        async with self.engine.begin() as conn:
             # In production, use Alembic for migrations.
             # This is for initial setup/dev.
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncSession:
        return self.session_factory()

    async def close(self):
        await self.engine.dispose()

# Global DB Manager Instance
db_manager = DatabaseManager()
