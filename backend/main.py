import os
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct, func

from .database import get_db, engine, Base
from .models import PatientAdmission
from .schemas import TimingResponse, StatsResponse, HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup: Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")
    yield
    # Shutdown: Dispose engine
    await engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title="Hospital Performance Test API",
    description="Railway deployment performance testing with PostgreSQL",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration - Whitelist external access
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:3000,http://127.0.0.1:8080").split(",")

# Add wildcard for Railway deployment (adjust as needed)
ALLOWED_ORIGINS.extend([
    "*"  # Allow all origins for testing - restrict in production
])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Backend-Time-Ms", "X-DB-Time-Ms"]
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "healthy", "service": "hospital-api"}


@app.get("/api/floors", response_model=TimingResponse)
async def get_unique_floors(db: AsyncSession = Depends(get_db)):
    """
    Get unique floor values from active patient admissions.
    Returns timing information for performance analysis.
    """
    request_start = time.perf_counter()

    # Database query with timing
    db_start = time.perf_counter()

    query = select(distinct(PatientAdmission.floor)).where(
        PatientAdmission.is_active == True
    ).order_by(PatientAdmission.floor)

    result = await db.execute(query)
    floors = [row[0] for row in result.fetchall()]

    db_time_ms = (time.perf_counter() - db_start) * 1000

    # Log timing
    logger.info(f"[TIMING] DB Query: {db_time_ms:.2f}ms | Floors: {len(floors)}")

    total_time_ms = (time.perf_counter() - request_start) * 1000
    logger.info(f"[TIMING] Backend Total: {total_time_ms:.2f}ms")

    return TimingResponse(
        data=floors,
        count=len(floors),
        db_time_ms=round(db_time_ms, 2),
        total_time_ms=round(total_time_ms, 2)
    )


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get basic statistics about patient admissions."""
    request_start = time.perf_counter()

    # Total patients
    total_query = select(func.count(PatientAdmission.id))
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # Active patients
    active_query = select(func.count(PatientAdmission.id)).where(
        PatientAdmission.is_active == True
    )
    active_result = await db.execute(active_query)
    active = active_result.scalar() or 0

    elapsed = (time.perf_counter() - request_start) * 1000
    logger.info(f"[TIMING] Stats query: {elapsed:.2f}ms")

    return StatsResponse(
        total_patients=total,
        active_patients=active,
        status="active"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint for Railway."""
    try:
        await db.execute(select(1))
        return HealthResponse(status="healthy", database="connected")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")
