#!/usr/bin/env python3
# scripts/generate_test_data.py
"""Generate realistic test data for GitHub Audit Log analysis.

This script generates synthetic data that mimics real GitHub data:
1. Audit Logs - Organization activity logs with various patterns
2. Org Members - Organization member list from GitHub API
3. Copilot Seats - Copilot seat assignment data for multiple organizations

Usage:
    # Generate all data types (recommended for dormant user analysis)
    python scripts/generate_test_data.py --all

    # Generate only audit logs
    python scripts/generate_test_data.py -n 10000 -o data/test.ndjson

    # Generate Org Members list
    python scripts/generate_test_data.py --generate-members --members-count 50

    # Generate Copilot Seats for 2 organizations
    python scripts/generate_test_data.py --generate-copilot --copilot-orgs acme-corp contoso
"""

from __future__ import annotations

import argparse
import json
import random
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


# ============================================================
# Configuration
# ============================================================

# Organization and repository configuration
ORG_NAME = "example-org"
ORG_ID = 12345678

# User pools with different activity patterns
ADMIN_USERS = [
    {"name": "admin-user", "id": 1001, "ip_pool": ["10.0.1.1", "10.0.1.2"]},
    {"name": "security-admin", "id": 1002, "ip_pool": ["10.0.2.1", "192.168.1.100"]},
    {"name": "org-owner", "id": 1003, "ip_pool": ["10.0.3.1"]},
]

REGULAR_USERS = [
    {"name": "dev-alice", "id": 2001, "ip_pool": ["10.1.1.1", "10.1.1.2"]},
    {"name": "dev-bob", "id": 2002, "ip_pool": ["10.1.2.1", "10.1.2.2", "10.1.2.3"]},
    {"name": "dev-carol", "id": 2003, "ip_pool": ["10.1.3.1"]},
    {"name": "dev-david", "id": 2004, "ip_pool": ["10.1.4.1", "10.1.4.2"]},
    {"name": "dev-eve", "id": 2005, "ip_pool": ["10.1.5.1"]},
    {"name": "dev-frank", "id": 2006, "ip_pool": ["10.1.6.1", "10.1.6.2"]},
    {"name": "qa-george", "id": 2007, "ip_pool": ["10.2.1.1"]},
    {"name": "qa-helen", "id": 2008, "ip_pool": ["10.2.2.1"]},
    {"name": "devops-ivan", "id": 2009, "ip_pool": ["10.3.1.1", "10.3.1.2"]},
    {"name": "devops-julia", "id": 2010, "ip_pool": ["10.3.2.1"]},
]

BOT_USERS = [
    {"name": "dependabot[bot]", "id": 9001, "ip_pool": ["140.82.112.1"]},
    {"name": "github-actions[bot]", "id": 9002, "ip_pool": ["140.82.112.2"]},
    {"name": "renovate[bot]", "id": 9003, "ip_pool": ["140.82.112.3"]},
]

# Suspicious user for anomaly patterns
SUSPICIOUS_USER = {
    "name": "suspicious-user",
    "id": 3001,
    "ip_pool": ["203.0.113.1", "198.51.100.1"],
}

# Repository pool
REPOSITORIES = [
    {"name": f"{ORG_NAME}/frontend-app", "id": 101, "visibility": "private"},
    {"name": f"{ORG_NAME}/backend-api", "id": 102, "visibility": "private"},
    {"name": f"{ORG_NAME}/mobile-app", "id": 103, "visibility": "private"},
    {"name": f"{ORG_NAME}/infrastructure", "id": 104, "visibility": "private"},
    {"name": f"{ORG_NAME}/documentation", "id": 105, "visibility": "internal"},
    {"name": f"{ORG_NAME}/open-source-lib", "id": 106, "visibility": "public"},
    {"name": f"{ORG_NAME}/data-pipeline", "id": 107, "visibility": "private"},
    {"name": f"{ORG_NAME}/ml-models", "id": 108, "visibility": "private"},
]

TEAMS = ["engineering", "qa", "devops", "security", "data-science"]

# Action distributions (realistic weights)
NORMAL_ACTIONS = [
    # High frequency actions (git operations)
    ("git.clone", 0.25),
    ("git.fetch", 0.20),
    ("git.push", 0.15),
    # Medium frequency actions
    ("pull_request.create", 0.08),
    ("pull_request.merge", 0.05),
    ("pull_request.close", 0.03),
    ("repo.download_zip", 0.02),
    # Lower frequency actions
    ("repo.create", 0.02),
    ("repo.add_member", 0.02),
    ("team.add_member", 0.02),
    ("team.add_repository", 0.02),
    ("workflows.completed_workflow_run", 0.05),
    ("protected_branch.create", 0.01),
    ("secret_scanning_alert.create", 0.01),
    ("secret_scanning_alert.resolve", 0.01),
    ("org.add_member", 0.01),
    ("org.invite_member", 0.01),
    ("hook.create", 0.01),
    ("integration_installation.create", 0.01),
    ("copilot.cfb_seat_added", 0.02),
]

