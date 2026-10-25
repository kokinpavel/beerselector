import io
import os
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command
from src.core.config import get_settings


def migration_config() -> Config:
    return Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))


def test_single_baseline_head():
    scripts = ScriptDirectory.from_config(migration_config())
    assert scripts.get_heads() == ["0003"]
    assert scripts.get_revision("0001").down_revision is None


def test_offline_upgrade_and_downgrade(monkeypatch):
    # Percent-encoded credentials must not pass through ConfigParser interpolation.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:p%25ss@localhost/test")
    get_settings.cache_clear()
    try:
        output = io.StringIO()
        config = migration_config()
        config.output_buffer = output
        command.upgrade(config, "head", sql=True)
        assert "CREATE TABLE alembic_version" in output.getvalue()
        assert "INSERT INTO alembic_version" in output.getvalue()
        assert "CREATE TABLE users" in output.getvalue()
        assert "CREATE TABLE external_accounts" in output.getvalue()
        output.seek(0)
        output.truncate()
        command.downgrade(config, "0003:base", sql=True)
        assert "DROP TABLE external_accounts" in output.getvalue()
        assert "DROP TABLE users" in output.getvalue()
        assert "DELETE FROM alembic_version" in output.getvalue()
    finally:
        get_settings.cache_clear()


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL must point to a disposable PostgreSQL database",
)
def test_postgres_migration_roundtrip(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    get_settings.cache_clear()
    try:
        config = migration_config()
        command.upgrade(config, "head")
        command.check(config)
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        command.check(config)
    finally:
        get_settings.cache_clear()
