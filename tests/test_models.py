# tests/test_models.py
"""Tests for Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from audit_analyzer.models import AuditLogEntry, AuditLogBatch


class TestAuditLogEntry:
    """Tests for AuditLogEntry model."""

    def test_create_from_dict(self, sample_audit_entry: dict[str, Any]) -> None:
        """Test creating entry from dictionary."""
        entry = AuditLogEntry.model_validate(sample_audit_entry)

        assert entry.action == "repo.create"
        assert entry.actor == "test-user"
        assert entry.org == "test-org"
        assert entry.repo == "test-org/new-repo"

    def test_timestamp_from_milliseconds(self) -> None:
        """Test parsing timestamp from milliseconds."""
        data = {
            "@timestamp": 1703980800000,
            "action": "repo.create",
            "actor": "test-user",
            "org": "test-org",
        }
        entry = AuditLogEntry.model_validate(data)

        # 2023-12-31 00:00:00 UTC
        assert entry.timestamp.year == 2023
        assert entry.timestamp.month == 12
        assert entry.timestamp.day == 31

    def test_timestamp_from_seconds(self) -> None:
        """Test parsing timestamp from seconds."""
        data = {
            "@timestamp": 1703980800,
            "action": "repo.create",
            "actor": "test-user",
            "org": "test-org",
        }
        entry = AuditLogEntry.model_validate(data)

        assert entry.timestamp.year == 2023

    def test_timestamp_from_iso_string(self) -> None:
        """Test parsing timestamp from ISO string."""
        data = {
            "@timestamp": "2023-12-31T00:00:00Z",
            "action": "repo.create",
            "actor": "test-user",
            "org": "test-org",
        }
        entry = AuditLogEntry.model_validate(data)

        assert entry.timestamp.year == 2023
        assert entry.timestamp.month == 12
        assert entry.timestamp.day == 31

    def test_action_category(self, sample_audit_entry: dict[str, Any]) -> None:
        """Test action_category property."""
        entry = AuditLogEntry.model_validate(sample_audit_entry)

        assert entry.action_category == "repo"

    def test_action_type(self, sample_audit_entry: dict[str, Any]) -> None:
        """Test action_type property."""
        entry = AuditLogEntry.model_validate(sample_audit_entry)

        assert entry.action_type == "create"

    def test_is_dangerous_action_true(self) -> None:
        """Test is_dangerous_action for dangerous actions."""
        data = {
            "@timestamp": 1703980800000,
            "action": "repo.destroy",
            "actor": "test-user",
            "org": "test-org",
        }
        entry = AuditLogEntry.model_validate(data)

        assert entry.is_dangerous_action() is True

    def test_is_dangerous_action_false(self, sample_audit_entry: dict[str, Any]) -> None:
        """Test is_dangerous_action for safe actions."""
        entry = AuditLogEntry.model_validate(sample_audit_entry)

        assert entry.is_dangerous_action() is False

    def test_extra_fields_captured(self) -> None:
        """Test that unknown fields are captured in data dict."""
        data = {
            "@timestamp": 1703980800000,
            "action": "repo.create",
            "actor": "test-user",
            "org": "test-org",
            "custom_field": "custom_value",
            "another_field": 123,
        }
        entry = AuditLogEntry.model_validate(data)

        assert entry.data["custom_field"] == "custom_value"
        assert entry.data["another_field"] == 123

    def test_immutable(self, sample_audit_entry: dict[str, Any]) -> None:
        """Test that entries are immutable (frozen)."""
        entry = AuditLogEntry.model_validate(sample_audit_entry)

        with pytest.raises(Exception):  # ValidationError for frozen model
            entry.action = "modified"  # type: ignore

    def test_validation_error_missing_required(self) -> None:
        """Test validation error for missing required fields."""
        data = {
            "@timestamp": 1703980800000,
            "action": "repo.create",
            # missing actor and org
        }

        with pytest.raises(Exception):
            AuditLogEntry.model_validate(data)


class TestAuditLogBatch:
    """Tests for AuditLogBatch model."""

    def test_from_json_lines(
        self,
        sample_audit_entries: list[dict[str, Any]],
    ) -> None:
        """Test creating batch from JSON lines."""
        batch = AuditLogBatch.from_json_lines(sample_audit_entries)

        assert len(batch) == len(sample_audit_entries)

    def test_iteration(self, sample_audit_entries: list[dict[str, Any]]) -> None:
        """Test iterating over batch."""
        batch = AuditLogBatch.from_json_lines(sample_audit_entries)

        entries = list(batch)
        assert len(entries) == len(sample_audit_entries)
        assert all(isinstance(e, AuditLogEntry) for e in entries)

    def test_time_range(self, sample_audit_entries: list[dict[str, Any]]) -> None:
        """Test time_range property."""
        batch = AuditLogBatch.from_json_lines(sample_audit_entries)

        time_range = batch.time_range
        assert time_range is not None

        min_ts, max_ts = time_range
        assert min_ts < max_ts

    def test_time_range_empty(self) -> None:
        """Test time_range for empty batch."""
        batch = AuditLogBatch(entries=[])

        assert batch.time_range is None
