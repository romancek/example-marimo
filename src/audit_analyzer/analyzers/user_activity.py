# src/audit_analyzer/analyzers/user_activity.py
"""User activity analysis for audit logs.

Analyzes per-user patterns including:
- Activity counts and distributions
- Most active users
- Action type breakdown per user
- User collaboration patterns
"""

from __future__ import annotations

from typing import Any

from audit_analyzer.analyzers.base import BaseAnalyzer
from audit_analyzer.utils.constants import KNOWN_BOT_PATTERNS


class UserActivityAnalyzer(BaseAnalyzer):
    """Analyzer for user-level activity patterns."""

    def __init__(
        self,
        df: Any,
        *,
        actor_column: str = "actor",
        action_column: str = "action",
        timestamp_column: str = "timestamp",
        exclude_bots: bool = True,
    ) -> None:
        """Initialize the user activity analyzer.

        Args:
            df: Input DataFrame with audit log data
            actor_column: Name of the column containing user/actor info
            action_column: Name of the column containing action types
            timestamp_column: Name of the timestamp column
            exclude_bots: Whether to exclude known bot accounts
        """
        self._actor_col = actor_column
        self._action_col = action_column
        self._timestamp_col = timestamp_column
        self._exclude_bots = exclude_bots
        super().__init__(df)

    def _validate_schema(self) -> None:
        """Ensure required columns exist."""
        required = {self._actor_col, self._action_col, self._timestamp_col}
        columns = set(self._get_column_names())
        missing = required - columns
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def analyze(self) -> dict[str, Any]:
        """Run comprehensive user activity analysis.

        Returns:
            Dictionary with analysis results including:
            - user_counts: Activity count per user
            - top_users: Most active users
            - action_breakdown: Actions per user
            - summary_stats: Overall statistics
        """
        df = self._filter_bots() if self._exclude_bots else self._df

        if self._is_polars():
            return self._analyze_polars(df)
        else:
            return self._analyze_pandas(df)

    def get_top_users(self, n: int = 10) -> Any:
        """Get the top N most active users.

        Args:
            n: Number of top users to return

        Returns:
            DataFrame with top users and their activity counts
        """
        df = self._filter_bots() if self._exclude_bots else self._df

        if self._is_polars():
            import polars as pl

            return (
                df.group_by(self._actor_col)
                .agg(pl.len().alias("activity_count"))
                .sort("activity_count", descending=True)
                .head(n)
            )
        else:
            return (
                df.groupby(self._actor_col)
                .size()
                .reset_index(name="activity_count")
                .nlargest(n, "activity_count")
            )

    def get_user_actions(self, username: str) -> Any:
        """Get action breakdown for a specific user.

        Args:
            username: The username to analyze

        Returns:
            DataFrame with action types and counts for the user
        """
        if self._is_polars():
            import polars as pl

            user_df = self._df.filter(pl.col(self._actor_col) == username)
            return (
                user_df.group_by(self._action_col)
                .agg(pl.len().alias("count"))
                .sort("count", descending=True)
            )
        else:
            user_df = self._df[self._df[self._actor_col] == username]
            return (
                user_df.groupby(self._action_col)
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
            )

    def get_activity_timeline(self, username: str | None = None) -> Any:
        """Get activity timeline, optionally for a specific user.

        Args:
            username: Optional username to filter by

        Returns:
            DataFrame with daily activity counts
        """
        df = self._df
        if username:
            if self._is_polars():
                import polars as pl

                df = df.filter(pl.col(self._actor_col) == username)
            else:
                df = df[df[self._actor_col] == username]

        if self._is_polars():
            import polars as pl

            return (
                df.with_columns(pl.col(self._timestamp_col).dt.date().alias("date"))
                .group_by("date")
                .agg(pl.len().alias("count"))
                .sort("date")
            )
        else:
            df = df.copy()
            df["date"] = df[self._timestamp_col].dt.date
            return (
                df.groupby("date").size().reset_index(name="count").sort_values("date")
            )

    def _filter_bots(self) -> Any:
        """Filter out known bot accounts."""
        if self._is_polars():
            import polars as pl

            # Build filter for bot patterns
            conditions = []
            for pattern in KNOWN_BOT_PATTERNS:
                if pattern.startswith("*"):
                    conditions.append(
                        pl.col(self._actor_col).str.ends_with(pattern[1:])
                    )
                elif pattern.endswith("*"):
                    conditions.append(
                        pl.col(self._actor_col).str.starts_with(pattern[:-1])
                    )
                else:
                    conditions.append(pl.col(self._actor_col) == pattern)

            if conditions:
                combined = conditions[0]
                for cond in conditions[1:]:
                    combined = combined | cond
                return self._df.filter(~combined)
            return self._df
        else:
            # Pandas implementation
            mask = ~self._df[self._actor_col].str.contains(
                "|".join(p.replace("*", ".*") for p in KNOWN_BOT_PATTERNS),
                regex=True,
                na=False,
            )
            return self._df[mask]

    def _analyze_polars(self, df: Any) -> dict[str, Any]:
        """Polars-specific analysis implementation."""
        import polars as pl

        # User activity counts
        user_counts = (
            df.group_by(self._actor_col)
            .agg(pl.len().alias("activity_count"))
            .sort("activity_count", descending=True)
        )

        # Action breakdown per user
        action_breakdown = (
            df.group_by([self._actor_col, self._action_col])
            .agg(pl.len().alias("count"))
            .sort(["count"], descending=True)
        )

        # Summary statistics
        total_users = user_counts.height
        total_events = df.height
        avg_events_per_user = total_events / total_users if total_users > 0 else 0

        return {
            "user_counts": user_counts,
            "top_users": user_counts.head(10),
            "action_breakdown": action_breakdown,
            "summary_stats": {
                "total_users": total_users,
                "total_events": total_events,
                "avg_events_per_user": round(avg_events_per_user, 2),
            },
        }

    def _analyze_pandas(self, df: Any) -> dict[str, Any]:
        """Pandas-specific analysis implementation."""
        # User activity counts
        user_counts = (
            df.groupby(self._actor_col)
            .size()
            .reset_index(name="activity_count")
            .sort_values("activity_count", ascending=False)
        )

        # Action breakdown per user
        action_breakdown = (
            df.groupby([self._actor_col, self._action_col])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )

        # Summary statistics
        total_users = len(user_counts)
        total_events = len(df)
        avg_events_per_user = total_events / total_users if total_users > 0 else 0

        return {
            "user_counts": user_counts,
            "top_users": user_counts.head(10),
            "action_breakdown": action_breakdown,
            "summary_stats": {
                "total_users": total_users,
                "total_events": total_events,
                "avg_events_per_user": round(avg_events_per_user, 2),
            },
        }
