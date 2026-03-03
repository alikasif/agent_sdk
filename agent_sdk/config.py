"""SDK configuration via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Agent SDK configuration.

    All settings can be overridden via environment variables
    prefixed with ``AGENT_SDK_``.
    """

    # Database
    db_path: str = "agent_sdk.db"
    db_pool_size: int = 5

    # Agent defaults
    max_steps: int = 30
    default_model: str = "gpt-4"
    default_temperature: float = 0.7
    max_tokens: int = 4096

    # Governance
    approval_timeout: float = 300.0

    # Scale
    queue_max_size: int = 1000
    queue_max_workers: int = 10

    # Logging
    log_level: str = "INFO"

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    model_config = {"env_prefix": "AGENT_SDK_"}
