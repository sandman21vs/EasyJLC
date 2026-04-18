"""Cache simples em disco com TTL — JSON por chave."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from easyjlc.config import cache_dir

log = logging.getLogger("easyjlc.cache")


class DiskCache:
    """Armazena payloads JSON por chave, expira por mtime + TTL."""

    def __init__(
        self,
        namespace: str,
        ttl_seconds: int = 24 * 3600,
        root: Path | None = None,
    ) -> None:
        base = root if root is not None else cache_dir()
        self.dir = base / namespace
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = max(0, ttl_seconds)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return self.dir / f"{digest}.json"

    def get(self, key: str) -> Any | None:
        return self._get(key, respect_ttl=True)

    def get_stale(self, key: str) -> Any | None:
        """Retorna cache mesmo expirado; útil como fallback quando a API falha."""
        return self._get(key, respect_ttl=False)

    def _get(self, key: str, respect_ttl: bool) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        if respect_ttl and self.ttl_seconds > 0:
            age = time.time() - path.stat().st_mtime
            if age > self.ttl_seconds:
                return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Cache corrompido em %s: %s", path, exc)
            return None

    def set(self, key: str, value: Any) -> None:
        path = self._path(key)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(value, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp.replace(path)
        except OSError as exc:
            log.warning("Falha ao gravar cache %s: %s", path, exc)

    def clear(self) -> None:
        for p in self.dir.glob("*.json"):
            try:
                p.unlink()
            except OSError:
                pass
