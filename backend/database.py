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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/railway")

# Convert postgres:// to postgresql+asyncpg:// if needed (Railway uses postgres://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# Async engine with connection pool
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False
)

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
