from typing import Annotated

from fastapi import APIRouter, Depends

from api import queries
from api.database import Database
from api.dependencies import filters_dependency, get_database, page_dependency
from api.models import (AnalyticsFilters, BacklogResponse, GroupBy, OverviewResponse,
                        Page, ResponseTimePage, SLAPage, TeamPage)

router = APIRouter(prefix="/api/v1", tags=["Analytics"])
FiltersDep = Annotated[AnalyticsFilters, Depends(filters_dependency)]
PageDep = Annotated[Page, Depends(page_dependency)]
DatabaseDep = Annotated[Database, Depends(get_database)]


def params(filters: AnalyticsFilters, page: Page | None = None) -> dict:
    values = filters.query_params()
    if page:
        values.update(limit=page.limit, offset=page.offset)
    return values


@router.get("/overview", response_model=OverviewResponse,
            summary="Portfolio overview", description="Ticket-grain snapshot KPIs.")
def overview(filters: FiltersDep, database: DatabaseDep):
    return database.fetch_one(queries.OVERVIEW, params(filters))


@router.get("/sla", response_model=SLAPage,
            summary="SLA compliance", description="Met/(Met+Breached); Pending is explicit.")
def sla(filters: FiltersDep, page: PageDep, database: DatabaseDep,
        group_by: GroupBy = GroupBy.overall):
    rows = database.fetch_all(queries.sla_query(group_by.value), params(filters, page))
    return {"limit": page.limit, "offset": page.offset, "items": rows}


@router.get("/teams", response_model=TeamPage,
            summary="Current-team performance", description="Current ownership, not causal attribution.")
def teams(filters: FiltersDep, page: PageDep, database: DatabaseDep):
    rows = database.fetch_all(queries.TEAM_PERFORMANCE, params(filters, page))
    return {"limit": page.limit, "offset": page.offset, "items": rows}


@router.get("/response-times", response_model=ResponseTimePage,
            summary="Response and resolution time", description="Null lifecycle events are excluded.")
def response_times(filters: FiltersDep, page: PageDep, database: DatabaseDep,
                   group_by: GroupBy = GroupBy.overall):
    rows = database.fetch_all(queries.response_times_query(group_by.value), params(filters, page))
    return {"limit": page.limit, "offset": page.offset, "items": rows}


@router.get("/backlog", response_model=BacklogResponse,
            summary="Current unresolved backlog", description="Paginated current snapshot, not historical backlog.")
def backlog(filters: FiltersDep, page: PageDep, database: DatabaseDep):
    query_params = params(filters, page)
    summary = database.fetch_one(queries.BACKLOG_SUMMARY, query_params)
    rows = database.fetch_all(queries.BACKLOG_ITEMS, query_params)
    return {**summary, "limit": page.limit, "offset": page.offset, "items": rows}
