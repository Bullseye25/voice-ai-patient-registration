"""
Database Engine & Session Lifecycle Configuration
Supports persistent SQLite with WAL (Write-Ahead Logging) mode.
"""
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Engine setup
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

is_sqlite = db_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_kwargs = {"connect_args": connect_args, "echo": False}
if not is_sqlite:
    engine_kwargs.update({"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20})

engine = create_engine(db_url, **engine_kwargs)

# Enable WAL mode and foreign keys for SQLite
if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    """FastAPI dependency to yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes tables in database."""
    Base.metadata.create_all(bind=engine)
