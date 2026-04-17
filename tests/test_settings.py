from pathlib import Path

from easyjlc import settings as settings_module
from easyjlc.settings import Settings


def test_defaults():
    s = Settings()
    assert s.theme == "system"
    assert s.language == "pt-BR"
    assert s.currency == "USD"
    assert s.cache_ttl_hours == 24
    assert s.output_dir is None
    assert s.recent_output_dirs == []


def test_round_trip(tmp_path: Path):
    path = tmp_path / "settings.json"
    s = Settings(output_dir="/tmp/out", theme="dark")
    s.add_recent_output("/tmp/out")
    s.add_recent_output("/tmp/other")
    settings_module.save(s, path)

    loaded = settings_module.load(path)
    assert loaded.output_dir == "/tmp/out"
    assert loaded.theme == "dark"
    assert loaded.recent_output_dirs == ["/tmp/other", "/tmp/out"]


def test_load_missing_returns_defaults(tmp_path: Path):
    loaded = settings_module.load(tmp_path / "missing.json")
    assert loaded == Settings()


def test_load_corrupt_returns_defaults(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid", encoding="utf-8")
    loaded = settings_module.load(path)
    assert loaded == Settings()


def test_recent_output_dedupe_and_limit():
    s = Settings()
    for i in range(12):
        s.add_recent_output(f"/tmp/p{i}", limit=5)
    assert len(s.recent_output_dirs) == 5
    assert s.recent_output_dirs[0] == "/tmp/p11"

    s.add_recent_output("/tmp/p10", limit=5)
    assert s.recent_output_dirs[0] == "/tmp/p10"
    assert s.recent_output_dirs.count("/tmp/p10") == 1


def test_from_dict_ignores_unknown_keys():
    s = Settings.from_dict({"theme": "dark", "bogus": 123})
    assert s.theme == "dark"
    assert not hasattr(s, "bogus")