# Dangerous actions (for anomaly patterns)
DANGEROUS_ACTIONS = [
    "repo.destroy",
    "repo.transfer",
    "repo.access",  # visibility change
    "org.remove_member",
    "org.update_member",
    "team.destroy",
    "team.remove_member",
    "hook.config_changed",
    "hook.destroy",
    "secret_scanning.disable",
    "protected_branch.destroy",
    "protected_branch.policy_override",
    "business.remove_admin",
]

# User agents
USER_AGENTS = [
    "GitHub Desktop/3.3.0",
    "git/2.42.0",
    "git/2.43.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "GitHub CLI/2.40.0",
    "python-requests/2.31.0",
]

# Countries for geographic distribution
COUNTRIES = [
    {"code": "JP", "name": "Japan"},
    {"code": "US", "name": "United States"},
    {"code": "GB", "name": "United Kingdom"},
    {"code": "DE", "name": "Germany"},
    {"code": "SG", "name": "Singapore"},
]

# Suspicious countries (for anomaly detection)
SUSPICIOUS_COUNTRIES = [
    {"code": "RU", "name": "Russia"},
    {"code": "CN", "name": "China"},
    {"code": "KP", "name": "North Korea"},
]

# Additional users for dormant user analysis
# These users appear in Org Members but have low/no activity in audit logs
DORMANT_USERS = [
    {"name": "dormant-user-1", "id": 4001, "ip_pool": ["10.4.1.1"]},
    {"name": "dormant-user-2", "id": 4002, "ip_pool": ["10.4.2.1"]},
    {"name": "dormant-user-3", "id": 4003, "ip_pool": ["10.4.3.1"]},
    {"name": "low-activity-1", "id": 4004, "ip_pool": ["10.4.4.1"]},
    {"name": "low-activity-2", "id": 4005, "ip_pool": ["10.4.5.1"]},
]

# Users who left the organization (in audit logs but not in current members)
FORMER_USERS = [
    {"name": "former-dev-mike", "id": 5001, "ip_pool": ["10.5.1.1"]},
    {"name": "former-qa-nancy", "id": 5002, "ip_pool": ["10.5.2.1"]},
]

# All organization members (for Org Members list generation)
# Excludes FORMER_USERS and BOT_USERS
ALL_ORG_MEMBERS = ADMIN_USERS + REGULAR_USERS + DORMANT_USERS

# Copilot configuration
COPILOT_EDITORS = [
    "vscode/1.85.0/copilot/1.142.0",
    "vscode/1.86.0/copilot/1.143.0",
    "JetBrains-IU/2023.3/copilot/1.4.5",
    "neovim/0.9.4/copilot/1.11.1",
]


# ============================================================
# Helper functions
# ============================================================


def weighted_choice(choices: list[tuple[str, float]]) -> str:
    """Select a random item based on weights."""
    items, weights = zip(*choices, strict=False)
    return random.choices(items, weights=weights, k=1)[0]


def generate_timestamp(
    base_time: datetime,
    *,
    business_hours: bool = True,
    late_night: bool = False,
    weekend: bool = False,
) -> datetime:
    """Generate a realistic timestamp.

    Args:
        base_time: Base datetime to generate around
        business_hours: Generate during business hours (9-18)
        late_night: Generate during late night (22-06)
        weekend: Generate on weekend

    Returns:
        Generated datetime with timezone
    """
    # Adjust day of week
    if weekend:
        # Move to Saturday or Sunday
        days_to_weekend = (5 - base_time.weekday()) % 7
        if days_to_weekend == 0:
            days_to_weekend = random.choice([0, 1])  # Saturday or Sunday
        base_time = base_time + timedelta(days=days_to_weekend)
    elif base_time.weekday() >= 5:
        # Move to Monday if currently weekend
        days_to_monday = (7 - base_time.weekday()) % 7
        base_time = base_time + timedelta(days=days_to_monday)

    # Adjust hour
    if late_night:
        hour = random.choice([22, 23, 0, 1, 2, 3, 4, 5])
    elif business_hours:
        hour = random.randint(9, 17)
    else:
        hour = random.randint(0, 23)

    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return base_time.replace(hour=hour, minute=minute, second=second, tzinfo=UTC)


