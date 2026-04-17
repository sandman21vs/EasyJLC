"""Histórico de downloads com persistência JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from easyjlc.config import history_path


@dataclass
class HistoryEntry:
    lcsc_id: str
    timestamp: str
    output_dir: str | None
    success: bool
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoryEntry":
        return cls(
            lcsc_id=str(data.get("lcsc_id", "")),
            timestamp=str(data.get("timestamp", "")),
            output_dir=data.get("output_dir"),
            success=bool(data.get("success", False)),
            message=str(data.get("message", "")),
        )


class History:
    def __init__(self, entries: list[HistoryEntry] | None = None) -> None:
        self.entries: list[HistoryEntry] = list(entries or [])

    def add(
        self,
        lcsc_id: str,
        output_dir: str | None,
        success: bool,
        message: str = "",
    ) -> HistoryEntry:
        entry = HistoryEntry(
            lcsc_id=lcsc_id,
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            output_dir=output_dir,
            success=success,
            message=message,
        )
        self.entries.insert(0, entry)
        return entry

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.entries):
            del self.entries[index]

    def clear(self) -> None:
        self.entries.clear()

    def to_list(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.entries]

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)


def load(path: Path | None = None) -> History:
    path = path or history_path()
    if not path.exists():
        return History()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return History()
    if not isinstance(raw, list):
        return History()
    entries = [HistoryEntry.from_dict(item) for item in raw if isinstance(item, dict)]
    return History(entries)


def save(history: History, path: Path | None = None) -> None:
    path = path or history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(history.to_list(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(path)
