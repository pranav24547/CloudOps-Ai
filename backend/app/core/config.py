"""Centralized application settings powered by pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Operational Modes
    cloudops_mode: Literal["demo", "live"] = Field(default="demo", validation_alias="CLOUDOPS_MODE")
    github_mode: str | None = Field(default=None, validation_alias="GITHUB_MODE")
    aws_mode: str | None = Field(default=None, validation_alias="AWS_MODE")
    docker_mode: str | None = Field(default=None, validation_alias="DOCKER_MODE")

    # LLM Settings (Default: gemini; fallback to demo only when explicitly set)
    llm_provider: str = Field(default="gemini", validation_alias="LLM_PROVIDER")
    llm_model: str | None = Field(default=None, validation_alias="LLM_MODEL")
    google_api_key: str | None = Field(default=None, validation_alias="GOOGLE_API_KEY")
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")

    # Security & Auth
    jwt_secret_key: str = Field(
        default="cloudops-super-secret-development-key-32chars",
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 1 day

    # Database
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    sql_echo: bool = Field(default=False, validation_alias="SQL_ECHO")

    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # MCP Server URLs
    aws_mcp_url: str = Field(default="http://127.0.0.1:8101/mcp", validation_alias="AWS_MCP_URL")
    github_mcp_url: str = Field(default="http://127.0.0.1:8102/mcp", validation_alias="GITHUB_MCP_URL")
    docker_mcp_url: str = Field(default="http://127.0.0.1:8103/mcp", validation_alias="DOCKER_MCP_URL")

    # AWS
    aws_region: str = Field(default="ap-south-1", validation_alias="AWS_REGION")
    aws_default_region: str = Field(default="ap-south-1", validation_alias="AWS_DEFAULT_REGION")

    # GitHub
    github_repository: str = Field(default="acme-corp/orders-api", validation_alias="GITHUB_REPOSITORY")
    github_token: str | None = Field(default=None, validation_alias="GITHUB_TOKEN")

    # Frontend
    next_public_api_url: str = Field(default="http://localhost:8000", validation_alias="NEXT_PUBLIC_API_URL")

    @property
    def effective_github_mode(self) -> str:
        if self.github_mode:
            return self.github_mode.lower()
        if self.github_token:
            return "live"
        return self.cloudops_mode.lower()

    @property
    def effective_aws_mode(self) -> str:
        if self.aws_mode:
            return self.aws_mode.lower()
        return self.cloudops_mode.lower()

    @property
    def effective_docker_mode(self) -> str:
        if self.docker_mode:
            return self.docker_mode.lower()
        return self.cloudops_mode.lower()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
