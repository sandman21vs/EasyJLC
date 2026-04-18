import os
import time
from pathlib import Path

from easyjlc.core.artifacts import find_kicad_artifacts


def test_find_kicad_artifacts_returns_newest_files(tmp_path: Path):
    old_sym = tmp_path / "old.kicad_sym"
    new_sym = tmp_path / "nested" / "new.kicad_sym"
    old_mod = tmp_path / "old.kicad_mod"
    new_mod = tmp_path / "nested" / "new.kicad_mod"
    new_sym.parent.mkdir()

    for path in [old_sym, new_sym, old_mod, new_mod]:
        path.write_text("", encoding="utf-8")

    old = time.time() - 100
    now = time.time()
    os.utime(old_sym, (old, old))
    os.utime(old_mod, (old, old))
    os.utime(new_sym, (now, now))
    os.utime(new_mod, (now, now))

    artifacts = find_kicad_artifacts(tmp_path)
    assert artifacts.symbol == new_sym
    assert artifacts.footprint == new_mod
    assert artifacts.has_any is True
    assert artifacts.has_all is True


def test_find_kicad_artifacts_filters_by_mtime(tmp_path: Path):
    old_sym = tmp_path / "old.kicad_sym"
    old_sym.write_text("", encoding="utf-8")
    old = time.time() - 100
    os.utime(old_sym, (old, old))

    artifacts = find_kicad_artifacts(tmp_path, changed_since=time.time() - 10)
    assert artifacts.symbol is None
    assert artifacts.footprint is None
    assert artifacts.has_any is False
    assert artifacts.has_all is False


def test_find_kicad_artifacts_missing_root():
    artifacts = find_kicad_artifacts("/path/that/does/not/exist")
    assert artifacts.has_any is False