def generate_document_id() -> str:
    """Generate a unique document ID."""
    return str(uuid.uuid4())


def generate_request_id() -> str:
    """Generate a GitHub-style request ID."""
    return f"{uuid.uuid4().hex[:8]}:{uuid.uuid4().hex[:8]}"


# ============================================================
# Event generators
# ============================================================


def generate_normal_event(timestamp: datetime) -> dict[str, Any]:
    """Generate a normal audit log event."""
    action = weighted_choice(NORMAL_ACTIONS)
    user = random.choice(REGULAR_USERS + ADMIN_USERS + BOT_USERS)
    repo = random.choice(REPOSITORIES)
    country = random.choice(COUNTRIES)

    event = {
        "@timestamp": int(timestamp.timestamp() * 1000),
        "action": action,
        "actor": user["name"],
        "actor_id": user["id"],
        "actor_ip": random.choice(user["ip_pool"]),
        "actor_is_bot": user["name"].endswith("[bot]"),
        "actor_location": {
            "country_code": country["code"],
            "country_name": country["name"],
        },
        "country_code": country["code"],
        "org": ORG_NAME,
        "org_id": ORG_ID,
        "operation_type": _get_operation_type(action),
        "user_agent": random.choice(USER_AGENTS),
        "_document_id": generate_document_id(),
        "request_id": generate_request_id(),
        "created_at": int(timestamp.timestamp() * 1000),
    }

    # Add repo info for repo-related actions
    if action.startswith(("repo.", "git.", "pull_request.", "protected_branch.")):
        event["repo"] = repo["name"]
        event["repo_id"] = repo["id"]
        event["visibility"] = repo["visibility"]
        event["public_repo"] = repo["visibility"] == "public"

    # Add team info for team actions
    if action.startswith("team."):
        event["team"] = random.choice(TEAMS)

    # Add user info for member actions
    if "member" in action:
        target_user = random.choice(REGULAR_USERS)
        event["user"] = target_user["name"]
        event["user_id"] = target_user["id"]

    return event


def generate_late_night_event(timestamp: datetime) -> dict[str, Any]:
    """Generate a late night (anomalous) event."""
    # Late night events are more likely to be from suspicious users
    if random.random() < 0.3:
        user = SUSPICIOUS_USER
        country = random.choice(SUSPICIOUS_COUNTRIES)
    else:
        user = random.choice(ADMIN_USERS)  # Admins sometimes work late
        country = random.choice(COUNTRIES)

    action = weighted_choice(NORMAL_ACTIONS)

    # Higher chance of dangerous actions at night
    if random.random() < 0.1:
        action = random.choice(DANGEROUS_ACTIONS)

    timestamp = generate_timestamp(timestamp, late_night=True)

    event = {
        "@timestamp": int(timestamp.timestamp() * 1000),
        "action": action,
        "actor": user["name"],
        "actor_id": user["id"],
        "actor_ip": random.choice(user["ip_pool"]),
        "actor_is_bot": False,
        "actor_location": {
            "country_code": country["code"],
            "country_name": country["name"],
        },
        "country_code": country["code"],
        "org": ORG_NAME,
        "org_id": ORG_ID,
        "operation_type": _get_operation_type(action),
        "user_agent": random.choice(USER_AGENTS),
        "_document_id": generate_document_id(),
        "request_id": generate_request_id(),
        "created_at": int(timestamp.timestamp() * 1000),
    }

    # Add repo info
    repo = random.choice(REPOSITORIES)
    if action.startswith(("repo.", "git.", "pull_request.", "protected_branch.")):
        event["repo"] = repo["name"]
        event["repo_id"] = repo["id"]

    return event


def generate_bulk_operation_events(
    base_timestamp: datetime,
    count: int = 60,
) -> list[dict[str, Any]]:
    """Generate bulk operation events (anomaly: many events in short time).

    Simulates a user performing 60+ operations in 5 minutes.
    """
    events = []
    user = random.choice([*ADMIN_USERS, SUSPICIOUS_USER])
    action = random.choice(["git.clone", "repo.download_zip", "git.fetch"])

    for _ in range(count):
        # Events within 5 minutes
        offset_seconds = random.randint(0, 300)
        timestamp = base_timestamp + timedelta(seconds=offset_seconds)

        event = {
            "@timestamp": int(timestamp.timestamp() * 1000),
            "action": action,
            "actor": user["name"],
            "actor_id": user["id"],
            "actor_ip": random.choice(user["ip_pool"]),
            "actor_is_bot": False,
            "org": ORG_NAME,
            "org_id": ORG_ID,
            "operation_type": "access",
            "user_agent": random.choice(USER_AGENTS),
            "_document_id": generate_document_id(),
            "request_id": generate_request_id(),
            "created_at": int(timestamp.timestamp() * 1000),
        }

        repo = random.choice(REPOSITORIES)
        event["repo"] = repo["name"]
        event["repo_id"] = repo["id"]

        events.append(event)

    return events


