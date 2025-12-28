# src/audit_analyzer/__init__.py
"""GitHub Organization Audit Log Analyzer.

A tool for analyzing GitHub Organization audit logs using marimo notebooks.
Supports both server-side (Polars/DuckDB) and WASM (Pandas) deployments.
"""

from audit_analyzer.loader import load_audit_log, load_audit_log_lazy
from audit_analyzer.models import AuditLogBatch, AuditLogEntry


__version__ = "0.1.0"

__all__ = [
    "AuditLogBatch",
    "AuditLogEntry",
    "__version__",
    "load_audit_log",
    "load_audit_log_lazy",
]
