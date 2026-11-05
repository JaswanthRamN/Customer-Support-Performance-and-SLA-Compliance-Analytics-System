"""Small injectable PostgreSQL boundary for parameterized read-only queries."""

from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row

from api.config import Settings


class DatabaseUnavailable(RuntimeError):
    """The database cannot be reached."""


class DatabaseQueryError(RuntimeError):
    """A database query failed without exposing SQL or credentials."""


class Database(Protocol):
    def ping(self) -> bool: ...
    def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...


class PostgreSQLDatabase:
    def __init__(self, settings: Settings, connector=None):
        self._settings = settings
        self._connector = connector or psycopg.connect

    def _connect(self):
        try:
            return self._connector(**self._settings.connection_kwargs(), row_factory=dict_row)
        except psycopg.OperationalError as error:
            raise DatabaseUnavailable("PostgreSQL is unavailable") from error

    def ping(self) -> bool:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute("SELECT 1 AS ok")
                return cursor.fetchone()["ok"] == 1
        except DatabaseUnavailable:
            raise
        except psycopg.Error as error:
            raise DatabaseQueryError("Readiness query failed") from error

    def fetch_one(self, query: str, params=None) -> dict[str, Any]:
        rows = self.fetch_all(query, params)
        return rows[0] if rows else {}

    def fetch_all(self, query: str, params=None) -> list[dict[str, Any]]:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(query, params or {})
                return list(cursor.fetchall())
        except DatabaseUnavailable:
            raise
        except psycopg.Error as error:
            raise DatabaseQueryError("Analytics query failed") from error
