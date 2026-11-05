from fastapi import APIRouter, Depends

from api.database import Database
from api.dependencies import get_database
from api.models import HealthResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", response_model=HealthResponse, summary="Process liveness")
def liveness() -> HealthResponse:
    return HealthResponse(status="ok", service="analytics-api")


@router.get("/ready", response_model=ReadinessResponse, summary="PostgreSQL readiness")
def readiness(database: Database = Depends(get_database)) -> ReadinessResponse:
    database.ping()
    return ReadinessResponse(status="ready", database="postgresql")
