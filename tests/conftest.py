# tests/conftest.py
"""Pytest configuration and fixtures for audit-analyzer tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest


if TYPE_CHECKING:
    from collections.abc import Callable


# ============================================================
# Fixtures: Sample Data
# ============================================================


@pytest.fixture
def sample_audit_entry() -> dict[str, Any]:
    """Single sample audit log entry."""
    return {
        "@timestamp": 1703980800000,  # 2023-12-31 00:00:00 UTC
        "action": "repo.create",
        "actor": "test-user",
        "actor_ip": "192.168.1.100",
        "org": "test-org",
        "repo": "test-org/new-repo",
        "user": None,
        "team": None,
    }


@pytest.fixture
def sample_audit_entries() -> list[dict[str, Any]]:
    """Multiple sample audit log entries."""
    base_time = 1703980800000  # 2023-12-31 00:00:00 UTC
    hour_ms = 3600 * 1000

    return [
        {
            "@timestamp": base_time,
            "action": "repo.create",
            "actor": "admin-user",
            "actor_ip": "10.0.0.1",
            "org": "test-org",
            "repo": "test-org/repo-1",
        },
        {
            "@timestamp": base_time + hour_ms,
            "action": "org.add_member",
            "actor": "admin-user",
            "actor_ip": "10.0.0.1",
            "org": "test-org",
            "user": "new-member",
        },
        {
            "@timestamp": base_time + 2 * hour_ms,
            "action": "team.create",
            "actor": "admin-user",
            "actor_ip": "10.0.0.1",
            "org": "test-org",
            "team": "dev-team",
        },
        {
            "@timestamp": base_time + 3 * hour_ms,
            "action": "repo.destroy",
            "actor": "admin-user",
            "actor_ip": "10.0.0.1",
            "org": "test-org",
            "repo": "test-org/old-repo",
        },
        {
            "@timestamp": base_time + 4 * hour_ms,
            "action": "repo.create",
            "actor": "dev-user",
            "actor_ip": "10.0.0.2",
            "org": "test-org",
            "repo": "test-org/repo-2",
        },
    ]


@pytest.fixture
def sample_bot_entries() -> list[dict[str, Any]]:
    """Sample entries from bot accounts."""
    base_time = 1703980800000

    return [
        {
            "@timestamp": base_time,
            "action": "pull_request.opened",
            "actor": "dependabot[bot]",
            "org": "test-org",
            "repo": "test-org/repo-1",
        },
        {
            "@timestamp": base_time + 1000,
            "action": "check_run.completed",
            "actor": "github-actions[bot]",
            "org": "test-org",
            "repo": "test-org/repo-1",
        },
    ]


# ============================================================
# Fixtures: DataFrames
# ============================================================


@pytest.fixture
def polars_df(sample_audit_entries: list[dict[str, Any]]):
    """Create a Polars DataFrame from sample entries."""
    pytest.importorskip("polars")
    import polars as pl

    # Normalize the data
    normalized = []
    for entry in sample_audit_entries:
        normalized.append(
            {
                "timestamp": datetime.fromtimestamp(entry["@timestamp"] / 1000),
                "action": entry["action"],
                "actor": entry["actor"],
                "actor_ip": entry.get("actor_ip"),
                "org": entry["org"],
                "repo": entry.get("repo"),
                "user": entry.get("user"),
                "team": entry.get("team"),
            }
        )

    return pl.DataFrame(normalized)


@pytest.fixture
def pandas_df(sample_audit_entries: list[dict[str, Any]]):
    """Create a Pandas DataFrame from sample entries."""
    pytest.importorskip("pandas")
    import pandas as pd

    # Normalize the data
    normalized = []
    for entry in sample_audit_entries:
        normalized.append(
            {
                "timestamp": datetime.fromtimestamp(entry["@timestamp"] / 1000),
                "action": entry["action"],
                "actor": entry["actor"],
                "actor_ip": entry.get("actor_ip"),
                "org": entry["org"],
                "repo": entry.get("repo"),
                "user": entry.get("user"),
                "team": entry.get("team"),
            }
        )

    return pd.DataFrame(normalized)


# ============================================================
# Fixtures: Temporary Files
# ============================================================


@pytest.fixture
def sample_json_file(
    tmp_path: Path,
    sample_audit_entries: list[dict[str, Any]],
) -> Path:
    """Create a temporary JSON file with sample data."""
    file_path = tmp_path / "audit_log.json"
    with file_path.open("w") as f:
        json.dump(sample_audit_entries, f)
    return file_path


@pytest.fixture
def sample_ndjson_file(
    tmp_path: Path,
    sample_audit_entries: list[dict[str, Any]],
) -> Path:
    """Create a temporary NDJSON file with sample data."""
    file_path = tmp_path / "audit_log.ndjson"
    with file_path.open("w") as f:
        for entry in sample_audit_entries:
            f.write(json.dumps(entry) + "\n")
    return file_path


# ============================================================
# Fixtures: Large Data Generation
# ============================================================


@pytest.fixture
def generate_large_dataset() -> Callable[[int], list[dict[str, Any]]]:
    """Factory fixture to generate large datasets for testing."""

    def _generate(size: int) -> list[dict[str, Any]]:
        import random

        actions = [
            "repo.create",
            "repo.destroy",
            "org.add_member",
            "org.remove_member",
            "team.create",
            "team.add_member",
            "hook.create",
            "push",
            "pull_request.opened",
            "pull_request.merged",
        ]
        actors = [f"user-{i}" for i in range(10)]
        repos = [f"test-org/repo-{i}" for i in range(20)]

        base_time = datetime(2023, 1, 1)
        entries = []

        for i in range(size):
            timestamp = base_time + timedelta(hours=i)
            entries.append(
                {
                    "@timestamp": int(timestamp.timestamp() * 1000),
                    "action": random.choice(actions),
                    "actor": random.choice(actors),
                    "actor_ip": f"10.0.0.{random.randint(1, 255)}",
                    "org": "test-org",
                    "repo": random.choice(repos),
                }
            )

        return entries

    return _generate


# ============================================================
# Markers Configuration
# ============================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests",
    )
    config.addinivalue_line(
        "markers",
        "wasm: marks tests for WASM compatibility",
    )
