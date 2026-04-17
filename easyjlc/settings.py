"""Preferências do usuário com persistência JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from easyjlc.config import settings_path


@dataclass
class Settings:
    output_dir: str | None = None
    theme: str = "system"
    language: str = "pt-BR"
    currency: str = "USD"
    cache_ttl_hours: int = 24
    window_geometry: str | None = None
    recent_output_dirs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def add_recent_output(self, path: str, limit: int = 8) -> None:
        if path in self.recent_output_dirs:
            self.recent_output_dirs.remove(path)
        self.recent_output_dirs.insert(0, path)
        del self.recent_output_dirs[limit:]


def load(path: Path | None = None) -> Settings:
    path = path or settings_path()
    if not path.exists():
        return Settings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()
    return Settings.from_dict(raw)


def save(settings: Settings, path: Path | None = None) -> None:
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(settings.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(path)
