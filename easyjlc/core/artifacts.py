"""Descoberta de arquivos KiCad gerados pelo easyeda2kicad."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KiCadArtifacts:
    symbol: Path | None = None
    footprint: Path | None = None

    @property
    def has_any(self) -> bool:
        return self.symbol is not None or self.footprint is not None


def find_kicad_artifacts(
    root: str | Path,
    changed_since: float | None = None,
) -> KiCadArtifacts:
    """Retorna os arquivos KiCad mais recentes encontrados em uma pasta."""
    base = Path(root).expanduser()
    if not base.exists() or not base.is_dir():
        return KiCadArtifacts()

    symbols = _matching_files(base, ".kicad_sym", changed_since)
    footprints = _matching_files(base, ".kicad_mod", changed_since)

    return KiCadArtifacts(
        symbol=_newest(symbols),
        footprint=_newest(footprints),
    )


def _matching_files(root: Path, suffix: str, changed_since: float | None) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob(f"*{suffix}"):
        if not path.is_file():
            continue
        if changed_since is not None and path.stat().st_mtime < changed_since:
            continue
        paths.append(path)
    return paths


def _newest(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    return max(paths, key=lambda path: path.stat().st_mtime)
