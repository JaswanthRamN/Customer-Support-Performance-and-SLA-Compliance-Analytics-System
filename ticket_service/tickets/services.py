"""ORM query builders; Django parameterizes all validated filter values."""

from django.http import Http404

from ticket_service.tickets.models import AssignmentHistory, Ticket


def build_ticket_queryset(filters):
    queryset = Ticket.objects.select_related("current_team", "current_agent").all()
    if value := filters.get("status"):
        queryset = queryset.filter(status=value)
    if value := filters.get("priority"):
        queryset = queryset.filter(priority=value)
    if value := filters.get("team_id"):
        queryset = queryset.filter(current_team_id=value)
    if value := filters.get("created_from"):
        queryset = queryset.filter(created_at__date__gte=value)
    if value := filters.get("created_to"):
        queryset = queryset.filter(created_at__date__lte=value)
    return queryset.order_by("-created_at", "ticket_id")


def get_ticket(ticket_id):
    try:
        return Ticket.objects.select_related("current_team", "current_agent").get(ticket_id=ticket_id)
    except Ticket.DoesNotExist as error:
        raise Http404("Ticket not found") from error


def get_assignment_history(ticket_id):
    if not Ticket.objects.filter(ticket_id=ticket_id).exists():
        raise Http404("Ticket not found")
    return AssignmentHistory.objects.select_related("team", "agent").filter(
        ticket_id=ticket_id).order_by("assigned_at", "assignment_id")
