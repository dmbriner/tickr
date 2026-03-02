from __future__ import annotations

import json

from pydantic import Field
from pydantic.field_validator import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Tickr API"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000", "https://dmbriner.github.io"])
    cors_origin_regex: str | None = None

    database_url: str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/statement_model")

    jwt_secret: str = Field(default="change-me-in-production")
    jwt_expires_minutes: int = Field(default=120)

    alpha_vantage_api_key: str | None = None
    fmp_api_key: str | None = None
    financial_modeling_prep_api_key: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                return json.loads(raw)
            return [item.strip() for item in raw.split(",") if item.strip()]
        return value


settings = Settings()