def generate_dangerous_action_event(timestamp: datetime) -> dict[str, Any]:
    """Generate a dangerous action event."""
    action = random.choice(DANGEROUS_ACTIONS)

    # Dangerous actions mostly by admins, sometimes suspicious
    if random.random() < 0.2:
        user = SUSPICIOUS_USER
        country = random.choice(SUSPICIOUS_COUNTRIES)
    else:
        user = random.choice(ADMIN_USERS)
        country = random.choice(COUNTRIES)

    event = {
        "@timestamp": int(timestamp.timestamp() * 1000),
        "action": action,
        "actor": user["name"],
        "actor_id": user["id"],
        "actor_ip": random.choice(user["ip_pool"]),
        "actor_is_bot": False,
        "actor_location": {
            "country_code": country["code"],
            "country_name": country["name"],
        },
        "country_code": country["code"],
        "org": ORG_NAME,
        "org_id": ORG_ID,
        "operation_type": _get_operation_type(action),
        "user_agent": random.choice(USER_AGENTS),
        "_document_id": generate_document_id(),
        "request_id": generate_request_id(),
        "created_at": int(timestamp.timestamp() * 1000),
    }

    repo = random.choice(REPOSITORIES)
    if action.startswith(("repo.", "protected_branch.", "hook.", "secret_scanning.")):
        event["repo"] = repo["name"]
        event["repo_id"] = repo["id"]

    if action.startswith("team."):
        event["team"] = random.choice(TEAMS)

    if "member" in action:
        target_user = random.choice(REGULAR_USERS)
        event["user"] = target_user["name"]
        event["user_id"] = target_user["id"]

    return event


def generate_weekend_event(timestamp: datetime) -> dict[str, Any]:
    """Generate a weekend activity event (anomaly)."""
    timestamp = generate_timestamp(timestamp, weekend=True, business_hours=False)

    # Weekend events from various sources
    if random.random() < 0.4:
        user = random.choice(BOT_USERS)  # Bots work on weekends
    elif random.random() < 0.3:
        user = SUSPICIOUS_USER
    else:
        user = random.choice(ADMIN_USERS + REGULAR_USERS)

    action = weighted_choice(NORMAL_ACTIONS)

    event = {
        "@timestamp": int(timestamp.timestamp() * 1000),
        "action": action,
        "actor": user["name"],
        "actor_id": user["id"],
        "actor_ip": random.choice(user["ip_pool"]),
        "actor_is_bot": user["name"].endswith("[bot]"),
        "org": ORG_NAME,
        "org_id": ORG_ID,
        "operation_type": _get_operation_type(action),
        "user_agent": random.choice(USER_AGENTS),
        "_document_id": generate_document_id(),
        "request_id": generate_request_id(),
        "created_at": int(timestamp.timestamp() * 1000),
    }

    repo = random.choice(REPOSITORIES)
    if action.startswith(("repo.", "git.", "pull_request.")):
        event["repo"] = repo["name"]
        event["repo_id"] = repo["id"]

    return event


def generate_unusual_ip_event(timestamp: datetime) -> dict[str, Any]:
    """Generate event from unusual IP (anomaly)."""
    user = random.choice(REGULAR_USERS + ADMIN_USERS)
    # Use an unusual IP not in the user's normal pool
    unusual_ip = f"198.51.100.{random.randint(1, 254)}"
    country = random.choice(SUSPICIOUS_COUNTRIES)

    action = weighted_choice(NORMAL_ACTIONS)

    event = {
        "@timestamp": int(timestamp.timestamp() * 1000),
        "action": action,
        "actor": user["name"],
        "actor_id": user["id"],
        "actor_ip": unusual_ip,
        "actor_is_bot": False,
        "actor_location": {
            "country_code": country["code"],
            "country_name": country["name"],
        },
        "country_code": country["code"],
        "org": ORG_NAME,
        "org_id": ORG_ID,
        "operation_type": _get_operation_type(action),
        "user_agent": random.choice(USER_AGENTS),
        "_document_id": generate_document_id(),
        "request_id": generate_request_id(),
        "created_at": int(timestamp.timestamp() * 1000),
    }

    repo = random.choice(REPOSITORIES)
    if action.startswith(("repo.", "git.", "pull_request.")):
        event["repo"] = repo["name"]
        event["repo_id"] = repo["id"]

    return event


