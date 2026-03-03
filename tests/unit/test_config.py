"""Unit tests for agent_sdk.config.Settings."""
import os
import pytest
from agent_sdk.config import Settings

def test_settings_defaults():
    s = Settings()
    assert s.db_path == "agent_sdk.db"
    assert s.db_pool_size == 5
    assert s.max_steps == 30
    assert s.default_model == "gpt-4"
    assert s.default_temperature == 0.7
    assert s.max_tokens == 4096
    assert s.approval_timeout == 300.0
    assert s.queue_max_size == 1000
    assert s.queue_max_workers == 10
    assert s.log_level == "INFO"
    assert s.server_host == "0.0.0.0"
    assert s.server_port == 8000

def test_env_var_overrides(monkeypatch):
    monkeypatch.setenv("AGENT_SDK_DB_PATH", "override.db")
    monkeypatch.setenv("AGENT_SDK_DB_POOL_SIZE", "99")
    monkeypatch.setenv("AGENT_SDK_DEFAULT_MODEL", "gpt-3.5")
    monkeypatch.setenv("AGENT_SDK_LOG_LEVEL", "DEBUG")
    s = Settings()
    assert s.db_path == "override.db"
    assert s.db_pool_size == 99
    assert s.default_model == "gpt-3.5"
    assert s.log_level == "DEBUG"
