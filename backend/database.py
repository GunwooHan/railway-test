import os
import time
import logging
from functools import wraps

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Railway provides DATABASE_URL automatically
# For local testing without PostgreSQL, use SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    # Default to SQLite for local development
    DATABASE_URL = "sqlite+aiosqlite:///./hospital.db"
    logger.info("Using SQLite for local development")
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

logger.info(f"Database URL scheme: {DATABASE_URL.split('://')[0]}")

# Async engine with connection pool
# SQLite doesn't support pool_size/max_overflow
is_sqlite = DATABASE_URL.startswith("sqlite")
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": False
}
if not is_sqlite:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

# Async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    """Dependency injection for FastAPI."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


def log_db_timing(func):
    """Decorator to log database operation timing."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"DB Operation [{func.__name__}]: {elapsed:.2f}ms")
        return result
    return wrapper