def _get_operation_type(action: str) -> str:
    """Determine operation type from action."""
    if any(x in action for x in ["create", "add", "invite", "install"]):
        return "create"
    elif any(x in action for x in ["destroy", "remove", "delete", "uninstall"]):
        return "remove"
    elif any(x in action for x in ["update", "change", "rename", "transfer", "config"]):
        return "modify"
    else:
        return "access"


# ============================================================
# Main generation function
# ============================================================


def generate_test_data(
    count: int = 10000,
    *,
    start_date: datetime | None = None,
    days_span: int = 90,
    anomaly_ratio: float = 0.05,
) -> list[dict[str, Any]]:
    """Generate test audit log data.

    Args:
        count: Total number of events to generate
        start_date: Starting date for events (default: 90 days ago)
        days_span: Number of days to span events across
        anomaly_ratio: Ratio of anomalous events (default: 5%)

    Returns:
        List of audit log events sorted by timestamp
    """
    if start_date is None:
        start_date = datetime.now(UTC) - timedelta(days=days_span)

    events: list[dict[str, Any]] = []
    anomaly_count = int(count * anomaly_ratio)
    normal_count = count - anomaly_count

    # Generate normal events
    print(f"Generating {normal_count} normal events...")
    for _ in range(normal_count):
        days_offset = random.randint(0, days_span - 1)
        base_time = start_date + timedelta(days=days_offset)
        timestamp = generate_timestamp(base_time, business_hours=True)
        events.append(generate_normal_event(timestamp))

    # Generate anomalous events
    print(f"Generating {anomaly_count} anomalous events...")

    # Late night events (30% of anomalies)
    late_night_count = int(anomaly_count * 0.3)
    for _ in range(late_night_count):
        days_offset = random.randint(0, days_span - 1)
        base_time = start_date + timedelta(days=days_offset)
        events.append(generate_late_night_event(base_time))

    # Bulk operations (10% of anomalies, but generates ~60 events each)
    bulk_incidents = max(1, int(anomaly_count * 0.02))
    for _ in range(bulk_incidents):
        days_offset = random.randint(0, days_span - 1)
        base_time = start_date + timedelta(days=days_offset)
        timestamp = generate_timestamp(base_time, business_hours=True)
        bulk_events = generate_bulk_operation_events(timestamp, count=60)
        events.extend(bulk_events)

    # Dangerous actions (20% of anomalies)
    dangerous_count = int(anomaly_count * 0.2)
    for _ in range(dangerous_count):
        days_offset = random.randint(0, days_span - 1)
        base_time = start_date + timedelta(days=days_offset)
        timestamp = generate_timestamp(
            base_time, business_hours=random.choice([True, False])
        )
        events.append(generate_dangerous_action_event(timestamp))

    # Weekend events (20% of anomalies)
    weekend_count = int(anomaly_count * 0.2)
    for _ in range(weekend_count):
        days_offset = random.randint(0, days_span - 1)
        base_time = start_date + timedelta(days=days_offset)
        events.append(generate_weekend_event(base_time))

    # Unusual IP events (20% of anomalies)
    unusual_ip_count = int(anomaly_count * 0.2)
    for _ in range(unusual_ip_count):
        days_offset = random.randint(0, days_span - 1)
        base_time = start_date + timedelta(days=days_offset)
        timestamp = generate_timestamp(base_time, business_hours=True)
        events.append(generate_unusual_ip_event(timestamp))

    # Sort by timestamp
    events.sort(key=lambda x: x["@timestamp"])

    return events


