from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from src.api.core.config import get_settings

Base = declarative_base()

_settings = get_settings()

# Use SQLAlchemy 2.0 style engine.
engine = create_engine(_settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session and ensures proper cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
