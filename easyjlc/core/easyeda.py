"""Runner para easyeda2kicad — venv isolado + subprocess com streaming."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Callable, Iterable, Sequence

from easyjlc.config import data_dir

log = logging.getLogger("easyjlc.easyeda")

LogCallback = Callable[[str], None]

_NO_WINDOW: dict = (
    {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
)

DEFAULT_EXTRA_PACKAGES: tuple[str, ...] = (
    "typing_extensions>=4.14.1",
    "pydantic>=2.11",
    "pydantic-core>=2.33",
    "easyeda2kicad",
)


def default_venv_dir() -> Path:
    return data_dir() / "easyeda2kicad-venv"


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _bootstrap_python() -> str | None:
    """Interpretador a usar para criar o venv do easyeda2kicad.

    Em dev usamos `sys.executable`. Em build PyInstaller isso aponta para o
    próprio binário (que não é um Python funcional), então caímos para um
    `python3`/`python` do PATH.
    """
    if getattr(sys, "frozen", False):
        for name in ("python3", "python"):
            found = shutil.which(name)
            if found:
                return found
        return None
    return sys.executable


class EasyEdaError(RuntimeError):
    """Erro levantado por falhas no runner easyeda2kicad."""


class EasyEdaRunner:
    """Resolve e executa o easyeda2kicad num venv isolado gerido pelo app."""

    def __init__(
        self,
        venv_dir: Path | None = None,
        extra_packages: Sequence[str] = DEFAULT_EXTRA_PACKAGES,
    ) -> None:
        self.venv_dir = venv_dir or default_venv_dir()
        self.extra_packages = tuple(extra_packages)
        self._runner_cmd: list[str] | None = None

    @property
    def runner_cmd(self) -> list[str] | None:
        return list(self._runner_cmd) if self._runner_cmd else None

    def is_ready(self) -> bool:
        return self._runner_cmd is not None and _runner_responds(self._runner_cmd)

    def resolve(self, log_cb: LogCallback | None = None) -> list[str]:
        """Devolve o comando pronto para rodar easyeda2kicad, instalando se necessário."""
        cb = log_cb or (lambda line: None)

        # 1) Venv local do app, se existir e funcional.
        py_in_venv = venv_python(self.venv_dir)
        if py_in_venv.exists():
            candidate = [str(py_in_venv), "-m", "easyeda2kicad"]
            if _runner_responds(candidate):
                self._runner_cmd = candidate
                return candidate
            cb(f'Venv "{self.venv_dir}" parece quebrado. Reinstalando...')
            candidate = self._create_and_install_venv(cb)
            if candidate:
                self._runner_cmd = candidate
                return candidate

        # 2) Python do sistema (caso o usuário já tenha instalado).
        if not getattr(sys, "frozen", False):
            sys_candidate = [sys.executable, "-m", "easyeda2kicad"]
            if _runner_responds(sys_candidate):
                self._runner_cmd = sys_candidate
                return sys_candidate

        # 3) CLI global instalada.
        cli = shutil.which("easyeda2kicad")
        if cli and _runner_responds([cli]):
            self._runner_cmd = [cli]
            return [cli]

        # 4) Última tentativa: criar venv novo.
        cb(f'Instalando easyeda2kicad em "{self.venv_dir}" (primeira execução pode demorar)...')
        candidate = self._create_and_install_venv(cb)
        if not candidate:
            raise EasyEdaError(
                "Não consegui localizar nem instalar o easyeda2kicad. "
                "Verifique conexão com a internet e pip."
            )
        self._runner_cmd = candidate
        return candidate

    def download(
        self,
        lcsc_id: str,
        output_dir: Path | None,
        log_cb: LogCallback | None = None,
    ) -> int:
        """Executa um download. Retorna o exit code do easyeda2kicad."""
        cb = log_cb or (lambda line: None)
        if not lcsc_id:
            raise EasyEdaError("LCSC ID vazio.")

        runner = self._runner_cmd or self.resolve(cb)

        cmd: list[str] = [
            *runner,
            "--full",
            "--overwrite",
            f"--lcsc_id={lcsc_id}",
        ]
        if output_dir is not None:
            cmd.extend(["--output", str(output_dir)])

        cb(f"$ {_format_cmd(cmd)}")
        return _run_streaming(cmd, cb)

    def _create_and_install_venv(self, cb: LogCallback) -> list[str] | None:
        py = venv_python(self.venv_dir)
        if not py.exists():
            cb(f'Criando virtualenv em "{self.venv_dir}"...')
            bootstrap = _bootstrap_python()
            if bootstrap is None:
                cb(
                    "Python 3 não encontrado no PATH. "
                    "Instale python3 para habilitar os downloads."
                )
                return None
            try:
                if getattr(sys, "frozen", False):
                    # Em build PyInstaller chamamos o python do sistema via subprocess
                    # para não usar o módulo `venv` interno (que depende de `sys.executable`).
                    if _run_streaming(
                        [bootstrap, "-m", "venv", str(self.venv_dir)], cb
                    ) != 0:
                        cb("Falha ao criar venv via python3 -m venv.")
                        return None
                else:
                    venv.EnvBuilder(with_pip=True).create(str(self.venv_dir))
            except Exception as exc:  # pragma: no cover — depende de SO
                cb(f"Falha ao criar venv: {exc}")
                return None

        cb("Atualizando pip/setuptools/wheel...")
        if _run_streaming(
            [str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
            cb,
        ) != 0:
            cb("Falha ao atualizar pip no venv.")
            return None

        cb("Instalando easyeda2kicad e dependências...")
        if _run_streaming(
            [str(py), "-m", "pip", "install", "--upgrade", *self.extra_packages],
            cb,
        ) != 0:
            cb("Falha ao instalar easyeda2kicad.")
            return None

        candidate = [str(py), "-m", "easyeda2kicad"]
        if not _runner_responds(candidate):
            cb("easyeda2kicad ainda indisponível após instalação.")
            return None

        return candidate


def _runner_responds(cmd: Sequence[str]) -> bool:
    try:
        result = subprocess.run(
            [*cmd, "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _run_streaming(cmd: Sequence[str], cb: LogCallback) -> int:
    try:
        proc = subprocess.Popen(
            list(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            **_NO_WINDOW,
        )
    except OSError as exc:
        cb(f"Falha ao iniciar processo: {exc}")
        return 1

    assert proc.stdout is not None
    for line in proc.stdout:
        cb(line.rstrip())
    proc.stdout.close()
    return proc.wait()


def _format_cmd(cmd: Iterable[str]) -> str:
    parts = []
    for p in cmd:
        s = str(p)
        if " " in s:
            s = f'"{s}"'
        parts.append(s)
    return " ".join(parts)
