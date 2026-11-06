"""Unmanaged ORM mappings to the schema created by sql/schema.sql."""

from django.db import models


class Team(models.Model):
    team_id = models.TextField(primary_key=True)
    team_name = models.TextField()
    specialization = models.TextField()

    class Meta:
        managed = False
        db_table = '"support_analytics"."teams"'


class Agent(models.Model):
    agent_id = models.TextField(primary_key=True)
    agent_label = models.TextField()
    team = models.ForeignKey(Team, models.DO_NOTHING, db_column="team_id")
    hired_at = models.DateTimeField()
    experience_level = models.TextField()

    class Meta:
        managed = False
        db_table = '"support_analytics"."agents"'


class Ticket(models.Model):
    PRIORITIES = [(value, value) for value in ("Critical", "High", "Medium", "Low")]
    STATUSES = [(value, value) for value in ("Open", "In Progress", "Pending", "Resolved", "Closed")]

    ticket_id = models.TextField(primary_key=True)
    customer_id = models.TextField()
    priority = models.TextField(choices=PRIORITIES)
    category = models.TextField()
    channel = models.TextField()
    status = models.TextField(choices=STATUSES)
    created_at = models.DateTimeField()
    first_response_at = models.DateTimeField(null=True)
    initial_resolved_at = models.DateTimeField(null=True)
    reopened_at = models.DateTimeField(null=True)
    reopen_count = models.SmallIntegerField()
    resolved_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    current_agent = models.ForeignKey(Agent, models.DO_NOTHING, db_column="current_agent_id")
    current_team = models.ForeignKey(Team, models.DO_NOTHING, db_column="current_team_id")
    response_target_minutes = models.IntegerField()
    resolution_target_minutes = models.IntegerField()
    response_deadline = models.DateTimeField()
    resolution_deadline = models.DateTimeField()
    response_sla_status = models.TextField()
    resolution_sla_status = models.TextField()
    overall_sla_status = models.TextField()

    class Meta:
        managed = False
        db_table = '"support_analytics"."tickets"'
        ordering = ["-created_at", "ticket_id"]


class AssignmentHistory(models.Model):
    assignment_id = models.TextField(primary_key=True)
    ticket = models.ForeignKey(Ticket, models.DO_NOTHING, db_column="ticket_id",
                               related_name="assignment_history")
    agent = models.ForeignKey(Agent, models.DO_NOTHING, db_column="agent_id")
    team = models.ForeignKey(Team, models.DO_NOTHING, db_column="team_id")
    assigned_at = models.DateTimeField()
    unassigned_at = models.DateTimeField(null=True)
    assignment_reason = models.TextField()

    class Meta:
        managed = False
        db_table = '"support_analytics"."assignment_history"'
        ordering = ["assigned_at", "assignment_id"]
