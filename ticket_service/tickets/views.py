from rest_framework.response import Response
from rest_framework.views import APIView

from ticket_service.tickets.pagination import TicketPagination
from ticket_service.tickets.serializers import (AssignmentHistorySerializer, TicketDetailSerializer,
                                                TicketFilterSerializer, TicketListSerializer)
from ticket_service.tickets.services import build_ticket_queryset, get_assignment_history, get_ticket


class TicketListView(APIView):
    """List tickets with validated operational filters and bounded pagination."""

    def get(self, request):
        filters = TicketFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        queryset = build_ticket_queryset(filters.validated_data)
        paginator = TicketPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(TicketListSerializer(page, many=True).data)


class TicketDetailView(APIView):
    """Retrieve one ticket from the existing shared table."""

    def get(self, request, ticket_id):
        return Response(TicketDetailSerializer(get_ticket(ticket_id)).data)


class TicketAssignmentHistoryView(APIView):
    """Retrieve paginated historical ownership intervals for one ticket."""

    def get(self, request, ticket_id):
        queryset = get_assignment_history(ticket_id)
        paginator = TicketPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(AssignmentHistorySerializer(page, many=True).data)
