# tests/test_loader.py
"""Tests for data loading utilities."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestLoadAuditLog:
    """Tests for load_audit_log function."""

    def test_load_json_file(self, sample_json_file: Path) -> None:
        """Test loading JSON array file."""
        from audit_analyzer.loader import load_audit_log

        df = load_audit_log(sample_json_file, validate=False)

        assert len(df) == 5

    def test_load_ndjson_file(self, sample_ndjson_file: Path) -> None:
        """Test loading NDJSON file."""
        from audit_analyzer.loader import load_audit_log

        df = load_audit_log(sample_ndjson_file, validate=False)

        assert len(df) == 5

    def test_load_with_validation(self, sample_json_file: Path) -> None:
        """Test loading with Pydantic validation."""
        from audit_analyzer.loader import load_audit_log

        df = load_audit_log(sample_json_file, validate=True)

        assert len(df) == 5

    def test_load_nonexistent_file(self) -> None:
        """Test error handling for nonexistent file."""
        from audit_analyzer.loader import load_audit_log

        with pytest.raises(FileNotFoundError):
            load_audit_log("/nonexistent/path/file.json")

    def test_load_unsupported_format(self, tmp_path: Path) -> None:
        """Test error handling for unsupported file format."""
        from audit_analyzer.loader import load_audit_log

        unsupported_file = tmp_path / "data.xml"
        unsupported_file.write_text("<data></data>")

        with pytest.raises(ValueError, match="Unsupported file format"):
            load_audit_log(unsupported_file)

    @pytest.mark.skipif(
        not pytest.importorskip("polars", reason="Polars not installed"),
        reason="Polars required",
    )
    def test_load_with_polars_backend(self, sample_json_file: Path) -> None:
        """Test loading with explicit Polars backend."""
        from audit_analyzer.loader import load_audit_log

        df = load_audit_log(sample_json_file, backend="polars")

        assert type(df).__module__.startswith("polars")

    @pytest.mark.skipif(
        not pytest.importorskip("pandas", reason="Pandas not installed"),
        reason="Pandas required",
    )
    def test_load_with_pandas_backend(self, sample_json_file: Path) -> None:
        """Test loading with explicit Pandas backend."""
        from audit_analyzer.loader import load_audit_log

        df = load_audit_log(sample_json_file, backend="pandas")

        assert type(df).__module__.startswith("pandas")


class TestStreamAuditLog:
    """Tests for stream_audit_log function."""

    def test_stream_batches(self, sample_ndjson_file: Path) -> None:
        """Test streaming in batches."""
        from audit_analyzer.loader import stream_audit_log

        batches = list(stream_audit_log(sample_ndjson_file, batch_size=2))

        # 5 entries with batch_size=2 should give 3 batches (2, 2, 1)
        assert len(batches) == 3
        assert len(batches[0]) == 2
        assert len(batches[1]) == 2
        assert len(batches[2]) == 1

    def test_stream_with_validation(self, sample_ndjson_file: Path) -> None:
        """Test streaming with Pydantic validation."""
        from audit_analyzer.loader import stream_audit_log

        batches = list(stream_audit_log(sample_ndjson_file, validate=True))

        total_entries = sum(len(batch) for batch in batches)
        assert total_entries == 5


class TestLoadAuditLogLazy:
    """Tests for lazy loading functions."""

    @pytest.mark.skipif(
        not pytest.importorskip("duckdb", reason="DuckDB not installed"),
        reason="DuckDB required",
    )
    def test_load_lazy_with_duckdb(self, sample_json_file: Path) -> None:
        """Test lazy loading with DuckDB."""
        from audit_analyzer.loader import load_audit_log_lazy

        result = load_audit_log_lazy(sample_json_file, use_duckdb=True)

        # DuckDB returns a relation that can be queried
        assert result is not None

    @pytest.mark.skipif(
        not pytest.importorskip("polars", reason="Polars not installed"),
        reason="Polars required",
    )
    def test_load_lazy_with_polars(self, sample_ndjson_file: Path) -> None:
        """Test lazy loading with Polars LazyFrame."""
        from audit_analyzer.loader import load_audit_log_lazy

        result = load_audit_log_lazy(sample_ndjson_file, use_duckdb=False)

        # Should return a LazyFrame
        assert hasattr(result, "collect")