def save_as_json(events: list[dict[str, Any]], path: Path) -> None:
    """Save events as JSON array."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(events)} events to {path} (JSON format)")


def save_as_ndjson(events: list[dict[str, Any]], path: Path) -> None:
    """Save events as NDJSON (newline-delimited JSON)."""
    with path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(f"Saved {len(events)} events to {path} (NDJSON format)")


# ============================================================
# Org Members Generation
# ============================================================


def generate_org_members(
    members: list[dict[str, Any]] | None = None,
    include_all: bool = True,
) -> list[dict[str, Any]]:
    """Generate Org Members list mimicking GitHub API response.

    Args:
        members: Custom member list. If None, uses ALL_ORG_MEMBERS.
        include_all: If True, include all default members.

    Returns:
        List of member objects as returned by GitHub API /orgs/{org}/members
    """
    if members is None:
        members = ALL_ORG_MEMBERS if include_all else []

    org_members = []
    for member in members:
        member_data = {
            "login": member["name"],
            "id": member["id"],
            "node_id": f"MDQ6VXNlcn{member['id']}",
            "avatar_url": f"https://avatars.githubusercontent.com/u/{member['id']}?v=4",
            "gravatar_id": "",
            "url": f"https://api.github.com/users/{member['name']}",
            "html_url": f"https://github.com/{member['name']}",
            "followers_url": f"https://api.github.com/users/{member['name']}/followers",
            "following_url": f"https://api.github.com/users/{member['name']}/following{{/other_user}}",
            "gists_url": f"https://api.github.com/users/{member['name']}/gists{{/gist_id}}",
            "starred_url": f"https://api.github.com/users/{member['name']}/starred{{/owner}}{{/repo}}",
            "subscriptions_url": f"https://api.github.com/users/{member['name']}/subscriptions",
            "organizations_url": f"https://api.github.com/users/{member['name']}/orgs",
            "repos_url": f"https://api.github.com/users/{member['name']}/repos",
            "events_url": f"https://api.github.com/users/{member['name']}/events{{/privacy}}",
            "received_events_url": f"https://api.github.com/users/{member['name']}/received_events",
            "type": "User",
            "user_view_type": "public",
            "site_admin": False,
        }
        org_members.append(member_data)

    return org_members


def save_org_members(members: list[dict[str, Any]], path: Path) -> None:
    """Save Org Members list as JSON."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(members, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(members)} members to {path}")


# ============================================================
# Copilot Seats Generation
# ============================================================


