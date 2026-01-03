#!/usr/bin/env python3
# scripts/generate_test_data.py
"""Generate realistic test data for GitHub Audit Log analysis.

This script generates synthetic data that mimics real GitHub data:
1. Audit Logs - Organization activity logs with various patterns
2. Org Members - Organization member list from GitHub API
3. Copilot Seats - Copilot seat assignment data for multiple organizations

Configuration is loaded from YAML files in scripts/config/:
- settings.yaml: Organization settings, defaults, user agents, etc.
- users.yaml: User definitions (admin, regular, bot, dormant, former, etc.)
- repositories.yaml: Repository definitions
- actions.yaml: Action definitions and weights

Usage:
    # Generate all data types (recommended for dormant user analysis)
    python scripts/generate_test_data.py --all

    # Generate only audit logs
    python scripts/generate_test_data.py -n 10000 -o data/test.json

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
from zoneinfo import ZoneInfo

import yaml


# タイムゾーン定義
# 時間生成はJSTベースで行い、最終的にUTCのUnix timestampに変換する
JST = ZoneInfo("Asia/Tokyo")


# ============================================================
# Configuration Loading
# ============================================================

# Path to config directory
CONFIG_DIR = Path(__file__).parent / "config"


def load_yaml_config(filename: str) -> dict[str, Any]:
    """Load a YAML configuration file.

    Args:
        filename: Name of the YAML file in the config directory.

    Returns:
        Parsed YAML content as a dictionary.
    """
    config_path = CONFIG_DIR / filename
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_config() -> dict[str, Any]:
    """Load all configuration files.

    Returns:
        Dictionary containing all configuration data.
    """
    return {
        "settings": load_yaml_config("settings.yaml"),
        "users": load_yaml_config("users.yaml"),
        "repositories": load_yaml_config("repositories.yaml"),
        "actions": load_yaml_config("actions.yaml"),
    }


# ============================================================
# Configuration Data Classes
# ============================================================


class Config:
    """Configuration container loaded from YAML files."""

    _instance: Config | None = None

    def __init__(self) -> None:
        """Initialize configuration from YAML files."""
        self._config = load_all_config()
        self._init_settings()
        self._init_users()
        self._init_repositories()
        self._init_actions()

    @classmethod
    def get_instance(cls) -> Config:
        """Get singleton instance of Config."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None

    def _init_settings(self) -> None:
        """Initialize settings from config."""
        settings = self._config["settings"]

        # Organization settings
        org = settings["organization"]
        self.org_name: str = org["name"]
        self.org_id: int = org["id"]

        # Defaults
        defaults = settings["defaults"]
        self.default_days: int = defaults["days"]
        self.default_event_count: int = defaults["event_count"]
        self.default_anomaly_ratio: float = defaults["anomaly_ratio"]
        self.default_copilot_coverage: float = defaults["copilot_coverage"]
        self.default_copilot_orgs: list[str] = defaults["copilot_orgs"]

        # User agents and editors
        self.user_agents: list[str] = settings["user_agents"]
        self.copilot_editors: list[str] = settings["copilot_editors"]

        # Countries
        self.countries: list[dict[str, str]] = settings["countries"]["normal"]
        self.suspicious_countries: list[dict[str, str]] = settings["countries"][
            "suspicious"
        ]

        # Teams
        self.teams: list[str] = settings["teams"]

    def _init_users(self) -> None:
        """Initialize user data from config."""
        users = self._config["users"]

        # Admin users
        self.admin_users: list[dict[str, Any]] = users["admin_users"]

        # Regular users (generated from pattern)
        self.regular_users: list[dict[str, Any]] = self._generate_regular_users(
            users["regular_users"]
        )

        # Bot users
        self.bot_users: list[dict[str, Any]] = users["bot_users"]

        # Suspicious user
        self.suspicious_user: dict[str, Any] = users["suspicious_user"]

        # Low activity users (generated from patterns)
        self.low_activity_users: list[dict[str, Any]] = (
            self._generate_low_activity_users(users["low_activity_users"])
        )

        # Dormant users (generated from patterns)
        self.dormant_users: list[dict[str, Any]] = self._generate_dormant_users(
            users["dormant_users"]
        )

        # Former users (generated from patterns)
        self.former_users: list[dict[str, Any]] = self._generate_former_users(
            users["former_users"]
        )

        # All org members (excludes former users and bots)
        self.all_org_members: list[dict[str, Any]] = (
            self.admin_users
            + self.regular_users
            + self.low_activity_users
            + self.dormant_users
        )

    def _generate_regular_users(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate regular users from pattern config."""
        users = []
        pattern = config["pattern"]
        start_id = config["start_id"]
        end_id = config["end_id"]
        user_id_start = config["user_id_start"]
        ip_prefix = config["ip_prefix"]

        for i in range(start_id, end_id + 1):
            name = pattern.format(id=i)
            user_id = user_id_start + (i - start_id)
            # Generate IP address
            ip_third = (i - 1) // 256
            ip_fourth = ((i - 1) % 256) + 1
            ip_pool = [f"{ip_prefix}.{ip_third}.{ip_fourth}"]

            users.append(
                {
                    "name": name,
                    "id": user_id,
                    "ip_pool": ip_pool,
                }
            )

        return users

    def _generate_low_activity_users(
        self, config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate low activity users from pattern config.

        Pattern-based generation:
        - period x events x copilot_states combinations
        - Naming: low-{period}-e{events:03d}-c{copilot}
        """
        users = []
        user_id = config["user_id_start"]
        ip_prefix = config["ip_prefix"]

        # Copilot state abbreviations for naming
        copilot_abbrev = {
            "none": "none",
            "1m": "1m",
            "3m": "3m",
            "6m": "6m",
            "null": "null",
        }

        for pattern in config["patterns"]:
            period = pattern["period"]
            for events in pattern["events"]:
                for copilot_state in pattern["copilot_states"]:
                    abbrev = copilot_abbrev.get(copilot_state, copilot_state)
                    name = f"low-{period}-e{events:03d}-c{abbrev}"
                    ip_offset = user_id - config["user_id_start"]
                    users.append(
                        {
                            "name": name,
                            "id": user_id,
                            "ip_pool": [
                                f"{ip_prefix}.{ip_offset // 256}.{(ip_offset % 256) + 1}"
                            ],
                            "events_per_month": events,
                            "copilot_state": copilot_state,
                            "period": period,
                        }
                    )
                    user_id += 1

        return users

    def _generate_dormant_users(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate dormant users from pattern config.

        Pattern-based generation:
        - activity type: historical_events x copilot_states
        - invite_only type: copilot_states only
        - Naming: dormant-a{activity}-c{copilot}
        """
        users = []
        user_id = config["user_id_start"]
        ip_prefix = config["ip_prefix"]

        # Activity level abbreviations
        activity_abbrev = {10: "010", 100: "100", 1000: "1k"}
        copilot_abbrev = {
            "none": "none",
            "1m": "1m",
            "3m": "3m",
            "6m": "6m",
            "null": "null",
        }

        for pattern in config["patterns"]:
            pattern_type = pattern["type"]

            if pattern_type == "activity":
                for events in pattern["historical_events"]:
                    for copilot_state in pattern["copilot_states"]:
                        a_abbrev = activity_abbrev.get(events, str(events))
                        c_abbrev = copilot_abbrev.get(copilot_state, copilot_state)
                        name = f"dormant-a{a_abbrev}-c{c_abbrev}"
                        ip_offset = user_id - config["user_id_start"]
                        users.append(
                            {
                                "name": name,
                                "id": user_id,
                                "ip_pool": [
                                    f"{ip_prefix}.{ip_offset // 256}.{(ip_offset % 256) + 1}"
                                ],
                                "historical_events": events,
                                "copilot_state": copilot_state,
                                "invite_only": False,
                            }
                        )
                        user_id += 1

            elif pattern_type == "invite_only":
                for copilot_state in pattern["copilot_states"]:
                    c_abbrev = copilot_abbrev.get(copilot_state, copilot_state)
                    name = f"dormant-ainv-c{c_abbrev}"
                    ip_offset = user_id - config["user_id_start"]
                    users.append(
                        {
                            "name": name,
                            "id": user_id,
                            "ip_pool": [
                                f"{ip_prefix}.{ip_offset // 256}.{(ip_offset % 256) + 1}"
                            ],
                            "historical_events": 0,
                            "copilot_state": copilot_state,
                            "invite_only": True,
                        }
                    )
                    user_id += 1

        return users

    def _generate_former_users(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate former users from pattern config.

        Pattern-based generation:
        - exit_months x events_per_month x copilot_states = 36 systematic users
        - Plus random users to reach target count
        - Naming: former-x{exit}m-e{events:03d}-c{copilot}
        """
        users = []
        user_id = config["user_id_start"]
        ip_prefix = config["ip_prefix"]
        patterns = config["patterns"]

        # Copilot state abbreviations for naming
        copilot_abbrev = {
            "none": "none",
            "pre-1m": "p1m",
            "pre-3m": "p3m",
            "unused": "unu",
        }

        # Generate systematic users from patterns
        for exit_month in patterns["exit_months"]:
            for events in patterns["events_per_month"]:
                for copilot_state in patterns["copilot_states"]:
                    c_abbrev = copilot_abbrev.get(copilot_state, copilot_state)
                    name = f"former-x{exit_month}m-e{events:03d}-c{c_abbrev}"
                    ip_offset = user_id - config["user_id_start"]
                    users.append(
                        {
                            "name": name,
                            "id": user_id,
                            "ip_pool": [
                                f"{ip_prefix}.{ip_offset // 256}.{(ip_offset % 256) + 1}"
                            ],
                            "exit_months_ago": exit_month,
                            "events_per_month": events,
                            "copilot_state": copilot_state,
                        }
                    )
                    user_id += 1

        # Generate random users
        random_config = config["random_users"]
        random_count = random_config["count"]
        name_pattern = random_config["name_pattern"]

        for i in range(random_count):
            name = name_pattern.format(id=i + 1)
            ip_offset = user_id - config["user_id_start"]
            users.append(
                {
                    "name": name,
                    "id": user_id,
                    "ip_pool": [
                        f"{ip_prefix}.{ip_offset // 256}.{(ip_offset % 256) + 1}"
                    ],
                    "exit_months_ago": random.choice(patterns["exit_months"]),
                    "events_per_month": random.choice(patterns["events_per_month"]),
                    "copilot_state": random.choice(patterns["copilot_states"]),
                }
            )
            user_id += 1

        return users

    def _init_repositories(self) -> None:
        """Initialize repository data from config."""
        repos_config = self._config["repositories"]
        self.repositories: list[dict[str, Any]] = []

        # Generate repositories from patterns
        for pattern_config in repos_config["repositories"]:
            pattern = pattern_config["pattern"]
            start_id = pattern_config["start_id"]
            end_id = pattern_config["end_id"]
            repo_id_start = pattern_config["repo_id_start"]
            visibility = pattern_config["visibility"]

            for i in range(start_id, end_id + 1):
                name = pattern.format(id=i)
                repo_id = repo_id_start + (i - start_id)
                self.repositories.append(
                    {
                        "name": f"{self.org_name}/{name}",
                        "id": repo_id,
                        "visibility": visibility,
                    }
                )

    def _init_actions(self) -> None:
        """Initialize action data from config."""
        actions_config = self._config["actions"]

        # Normal actions with weights
        self.normal_actions: list[tuple[str, float]] = [
            (a["action"], a["weight"]) for a in actions_config["normal_actions"]
        ]

        # Dangerous actions
        self.dangerous_actions: list[str] = actions_config["dangerous_actions"]


# ============================================================
# Global config accessor (for backward compatibility)
# ============================================================


def get_config() -> Config:
    """Get the global configuration instance."""
    return Config.get_instance()


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

    時間生成はJSTベースで行い、最終的にUTCに変換して返す。
    これにより、営業時間や深夜時間が日本時間で正しく反映される。

    Args:
        base_time: Base datetime to generate around (UTC)
        business_hours: Generate during business hours (JST 9:00-18:00)
        late_night: Generate during late night (JST 22:00-06:00)
        weekend: Generate on weekend (JST)

    Returns:
        Generated datetime with UTC timezone
    """
    # JSTに変換して日付・曜日を調整
    base_time_jst = base_time.astimezone(JST)

    # Adjust day of week (based on JST)
    if weekend:
        # Move to Saturday or Sunday
        days_to_weekend = (5 - base_time_jst.weekday()) % 7
        if days_to_weekend == 0:
            days_to_weekend = random.choice([0, 1])  # Saturday or Sunday
        base_time_jst = base_time_jst + timedelta(days=days_to_weekend)
    elif base_time_jst.weekday() >= 5:
        # Move to Monday if currently weekend
        days_to_monday = (7 - base_time_jst.weekday()) % 7
        base_time_jst = base_time_jst + timedelta(days=days_to_monday)

    # Adjust hour (JST hours)
    if late_night:
        # JST 22:00-05:59 (深夜・早朝)
        hour = random.choice([22, 23, 0, 1, 2, 3, 4, 5])
    elif business_hours:
        # JST 9:00-17:59 (営業時間)
        hour = random.randint(9, 17)
    else:
        hour = random.randint(0, 23)

    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    # JSTで時刻を設定し、UTCに変換して返す
    result_jst = base_time_jst.replace(hour=hour, minute=minute, second=second)
    return result_jst.astimezone(UTC)


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
    cfg = get_config()
    action = weighted_choice(cfg.normal_actions)
    user = random.choice(cfg.regular_users + cfg.admin_users + cfg.bot_users)
    repo = random.choice(cfg.repositories)
    country = random.choice(cfg.countries)

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
        "org": cfg.org_name,
        "org_id": cfg.org_id,
        "operation_type": _get_operation_type(action),
        "user_agent": random.choice(cfg.user_agents),
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
        event["team"] = random.choice(cfg.teams)

    # Add user info for member actions
    if "member" in action:
        target_user = random.choice(cfg.regular_users)
        event["user"] = target_user["name"]
        event["user_id"] = target_user["id"]

    return event


def generate_late_night_event(timestamp: datetime) -> dict[str, Any]:
    """Generate a late night (anomalous) event."""
    cfg = get_config()
    # Late night events are more likely to be from suspicious users
    if random.random() < 0.3:
        user = cfg.suspicious_user
        country = random.choice(cfg.suspicious_countries)
    else:
        user = random.choice(cfg.admin_users)  # Admins sometimes work late
        country = random.choice(cfg.countries)

    action = weighted_choice(cfg.normal_actions)

    # Higher chance of dangerous actions at night
    if random.random() < 0.1:
        action = random.choice(cfg.dangerous_actions)

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
        "org": cfg.org_name,
        "org_id": cfg.org_id,
        "operation_type": _get_operation_type(action),
        "user_agent": random.choice(cfg.user_agents),
        "_document_id": generate_document_id(),
        "request_id": generate_request_id(),
        "created_at": int(timestamp.timestamp() * 1000),
    }

    # Add repo info
    repo = random.choice(cfg.repositories)
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
    cfg = get_config()
    events = []
    user = random.choice([*cfg.admin_users, cfg.suspicious_user])
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
            "org": cfg.org_name,
            "org_id": cfg.org_id,
            "operation_type": "access",
            "user_agent": random.choice(cfg.user_agents),
            "_document_id": generate_document_id(),
            "request_id": generate_request_id(),
            "created_at": int(timestamp.timestamp() * 1000),
        }

        repo = random.choice(cfg.repositories)
        event["repo"] = repo["name"]
        event["repo_id"] = repo["id"]

        events.append(event)

    return events


def generate_dangerous_action_event(timestamp: datetime) -> dict[str, Any]:
    """Generate a dangerous action event."""
    cfg = get_config()
    action = random.choice(cfg.dangerous_actions)

    # Dangerous actions mostly by admins, sometimes suspicious
    if random.random() < 0.2:
        user = cfg.suspicious_user
        country = random.choice(cfg.suspicious_countries)
    else:
        user = random.choice(cfg.admin_users)
        country = random.choice(cfg.countries)

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
        "org": cfg.org_name,
        "org_id": cfg.org_id,
        "operation_type": _get_operation_type(action),
        "user_agent": random.choice(cfg.user_agents),
        "_document_id": generate_document_id(),
        "request_id": generate_request_id(),
        "created_at": int(timestamp.timestamp() * 1000),
    }

    repo = random.choice(cfg.repositories)
    if action.startswith(("repo.", "protected_branch.", "hook.", "secret_scanning.")):
        event["repo"] = repo["name"]
        event["repo_id"] = repo["id"]

    if action.startswith("team."):
        event["team"] = random.choice(cfg.teams)

    if "member" in action:
        target_user = random.choice(cfg.regular_users)
        event["user"] = target_user["name"]
        event["user_id"] = target_user["id"]

    return event


def generate_weekend_event(timestamp: datetime) -> dict[str, Any]:
    """Generate a weekend activity event (anomaly)."""
    cfg = get_config()
    timestamp = generate_timestamp(timestamp, weekend=True, business_hours=False)

    # Weekend events from various sources
    if random.random() < 0.4:
        user = random.choice(cfg.bot_users)  # Bots work on weekends
    elif random.random() < 0.3:
        user = cfg.suspicious_user
    else:
        user = random.choice(cfg.admin_users + cfg.regular_users)

    action = weighted_choice(cfg.normal_actions)

    event = {
        "@timestamp": int(timestamp.timestamp() * 1000),
        "action": action,
        "actor": user["name"],
        "actor_id": user["id"],
        "actor_ip": random.choice(user["ip_pool"]),
        "actor_is_bot": user["name"].endswith("[bot]"),
        "org": cfg.org_name,
        "org_id": cfg.org_id,
        "operation_type": _get_operation_type(action),
        "user_agent": random.choice(cfg.user_agents),
        "_document_id": generate_document_id(),
        "request_id": generate_request_id(),
        "created_at": int(timestamp.timestamp() * 1000),
    }

    repo = random.choice(cfg.repositories)
    if action.startswith(("repo.", "git.", "pull_request.")):
        event["repo"] = repo["name"]
        event["repo_id"] = repo["id"]

    return event


def generate_unusual_ip_event(timestamp: datetime) -> dict[str, Any]:
    """Generate event from unusual IP (anomaly)."""
    cfg = get_config()
    user = random.choice(cfg.regular_users + cfg.admin_users)
    # Use an unusual IP not in the user's normal pool
    unusual_ip = f"198.51.100.{random.randint(1, 254)}"
    country = random.choice(cfg.suspicious_countries)

    action = weighted_choice(cfg.normal_actions)

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
        "org": cfg.org_name,
        "org_id": cfg.org_id,
        "operation_type": _get_operation_type(action),
        "user_agent": random.choice(cfg.user_agents),
        "_document_id": generate_document_id(),
        "request_id": generate_request_id(),
        "created_at": int(timestamp.timestamp() * 1000),
    }

    repo = random.choice(cfg.repositories)
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
        members: Custom member list. If None, uses all org members from config.
        include_all: If True, include all default members.

    Returns:
        List of member objects as returned by GitHub API /orgs/{org}/members
    """
    cfg = get_config()
    if members is None:
        members = cfg.all_org_members if include_all else []

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
        members: Custom member list. If None, uses all org members from config.
        coverage_ratio: Ratio of members who have Copilot seats (0.0-1.0).

    Returns:
        Copilot seats response object as returned by GitHub API.
    """
    cfg = get_config()
    if members is None:
        members = cfg.all_org_members

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
            last_activity_editor = random.choice(cfg.copilot_editors)
            pending_cancellation = None
        elif pattern < 0.85:
            # Low activity: 1-3 months ago
            days_ago = random.randint(31, 90)
            last_activity = now - timedelta(days=days_ago)
            last_activity_editor = random.choice(cfg.copilot_editors)
            pending_cancellation = None
        elif pattern < 0.95:
            # Dormant: 3+ months ago
            days_ago = random.randint(91, 180)
            last_activity = now - timedelta(days=days_ago)
            last_activity_editor = random.choice(cfg.copilot_editors)
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
                "id": cfg.org_id,
                "node_id": f"MDEyOk9yZ2FuaXphdGlvbn{cfg.org_id}",
                "url": f"https://api.github.com/orgs/{org_name}",
                "repos_url": f"https://api.github.com/orgs/{org_name}/repos",
                "events_url": f"https://api.github.com/orgs/{org_name}/events",
                "hooks_url": f"https://api.github.com/orgs/{org_name}/hooks",
                "issues_url": f"https://api.github.com/orgs/{org_name}/issues",
                "members_url": f"https://api.github.com/orgs/{org_name}/members{{/member}}",
                "public_members_url": f"https://api.github.com/orgs/{org_name}/public_members{{/member}}",
                "avatar_url": f"https://avatars.githubusercontent.com/u/{cfg.org_id}?v=4",
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

    # Anomaly indicators (JST基準で判定)
    cfg = get_config()

    def get_jst_hour(timestamp_ms: int) -> int:
        """タイムスタンプからJSTの時間を取得。"""
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).astimezone(JST).hour

    def get_jst_weekday(timestamp_ms: int) -> int:
        """タイムスタンプからJSTの曜日を取得。"""
        return (
            datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
            .astimezone(JST)
            .weekday()
        )

    late_night = sum(
        1
        for e in events
        if get_jst_hour(e["@timestamp"]) >= 22 or get_jst_hour(e["@timestamp"]) < 6
    )
    dangerous = sum(1 for e in events if e["action"] in cfg.dangerous_actions)
    weekend = sum(1 for e in events if get_jst_weekday(e["@timestamp"]) >= 5)
    suspicious_codes = [c["code"] for c in cfg.suspicious_countries]
    suspicious_country = sum(
        1 for e in events if e.get("country_code") in suspicious_codes
    )

    print("\nAnomaly indicators (JST基準):")
    print(f"  Late night events (JST 22:00-06:00): {late_night}")
    print(f"  Dangerous actions: {dangerous}")
    print(f"  Weekend events (JST): {weekend}")
    print(f"  Suspicious country access: {suspicious_country}")


# ============================================================
# CLI
# ============================================================


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    # Load config for defaults
    cfg = get_config()

    parser = argparse.ArgumentParser(
        description="Generate realistic GitHub test data (Audit Logs, Org Members, Copilot Seats)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate all data types
    python scripts/generate_test_data.py --all

    # Generate only audit logs
    python scripts/generate_test_data.py -n 10000 -o data/test.json

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
        default=cfg.default_event_count,
        help=f"Number of audit log events to generate (default: {cfg.default_event_count})",
    )
    audit_group.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output file path for audit logs (default: data/test_audit_log.json)",
    )
    audit_group.add_argument(
        "--format",
        "-f",
        choices=["json", "ndjson"],
        default="json",
        help="Output format for audit logs (default: json)",
    )
    audit_group.add_argument(
        "--days",
        "-d",
        type=int,
        default=cfg.default_days,
        help=f"Number of days to span (default: {cfg.default_days})",
    )
    audit_group.add_argument(
        "--anomaly-ratio",
        "-a",
        type=float,
        default=cfg.default_anomaly_ratio,
        help=f"Ratio of anomalous events (default: {cfg.default_anomaly_ratio})",
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
        default=None,  # Will be set based on --all flag
        help=f"Organization names for Copilot data (default with --all: {', '.join(cfg.default_copilot_orgs)})",
    )
    copilot_group.add_argument(
        "--copilot-coverage",
        type=float,
        default=cfg.default_copilot_coverage,
        help=f"Ratio of members with Copilot seats (default: {cfg.default_copilot_coverage})",
    )

    return parser


def _run_audit_log_generation(args: argparse.Namespace) -> None:
    """Generate audit log data."""
    output_path = args.output or args.data_dir / "test_audit_log.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
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
    cfg = get_config()
    members_output = args.members_output or args.data_dir / "org_members.json"
    members_output.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("Generating Org Members")
    print("=" * 60)

    members = generate_org_members()
    save_org_members(members, members_output)

    print(f"Generated {len(members)} organization members")
    print(f"  Admin users: {len(cfg.admin_users)}")
    print(f"  Regular users: {len(cfg.regular_users)}")
    print(f"  Low activity users: {len(cfg.low_activity_users)}")
    print(f"  Dormant users: {len(cfg.dormant_users)}")


def _run_copilot_generation(args: argparse.Namespace) -> None:
    """Generate Copilot seats data."""
    print(f"\n{'=' * 60}")
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

    # Load config
    cfg = get_config()

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

    # Set copilot orgs based on --all flag
    if args.copilot_orgs is None:
        if args.all:
            args.copilot_orgs = cfg.default_copilot_orgs
        else:
            args.copilot_orgs = [cfg.org_name]

    # Run generators
    if generate_audit:
        _run_audit_log_generation(args)

    if generate_members:
        _run_members_generation(args)

    if generate_copilot:
        _run_copilot_generation(args)

    print(f"\n{'=' * 60}")
    print("Data generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
