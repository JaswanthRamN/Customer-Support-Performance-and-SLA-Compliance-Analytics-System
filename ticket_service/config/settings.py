"""Environment-based settings for the read-only ticket API."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [value.strip() for value in
                 os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
                 if value.strip()]

ROOT_URLCONF = "ticket_service.config.urls"
INSTALLED_APPS = ["rest_framework", "ticket_service.tickets"]
MIDDLEWARE = []
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.getenv("PGHOST", "localhost"),
        "PORT": int(os.getenv("PGPORT", "5432")),
        "NAME": os.getenv("PGDATABASE", "customer_support_analytics"),
        "USER": os.getenv("PGUSER", "postgres"),
        "PASSWORD": os.getenv("PGPASSWORD", ""),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "sslmode": os.getenv("PGSSLMODE", "prefer"),
            "connect_timeout": int(os.getenv("API_DB_CONNECT_TIMEOUT", "5")),
        },
    }
}

# The shared support tables are owned by sql/schema.sql, never Django migrations.
MIGRATION_MODULES = {"tickets": None}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_PAGINATION_CLASS": "ticket_service.tickets.pagination.TicketPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "ticket_service.tickets.exceptions.api_exception_handler",
}
