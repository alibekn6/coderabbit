from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import logging

from src.core.config import Config

logger = logging.getLogger(__name__)

config = Config()

engine = create_async_engine(
    config.db_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=20,
    max_overflow=0,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_session() -> AsyncSession:
    return AsyncSessionLocal()

async def check_db_connection():
    """Check if database connection is working."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

async def close_db():
    await engine.dispose()
    logger.info("Database connections closed")
