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

# CORS Configuration - Allow all external access for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using wildcard origin
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
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


@app.post("/api/seed")
async def seed_database(count: int = 1000, db: AsyncSession = Depends(get_db)):
    """Seed database with test patient data."""
    import random
    from datetime import timedelta
    from faker import Faker
    from .models import Gender, InsuranceType, CareLevel

    fake = Faker('ko_KR')

    # Check existing count
    result = await db.execute(select(func.count(PatientAdmission.id)))
    existing = result.scalar() or 0

    if existing >= count:
        return {"message": f"Database already has {existing} records", "total": existing}

    records_to_add = count - existing
    logger.info(f"Seeding {records_to_add} records...")

    DIAGNOSES = ["뇌졸중 후유증", "치매", "파킨슨병", "골절 후 재활", "당뇨합병증",
                 "만성폐쇄성폐질환", "심부전", "척추질환", "관절염", "욕창"]
    ADMISSION_ROUTES = ["외래", "응급", "타병원전원", "요양시설전원", "가정"]
    DOCTOR_NAMES = ["김영수", "이정희", "박민수", "최수진", "정대현"]
    RELATIONSHIPS = ["자녀", "배우자", "손자녀", "형제자매", "기타"]

    for i in range(records_to_add):
        gender = random.choice([Gender.MALE, Gender.FEMALE])
        birth_date = fake.date_of_birth(minimum_age=60, maximum_age=95)
        admission_date = fake.date_between(start_date='-2y', end_date='today')
        floor = random.choices([1, 2, 3, 4, 5], weights=[30, 25, 20, 15, 10])[0]

        birth_year = birth_date.year % 100
        resident_front = f"{birth_year:02d}{birth_date.month:02d}{birth_date.day:02d}"

        patient = PatientAdmission(
            patient_id=f"P{2024000000 + existing + i:010d}",
            resident_number=f"{resident_front}-*******",
            patient_name=fake.name(),
            gender=gender.value,
            birth_date=birth_date,
            contact_phone=fake.phone_number(),
            guardian_name=fake.name(),
            guardian_phone=fake.phone_number(),
            guardian_relationship=random.choice(RELATIONSHIPS),
            floor=floor,
            room_number=f"{floor}{random.randint(1, 20):02d}",
            bed_number=str(random.randint(1, 4)),
            admission_date=admission_date,
            expected_discharge_date=admission_date + timedelta(days=random.randint(30, 365)),
            admission_route=random.choice(ADMISSION_ROUTES),
            primary_diagnosis=random.choice(DIAGNOSES),
            secondary_diagnosis=random.choice(DIAGNOSES + [None]),
            attending_doctor=random.choice(DOCTOR_NAMES),
            nursing_unit=f"{floor}층 간호단위",
            insurance_type=random.choice(list(InsuranceType)).value,
            care_level=random.choice(list(CareLevel)).value,
            is_active=random.random() > 0.2
        )
        db.add(patient)

        if (i + 1) % 100 == 0:
            await db.commit()
            logger.info(f"Inserted {existing + i + 1} records...")

    await db.commit()

    result = await db.execute(select(func.count(PatientAdmission.id)))
    final_count = result.scalar() or 0

    return {"message": "Seeding complete", "total": final_count, "added": records_to_add}
