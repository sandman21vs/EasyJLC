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

    @property
    def has_all(self) -> bool:
        return self.symbol is not None and self.footprint is not None


def find_kicad_artifacts(
    root: str | Path,
    changed_since: float | None = None,
    lcsc_id: str | None = None,
) -> KiCadArtifacts:
    """Retorna os arquivos KiCad mais recentes encontrados em uma pasta."""
    base = Path(root).expanduser()
    if not base.exists() or not base.is_dir():
        return KiCadArtifacts()

    symbols = _matching_files(base, ".kicad_sym", changed_since, lcsc_id)
    footprints = _matching_files(base, ".kicad_mod", changed_since, lcsc_id)

    return KiCadArtifacts(
        symbol=_newest(symbols),
        footprint=_newest(footprints),
    )


def _matching_files(
    root: Path,
    suffix: str,
    changed_since: float | None,
    lcsc_id: str | None,
) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob(f"*{suffix}"):
        if not path.is_file():
            continue
        if changed_since is not None and path.stat().st_mtime < changed_since:
            continue
        if lcsc_id is not None and not _file_mentions_lcsc(path, lcsc_id):
            continue
        paths.append(path)
    return paths


def _newest(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    return max(paths, key=lambda path: path.stat().st_mtime)


def _file_mentions_lcsc(path: Path, lcsc_id: str) -> bool:
    needle = lcsc_id.strip().upper()
    if not needle:
        return True
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return needle in text.upper()
