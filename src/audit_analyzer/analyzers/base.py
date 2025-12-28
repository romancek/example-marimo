# src/audit_analyzer/analyzers/base.py
"""Base classes and protocols for analyzers.

Provides a common interface for all analyzers to ensure consistency
and enable polymorphic usage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    import pandas as pd
    import polars as pl


# Type variable for DataFrame types
DF = TypeVar("DF")


@runtime_checkable
class DataFrameLike(Protocol):
    """Protocol for DataFrame-like objects supporting basic operations."""

    def __len__(self) -> int: ...

    def filter(self, *args: Any, **kwargs: Any) -> "DataFrameLike": ...

    def group_by(self, *args: Any, **kwargs: Any) -> Any: ...


class BaseAnalyzer(ABC, Generic[DF]):
    """Abstract base class for all analyzers.

    Subclasses must implement the `analyze` method and can optionally
    override other methods for customization.
    """

    def __init__(self, df: DF) -> None:
        """Initialize analyzer with a DataFrame.

        Args:
            df: Input DataFrame (Polars or Pandas)
        """
        self._df = df
        self._validate_schema()

    @property
    def df(self) -> DF:
        """Access the underlying DataFrame."""
        return self._df

    @abstractmethod
    def analyze(self) -> dict[str, Any]:
        """Run the analysis and return results.

        Returns:
            Dictionary containing analysis results
        """
        ...

    def _validate_schema(self) -> None:
        """Validate that the DataFrame has required columns.

        Override in subclasses to add specific validation.
        Raises ValueError if validation fails.
        """
        pass

    def _get_column_names(self) -> list[str]:
        """Get column names from the DataFrame.

        Works with both Polars and Pandas.
        """
        if hasattr(self._df, "columns"):
            return list(self._df.columns)
        return []

    def _is_polars(self) -> bool:
        """Check if the DataFrame is a Polars DataFrame."""
        return type(self._df).__module__.startswith("polars")

    def _is_pandas(self) -> bool:
        """Check if the DataFrame is a Pandas DataFrame."""
        return type(self._df).__module__.startswith("pandas")
