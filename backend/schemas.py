from pydantic import BaseModel
from typing import List


class FloorResponse(BaseModel):
    """층 정보 응답 스키마"""
    floors: List[int]
    count: int


class TimingResponse(BaseModel):
    """타이밍 정보를 포함한 응답 스키마"""
    data: List[int]
    count: int
    db_time_ms: float
    total_time_ms: float

    class Config:
        json_schema_extra = {
            "example": {
                "data": [1, 2, 3, 4, 5],
                "count": 5,
                "db_time_ms": 12.34,
                "total_time_ms": 15.67
            }
        }


class StatsResponse(BaseModel):
    """통계 응답 스키마"""
    total_patients: int
    active_patients: int
    status: str


class HealthResponse(BaseModel):
    """헬스체크 응답 스키마"""
    status: str
    database: str
