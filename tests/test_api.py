"""Endpoint and configuration contracts using an injected database boundary."""

import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.config import Settings
from api.database import DatabaseQueryError, DatabaseUnavailable
from api.main import create_app


class FakeDatabase:
    def __init__(self, fail_ping=False, fail_query=False):
        self.fail_ping = fail_ping
        self.fail_query = fail_query
        self.calls = []

    def ping(self):
        if self.fail_ping:
            raise DatabaseUnavailable("hidden database detail")
        return True

    def fetch_one(self, query, params=None):
        if self.fail_query:
            raise DatabaseQueryError("hidden SQL detail")
        self.calls.append((query, params))
        if "overview" in query:
            return {"total_tickets": 10000, "resolved_tickets": 8864,
                    "unresolved_tickets": 1136, "overdue_tickets": 1082,
                    "reopened_tickets": 931, "rated_tickets": 3758,
                    "average_csat": 3.87,
                    "analysis_as_of": datetime(2026, 7, 1, tzinfo=timezone.utc)}
        if "backlog-summary" in query:
            return {"total": 1136, "overdue": 1082}
        return {}

    def fetch_all(self, query, params=None):
        if self.fail_query:
            raise DatabaseQueryError("hidden SQL detail")
        self.calls.append((query, params))
        if "backlog-items" in query:
            return [{"ticket_id": "TK000001", "priority": "High", "category": "Technical",
                     "channel": "Email", "status": "Pending",
                     "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                     "resolution_deadline": datetime(2026, 1, 2, tzinfo=timezone.utc),
                     "unresolved_age_hours": 100.0, "current_team_id": "TM02",
                     "current_team_name": "Technical Support", "current_agent_id": "AG011",
                     "current_agent_label": "Synthetic Agent 11", "is_overdue": True}]
        if "/* sla */" in query:
            return [{"dimension_id": "ALL", "dimension_name": "All tickets", "tickets": 10000,
                     "response_met": 8013, "response_breached": 1976, "response_pending": 11,
                     "response_compliance_pct": 80.22, "resolution_met": 5343,
                     "resolution_breached": 4603, "resolution_pending": 54,
                     "resolution_compliance_pct": 53.72, "overall_met": 4387,
                     "overall_breached": 5569, "overall_pending": 44,
                     "overall_compliance_pct": 44.06}]
        if "/* teams */" in query:
            return [{"team_id": "TM01", "team_name": "Tier 1 Support", "tickets": 3687,
                     "unresolved_tickets": 400, "overdue_tickets": 380, "answered_tickets": 3600,
                     "average_response_hours": 2.5, "resolved_tickets": 3287,
                     "average_resolution_hours": 39.0, "response_compliance_pct": 81.0,
                     "resolution_compliance_pct": 55.0, "reassigned_tickets": 900,
                     "reopened_tickets": 320, "rated_tickets": 1400, "average_csat": 3.9}]
        if "/* response-times */" in query:
            return [{"dimension_id": "ALL", "dimension_name": "All tickets", "tickets": 10000,
                     "answered_tickets": 9796, "unanswered_tickets": 204,
                     "average_response_hours": 2.70, "median_response_hours": 1.25,
                     "resolved_tickets": 8864, "unresolved_tickets": 1136,
                     "average_resolution_hours": 40.57, "median_resolution_hours": 18.33}]
        return []


class APITests(unittest.TestCase):
    def setUp(self):
        self.database = FakeDatabase()
        self.client = TestClient(create_app(database=self.database))

    def test_liveness(self):
        response = self.client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_readiness_and_safe_failure(self):
        self.assertEqual(self.client.get("/health/ready").status_code, 200)
        failed = TestClient(create_app(database=FakeDatabase(fail_ping=True))).get(
            "/health/ready", headers={"x-request-id": "test-request"})
        self.assertEqual(failed.status_code, 503)
        self.assertEqual(failed.json(), {"detail": "Analytics database is unavailable",
                                         "request_id": "test-request"})
        self.assertNotIn("hidden", failed.text)

    def test_overview_with_validated_filters(self):
        response = self.client.get("/api/v1/overview?priority=High&team_id=TM02")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_tickets"], 10000)
        _, params = self.database.calls[-1]
        self.assertEqual(params["priority"], "High")
        self.assertEqual(params["team_id"], "TM02")
        self.assertNotIn("High", self.database.calls[-1][0])
        self.assertIn("%(priority)s", self.database.calls[-1][0])

    def test_query_failure_is_safe(self):
        failed = TestClient(create_app(database=FakeDatabase(fail_query=True))).get(
            "/api/v1/overview", headers={"x-request-id": "query-request"})
        self.assertEqual(failed.status_code, 500)
        self.assertEqual(failed.json(), {"detail": "Analytics query failed",
                                         "request_id": "query-request"})
        self.assertNotIn("hidden", failed.text)

    def test_sla_endpoint(self):
        response = self.client.get("/api/v1/sla?group_by=priority&limit=10&offset=0")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["overall_compliance_pct"], 44.06)

    def test_team_endpoint(self):
        response = self.client.get("/api/v1/teams?limit=3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["team_id"], "TM01")

    def test_response_time_endpoint(self):
        response = self.client.get("/api/v1/response-times?group_by=team")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["answered_tickets"], 9796)

    def test_backlog_pagination(self):
        response = self.client.get("/api/v1/backlog?limit=1&offset=5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1136)
        self.assertEqual(response.json()["limit"], 1)
        self.assertEqual(self.database.calls[-1][1]["offset"], 5)

    def test_validation_rejects_bad_inputs(self):
        self.assertEqual(self.client.get("/api/v1/overview?priority=Urgent").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/backlog?limit=101").status_code, 422)
        self.assertEqual(self.client.get(
            "/api/v1/overview?created_from=2026-06-01&created_to=2026-01-01").status_code, 422)

    def test_openapi_lists_tested_routes(self):
        document = self.client.get("/openapi.json").json()
        for path in ["/health/live", "/health/ready", "/api/v1/overview", "/api/v1/sla",
                     "/api/v1/teams", "/api/v1/response-times", "/api/v1/backlog"]:
            self.assertIn(path, document["paths"])

    def test_settings_validation_and_secret_repr(self):
        env = {"PGHOST": "localhost", "PGDATABASE": "analytics", "PGUSER": "reader",
               "PGPASSWORD": "secret", "PGPORT": "5432"}
        settings = Settings.from_environment(env)
        self.assertNotIn("secret", repr(settings))
        self.assertEqual(settings.db_port, 5432)
        self.assertEqual(settings.connection_kwargs()["options"], "-c timezone=UTC")


if __name__ == "__main__":
    unittest.main()
