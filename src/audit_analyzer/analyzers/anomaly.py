# src/audit_analyzer/analyzers/anomaly.py
"""Anomaly detection for audit logs.

Detects suspicious patterns including:
- Off-hours activity
- Bulk operations
- Unusual IP addresses
- Dangerous actions
- Rate anomalies
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from audit_analyzer.analyzers.base import BaseAnalyzer
from audit_analyzer.utils.constants import (
    BULK_OPERATION_THRESHOLDS,
    BUSINESS_HOURS,
    DANGEROUS_ACTIONS,
    HIGH_RISK_ACTIONS,
    WEEKEND_DAYS,
)

if TYPE_CHECKING:
    import pandas as pd
    import polars as pl


class RiskLevel(StrEnum):
    """Risk level for detected anomalies."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True)
class Anomaly:
    """Represents a detected anomaly.

    Attributes:
        anomaly_type: Type of anomaly detected
        risk_level: Risk level assessment
        description: Human-readable description
        timestamp: When the anomaly occurred
        actor: User who triggered the anomaly (if applicable)
        details: Additional context
    """

    anomaly_type: str
    risk_level: RiskLevel
    description: str
    timestamp: datetime | None = None
    actor: str | None = None
    details: dict[str, Any] | None = None


class AnomalyDetector(BaseAnalyzer):
    """Detector for suspicious patterns in audit logs."""

    def __init__(
        self,
        df: Any,
        *,
        timestamp_column: str = "timestamp",
        action_column: str = "action",
        actor_column: str = "actor",
        ip_column: str = "actor_ip",
    ) -> None:
        """Initialize the anomaly detector.

        Args:
            df: Input DataFrame with audit log data
            timestamp_column: Name of the timestamp column
            action_column: Name of the action column
            actor_column: Name of the actor/user column
            ip_column: Name of the IP address column
        """
        self._timestamp_col = timestamp_column
        self._action_col = action_column
        self._actor_col = actor_column
        self._ip_col = ip_column
        super().__init__(df)

    def _validate_schema(self) -> None:
        """Ensure required columns exist."""
        required = {self._timestamp_col, self._action_col, self._actor_col}
        columns = set(self._get_column_names())
        missing = required - columns
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def analyze(self) -> dict[str, Any]:
        """Run comprehensive anomaly detection.

        Returns:
            Dictionary with detected anomalies including:
            - anomalies: List of Anomaly objects
            - dangerous_actions: Events with dangerous actions
            - off_hours_activity: Events outside business hours
            - bulk_operations: Potential bulk operation patterns
            - summary: Overall risk assessment
        """
        anomalies: list[Anomaly] = []

        # Detect various anomaly types
        dangerous = self.detect_dangerous_actions()
        off_hours = self.detect_off_hours_activity()
        bulk_ops = self.detect_bulk_operations()

        # Aggregate anomalies
        anomalies.extend(dangerous)
        anomalies.extend(off_hours)
        anomalies.extend(bulk_ops)

        # Sort by risk level
        risk_order = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.HIGH: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 3,
            RiskLevel.INFO: 4,
        }
        anomalies.sort(key=lambda a: (risk_order[a.risk_level], a.timestamp or datetime.min))

        # Calculate summary
        risk_counts = {level: 0 for level in RiskLevel}
        for anomaly in anomalies:
            risk_counts[anomaly.risk_level] += 1

        return {
            "anomalies": anomalies,
            "risk_summary": risk_counts,
            "total_anomalies": len(anomalies),
            "critical_count": risk_counts[RiskLevel.CRITICAL],
            "high_count": risk_counts[RiskLevel.HIGH],
        }

    def detect_dangerous_actions(self) -> list[Anomaly]:
        """Detect events with dangerous action types.

        Returns:
            List of Anomaly objects for dangerous actions
        """
        anomalies = []

        if self._is_polars():
            import polars as pl

            dangerous_df = self._df.filter(
                pl.col(self._action_col).is_in(list(DANGEROUS_ACTIONS))
            )
            high_risk_df = self._df.filter(
                pl.col(self._action_col).is_in(list(HIGH_RISK_ACTIONS))
            )

            for row in dangerous_df.iter_rows(named=True):
                anomalies.append(
                    Anomaly(
                        anomaly_type="dangerous_action",
                        risk_level=RiskLevel.CRITICAL,
                        description=f"Dangerous action: {row[self._action_col]}",
                        timestamp=row[self._timestamp_col],
                        actor=row[self._actor_col],
                        details={"action": row[self._action_col]},
                    )
                )

            for row in high_risk_df.iter_rows(named=True):
                anomalies.append(
                    Anomaly(
                        anomaly_type="high_risk_action",
                        risk_level=RiskLevel.HIGH,
                        description=f"High-risk action: {row[self._action_col]}",
                        timestamp=row[self._timestamp_col],
                        actor=row[self._actor_col],
                        details={"action": row[self._action_col]},
                    )
                )
        else:
            dangerous_mask = self._df[self._action_col].isin(list(DANGEROUS_ACTIONS))
            high_risk_mask = self._df[self._action_col].isin(list(HIGH_RISK_ACTIONS))

            for _, row in self._df[dangerous_mask].iterrows():
                anomalies.append(
                    Anomaly(
                        anomaly_type="dangerous_action",
                        risk_level=RiskLevel.CRITICAL,
                        description=f"Dangerous action: {row[self._action_col]}",
                        timestamp=row[self._timestamp_col],
                        actor=row[self._actor_col],
                        details={"action": row[self._action_col]},
                    )
                )

            for _, row in self._df[high_risk_mask].iterrows():
                anomalies.append(
                    Anomaly(
                        anomaly_type="high_risk_action",
                        risk_level=RiskLevel.HIGH,
                        description=f"High-risk action: {row[self._action_col]}",
                        timestamp=row[self._timestamp_col],
                        actor=row[self._actor_col],
                        details={"action": row[self._action_col]},
                    )
                )

        return anomalies

    def detect_off_hours_activity(self) -> list[Anomaly]:
        """Detect activity outside business hours.

        Returns:
            List of Anomaly objects for off-hours activity
        """
        anomalies = []
        start_hour = BUSINESS_HOURS["start_hour"]
        end_hour = BUSINESS_HOURS["end_hour"]

        if self._is_polars():
            import polars as pl

            off_hours_df = self._df.filter(
                (pl.col(self._timestamp_col).dt.hour() < start_hour)
                | (pl.col(self._timestamp_col).dt.hour() >= end_hour)
                | (pl.col(self._timestamp_col).dt.weekday().is_in(list(WEEKEND_DAYS)))
            )

            # Group by actor to avoid too many individual anomalies
            actor_counts = (
                off_hours_df.group_by(self._actor_col)
                .agg(pl.len().alias("count"))
                .filter(pl.col("count") > 5)  # Only flag if > 5 off-hours events
            )

            for row in actor_counts.iter_rows(named=True):
                anomalies.append(
                    Anomaly(
                        anomaly_type="off_hours_activity",
                        risk_level=RiskLevel.MEDIUM,
                        description=f"User {row[self._actor_col]} has {row['count']} off-hours events",
                        actor=row[self._actor_col],
                        details={"event_count": row["count"]},
                    )
                )
        else:
            df = self._df.copy()
            hour = df[self._timestamp_col].dt.hour
            weekday = df[self._timestamp_col].dt.weekday
            off_hours_mask = (
                (hour < start_hour) | (hour >= end_hour) | weekday.isin(list(WEEKEND_DAYS))
            )

            actor_counts = (
                df[off_hours_mask].groupby(self._actor_col).size().reset_index(name="count")
            )
            actor_counts = actor_counts[actor_counts["count"] > 5]

            for _, row in actor_counts.iterrows():
                anomalies.append(
                    Anomaly(
                        anomaly_type="off_hours_activity",
                        risk_level=RiskLevel.MEDIUM,
                        description=f"User {row[self._actor_col]} has {row['count']} off-hours events",
                        actor=row[self._actor_col],
                        details={"event_count": row["count"]},
                    )
                )

        return anomalies

    def detect_bulk_operations(
        self,
        window_minutes: int = 60,
    ) -> list[Anomaly]:
        """Detect potential bulk operations.

        Args:
            window_minutes: Time window to check for bulk operations

        Returns:
            List of Anomaly objects for bulk operations
        """
        anomalies = []
        default_threshold = BULK_OPERATION_THRESHOLDS["default"]

        if self._is_polars():
            import polars as pl

            # Group by actor, action, and time window
            df = self._df.with_columns(
                (
                    pl.col(self._timestamp_col).dt.truncate(f"{window_minutes}m")
                ).alias("time_window")
            )

            bulk_df = (
                df.group_by([self._actor_col, self._action_col, "time_window"])
                .agg(pl.len().alias("count"))
                .filter(pl.col("count") > default_threshold)
            )

            for row in bulk_df.iter_rows(named=True):
                action = row[self._action_col]
                threshold = BULK_OPERATION_THRESHOLDS.get(action, default_threshold)

                if row["count"] > threshold:
                    anomalies.append(
                        Anomaly(
                            anomaly_type="bulk_operation",
                            risk_level=RiskLevel.HIGH,
                            description=f"Bulk operation detected: {row['count']} '{action}' events by {row[self._actor_col]}",
                            timestamp=row["time_window"],
                            actor=row[self._actor_col],
                            details={
                                "action": action,
                                "count": row["count"],
                                "threshold": threshold,
                            },
                        )
                    )
        else:
            df = self._df.copy()
            df["time_window"] = df[self._timestamp_col].dt.floor(f"{window_minutes}min")

            bulk_df = (
                df.groupby([self._actor_col, self._action_col, "time_window"])
                .size()
                .reset_index(name="count")
            )
            bulk_df = bulk_df[bulk_df["count"] > default_threshold]

            for _, row in bulk_df.iterrows():
                action = row[self._action_col]
                threshold = BULK_OPERATION_THRESHOLDS.get(action, default_threshold)

                if row["count"] > threshold:
                    anomalies.append(
                        Anomaly(
                            anomaly_type="bulk_operation",
                            risk_level=RiskLevel.HIGH,
                            description=f"Bulk operation detected: {row['count']} '{action}' events by {row[self._actor_col]}",
                            timestamp=row["time_window"],
                            actor=row[self._actor_col],
                            details={
                                "action": action,
                                "count": row["count"],
                                "threshold": threshold,
                            },
                        )
                    )

        return anomalies

    def detect_unusual_ips(self, known_ips: set[str] | None = None) -> list[Anomaly]:
        """Detect activity from unusual IP addresses.

        Args:
            known_ips: Set of known/allowed IP addresses

        Returns:
            List of Anomaly objects for unusual IPs
        """
        if self._ip_col not in self._get_column_names():
            return []

        anomalies = []
        known_ips = known_ips or set()

        if self._is_polars():
            import polars as pl

            # Get unique IPs per actor
            ip_df = (
                self._df.filter(pl.col(self._ip_col).is_not_null())
                .group_by([self._actor_col, self._ip_col])
                .agg(pl.len().alias("count"))
            )

            # Flag actors with multiple IPs
            multi_ip_actors = (
                ip_df.group_by(self._actor_col)
                .agg(pl.n_unique(self._ip_col).alias("unique_ips"))
                .filter(pl.col("unique_ips") > 3)
            )

            for row in multi_ip_actors.iter_rows(named=True):
                anomalies.append(
                    Anomaly(
                        anomaly_type="multiple_ips",
                        risk_level=RiskLevel.MEDIUM,
                        description=f"User {row[self._actor_col]} accessed from {row['unique_ips']} different IPs",
                        actor=row[self._actor_col],
                        details={"unique_ips": row["unique_ips"]},
                    )
                )
        else:
            df = self._df[self._df[self._ip_col].notna()].copy()

            # Get unique IPs per actor
            ip_counts = (
                df.groupby(self._actor_col)[self._ip_col].nunique().reset_index(name="unique_ips")
            )
            ip_counts = ip_counts[ip_counts["unique_ips"] > 3]

            for _, row in ip_counts.iterrows():
                anomalies.append(
                    Anomaly(
                        anomaly_type="multiple_ips",
                        risk_level=RiskLevel.MEDIUM,
                        description=f"User {row[self._actor_col]} accessed from {row['unique_ips']} different IPs",
                        actor=row[self._actor_col],
                        details={"unique_ips": row["unique_ips"]},
                    )
                )

        return anomalies
