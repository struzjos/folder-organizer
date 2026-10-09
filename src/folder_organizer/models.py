"""Data classes shared by storage and UI."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def path_key(path: str) -> str:
    """Normalized form of a path for duplicate checks (case-insensitive on Windows)."""
    return os.path.normcase(os.path.normpath(path))


@dataclass
class FolderEntry:
    """One button: a custom name (label) that opens `path` in Explorer."""

    label: str
    path: str
    added_at: str = field(default_factory=now_iso)

    def key(self) -> str:
        return path_key(self.path)

    def to_dict(self) -> dict[str, str]:
        return {"label": self.label, "path": self.path, "added_at": self.added_at}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FolderEntry:
        label, path = data["label"], data["path"]
        if not isinstance(label, str) or not isinstance(path, str) or not path:
            raise ValueError(f"invalid entry: {data!r}")
        return cls(label=label, path=path, added_at=str(data.get("added_at", "")))


@dataclass(frozen=True)
class PermanentSnapshot:
    """One saved version of the Permanent list."""

    snapshot_id: str
    timestamp: datetime
    action: str
    entries: list[FolderEntry]
