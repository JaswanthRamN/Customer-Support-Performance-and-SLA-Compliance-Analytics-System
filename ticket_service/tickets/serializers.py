"""Output and query-parameter validation for the ticket API."""

from rest_framework import serializers

from ticket_service.tickets.models import AssignmentHistory, Ticket


class TicketFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[value for value, _ in Ticket.STATUSES], required=False)
    priority = serializers.ChoiceField(choices=[value for value, _ in Ticket.PRIORITIES], required=False)
    team_id = serializers.RegexField(r"^TM\d+$", max_length=20, required=False)
    created_from = serializers.DateField(required=False)
    created_to = serializers.DateField(required=False)

    def validate(self, attrs):
        if attrs.get("created_from") and attrs.get("created_to"):
            if attrs["created_from"] > attrs["created_to"]:
                raise serializers.ValidationError("created_from must be on or before created_to")
        return attrs


class TicketListSerializer(serializers.ModelSerializer):
    current_team_name = serializers.CharField(source="current_team.team_name", read_only=True)
    current_agent_label = serializers.CharField(source="current_agent.agent_label", read_only=True)

    class Meta:
        model = Ticket
        fields = ("ticket_id", "priority", "category", "channel", "status", "created_at",
                  "first_response_at", "resolved_at", "current_team_id", "current_team_name",
                  "current_agent_id", "current_agent_label", "response_sla_status",
                  "resolution_sla_status", "overall_sla_status")
        read_only_fields = fields


class TicketDetailSerializer(TicketListSerializer):
    class Meta(TicketListSerializer.Meta):
        fields = TicketListSerializer.Meta.fields + (
            "customer_id", "initial_resolved_at", "reopened_at", "reopen_count", "closed_at",
            "response_target_minutes", "resolution_target_minutes", "response_deadline",
            "resolution_deadline",
        )
        read_only_fields = fields


class AssignmentHistorySerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.team_name", read_only=True)
    agent_label = serializers.CharField(source="agent.agent_label", read_only=True)

    class Meta:
        model = AssignmentHistory
        fields = ("assignment_id", "ticket_id", "agent_id", "agent_label", "team_id",
                  "team_name", "assigned_at", "unassigned_at", "assignment_reason")
        read_only_fields = fields
