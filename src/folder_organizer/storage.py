"""JSON persistence: Permanent list with change history, Daily lists, window state.

data/
  permanent.json              current Permanent list
  permanent_history/<id>.json one snapshot per change (id = timestamp, sortable)
  daily/YYYY-MM-DD.json       one file per logical day; empty days have no file
  state.json                  window geometry, splitter sizes, always-on-top
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import FolderEntry, PermanentSnapshot

log = logging.getLogger(__name__)

SNAPSHOT_ID_FORMAT = "%Y-%m-%d_%H-%M-%S-%f"


class Storage:
    def __init__(self, data_dir: Path, max_snapshots: int = 1000) -> None:
        self.data_dir = Path(data_dir)
        self.daily_dir = self.data_dir / "daily"
        self.snapshot_dir = self.data_dir / "permanent_history"
        self.permanent_file = self.data_dir / "permanent.json"
        self.state_file = self.data_dir / "state.json"
        self.max_snapshots = max_snapshots

    def ensure(self) -> None:
        """Create the data folders and empty files on first run. Never overwrites."""
        for folder in (self.data_dir, self.daily_dir, self.snapshot_dir):
            folder.mkdir(parents=True, exist_ok=True)
        if not self.permanent_file.exists():
            _write_json(self.permanent_file, {"entries": []})
        if not self.state_file.exists():
            _write_json(self.state_file, {})

    # Permanent

    def load_permanent(self) -> list[FolderEntry]:
        data = _read_json(self.permanent_file)
        if data is None:
            snapshots = self.list_permanent_snapshots()
            if snapshots:
                log.warning("Using latest Permanent snapshot %s", snapshots[0].snapshot_id)
                return snapshots[0].entries
            return []
        return _parse_entries(data)

    def save_permanent(self, entries: Iterable[FolderEntry], action: str) -> bool:
        """Save the Permanent list and record a snapshot. Returns False if nothing changed."""
        entries = list(entries)
        if _same_entries(entries, self.load_permanent()):
            return False
        payload = [e.to_dict() for e in entries]
        _write_json(self.permanent_file, {"entries": payload})
        now = datetime.now()
        snapshot_id = self._new_snapshot_id(now)
        _write_json(
            self.snapshot_dir / f"{snapshot_id}.json",
            {"timestamp": now.isoformat(timespec="seconds"), "action": action, "entries": payload},
        )
        self._prune_snapshots()
        log.info("Permanent: %s", action)
        return True

    def list_permanent_snapshots(self) -> list[PermanentSnapshot]:
        """All snapshots, newest first."""
        snapshots = (self._read_snapshot(f) for f in reversed(self._snapshot_files()))
        return [s for s in snapshots if s is not None]

    def load_permanent_snapshot(self, snapshot_id: str) -> PermanentSnapshot | None:
        return self._read_snapshot(self.snapshot_dir / f"{snapshot_id}.json")

    def restore_permanent(self, snapshot_id: str) -> bool:
        """Make a snapshot the current list. The restore itself becomes a new snapshot."""
        snapshot = self.load_permanent_snapshot(snapshot_id)
        if snapshot is None:
            return False
        return self.save_permanent(
            snapshot.entries, f"restored version from {snapshot.timestamp:%Y-%m-%d %H:%M:%S}"
        )

    def _new_snapshot_id(self, now: datetime) -> str:
        while True:
            snapshot_id = now.strftime(SNAPSHOT_ID_FORMAT)
            if not (self.snapshot_dir / f"{snapshot_id}.json").exists():
                return snapshot_id
            now += timedelta(microseconds=1)

    def _snapshot_files(self) -> list[Path]:
        """Snapshot files, oldest first."""
        if not self.snapshot_dir.is_dir():
            return []
        return sorted(f for f in self.snapshot_dir.glob("*.json") if _parse_snapshot_id(f.stem))

    def _read_snapshot(self, file: Path) -> PermanentSnapshot | None:
        timestamp = _parse_snapshot_id(file.stem)
        data = _read_json(file)
        if timestamp is None or not isinstance(data, dict):
            return None
        return PermanentSnapshot(file.stem, timestamp, str(data.get("action", "")), _parse_entries(data))

    def _prune_snapshots(self) -> None:
        if self.max_snapshots <= 0:
            return
        for file in self._snapshot_files()[: -self.max_snapshots]:
            file.unlink(missing_ok=True)

    # Daily

    def load_day(self, day: date) -> list[FolderEntry]:
        data = _read_json(self._day_file(day))
        return _parse_entries(data) if data is not None else []

    def save_day(self, day: date, entries: Iterable[FolderEntry]) -> None:
        entries = list(entries)
        file = self._day_file(day)
        if not entries:
            file.unlink(missing_ok=True)  # empty days are not kept
            return
        _write_json(file, {"date": day.isoformat(), "entries": [e.to_dict() for e in entries]})

    def list_days(self) -> list[date]:
        """Days that have saved entries, oldest first."""
        if not self.daily_dir.is_dir():
            return []
        days = []
        for file in self.daily_dir.glob("*.json"):
            try:
                days.append(date.fromisoformat(file.stem))
            except ValueError:
                continue
        return sorted(days)

    def last_nonempty_day_before(self, day: date) -> date | None:
        earlier = [d for d in self.list_days() if d < day]
        return earlier[-1] if earlier else None

    def _day_file(self, day: date) -> Path:
        return self.daily_dir / f"{day.isoformat()}.json"

    # Window state

    def load_state(self) -> dict[str, Any]:
        data = _read_json(self.state_file)
        return data if isinstance(data, dict) else {}

    def save_state(self, state: dict[str, Any]) -> None:
        _write_json(self.state_file, state)


def _parse_snapshot_id(snapshot_id: str) -> datetime | None:
    try:
        return datetime.strptime(snapshot_id, SNAPSHOT_ID_FORMAT)
    except ValueError:
        return None


def _parse_entries(data: Any) -> list[FolderEntry]:
    items = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    entries = []
    for item in items:
        try:
            entries.append(FolderEntry.from_dict(item))
        except (KeyError, TypeError, ValueError):
            log.warning("Skipping invalid entry %r", item)
    return entries


def _same_entries(a: list[FolderEntry], b: list[FolderEntry]) -> bool:
    return [(e.label, e.path) for e in a] == [(e.label, e.path) for e in b]


def _read_json(path: Path) -> Any | None:
    """Read JSON. Missing file -> None. A corrupt file is moved aside (kept for recovery) -> None."""
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        backup = path.with_name(f"{path.name}.corrupt-{datetime.now():%Y%m%d-%H%M%S}")
        log.warning("Could not read %s (%s); moving it to %s", path, e, backup.name)
        try:
            path.replace(backup)
        except OSError:
            log.exception("Could not move %s aside", path)
        return None


def _write_json(path: Path, data: Any) -> None:
    """Atomic write: write a temp file, then replace the target."""
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)
