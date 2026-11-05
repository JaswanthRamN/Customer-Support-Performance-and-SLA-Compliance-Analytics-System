"""FastAPI dependencies shared by routers."""

from datetime import date

from fastapi import HTTPException, Query, Request

from api.database import Database
from api.models import AnalyticsFilters, Page, Priority


def get_database(request: Request) -> Database:
    return request.app.state.database


def filters_dependency(
    priority: Priority | None = Query(default=None, description="Ticket priority"),
    team_id: str | None = Query(default=None, pattern=r"^TM\d+$", max_length=20),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
) -> AnalyticsFilters:
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="created_from must be on or before created_to")
    return AnalyticsFilters(priority=priority, team_id=team_id,
                            created_from=created_from, created_to=created_to)


def page_dependency(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
) -> Page:
    return Page(limit=limit, offset=offset)
