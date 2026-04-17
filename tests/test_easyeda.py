import os
from pathlib import Path

from easyjlc.core import easyeda
from easyjlc.core.easyeda import EasyEdaRunner, _format_cmd, venv_python


def test_venv_python_platform(tmp_path: Path):
    py = venv_python(tmp_path)
    if os.name == "nt":
        assert py == tmp_path / "Scripts" / "python.exe"
    else:
        assert py == tmp_path / "bin" / "python"


def test_format_cmd_quotes_spaces():
    out = _format_cmd(["python", "-m", "easyeda2kicad", "--output", "/tmp/my out"])
    assert '"/tmp/my out"' in out
    assert out.startswith("python -m easyeda2kicad")


def test_runner_default_venv_dir_is_inside_data_dir(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(easyeda, "data_dir", lambda: tmp_path)
    runner = EasyEdaRunner()
    assert runner.venv_dir == tmp_path / "easyeda2kicad-venv"


def test_runner_cmd_none_before_resolve(tmp_path: Path):
    runner = EasyEdaRunner(venv_dir=tmp_path / "nope")
    assert runner.runner_cmd is None
    assert runner.is_ready() is False


def test_download_raises_on_empty_id(tmp_path: Path):
    runner = EasyEdaRunner(venv_dir=tmp_path / "nope")
    runner._runner_cmd = ["python", "-m", "easyeda2kicad"]  # evita resolve
    try:
        runner.download("", None)
    except easyeda.EasyEdaError:
        return
    raise AssertionError("Deveria ter levantado EasyEdaError")
