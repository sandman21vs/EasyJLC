from pathlib import Path

from easyjlc import history as history_module
from easyjlc.history import History


def test_add_and_order():
    h = History()
    h.add("C2040", "/tmp/out", success=True)
    h.add("C1234", "/tmp/out", success=False, message="404")

    assert len(h) == 2
    assert h.entries[0].lcsc_id == "C1234"
    assert h.entries[0].success is False
    assert h.entries[1].lcsc_id == "C2040"


def test_remove_and_clear():
    h = History()
    h.add("A", None, True)
    h.add("B", None, True)
    h.remove(0)
    assert [e.lcsc_id for e in h] == ["A"]
    h.clear()
    assert len(h) == 0


def test_round_trip(tmp_path: Path):
    path = tmp_path / "history.json"
    h = History()
    h.add("C2040", "/tmp/out", True, "ok")
    h.add("C1", None, False, "erro")
    history_module.save(h, path)

    loaded = history_module.load(path)
    assert len(loaded) == 2
    assert loaded.entries[0].lcsc_id == "C1"
    assert loaded.entries[1].output_dir == "/tmp/out"


def test_load_missing_returns_empty(tmp_path: Path):
    assert len(history_module.load(tmp_path / "missing.json")) == 0


def test_load_corrupt_returns_empty(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("xxx", encoding="utf-8")
    assert len(history_module.load(p)) == 0


def test_timestamp_is_iso8601():
    h = History()
    entry = h.add("C1", None, True)
    # Deve ser ISO 8601 com timezone; parse não lança
    from datetime import datetime

    parsed = datetime.fromisoformat(entry.timestamp)
    assert parsed.tzinfo is not None
