# tests/test_analyzers.py
"""Tests for analyzer modules."""

from __future__ import annotations

import pytest


class TestUserActivityAnalyzer:
    """Tests for UserActivityAnalyzer."""

    @pytest.mark.skipif(
        not pytest.importorskip("polars", reason="Polars not installed"),
        reason="Polars required",
    )
    def test_analyze_polars(self, polars_df) -> None:
        """Test analysis with Polars DataFrame."""
        from audit_analyzer.analyzers import UserActivityAnalyzer

        analyzer = UserActivityAnalyzer(polars_df, exclude_bots=False)
        results = analyzer.analyze()

        assert "user_counts" in results
        assert "top_users" in results
        assert "summary_stats" in results
        assert results["summary_stats"]["total_events"] == 5

    @pytest.mark.skipif(
        not pytest.importorskip("pandas", reason="Pandas not installed"),
        reason="Pandas required",
    )
    def test_analyze_pandas(self, pandas_df) -> None:
        """Test analysis with Pandas DataFrame."""
        from audit_analyzer.analyzers import UserActivityAnalyzer

        analyzer = UserActivityAnalyzer(pandas_df, exclude_bots=False)
        results = analyzer.analyze()

        assert "user_counts" in results
        assert "summary_stats" in results
        assert results["summary_stats"]["total_events"] == 5

    @pytest.mark.skipif(
        not pytest.importorskip("polars", reason="Polars not installed"),
        reason="Polars required",
    )
    def test_get_top_users(self, polars_df) -> None:
        """Test getting top users."""
        from audit_analyzer.analyzers import UserActivityAnalyzer

        analyzer = UserActivityAnalyzer(polars_df, exclude_bots=False)
        top_users = analyzer.get_top_users(n=5)

        assert len(top_users) <= 5

    @pytest.mark.skipif(
        not pytest.importorskip("polars", reason="Polars not installed"),
        reason="Polars required",
    )
    def test_get_user_actions(self, polars_df) -> None:
        """Test getting actions for specific user."""
        from audit_analyzer.analyzers import UserActivityAnalyzer

        analyzer = UserActivityAnalyzer(polars_df, exclude_bots=False)
        actions = analyzer.get_user_actions("admin-user")

        assert len(actions) > 0

    def test_missing_column_error(self) -> None:
        """Test error when required column is missing."""
        pytest.importorskip("polars")
        import polars as pl

        from audit_analyzer.analyzers import UserActivityAnalyzer

        df = pl.DataFrame({"col1": [1, 2, 3]})

        with pytest.raises(ValueError, match="Missing required columns"):
            UserActivityAnalyzer(df)


class TestTimeSeriesAnalyzer:
    """Tests for TimeSeriesAnalyzer."""

    @pytest.mark.skipif(
        not pytest.importorskip("polars", reason="Polars not installed"),
        reason="Polars required",
    )
    def test_analyze_polars(self, polars_df) -> None:
        """Test analysis with Polars DataFrame."""
        from audit_analyzer.analyzers import TimeSeriesAnalyzer

        analyzer = TimeSeriesAnalyzer(polars_df)
        results = analyzer.analyze()

        assert "hourly_distribution" in results
        assert "daily_counts" in results
        assert "weekly_pattern" in results
        assert "summary_stats" in results

    @pytest.mark.skipif(
        not pytest.importorskip("polars", reason="Polars not installed"),
        reason="Polars required",
    )
    def test_get_hourly_distribution(self, polars_df) -> None:
        """Test hourly distribution."""
        from audit_analyzer.analyzers import TimeSeriesAnalyzer

        analyzer = TimeSeriesAnalyzer(polars_df)
        hourly = analyzer.get_hourly_distribution()

        assert len(hourly) > 0

    @pytest.mark.skipif(
        not pytest.importorskip("polars", reason="Polars not installed"),
        reason="Polars required",
    )
    def test_get_time_range(self, polars_df) -> None:
        """Test time range extraction."""
        from audit_analyzer.analyzers import TimeSeriesAnalyzer

        analyzer = TimeSeriesAnalyzer(polars_df)
        time_range = analyzer.get_time_range()

        assert time_range is not None
        min_ts, max_ts = time_range
        assert min_ts < max_ts


class TestAnomalyDetector:
    """Tests for AnomalyDetector."""

    @pytest.mark.skipif(
        not pytest.importorskip("polars", reason="Polars not installed"),
        reason="Polars required",
    )
    def test_analyze_polars(self, polars_df) -> None:
        """Test analysis with Polars DataFrame."""
        from audit_analyzer.analyzers import AnomalyDetector

        analyzer = AnomalyDetector(polars_df)
        results = analyzer.analyze()

        assert "anomalies" in results
        assert "risk_summary" in results
        assert "total_anomalies" in results

    @pytest.mark.skipif(
        not pytest.importorskip("polars", reason="Polars not installed"),
        reason="Polars required",
    )
    def test_detect_dangerous_actions(self, polars_df) -> None:
        """Test dangerous action detection."""
        from audit_analyzer.analyzers import AnomalyDetector

        analyzer = AnomalyDetector(polars_df)
        anomalies = analyzer.detect_dangerous_actions()

        # Sample data has repo.destroy which is dangerous
        dangerous_actions = [
            a for a in anomalies if a.anomaly_type == "dangerous_action"
        ]
        assert len(dangerous_actions) > 0

    @pytest.mark.skipif(
        not pytest.importorskip("polars", reason="Polars not installed"),
        reason="Polars required",
    )
    def test_anomaly_risk_levels(self, polars_df) -> None:
        """Test that anomalies have proper risk levels."""
        from audit_analyzer.analyzers import AnomalyDetector
        from audit_analyzer.analyzers.anomaly import RiskLevel

        analyzer = AnomalyDetector(polars_df)
        anomalies = analyzer.detect_dangerous_actions()

        for anomaly in anomalies:
            assert anomaly.risk_level in RiskLevel
