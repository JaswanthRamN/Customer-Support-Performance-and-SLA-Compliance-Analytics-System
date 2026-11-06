from rest_framework.pagination import LimitOffsetPagination


class TicketPagination(LimitOffsetPagination):
    default_limit = 25
    max_limit = 100
