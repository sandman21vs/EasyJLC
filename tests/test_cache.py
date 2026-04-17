import os
import time
from pathlib import Path

from easyjlc.core.cache import DiskCache


def test_set_and_get_round_trip(tmp_path: Path):
    c = DiskCache("unit", root=tmp_path)
    c.set("abc", {"hello": "world", "n": 3})
    assert c.get("abc") == {"hello": "world", "n": 3}


def test_missing_returns_none(tmp_path: Path):
    c = DiskCache("unit", root=tmp_path)
    assert c.get("nope") is None


def test_ttl_expires(tmp_path: Path):
    c = DiskCache("unit", ttl_seconds=1, root=tmp_path)
    c.set("k", [1, 2, 3])
    # Força mtime antigo.
    p = c._path("k")
    old = time.time() - 10
    os.utime(p, (old, old))
    assert c.get("k") is None


def test_clear_removes_entries(tmp_path: Path):
    c = DiskCache("unit", root=tmp_path)
    c.set("a", 1)
    c.set("b", 2)
    c.clear()
    assert c.get("a") is None
    assert c.get("b") is None


def test_corrupt_file_returns_none(tmp_path: Path):
    c = DiskCache("unit", root=tmp_path)
    c.set("k", {"ok": True})
    p = c._path("k")
    p.write_text("not-json", encoding="utf-8")
    assert c.get("k") is None


def test_namespace_isolation(tmp_path: Path):
    a = DiskCache("ns_a", root=tmp_path)
    b = DiskCache("ns_b", root=tmp_path)
    a.set("shared", "A")
    b.set("shared", "B")
    assert a.get("shared") == "A"
    assert b.get("shared") == "B"
