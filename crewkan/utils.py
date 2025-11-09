# utils.py - Shared utilities for CrewKan

from pathlib import Path
from datetime import datetime, timezone
import yaml
import uuid


def now_iso():
    """Return current time in ISO format with Z suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path, default=None):
    """Load YAML file, returning default if file doesn't exist."""
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: dict):
    """Save data to YAML file, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def generate_task_id(prefix="T"):
    """Generate a unique task ID with timestamp and random suffix."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"{prefix}-{ts}-{suffix}"