def generate_copilot_seats(
    org_name: str,
    members: list[dict[str, Any]] | None = None,
    coverage_ratio: float = 0.8,
) -> dict[str, Any]:
    """Generate Copilot Seats data mimicking GitHub API response.

    Activity patterns:
    - Active (60%): last_activity within 1 month
    - Low activity (25%): last_activity 1-3 months ago
    - Dormant (10%): last_activity 3+ months ago
    - Never used (5%): pending_cancellation_date or null last_activity

    Args:
        org_name: Organization name for the Copilot data.
        members: Custom member list. If None, uses ALL_ORG_MEMBERS.
        coverage_ratio: Ratio of members who have Copilot seats (0.0-1.0).

    Returns:
        Copilot seats response object as returned by GitHub API.
    """
    if members is None:
        members = ALL_ORG_MEMBERS

    now = datetime.now(UTC)
    seats = []

    # Select members who have Copilot seats
    seat_count = int(len(members) * coverage_ratio)
    seated_members = random.sample(members, min(seat_count, len(members)))

    for member in seated_members:
        # Determine activity pattern
        pattern = random.random()
        if pattern < 0.60:
            # Active: within 1 month
            days_ago = random.randint(0, 30)
            last_activity = now - timedelta(days=days_ago)
            last_activity_editor = random.choice(COPILOT_EDITORS)
            pending_cancellation = None
        elif pattern < 0.85:
            # Low activity: 1-3 months ago
            days_ago = random.randint(31, 90)
            last_activity = now - timedelta(days=days_ago)
            last_activity_editor = random.choice(COPILOT_EDITORS)
            pending_cancellation = None
        elif pattern < 0.95:
            # Dormant: 3+ months ago
            days_ago = random.randint(91, 180)
            last_activity = now - timedelta(days=days_ago)
            last_activity_editor = random.choice(COPILOT_EDITORS)
            pending_cancellation = None
        else:
            # Never used: null last_activity or pending cancellation
            last_activity = None
            last_activity_editor = None
            # 50% chance of pending cancellation
            if random.random() < 0.5:
                pending_cancellation = (
                    now + timedelta(days=random.randint(1, 30))
                ).strftime("%Y-%m-%d")
            else:
                pending_cancellation = None

        # Created date (assigned date)
        created_days_ago = random.randint(30, 365)
        created_at = (now - timedelta(days=created_days_ago)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        # Updated date
        if last_activity:
            updated_at = last_activity.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            updated_at = created_at

        seat_data = {
            "created_at": created_at,
            "updated_at": updated_at,
            "pending_cancellation_date": pending_cancellation,
            "last_activity_at": last_activity.strftime("%Y-%m-%dT%H:%M:%SZ")
            if last_activity
            else None,
            "last_activity_editor": last_activity_editor,
            "assignee": {
                "login": member["name"],
                "id": member["id"],
                "node_id": f"MDQ6VXNlcn{member['id']}",
                "avatar_url": f"https://avatars.githubusercontent.com/u/{member['id']}?v=4",
                "gravatar_id": "",
                "url": f"https://api.github.com/users/{member['name']}",
                "html_url": f"https://github.com/{member['name']}",
                "type": "User",
                "site_admin": False,
            },
            "assigning_team": None,
            "organization": {
                "login": org_name,
                "id": ORG_ID,
                "node_id": f"MDEyOk9yZ2FuaXphdGlvbn{ORG_ID}",
                "url": f"https://api.github.com/orgs/{org_name}",
                "repos_url": f"https://api.github.com/orgs/{org_name}/repos",
                "events_url": f"https://api.github.com/orgs/{org_name}/events",
                "hooks_url": f"https://api.github.com/orgs/{org_name}/hooks",
                "issues_url": f"https://api.github.com/orgs/{org_name}/issues",
                "members_url": f"https://api.github.com/orgs/{org_name}/members{{/member}}",
                "public_members_url": f"https://api.github.com/orgs/{org_name}/public_members{{/member}}",
                "avatar_url": f"https://avatars.githubusercontent.com/u/{ORG_ID}?v=4",
                "description": f"{org_name} organization",
            },
        }
        seats.append(seat_data)

    # Sort by last_activity_at (most recent first, nulls last)
    seats.sort(
        key=lambda x: x["last_activity_at"] or "0000-00-00T00:00:00Z",
        reverse=True,
    )

    return {
        "total_seats": len(seats),
        "seats": seats,
    }


def save_copilot_seats(data: dict[str, Any], path: Path) -> None:
    """Save Copilot Seats data as JSON."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {data['total_seats']} Copilot seats to {path}")


def print_summary(events: list[dict[str, Any]]) -> None:
    """Print summary statistics of generated data."""
    print("\n" + "=" * 60)
    print("Generated Data Summary")
    print("=" * 60)

    print(f"\nTotal events: {len(events)}")

    # Time range
    timestamps = [e["@timestamp"] for e in events]
    start = datetime.fromtimestamp(min(timestamps) / 1000, tz=UTC)
    end = datetime.fromtimestamp(max(timestamps) / 1000, tz=UTC)
    print(f"Time range: {start.date()} to {end.date()}")

    # Action distribution
    actions: dict[str, int] = {}
    for e in events:
        action = e["action"]
        actions[action] = actions.get(action, 0) + 1

    print(f"\nUnique actions: {len(actions)}")
    print("\nTop 10 actions:")
    for action, count in sorted(actions.items(), key=lambda x: -x[1])[:10]:
        print(f"  {action}: {count}")

    # Actor distribution
    actors: dict[str, int] = {}
    for e in events:
        actor = e["actor"]
        actors[actor] = actors.get(actor, 0) + 1

    print(f"\nUnique actors: {len(actors)}")
    print("\nTop 10 actors:")
    for actor, count in sorted(actors.items(), key=lambda x: -x[1])[:10]:
        print(f"  {actor}: {count}")

    # Anomaly indicators
    late_night = sum(
        1
        for e in events
        if datetime.fromtimestamp(e["@timestamp"] / 1000, tz=UTC).hour >= 22
        or datetime.fromtimestamp(e["@timestamp"] / 1000, tz=UTC).hour < 6
    )
    dangerous = sum(1 for e in events if e["action"] in DANGEROUS_ACTIONS)
    weekend = sum(
        1
        for e in events
        if datetime.fromtimestamp(e["@timestamp"] / 1000, tz=UTC).weekday() >= 5
    )
    suspicious_country = sum(
        1 for e in events if e.get("country_code") in ["RU", "CN", "KP"]
    )

    print("\nAnomaly indicators:")
    print(f"  Late night events (22:00-06:00): {late_night}")
    print(f"  Dangerous actions: {dangerous}")
    print(f"  Weekend events: {weekend}")
    print(f"  Suspicious country access: {suspicious_country}")


# ============================================================
# CLI
# ============================================================


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate realistic GitHub test data (Audit Logs, Org Members, Copilot Seats)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate all data types
    python scripts/generate_test_data.py --all

    # Generate only audit logs
    python scripts/generate_test_data.py -n 10000 -o data/test.ndjson

    # Generate Org Members list
    python scripts/generate_test_data.py --generate-members

    # Generate Copilot Seats for multiple organizations
    python scripts/generate_test_data.py --generate-copilot --copilot-orgs acme-corp contoso
        """,
    )

    # Common options
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all data types (audit logs, org members, copilot seats)",
    )
    parser.add_argument(
        "--seed", "-s", type=int, default=None, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Output directory for all generated files (default: data)",
    )

    # Audit log options
    audit_group = parser.add_argument_group("Audit Log Options")
    audit_group.add_argument(
        "--count",
        "-n",
        type=int,
        default=10000,
        help="Number of audit log events to generate (default: 10000)",
    )
    audit_group.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output file path for audit logs (default: data/test_audit_log.ndjson)",
    )
    audit_group.add_argument(
        "--format",
        "-f",
        choices=["json", "ndjson"],
        default="ndjson",
        help="Output format for audit logs (default: ndjson)",
    )
    audit_group.add_argument(
        "--days",
        "-d",
        type=int,
        default=90,
        help="Number of days to span (default: 90)",
    )
    audit_group.add_argument(
        "--anomaly-ratio",
        "-a",
        type=float,
        default=0.05,
        help="Ratio of anomalous events (default: 0.05)",
    )

    # Org Members options
    members_group = parser.add_argument_group("Org Members Options")
    members_group.add_argument(
        "--generate-members",
        action="store_true",
        help="Generate Org Members list",
    )
    members_group.add_argument(
        "--members-output",
        type=Path,
        default=None,
        help="Output file path for org members (default: data/org_members.json)",
    )

    # Copilot Seats options
    copilot_group = parser.add_argument_group("Copilot Seats Options")
    copilot_group.add_argument(
        "--generate-copilot",
        action="store_true",
        help="Generate Copilot Seats data",
    )
    copilot_group.add_argument(
        "--copilot-orgs",
        nargs="+",
        default=["example-org"],
        help="Organization names for Copilot data (default: example-org)",
    )
    copilot_group.add_argument(
        "--copilot-coverage",
        type=float,
        default=0.8,
        help="Ratio of members with Copilot seats (default: 0.8)",
    )

    return parser


