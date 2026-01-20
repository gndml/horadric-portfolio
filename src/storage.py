"""JSON-based state persistence for alert cooldowns."""

import json
import os
from datetime import datetime, timedelta
from typing import Optional
from src.rules import Severity, get_cooldown_minutes


STATE_FILE = "state.json"


def _get_state_path() -> str:
    """Get path to state file."""
    # Look for state.json in current directory or project root
    if os.path.exists(STATE_FILE):
        return STATE_FILE
    project_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(project_root, STATE_FILE)


def load_state() -> dict:
    """Load state from JSON file."""
    state_path = _get_state_path()
    try:
        if os.path.exists(state_path):
            with open(state_path, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load state file: {e}")

    return {"last_alerts": {}, "version": 1}


def save_state(state: dict) -> None:
    """Save state to JSON file."""
    state_path = _get_state_path()
    try:
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except IOError as e:
        print(f"Warning: Could not save state file: {e}")


def should_fire(rule_name: str, severity: Severity) -> bool:
    """
    Check if an alert should fire based on cooldown.

    Returns True if:
    - Rule has never fired before
    - Enough time has passed since last fire (based on severity cooldown)
    """
    state = load_state()
    last_alerts = state.get("last_alerts", {})

    if rule_name not in last_alerts:
        return True

    last_fire_str = last_alerts[rule_name]
    try:
        last_fire = datetime.fromisoformat(last_fire_str)
    except (ValueError, TypeError):
        return True

    cooldown_minutes = get_cooldown_minutes(severity)
    cooldown_delta = timedelta(minutes=cooldown_minutes)

    return datetime.now() - last_fire >= cooldown_delta


def record_fire(rule_name: str) -> None:
    """Record that an alert was fired."""
    state = load_state()
    if "last_alerts" not in state:
        state["last_alerts"] = {}

    state["last_alerts"][rule_name] = datetime.now().isoformat()
    save_state(state)


def get_last_fire_time(rule_name: str) -> Optional[datetime]:
    """Get the last time a rule was fired."""
    state = load_state()
    last_alerts = state.get("last_alerts", {})

    if rule_name not in last_alerts:
        return None

    try:
        return datetime.fromisoformat(last_alerts[rule_name])
    except (ValueError, TypeError):
        return None


def clear_cooldowns() -> None:
    """Clear all cooldowns (for testing/reset)."""
    state = {"last_alerts": {}, "version": 1}
    save_state(state)


def get_cooldown_status() -> dict:
    """Get status of all cooldowns for debugging."""
    state = load_state()
    last_alerts = state.get("last_alerts", {})

    status = {}
    now = datetime.now()

    for rule_name, last_fire_str in last_alerts.items():
        try:
            last_fire = datetime.fromisoformat(last_fire_str)
            elapsed = now - last_fire
            status[rule_name] = {
                "last_fire": last_fire_str,
                "elapsed_minutes": elapsed.total_seconds() / 60,
            }
        except (ValueError, TypeError):
            status[rule_name] = {"last_fire": last_fire_str, "error": "invalid timestamp"}

    return status
