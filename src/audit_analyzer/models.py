# src/audit_analyzer/models.py
"""Pydantic models for GitHub Audit Log entries.

Design principles:
- Strict validation with clear error messages
- Immutable models (frozen=True)
- Proper datetime handling with timezone awareness
- Support for both validation and serialization to DataFrame
- Flexible schema to accommodate GitHub API changes

Reference:
- https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/audit-log-events-for-your-enterprise
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class AuditLogAction(StrEnum):
    """Common GitHub audit log actions.

    Note: This is not exhaustive. GitHub has 500+ action types.
    See: https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/audit-log-events-for-your-enterprise
    """

    # Repository actions (high frequency)
    REPO_CREATE = "repo.create"
    REPO_DESTROY = "repo.destroy"
    REPO_ARCHIVED = "repo.archived"
    REPO_UNARCHIVED = "repo.unarchived"
    REPO_CHANGE_VISIBILITY = "repo.access"
    REPO_ADD_MEMBER = "repo.add_member"
    REPO_REMOVE_MEMBER = "repo.remove_member"
    REPO_TRANSFER = "repo.transfer"
    REPO_RENAME = "repo.rename"
    REPO_DOWNLOAD_ZIP = "repo.download_zip"

    # Organization member actions
    ORG_ADD_MEMBER = "org.add_member"
    ORG_REMOVE_MEMBER = "org.remove_member"
    ORG_INVITE_MEMBER = "org.invite_member"
    ORG_UPDATE_MEMBER = "org.update_member"
    ORG_ADD_BILLING_MANAGER = "org.add_billing_manager"
    ORG_REMOVE_BILLING_MANAGER = "org.remove_billing_manager"
    ORG_ADD_OUTSIDE_COLLABORATOR = "org.add_outside_collaborator"
    ORG_REMOVE_OUTSIDE_COLLABORATOR = "org.remove_outside_collaborator"

    # Team actions
    TEAM_CREATE = "team.create"
    TEAM_DESTROY = "team.destroy"
    TEAM_ADD_MEMBER = "team.add_member"
    TEAM_REMOVE_MEMBER = "team.remove_member"
    TEAM_ADD_REPOSITORY = "team.add_repository"
    TEAM_REMOVE_REPOSITORY = "team.remove_repository"
    TEAM_CHANGE_PRIVACY = "team.change_privacy"

    # Git actions (very high frequency)
    GIT_CLONE = "git.clone"
    GIT_FETCH = "git.fetch"
    GIT_PUSH = "git.push"

    # Pull request actions
    PULL_REQUEST_CREATE = "pull_request.create"
    PULL_REQUEST_MERGE = "pull_request.merge"
    PULL_REQUEST_CLOSE = "pull_request.close"

    # Authentication/OAuth
    ORG_OAUTH_APP_ACCESS_APPROVED = "org.oauth_app_access_approved"
    ORG_OAUTH_APP_ACCESS_DENIED = "org.oauth_app_access_denied"
    ORG_OAUTH_APP_ACCESS_BLOCKED = "org.oauth_app_access_blocked"

    # Webhooks
    HOOK_CREATE = "hook.create"
    HOOK_DESTROY = "hook.destroy"
    HOOK_CONFIG_CHANGED = "hook.config_changed"
    HOOK_EVENTS_CHANGED = "hook.events_changed"

    # Secret scanning
    SECRET_SCANNING_ALERT_CREATE = "secret_scanning_alert.create"
    SECRET_SCANNING_ALERT_RESOLVE = "secret_scanning_alert.resolve"
    SECRET_SCANNING_DISABLE = "secret_scanning.disable"
    SECRET_SCANNING_ENABLE = "secret_scanning.enable"

    # Branch protection
    PROTECTED_BRANCH_CREATE = "protected_branch.create"
    PROTECTED_BRANCH_DESTROY = "protected_branch.destroy"
    PROTECTED_BRANCH_POLICY_OVERRIDE = "protected_branch.policy_override"

    # GitHub Actions
    WORKFLOWS_COMPLETED = "workflows.completed_workflow_run"
    WORKFLOWS_APPROVE = "workflows.approve_workflow_run"

    # Integration/Apps
    INTEGRATION_CREATE = "integration.create"
    INTEGRATION_DESTROY = "integration.destroy"
    INTEGRATION_INSTALL = "integration_installation.create"
    INTEGRATION_UNINSTALL = "integration_installation.destroy"

    # Copilot
    COPILOT_SEAT_ADDED = "copilot.cfb_seat_added"
    COPILOT_SEAT_REMOVED = "copilot.cfb_seat_removed"

    # Business/Enterprise
    BUSINESS_ADD_ADMIN = "business.add_admin"
    BUSINESS_REMOVE_ADMIN = "business.remove_admin"
    BUSINESS_ADD_MEMBER = "business.add_member"
    BUSINESS_REMOVE_MEMBER = "business.remove_member"

    # Other
    UNKNOWN = "unknown"


class OperationType(StrEnum):
    """GitHub Audit Log operation types."""

    CREATE = "create"
    MODIFY = "modify"
    REMOVE = "remove"
    ACCESS = "access"


class ProgrammaticAccessType(StrEnum):
    """Types of programmatic access."""

    OAUTH_ACCESS = "OAuth access token"
    GITHUB_APP = "GitHub App server-to-server token"
    FINE_GRAINED_PAT = "fine-grained personal access token"
    PAT = "personal access token"


# Dangerous actions that require special attention
DANGEROUS_ACTIONS: frozenset[str] = frozenset(
    [
        "repo.destroy",
        "repo.transfer",
        "repo.access",
        "org.remove_member",
        "org.remove_outside_collaborator",
        "org.update_member",
        "team.destroy",
        "team.remove_member",
        "hook.create",
        "hook.config_changed",
        "hook.destroy",
        "secret_scanning.disable",
        "protected_branch.destroy",
        "protected_branch.policy_override",
        "business.remove_admin",
        "integration.destroy",
        "integration_installation.destroy",
    ]
)


class AuditLogEntry(BaseModel):
    """Single audit log entry from GitHub Organization.

    Based on GitHub Enterprise Cloud Audit Log API schema.
    See: https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/audit-log-events-for-your-enterprise

    Attributes:
        timestamp: Event timestamp (Unix milliseconds or ISO format)
        action: The action performed (e.g., "repo.create")
        actor: Username who performed the action
        actor_id: Numeric ID of the actor
        actor_ip: IP address of the actor (may be None for system events)
        org: Organization name
        org_id: Numeric ID of the organization
        repo: Repository name (if applicable, format: "org/repo")
        repo_id: Numeric ID of the repository
        user: Target user (if applicable, e.g., for member actions)
        user_id: Numeric ID of the target user
        user_agent: HTTP User-Agent string
        business: Enterprise name (if applicable)
        business_id: Numeric ID of the enterprise
        operation_type: Type of operation (create, modify, remove, access)
        request_id: GitHub request ID for tracing
        document_id: Unique document ID
        created_at: Event creation timestamp
        extra_data: Additional event-specific data

    Example:
        >>> entry = AuditLogEntry(
        ...     timestamp=1703980800000,
        ...     action="repo.create",
        ...     actor="admin-user",
        ...     org="my-org",
        ...     repo="my-org/new-repo",
        ... )
    """

    model_config = ConfigDict(
        frozen=True,  # Immutable
        str_strip_whitespace=True,
        validate_default=True,
        extra="allow",  # Allow unknown fields from GitHub API
        populate_by_name=True,  # Allow both field name and alias
    )

    # === Core Required Fields ===
    timestamp: Annotated[datetime, Field(alias="@timestamp")]
    action: str = Field(..., min_length=1)
    actor: str = Field(default="")  # May be empty for system events
    org: str = Field(default="")  # May be empty for user-level events

    # === Actor Information ===
    actor_id: int | None = Field(default=None)
    actor_ip: str | None = Field(default=None)
    actor_is_bot: bool | None = Field(default=None)

    # === Actor Location (for geo-analysis) ===
    actor_location: dict[str, Any] | None = Field(default=None)
    country_code: str | None = Field(default=None)

    # === Organization Information ===
    org_id: int | None = Field(default=None)

    # === Repository Information ===
    repo: str | None = Field(default=None)
    repo_id: int | None = Field(default=None)
    public_repo: bool | None = Field(default=None)
    visibility: str | None = Field(default=None)  # public, private, internal

    # === Target User Information ===
    user: str | None = Field(default=None)
    user_id: int | None = Field(default=None)

    # === Team Information ===
    team: str | None = Field(default=None)

    # === Enterprise Information ===
    business: str | None = Field(default=None)
    business_id: int | None = Field(default=None)

    # === Metadata ===
    operation_type: str | None = Field(default=None)
    user_agent: str | None = Field(default=None)
    request_id: str | None = Field(default=None)
    document_id: str | None = Field(default=None, alias="_document_id")
    created_at: datetime | None = Field(default=None)

    # === Token/Access Information ===
    programmatic_access_type: str | None = Field(default=None)
    token_scopes: str | None = Field(default=None)
    oauth_application_id: int | None = Field(default=None)

    # === Additional data (catch-all for event-specific fields) ===
    extra_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        """Parse timestamp from various formats.

        Supports:
        - Unix timestamp in milliseconds (int)
        - Unix timestamp in seconds (int/float)
        - ISO 8601 string
        - datetime object
        """
        if isinstance(v, datetime):
            return v if v.tzinfo else v.replace(tzinfo=UTC)
        if isinstance(v, (int, float)):
            # Heuristic: if > 10^12, it's milliseconds
            if v > 1e12:
                return datetime.fromtimestamp(v / 1000, tz=UTC)
            return datetime.fromtimestamp(v, tz=UTC)
        if isinstance(v, str):
            # Try ISO format (Python 3.11+ supports 'Z' suffix)
            dt = datetime.fromisoformat(v)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        raise ValueError(f"Cannot parse timestamp: {v}")

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v: Any) -> datetime | None:
        """Parse created_at timestamp."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v if v.tzinfo else v.replace(tzinfo=UTC)
        if isinstance(v, (int, float)):
            if v > 1e12:
                return datetime.fromtimestamp(v / 1000, tz=UTC)
            return datetime.fromtimestamp(v, tz=UTC)
        if isinstance(v, str):
            dt = datetime.fromisoformat(v)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        return None

    @model_validator(mode="before")
    @classmethod
    def extract_extra_data(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Extract unknown fields into the 'extra_data' dict.

        This preserves event-specific fields that aren't in the base schema.
        Examples: hook_id, name, permission, branch, etc.
        """
        known_fields = {
            "@timestamp",
            "timestamp",
            "action",
            "actor",
            "actor_id",
            "actor_ip",
            "actor_is_bot",
            "actor_location",
            "country_code",
            "org",
            "org_id",
            "repo",
            "repo_id",
            "public_repo",
            "visibility",
            "user",
            "user_id",
            "team",
            "business",
            "business_id",
            "operation_type",
            "user_agent",
            "request_id",
            "_document_id",
            "document_id",
            "created_at",
            "programmatic_access_type",
            "token_scopes",
            "oauth_application_id",
            "extra_data",
        }
        extra = {k: v for k, v in values.items() if k not in known_fields}
        if extra:
            values["extra_data"] = {**values.get("extra_data", {}), **extra}
        return values

    @property
    def action_category(self) -> str:
        """Extract action category (e.g., 'repo' from 'repo.create')."""
        return self.action.split(".")[0] if "." in self.action else self.action

    @property
    def action_type(self) -> str:
        """Extract action type (e.g., 'create' from 'repo.create')."""
        parts = self.action.split(".")
        return parts[1] if len(parts) > 1 else self.action

    @property
    def is_bot_actor(self) -> bool:
        """Check if the actor is a bot."""
        if self.actor_is_bot is True:
            return True
        return self.actor.endswith("[bot]") if self.actor else False

    def is_dangerous_action(self) -> bool:
        """Check if this action is potentially dangerous.

        Dangerous actions include:
        - Deleting repositories, teams, or organizations
        - Removing members or collaborators
        - Changing visibility or access settings
        - Modifying webhooks or integrations
        - Disabling security features
        - Bypassing branch protection
        """
        # Fast path: check against known dangerous actions
        if self.action in DANGEROUS_ACTIONS:
            return True

        # Pattern-based check for less common dangerous actions
        dangerous_patterns = [
            "destroy",
            "delete",
            "remove_member",
            "remove_outside_collaborator",
            "policy_override",
            "bypass",
        ]
        return any(pattern in self.action for pattern in dangerous_patterns)

    def is_off_hours(
        self,
        start_hour: int = 9,
        end_hour: int = 18,
        weekend_days: frozenset[int] | None = None,
    ) -> bool:
        """Check if this event occurred outside business hours.

        Args:
            start_hour: Start of business hours (default 9 AM)
            end_hour: End of business hours (default 6 PM)
            weekend_days: Weekend days (default Saturday=5, Sunday=6)

        Returns:
            True if event is outside business hours
        """
        if weekend_days is None:
            weekend_days = frozenset([5, 6])

        hour = self.timestamp.hour
        weekday = self.timestamp.weekday()

        if weekday in weekend_days:
            return True
        if hour < start_hour or hour >= end_hour:
            return True
        return False

    def is_late_night(
        self,
        start_hour: int = 22,
        end_hour: int = 6,
    ) -> bool:
        """Check if this event occurred during late night hours.

        Args:
            start_hour: Start of late night (default 10 PM)
            end_hour: End of late night (default 6 AM)

        Returns:
            True if event is during late night hours (22:00-06:00)
        """
        hour = self.timestamp.hour
        return hour >= start_hour or hour < end_hour

    def to_flat_dict(self) -> dict[str, Any]:
        """Convert to a flat dictionary for DataFrame creation.

        Merges extra_data into the main dict for easier DataFrame operations.
        """
        base = self.model_dump(by_alias=False, exclude={"extra_data"})
        # Flatten extra_data
        if self.extra_data:
            for k, v in self.extra_data.items():
                if k not in base:
                    base[k] = v
        return base


class AuditLogBatch(BaseModel):
    """Batch of audit log entries for bulk processing.

    Useful for validating large JSON exports from GitHub.
    """

    model_config = ConfigDict(frozen=True)

    entries: list[AuditLogEntry] = Field(default_factory=list)

    @classmethod
    def from_json_lines(cls, lines: list[dict[str, Any]]) -> AuditLogBatch:
        """Create batch from list of JSON objects (NDJSON format)."""
        entries = [AuditLogEntry.model_validate(line) for line in lines]
        return cls(entries=entries)

    @classmethod
    def from_json_array(cls, data: list[dict[str, Any]]) -> AuditLogBatch:
        """Create batch from JSON array."""
        return cls.from_json_lines(data)

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    def __getitem__(self, index: int) -> AuditLogEntry:
        return self.entries[index]

    @property
    def time_range(self) -> tuple[datetime, datetime] | None:
        """Get the time range of entries in this batch."""
        if not self.entries:
            return None
        timestamps = [e.timestamp for e in self.entries]
        return min(timestamps), max(timestamps)

    @property
    def actors(self) -> set[str]:
        """Get unique actors in this batch."""
        return {e.actor for e in self.entries if e.actor}

    @property
    def actions(self) -> set[str]:
        """Get unique actions in this batch."""
        return {e.action for e in self.entries}

    def filter_by_action(self, action_pattern: str) -> AuditLogBatch:
        """Filter entries by action pattern."""
        filtered = [e for e in self.entries if action_pattern in e.action]
        return AuditLogBatch(entries=filtered)

    def filter_by_actor(self, actor: str) -> AuditLogBatch:
        """Filter entries by actor."""
        filtered = [e for e in self.entries if e.actor == actor]
        return AuditLogBatch(entries=filtered)

    def filter_dangerous(self) -> AuditLogBatch:
        """Get only dangerous actions."""
        filtered = [e for e in self.entries if e.is_dangerous_action()]
        return AuditLogBatch(entries=filtered)

    def to_dicts(self) -> list[dict[str, Any]]:
        """Convert all entries to flat dictionaries."""
        return [e.to_flat_dict() for e in self.entries]


# Type alias for DataFrame compatibility
AuditLogData = list[dict[str, Any]] | AuditLogBatch
