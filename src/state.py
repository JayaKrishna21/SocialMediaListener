"""
Tracks the last successful run's timestamp so each daily run only collects
content posted since the previous run -- not a fixed 24h window that would
silently miss content if a run is ever late or fails.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_last_run(state_file: str) -> datetime:
    """
    Returns the timestamp of the last successful run.
    Falls back to (now - 24h) if no state file exists yet (first run).
    """
    path = Path(state_file)
    if not path.exists():
        return datetime.now(timezone.utc) - timedelta(hours=24)

    data = json.loads(path.read_text())
    return datetime.fromisoformat(data["last_run_utc"])


def save_last_run(state_file: str, timestamp: datetime) -> None:
    """
    Persists the given timestamp as the new 'last successful run' marker.
    Only call this AFTER a run has fully succeeded (all collectors ran,
    all rows written) -- never on partial failure, or you'll silently
    drop the gap on the next run.
    """
    path = Path(state_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_run_utc": timestamp.isoformat()}, indent=2))