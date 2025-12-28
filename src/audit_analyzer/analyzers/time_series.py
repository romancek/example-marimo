# src/audit_analyzer/analyzers/time_series.py
"""Time series analysis for audit logs.

Analyzes temporal patterns including:
- Activity over time (hourly, daily, weekly, monthly)
- Trend detection
- Seasonality patterns
- Peak activity periods
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from audit_analyzer.analyzers.base import BaseAnalyzer
from audit_analyzer.utils.constants import BUSINESS_HOURS, WEEKEND_DAYS

if TYPE_CHECKING:
    import pandas as pd
    import polars as pl


TimeGranularity = Literal["hour", "day", "week", "month"]


class TimeSeriesAnalyzer(BaseAnalyzer):
    """Analyzer for temporal patterns in audit logs."""

    def __init__(
        self,
        df: Any,
        *,
        timestamp_column: str = "timestamp",
        action_column: str = "action",
    ) -> None:
        """Initialize the time series analyzer.

        Args:
            df: Input DataFrame with audit log data
            timestamp_column: Name of the timestamp column
            action_column: Name of the action column
        """
        self._timestamp_col = timestamp_column
        self._action_col = action_column
        super().__init__(df)

    def _validate_schema(self) -> None:
        """Ensure required columns exist."""
        required = {self._timestamp_col}
        columns = set(self._get_column_names())
        missing = required - columns
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def analyze(self) -> dict[str, Any]:
        """Run comprehensive time series analysis.

        Returns:
            Dictionary with analysis results including:
            - hourly_distribution: Activity by hour of day
            - daily_counts: Activity per day
            - weekly_pattern: Activity by day of week
            - monthly_trend: Activity per month
            - off_hours_activity: Activity outside business hours
        """
        if self._is_polars():
            return self._analyze_polars()
        else:
            return self._analyze_pandas()

    def get_activity_by_granularity(
        self,
        granularity: TimeGranularity = "day",
    ) -> Any:
        """Get activity counts at specified time granularity.

        Args:
            granularity: Time granularity ("hour", "day", "week", "month")

        Returns:
            DataFrame with time period and counts
        """
        if self._is_polars():
            return self._aggregate_polars(granularity)
        else:
            return self._aggregate_pandas(granularity)

    def get_hourly_distribution(self) -> Any:
        """Get activity distribution by hour of day (0-23).

        Returns:
            DataFrame with hour and activity count
        """
        if self._is_polars():
            import polars as pl

            return (
                self._df.with_columns(
                    pl.col(self._timestamp_col).dt.hour().alias("hour")
                )
                .group_by("hour")
                .agg(pl.len().alias("count"))
                .sort("hour")
            )
        else:
            df = self._df.copy()
            df["hour"] = df[self._timestamp_col].dt.hour
            return df.groupby("hour").size().reset_index(name="count").sort_values("hour")

    def get_weekday_distribution(self) -> Any:
        """Get activity distribution by day of week.

        Returns:
            DataFrame with weekday (0=Monday, 6=Sunday) and activity count
        """
        if self._is_polars():
            import polars as pl

            return (
                self._df.with_columns(
                    pl.col(self._timestamp_col).dt.weekday().alias("weekday")
                )
                .group_by("weekday")
                .agg(pl.len().alias("count"))
                .sort("weekday")
            )
        else:
            df = self._df.copy()
            df["weekday"] = df[self._timestamp_col].dt.weekday
            return (
                df.groupby("weekday").size().reset_index(name="count").sort_values("weekday")
            )

    def get_off_hours_activity(self) -> Any:
        """Get activity that occurred outside business hours.

        Returns:
            DataFrame with off-hours events
        """
        start_hour = BUSINESS_HOURS["start_hour"]
        end_hour = BUSINESS_HOURS["end_hour"]

        if self._is_polars():
            import polars as pl

            return self._df.filter(
                (pl.col(self._timestamp_col).dt.hour() < start_hour)
                | (pl.col(self._timestamp_col).dt.hour() >= end_hour)
                | (pl.col(self._timestamp_col).dt.weekday().is_in(list(WEEKEND_DAYS)))
            )
        else:
            df = self._df.copy()
            hour = df[self._timestamp_col].dt.hour
            weekday = df[self._timestamp_col].dt.weekday
            return df[
                (hour < start_hour) | (hour >= end_hour) | (weekday.isin(list(WEEKEND_DAYS)))
            ]

    def get_time_range(self) -> tuple[datetime, datetime] | None:
        """Get the time range of the data.

        Returns:
            Tuple of (min_timestamp, max_timestamp) or None if empty
        """
        if len(self._df) == 0:
            return None

        if self._is_polars():
            min_ts = self._df.select(self._timestamp_col).min().item()
            max_ts = self._df.select(self._timestamp_col).max().item()
        else:
            min_ts = self._df[self._timestamp_col].min()
            max_ts = self._df[self._timestamp_col].max()

        return (min_ts, max_ts)

    def _aggregate_polars(self, granularity: TimeGranularity) -> Any:
        """Polars aggregation by time granularity."""
        import polars as pl

        if granularity == "hour":
            return (
                self._df.group_by_dynamic(self._timestamp_col, every="1h")
                .agg(pl.len().alias("count"))
                .sort(self._timestamp_col)
            )
        elif granularity == "day":
            return (
                self._df.with_columns(
                    pl.col(self._timestamp_col).dt.date().alias("date")
                )
                .group_by("date")
                .agg(pl.len().alias("count"))
                .sort("date")
            )
        elif granularity == "week":
            return (
                self._df.group_by_dynamic(self._timestamp_col, every="1w")
                .agg(pl.len().alias("count"))
                .sort(self._timestamp_col)
            )
        elif granularity == "month":
            return (
                self._df.with_columns(
                    pl.col(self._timestamp_col).dt.month().alias("month"),
                    pl.col(self._timestamp_col).dt.year().alias("year"),
                )
                .group_by(["year", "month"])
                .agg(pl.len().alias("count"))
                .sort(["year", "month"])
            )
        else:
            raise ValueError(f"Unknown granularity: {granularity}")

    def _aggregate_pandas(self, granularity: TimeGranularity) -> Any:
        """Pandas aggregation by time granularity."""
        df = self._df.copy()

        if granularity == "hour":
            df["period"] = df[self._timestamp_col].dt.floor("h")
        elif granularity == "day":
            df["period"] = df[self._timestamp_col].dt.date
        elif granularity == "week":
            df["period"] = df[self._timestamp_col].dt.to_period("W").dt.start_time
        elif granularity == "month":
            df["period"] = df[self._timestamp_col].dt.to_period("M").dt.start_time
        else:
            raise ValueError(f"Unknown granularity: {granularity}")

        return df.groupby("period").size().reset_index(name="count").sort_values("period")

    def _analyze_polars(self) -> dict[str, Any]:
        """Polars-specific analysis implementation."""
        import polars as pl

        # Hourly distribution
        hourly = (
            self._df.with_columns(pl.col(self._timestamp_col).dt.hour().alias("hour"))
            .group_by("hour")
            .agg(pl.len().alias("count"))
            .sort("hour")
        )

        # Daily counts
        daily = (
            self._df.with_columns(pl.col(self._timestamp_col).dt.date().alias("date"))
            .group_by("date")
            .agg(pl.len().alias("count"))
            .sort("date")
        )

        # Weekly pattern
        weekly = (
            self._df.with_columns(
                pl.col(self._timestamp_col).dt.weekday().alias("weekday")
            )
            .group_by("weekday")
            .agg(pl.len().alias("count"))
            .sort("weekday")
        )

        # Off-hours activity count
        off_hours = self.get_off_hours_activity()
        off_hours_pct = len(off_hours) / len(self._df) * 100 if len(self._df) > 0 else 0

        # Time range
        time_range = self.get_time_range()

        return {
            "hourly_distribution": hourly,
            "daily_counts": daily,
            "weekly_pattern": weekly,
            "off_hours_activity": off_hours,
            "summary_stats": {
                "total_events": len(self._df),
                "off_hours_percentage": round(off_hours_pct, 2),
                "time_range": time_range,
                "peak_hour": hourly.filter(
                    pl.col("count") == pl.col("count").max()
                )["hour"][0]
                if len(hourly) > 0
                else None,
            },
        }

    def _analyze_pandas(self) -> dict[str, Any]:
        """Pandas-specific analysis implementation."""
        df = self._df.copy()

        # Hourly distribution
        df["hour"] = df[self._timestamp_col].dt.hour
        hourly = df.groupby("hour").size().reset_index(name="count").sort_values("hour")

        # Daily counts
        df["date"] = df[self._timestamp_col].dt.date
        daily = df.groupby("date").size().reset_index(name="count").sort_values("date")

        # Weekly pattern
        df["weekday"] = df[self._timestamp_col].dt.weekday
        weekly = (
            df.groupby("weekday").size().reset_index(name="count").sort_values("weekday")
        )

        # Off-hours activity
        off_hours = self.get_off_hours_activity()
        off_hours_pct = len(off_hours) / len(self._df) * 100 if len(self._df) > 0 else 0

        # Time range
        time_range = self.get_time_range()

        return {
            "hourly_distribution": hourly,
            "daily_counts": daily,
            "weekly_pattern": weekly,
            "off_hours_activity": off_hours,
            "summary_stats": {
                "total_events": len(self._df),
                "off_hours_percentage": round(off_hours_pct, 2),
                "time_range": time_range,
                "peak_hour": hourly.loc[hourly["count"].idxmax(), "hour"]
                if len(hourly) > 0
                else None,
            },
        }
