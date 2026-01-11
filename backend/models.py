import enum
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Enum, Boolean
from sqlalchemy.sql import func

from .database import Base


class Gender(enum.Enum):
    MALE = "M"
    FEMALE = "F"


class InsuranceType(enum.Enum):
    NATIONAL_HEALTH = "국민건강보험"
    MEDICAL_AID_1 = "의료급여1종"
    MEDICAL_AID_2 = "의료급여2종"
    LONG_TERM_CARE = "장기요양보험"
    SELF_PAY = "비급여"


class CareLevel(enum.Enum):
    LEVEL_1 = "1등급"
    LEVEL_2 = "2등급"
    LEVEL_3 = "3등급"
    LEVEL_4 = "4등급"
    LEVEL_5 = "5등급"
    COGNITIVE = "인지지원등급"
    NONE = "등급없음"


class PatientAdmission(Base):
    """요양병원 환자 입원 정보 테이블"""
    __tablename__ = "patient_admissions"

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Patient Identification (환자 식별)
    patient_id = Column(String(20), nullable=False, index=True)
    resident_number = Column(String(14), nullable=False)

    # Patient Demographics (환자 인적사항)
    patient_name = Column(String(50), nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    birth_date = Column(Date, nullable=False)
    contact_phone = Column(String(20))

    # Guardian Information (보호자 정보)
    guardian_name = Column(String(50), nullable=False)
    guardian_phone = Column(String(20), nullable=False)
    guardian_relationship = Column(String(20))

    # Room Information (병실 정보) - floor is the key query target
    floor = Column(Integer, nullable=False, index=True)
    room_number = Column(String(10), nullable=False)
    bed_number = Column(String(5), nullable=False)

    # Admission Information (입원 정보)
    admission_date = Column(Date, nullable=False, index=True)
    expected_discharge_date = Column(Date)
    actual_discharge_date = Column(Date)
    admission_route = Column(String(50))

    # Medical Information (의료 정보)
    primary_diagnosis = Column(String(200), nullable=False)
    secondary_diagnosis = Column(Text)
    attending_doctor = Column(String(50), nullable=False)
    nursing_unit = Column(String(50))

    # Insurance & Care Level (보험 및 등급 정보)
    insurance_type = Column(Enum(InsuranceType), nullable=False)
    care_level = Column(Enum(CareLevel))

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
