"""
Synchronous database connection for cache operations.
Used by Celery tasks and cache repository.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from src.core.config import settings

# Create sync engine for cache operations
sync_engine = create_engine(
    settings.db_url.replace('postgresql+asyncpg://', 'postgresql://'),  # Use psycopg2
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

# Session factory
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


def get_sync_db() -> Generator[Session, None, None]:
    """
    Get synchronous database session for cache operations.
    Used by API endpoints and Celery tasks.
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_sync_session() -> Session:
    """
    Get synchronous database session (non-generator version).
    Used by Celery tasks.
    """
    return SyncSessionLocal()
