"""
SQLite database setup and session management.
"""
import os
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.db.models import Base


def get_database_url() -> str:
    """Get SQLite database URL."""
    db_path = Path(settings.sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


# Create engine
engine = create_engine(
    get_database_url(),
    connect_args={"check_same_thread": False},  # SQLite specific
    echo=settings.debug,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


_initialized = False


def init_db():
    """Initialize database tables (idempotent)."""
    global _initialized
    Base.metadata.create_all(bind=engine)
    _initialized = True


def get_db() -> Session:
    """Get database session (for FastAPI dependency)."""
    if not _initialized:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Session:
    """Get database session as context manager."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
