"""DRF route, serializer, filter, pagination, and unmanaged-model tests."""

import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticket_service.config.settings")
import django
django.setup()

from rest_framework.test import APIClient

from django.conf import settings

from ticket_service.tickets.models import Agent, AssignmentHistory, Team, Ticket
from ticket_service.tickets.serializers import TicketFilterSerializer


def team():
    return SimpleNamespace(team_id="TM02", team_name="Technical Support")


def agent():
    return SimpleNamespace(agent_id="AG011", agent_label="Synthetic Agent 11")


def ticket():
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SimpleNamespace(
        ticket_id="TK000001", customer_id="CU00001", priority="High", category="Technical",
        channel="Email", status="Pending", created_at=created, first_response_at=created,
        initial_resolved_at=None, reopened_at=None, reopen_count=0, resolved_at=None,
        closed_at=None, current_team_id="TM02", current_team=team(),
        current_agent_id="AG011", current_agent=agent(), response_target_minutes=60,
        resolution_target_minutes=480, response_deadline=created, resolution_deadline=created,
        response_sla_status="Met", resolution_sla_status="Breached", overall_sla_status="Breached")


def assignment():
    return SimpleNamespace(assignment_id="AS000001", ticket_id="TK000001",
                           agent_id="AG011", agent=agent(), team_id="TM02", team=team(),
                           assigned_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                           unassigned_at=None, assignment_reason="Initial")


class TicketServiceTests(unittest.TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("ticket_service.tickets.views.build_ticket_queryset")
    def test_ticket_list_filters_and_pagination(self, build):
        build.return_value = [ticket()]
        response = self.client.get(
            "/api/v1/tickets/?status=Pending&priority=High&team_id=TM02&limit=1&offset=0")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["ticket_id"], "TK000001")
        self.assertEqual(build.call_args.args[0]["priority"], "High")

    @patch("ticket_service.tickets.views.build_ticket_queryset")
    def test_pagination_is_capped_at_one_hundred(self, build):
        build.return_value = [ticket() for _ in range(101)]
        response = self.client.get("/api/v1/tickets/?limit=1000")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 100)

    @patch("ticket_service.tickets.views.get_ticket")
    def test_ticket_detail(self, get_one):
        get_one.return_value = ticket()
        response = self.client.get("/api/v1/tickets/TK000001/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_team_name"], "Technical Support")
        self.assertEqual(response.data["resolution_target_minutes"], 480)

    @patch("ticket_service.tickets.views.get_assignment_history")
    def test_assignment_history(self, history):
        history.return_value = [assignment()]
        response = self.client.get("/api/v1/tickets/TK000001/assignments/?limit=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["assignment_reason"], "Initial")
        self.assertEqual(response.data["results"][0]["agent_label"], "Synthetic Agent 11")

    def test_invalid_filters(self):
        for query in ["priority=Urgent", "status=Deleted", "team_id=bad",
                      "created_from=2026-06-01&created_to=2026-01-01"]:
            with self.subTest(query=query):
                response = self.client.get("/api/v1/tickets/?" + query)
                self.assertEqual(response.status_code, 400)

    def test_filter_serializer_date_validation(self):
        serializer = TicketFilterSerializer(data={"created_from": "2026-02-01",
                                                   "created_to": "2026-01-01"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_shared_models_are_unmanaged_and_schema_qualified(self):
        for model in (Team, Agent, Ticket, AssignmentHistory):
            self.assertFalse(model._meta.managed)
        self.assertEqual(Ticket._meta.db_table, '"support_analytics"."tickets"')
        self.assertEqual(settings.MIGRATION_MODULES["tickets"], None)

    def test_routes_are_read_only(self):
        self.assertEqual(self.client.post("/api/v1/tickets/", {}, format="json").status_code, 405)
        self.assertEqual(self.client.patch(
            "/api/v1/tickets/TK000001/", {"status": "Closed"}, format="json").status_code, 405)


if __name__ == "__main__":
    unittest.main()
