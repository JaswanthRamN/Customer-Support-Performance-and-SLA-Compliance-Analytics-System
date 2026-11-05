"""Pydantic request enums and response contracts."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Priority(str, Enum):
    critical = "Critical"
    high = "High"
    medium = "Medium"
    low = "Low"


class GroupBy(str, Enum):
    overall = "overall"
    priority = "priority"
    team = "team"


class AnalyticsFilters(BaseModel):
    priority: Priority | None = None
    team_id: str | None = Field(default=None, pattern=r"^TM\d+$", max_length=20)
    created_from: date | None = None
    created_to: date | None = None

    @model_validator(mode="after")
    def valid_date_range(self):
        if self.created_from and self.created_to and self.created_from > self.created_to:
            raise ValueError("created_from must be on or before created_to")
        return self

    def query_params(self) -> dict[str, Any]:
        return {
            "priority": self.priority.value if self.priority else None,
            "team_id": self.team_id,
            "created_from": self.created_from,
            "created_to": self.created_to,
        }


class Page(BaseModel):
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1_000_000)


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(APIModel):
    status: str
    service: str


class ReadinessResponse(APIModel):
    status: str
    database: str


class OverviewResponse(APIModel):
    total_tickets: int
    resolved_tickets: int
    unresolved_tickets: int
    overdue_tickets: int
    reopened_tickets: int
    rated_tickets: int
    average_csat: float | None
    analysis_as_of: datetime | None


class SLAResult(APIModel):
    dimension_id: str
    dimension_name: str
    tickets: int
    response_met: int
    response_breached: int
    response_pending: int
    response_compliance_pct: float | None
    resolution_met: int
    resolution_breached: int
    resolution_pending: int
    resolution_compliance_pct: float | None
    overall_met: int
    overall_breached: int
    overall_pending: int
    overall_compliance_pct: float | None


class TeamResult(APIModel):
    team_id: str
    team_name: str
    tickets: int
    unresolved_tickets: int
    overdue_tickets: int
    answered_tickets: int
    average_response_hours: float | None
    resolved_tickets: int
    average_resolution_hours: float | None
    response_compliance_pct: float | None
    resolution_compliance_pct: float | None
    reassigned_tickets: int
    reopened_tickets: int
    rated_tickets: int
    average_csat: float | None


class ResponseTimeResult(APIModel):
    dimension_id: str
    dimension_name: str
    tickets: int
    answered_tickets: int
    unanswered_tickets: int
    average_response_hours: float | None
    median_response_hours: float | None
    resolved_tickets: int
    unresolved_tickets: int
    average_resolution_hours: float | None
    median_resolution_hours: float | None


class BacklogItem(APIModel):
    ticket_id: str
    priority: str
    category: str
    channel: str
    status: str
    created_at: datetime
    resolution_deadline: datetime
    unresolved_age_hours: float
    current_team_id: str
    current_team_name: str
    current_agent_id: str
    current_agent_label: str
    is_overdue: bool


class BacklogResponse(APIModel):
    total: int
    overdue: int
    limit: int
    offset: int
    items: list[BacklogItem]


class SLAPage(BaseModel):
    limit: int
    offset: int
    items: list[SLAResult]


class TeamPage(BaseModel):
    limit: int
    offset: int
    items: list[TeamResult]


class ResponseTimePage(BaseModel):
    limit: int
    offset: int
    items: list[ResponseTimeResult]


class ErrorResponse(BaseModel):
    detail: str
    request_id: str
