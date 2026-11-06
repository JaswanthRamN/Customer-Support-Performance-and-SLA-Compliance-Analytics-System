from django.urls import path

from ticket_service.tickets.views import (TicketAssignmentHistoryView, TicketDetailView,
                                          TicketListView)

urlpatterns = [
    path("tickets/", TicketListView.as_view(), name="ticket-list"),
    path("tickets/<str:ticket_id>/", TicketDetailView.as_view(), name="ticket-detail"),
    path("tickets/<str:ticket_id>/assignments/", TicketAssignmentHistoryView.as_view(),
         name="ticket-assignment-history"),
]