def _run_audit_log_generation(args: argparse.Namespace) -> None:
    """Generate audit log data."""
    output_path = args.output or args.data_dir / "test_audit_log.ndjson"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("Generating Audit Logs")
    print("=" * 60)
    print(f"Generating {args.count} events over {args.days} days...")

    events = generate_test_data(
        count=args.count,
        days_span=args.days,
        anomaly_ratio=args.anomaly_ratio,
    )

    if args.format == "json":
        save_as_json(events, output_path)
    else:
        save_as_ndjson(events, output_path)

    print_summary(events)


def _run_members_generation(args: argparse.Namespace) -> None:
    """Generate org members data."""
    members_output = args.members_output or args.data_dir / "org_members.json"
    members_output.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("Generating Org Members")
    print("=" * 60)

    members = generate_org_members()
    save_org_members(members, members_output)

    print(f"Generated {len(members)} organization members")
    print(f"  Admin users: {len(ADMIN_USERS)}")
    print(f"  Regular users: {len(REGULAR_USERS)}")
    print(f"  Dormant users: {len(DORMANT_USERS)}")


def _run_copilot_generation(args: argparse.Namespace) -> None:
    """Generate Copilot seats data."""
    print(f"\n{'='*60}")
    print("Generating Copilot Seats")
    print("=" * 60)

    for org_name in args.copilot_orgs:
        copilot_output = args.data_dir / f"copilot_seats_{org_name}.json"
        copilot_output.parent.mkdir(parents=True, exist_ok=True)

        copilot_data = generate_copilot_seats(
            org_name=org_name,
            coverage_ratio=args.copilot_coverage,
        )
        save_copilot_seats(copilot_data, copilot_output)

        # Activity summary
        seats = copilot_data["seats"]
        active_count = sum(1 for s in seats if s.get("last_activity_at"))
        never_used = sum(1 for s in seats if not s.get("last_activity_at"))
        pending = sum(1 for s in seats if s.get("pending_cancellation_date"))

        print(f"  Organization: {org_name}")
        print(f"    Total seats: {len(seats)}")
        print(f"    Active (has last_activity): {active_count}")
        print(f"    Never used: {never_used}")
        print(f"    Pending cancellation: {pending}")


def main() -> None:
    """Main entry point."""
    parser = _create_argument_parser()
    args = parser.parse_args()

    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    # Create output directory
    args.data_dir.mkdir(parents=True, exist_ok=True)

    # Determine what to generate
    generate_audit = not (args.generate_members or args.generate_copilot) or args.all
    generate_members = args.generate_members or args.all
    generate_copilot = args.generate_copilot or args.all

    # Run generators
    if generate_audit:
        _run_audit_log_generation(args)

    if generate_members:
        _run_members_generation(args)

    if generate_copilot:
        _run_copilot_generation(args)

    print(f"\n{'='*60}")
    print("Data generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
