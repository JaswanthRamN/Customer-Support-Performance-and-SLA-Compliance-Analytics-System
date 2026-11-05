"""Environment-only API and PostgreSQL configuration."""

import os

from pydantic import BaseModel, Field, ValidationError, field_validator


class Settings(BaseModel):
    """Validated runtime configuration; secrets are never included in repr output."""

    api_title: str = Field(min_length=1, max_length=100)
    api_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    db_host: str = Field(min_length=1)
    db_port: int = Field(ge=1, le=65535)
    db_name: str = Field(min_length=1)
    db_user: str = Field(min_length=1)
    db_password: str | None = Field(default=None, repr=False)
    db_sslmode: str = "prefer"
    db_connect_timeout: int = Field(default=5, ge=1, le=30)

    @field_validator("db_sslmode")
    @classmethod
    def valid_sslmode(cls, value: str) -> str:
        allowed = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
        if value not in allowed:
            raise ValueError(f"must be one of {sorted(allowed)}")
        return value

    @classmethod
    def from_environment(cls, environ=None) -> "Settings":
        env = os.environ if environ is None else environ
        data = {
            "api_title": env.get("API_TITLE", "Customer Support Analytics API"),
            "api_version": env.get("API_VERSION", "1.0.0"),
            "db_host": env.get("PGHOST", ""),
            "db_port": env.get("PGPORT", "5432"),
            "db_name": env.get("PGDATABASE", ""),
            "db_user": env.get("PGUSER", ""),
            "db_password": env.get("PGPASSWORD") or None,
            "db_sslmode": env.get("PGSSLMODE", "prefer"),
            "db_connect_timeout": env.get("API_DB_CONNECT_TIMEOUT", "5"),
        }
        return cls.model_validate(data)

    def connection_kwargs(self) -> dict:
        values = {
            "host": self.db_host,
            "port": self.db_port,
            "dbname": self.db_name,
            "user": self.db_user,
            "sslmode": self.db_sslmode,
            "connect_timeout": self.db_connect_timeout,
        }
        if self.db_password:
            values["password"] = self.db_password
        return values


def configuration_error(error: ValidationError) -> RuntimeError:
    fields = sorted({str(item["loc"][0]) for item in error.errors()})
    return RuntimeError("Invalid or missing API configuration fields: " + ", ".join(fields))
