# src/audit_analyzer/utils/constants.py
"""Constants and configuration values for audit log analysis.

These values are used across analyzers for consistent behavior.
Modify these to customize detection thresholds and patterns.

Reference:
- https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/audit-log-events-for-your-enterprise
"""

from __future__ import annotations

from typing import Final


# ============================================================
# Dangerous Actions (CRITICAL risk)
# ============================================================
# These actions can cause significant damage or data loss

DANGEROUS_ACTIONS: Final[frozenset[str]] = frozenset(
    [
        # Repository deletion/modification
        "repo.destroy",
        "repo.access",  # Visibility change (public/private)
        "repo.transfer",
        "repo.archived",
        # Organization member changes
        "org.remove_member",
        "org.block_user",
        "org.remove_outside_collaborator",
        # Team changes
        "team.destroy",
        "team.remove_member",
        "team.demote_maintainer",
        # Webhooks (potential data exfiltration)
        "hook.create",
        "hook.config_changed",
        "hook.destroy",
        # OAuth/Integration applications
        "org.oauth_app_access_approved",
        "integration_installation.create",
        "integration.create",
        # Secrets and scanning
        "secret_scanning_alert.dismiss",
        "secret_scanning.disable",
        "repository_secret_scanning.disable",
        # Branch protection
        "protected_branch.destroy",
        "protected_branch.policy_override",
        "protected_branch.rejected_ref_update",
        # Billing/Enterprise
        "business.set_payment_method",
        "business.remove_admin",
        "business.remove_member",
        # Security features
        "repository_vulnerability_alerts.disable",
        "dependabot_security_updates.disable",
    ]
)

HIGH_RISK_ACTIONS: Final[frozenset[str]] = frozenset(
    [
        # Admin privilege changes
        "org.add_billing_manager",
        "org.add_member",  # New members get access
        "team.promote_maintainer",
        "business.add_admin",
        # Repository access
        "repo.add_member",
        "repo.update_member",
        "team.add_repository",
        # Deploy keys (persistent access)
        "public_key.create",
        "deploy_key.create",
        # Actions/Workflows (code execution)
        "workflows.approve_workflow_run",
        "workflows.rerun_workflow_run",
        "repo.create_actions_secret",
        "org.create_actions_secret",
        "environment.create_actions_secret",
        # Configuration changes
        "org.update_default_repository_permission",
        "org.set_default_workflow_permissions",
        "repo.set_default_workflow_permissions",
        # Audit log access
        "org.audit_log_export",
        "business.audit_log_export",
    ]
)


# ============================================================
# Time-based Analysis
# ============================================================

# Business hours definition (for anomaly detection)
BUSINESS_HOURS: Final[dict[str, int]] = {
    "start_hour": 9,  # 9:00 AM
    "end_hour": 18,  # 6:00 PM
    "timezone": 0,  # UTC offset (adjust per organization)
}

# Weekend days (0=Monday, 6=Sunday)
WEEKEND_DAYS: Final[frozenset[int]] = frozenset([5, 6])


# ============================================================
# Anomaly Detection Thresholds
# ============================================================

# Operations per hour that trigger alerts
BULK_OPERATION_THRESHOLDS: Final[dict[str, int]] = {
    "default": 100,  # Generic threshold per hour
    "repo.create": 10,  # Creating many repos quickly
    "repo.destroy": 3,  # Deleting repos is very suspicious
    "repo.add_member": 20,  # Bulk member additions
    "repo.remove_member": 10,  # Bulk member removals
    "org.add_member": 15,  # Bulk org member additions
    "org.remove_member": 5,  # Bulk org member removals
    "org.invite_member": 20,  # Bulk invitations
    "team.add_member": 25,  # Bulk team additions
    "hook.create": 5,  # Webhook creation spike
    "protected_branch.destroy": 3,  # Branch protection removal
}

# Short-term bulk operation thresholds (per 5 minutes)
RAPID_OPERATION_THRESHOLDS: Final[dict[str, int]] = {
    "default": 50,  # 50 operations in 5 minutes
    "repo.destroy": 2,  # 2+ deletions in 5 min is critical
    "hook.create": 3,  # 3+ webhooks in 5 min
    "repo.add_member": 15,  # Adding many collaborators quickly
    "org.remove_member": 3,  # Removing members quickly
    "protected_branch.destroy": 2,  # Removing branch protection
}

# Time windows for rate limiting analysis (in minutes)
RATE_LIMIT_WINDOWS: Final[dict[str, int]] = {
    "rapid": 5,  # 5 minutes - immediate threat detection
    "short": 15,  # 15 minutes - quick anomaly detection
    "medium": 60,  # 1 hour - pattern detection
    "long": 1440,  # 24 hours - daily analysis
}


# ============================================================
# Bot/Automation Patterns
# ============================================================

KNOWN_BOT_PATTERNS: Final[tuple[str, ...]] = (
    # GitHub official bots
    "github-actions[bot]",
    "dependabot[bot]",
    "dependabot-preview[bot]",
    # Popular third-party bots
    "renovate[bot]",
    "snyk-bot",
    "codecov[bot]",
    "sonarcloud[bot]",
    "mergify[bot]",
    "release-drafter[bot]",
    "semantic-release-bot",
    "greenkeeper[bot]",
    "netlify[bot]",
    "vercel[bot]",
    "imgbot[bot]",
    "allcontributors[bot]",
    "stale[bot]",
    # Glob patterns
    "*-bot",
    "*[bot]",
)

# Bot actions that are normal and should not trigger alerts
BOT_EXPECTED_ACTIONS: Final[frozenset[str]] = frozenset(
    [
        "git.push",
        "git.clone",
        "pull_request.create",
        "pull_request.merge",
        "workflows.completed_workflow_run",
        "secret_scanning_alert.create",
        "secret_scanning_alert.resolve",
        "dependabot_security_updates.enable",
    ]
)


# ============================================================
# IP Analysis
# ============================================================

# Known GitHub IP ranges (for detecting external access)
# Note: These should be updated periodically from:
# https://api.github.com/meta
GITHUB_IP_RANGES: Final[tuple[str, ...]] = (
    "192.30.252.0/22",
    "185.199.108.0/22",
    "140.82.112.0/20",
    "143.55.64.0/20",
)

# Private IP ranges (RFC 1918)
PRIVATE_IP_RANGES: Final[tuple[str, ...]] = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
)


# ============================================================
# Display / Formatting
# ============================================================

# Action category colors for visualization
ACTION_CATEGORY_COLORS: Final[dict[str, str]] = {
    "repo": "#0969da",  # Blue
    "org": "#8250df",  # Purple
    "team": "#1f883d",  # Green
    "hook": "#cf222e",  # Red
    "secret": "#bf8700",  # Yellow
    "protected_branch": "#6e7781",  # Gray
    "business": "#0550ae",  # Dark blue
    "default": "#57606a",  # Default gray
}

# Risk level colors
RISK_LEVEL_COLORS: Final[dict[str, str]] = {
    "critical": "#cf222e",  # Red
    "high": "#bf8700",  # Orange
    "medium": "#8250df",  # Purple
    "low": "#1f883d",  # Green
    "info": "#57606a",  # Gray
}
