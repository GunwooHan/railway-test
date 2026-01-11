"""
Database seeder for hospital patient admission test data.
Generates 1000 realistic Korean nursing hospital patient records.
"""
import asyncio
import random
import sys
import os
from datetime import date, timedelta

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker
from sqlalchemy import select, func

from backend.database import async_session, engine, Base
from backend.models import PatientAdmission, Gender, InsuranceType, CareLevel

fake = Faker('ko_KR')

# Korean nursing hospital specific data
DIAGNOSES = [
    "뇌졸중 후유증",
    "치매",
    "파킨슨병",
    "골절 후 재활",
    "당뇨합병증",
    "만성폐쇄성폐질환",
    "심부전",
    "척추질환",
    "관절염",
    "욕창",
    "고혈압성 심장질환",
    "만성신부전",
    "폐렴",
    "위장관 질환",
    "뇌경색"
]

ADMISSION_ROUTES = ["외래", "응급", "타병원전원", "요양시설전원", "가정"]

DOCTOR_NAMES = [
    "김영수", "이정희", "박민수", "최수진", "정대현",
    "강미영", "조현우", "윤서연", "임재훈", "한지민",
    "송민호", "장서영", "권태우", "오세진", "신동욱"
]

RELATIONSHIPS = ["자녀", "배우자", "손자녀", "형제자매", "조카", "며느리", "사위", "기타"]


async def seed_database(count: int = 1000):
    """Generate test patient admission records."""
    print(f"Starting database seeding with {count} records...")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created/verified")

    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(func.count(PatientAdmission.id)))
        existing = result.scalar() or 0

        if existing >= count:
            print(f"Database already has {existing} records. Skipping seed.")
            return existing

        records_to_add = count - existing
        print(f"Adding {records_to_add} patient records...")

        patients = []
        for i in range(records_to_add):
            # Generate patient data
            gender = random.choice([Gender.MALE, Gender.FEMALE])
            birth_date = fake.date_of_birth(minimum_age=60, maximum_age=95)
            admission_date = fake.date_between(start_date='-2y', end_date='today')

            # Floor distribution: more patients on lower floors (1-5)
            floor_weights = [30, 25, 20, 15, 10]
            floor = random.choices([1, 2, 3, 4, 5], weights=floor_weights)[0]

            # Room number format: floor + room (01-20)
            room_num = random.randint(1, 20)
            room_number = f"{floor}{room_num:02d}"

            # Generate masked resident number
            birth_year = birth_date.year % 100
            birth_month = birth_date.month
            birth_day = birth_date.day
            resident_front = f"{birth_year:02d}{birth_month:02d}{birth_day:02d}"

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
                room_number=room_number,
                bed_number=str(random.randint(1, 4)),
                admission_date=admission_date,
                expected_discharge_date=admission_date + timedelta(days=random.randint(30, 365)),
                admission_route=random.choice(ADMISSION_ROUTES),
                primary_diagnosis=random.choice(DIAGNOSES),
                secondary_diagnosis=random.choice(DIAGNOSES + [None, None]),
                attending_doctor=random.choice(DOCTOR_NAMES),
                nursing_unit=f"{floor}층 간호단위",
                insurance_type=random.choice(list(InsuranceType)).value,
                care_level=random.choice(list(CareLevel)).value,
                is_active=random.random() > 0.2  # 80% active
            )
            patients.append(patient)

            # Batch insert every 100 records
            if len(patients) >= 100:
                session.add_all(patients)
                await session.commit()
                print(f"  Inserted {existing + i + 1} records...")
                patients = []

        # Insert remaining records
        if patients:
            session.add_all(patients)
            await session.commit()

        # Verify final count
        result = await session.execute(select(func.count(PatientAdmission.id)))
        final_count = result.scalar() or 0

        print(f"Seeding complete! Total records: {final_count}")
        return final_count


async def clear_database():
    """Clear all patient admission records."""
    async with async_session() as session:
        await session.execute(PatientAdmission.__table__.delete())
        await session.commit()
        print("Database cleared")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed hospital database")
    parser.add_argument("--count", type=int, default=1000, help="Number of records to seed")
    parser.add_argument("--clear", action="store_true", help="Clear database before seeding")
    args = parser.parse_args()

    async def main():
        if args.clear:
            await clear_database()
        await seed_database(args.count)

    asyncio.run(main())
