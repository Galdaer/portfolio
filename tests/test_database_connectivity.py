"""
Diagnostic tests for the medical database connectivity and schema presence.

These tests are designed to run quickly and provide actionable diagnostics
when the system falls back to direct MCP due to DB unavailability.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest

# Ensure healthcare-api package is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
HEALTHCARE_API_PATH = PROJECT_ROOT / "services" / "user" / "healthcare-api"
if str(HEALTHCARE_API_PATH) not in sys.path:
    sys.path.append(str(HEALTHCARE_API_PATH))


def test_postgres_env_variables_present():
    required = [
        "POSTGRES_HOST",
        "POSTGRES_DB",
        "POSTGRES_USER",
        # password may be supplied via secret manager; tolerate missing but log
    ]
    missing = [k for k in required if not os.getenv(k)]
    assert not missing, f"Missing DB env vars: {missing}. Configure environment or config.app.postgres_url"


def test_database_connection_factory_smoke():
    from src.security.database_factory import (
        PostgresConnectionFactory,
    )

    # Prefer full URL if the app config provides one
    conn_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if conn_url:
        factory = PostgresConnectionFactory(conn_url)
    else:
        factory = PostgresConnectionFactory(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "intelluxe"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            sslmode=os.getenv("POSTGRES_SSLMODE", "prefer"),
        )

    info = factory.get_connection_info()
    assert isinstance(info, dict)


def test_database_connection_and_tables(monkeypatch):
    """Try opening a connection and checking core tables if server reachable.

    If the connection fails (e.g., server not running in host env), mark as xfail
    with a clear reason so CI/devs know it's environment-related.
    """
    import psycopg2
    from src.security.database_factory import (
        PostgresConnectionFactory,
    )

    conn_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if conn_url:
        factory = PostgresConnectionFactory(conn_url)
    else:
        factory = PostgresConnectionFactory(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "intelluxe"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            sslmode=os.getenv("POSTGRES_SSLMODE", "prefer"),
        )

    try:
        conn = factory.create_connection()
    except RuntimeError as e:
        pytest.xfail(f"DB not reachable in this environment: {e}")
        return

    try:
        cur = conn.cursor()
        tables = ["pubmed_articles", "clinical_trials", "fda_drugs"]
        exists = {}
        for t in tables:
            try:
                cur.execute(f"SELECT to_regclass('{t}') IS NOT NULL;")
                row = cur.fetchone()
                exists[t] = bool(row and row[0])
            except Exception:
                exists[t] = False
        # At least one table should exist in a properly provisioned env
        assert any(exists.values()), f"No core medical tables found: {exists}"
    finally:
        try:
            conn.close()
        except Exception:
            pass
