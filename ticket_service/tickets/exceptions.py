"""Do not expose SQL, credentials, or driver diagnostics in API responses."""

from django.db import DatabaseError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response
    if isinstance(exc, DatabaseError):
        return Response({"detail": "Ticket database is unavailable"}, status=503)
    return None
