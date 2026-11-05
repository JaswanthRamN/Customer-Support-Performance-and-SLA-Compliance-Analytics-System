"""FastAPI application factory."""

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from api.config import Settings, configuration_error
from api.database import DatabaseQueryError, DatabaseUnavailable, PostgreSQLDatabase
from api.routers import analytics, health

logger = logging.getLogger("analytics_api")


def create_app(settings: Settings | None = None, database=None) -> FastAPI:
    if database is None:
        try:
            settings = settings or Settings.from_environment()
        except ValidationError as error:
            raise configuration_error(error) from error
        database = PostgreSQLDatabase(settings)
    settings = settings or Settings(
        api_title="Customer Support Analytics API", api_version="1.0.0",
        db_host="injected", db_port=5432, db_name="injected", db_user="injected"
    )
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=("Read-only analytics over the support_analytics PostgreSQL reporting layer. "
                     "All data is synthetic; SLA targets are illustrative project assumptions."),
        contact={"name": "Portfolio project"},
    )
    app.state.database = database
    app.include_router(health.router)
    app.include_router(analytics.router)

    @app.exception_handler(DatabaseUnavailable)
    async def unavailable_handler(request: Request, error: DatabaseUnavailable):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        logger.warning("Database unavailable request_id=%s", request_id)
        return JSONResponse(status_code=503,
                            content={"detail": "Analytics database is unavailable", "request_id": request_id})

    @app.exception_handler(DatabaseQueryError)
    async def query_handler(request: Request, error: DatabaseQueryError):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        logger.error("Database query failed request_id=%s", request_id)
        return JSONResponse(status_code=500,
                            content={"detail": "Analytics query failed", "request_id": request_id})
    return app
