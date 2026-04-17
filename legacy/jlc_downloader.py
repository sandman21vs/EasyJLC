#!/usr/bin/env python3
"""Cross-platform downloader wrapper for easyeda2kicad."""

from __future__ import annotations

import subprocess
import sys
import os
import shutil
import venv
from pathlib import Path


def prompt_choice(prompt: str, valid: set[str]) -> str:
    while True:
        value = input(prompt).strip()
        if value in valid:
            return value
        print(f"Please type one of: {', '.join(sorted(valid))}")


def prompt_yes_no(prompt: str) -> bool:
    while True:
        value = input(prompt).strip().lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please type Y or N.")


def get_venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def runner_available(easyeda_runner: list[str]) -> bool:
    result = subprocess.run(
        [*easyeda_runner, "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def create_and_install_venv(venv_dir: Path) -> list[str] | None:
    python_in_venv = get_venv_python(venv_dir)

    if not python_in_venv.exists():
        print()
        print(f'Creating local virtual environment: "{venv_dir}"')
        try:
            venv.EnvBuilder(with_pip=True).create(str(venv_dir))
        except Exception:
            print("Failed to create virtual environment.")
            return None

    print("Installing easyeda2kicad (first run may take a moment)...")
    bootstrap = subprocess.run(
        [
            str(python_in_venv),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ],
        check=False,
    )
    if bootstrap.returncode != 0:
        print("Failed to bootstrap pip in local virtual environment.")
        return None

    install = subprocess.run(
        [
            str(python_in_venv),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "typing_extensions>=4.14.1",
            "pydantic>=2.11",
            "pydantic-core>=2.33",
            "easyeda2kicad",
        ],
        check=False,
    )
    if install.returncode != 0:
        print("Failed to install easyeda2kicad in local virtual environment.")
        return None

    easyeda_runner = [str(python_in_venv), "-m", "easyeda2kicad"]
    if not runner_available(easyeda_runner):
        print("easyeda2kicad is still unavailable after installation.")
        return None

    return easyeda_runner


def resolve_easyeda_runner(script_dir: Path) -> list[str] | None:
    venv_dir = script_dir / ".easyeda2kicad-venv"
    python_in_venv = get_venv_python(venv_dir)
    venv_runner = [str(python_in_venv), "-m", "easyeda2kicad"]

    if python_in_venv.exists():
        if runner_available(venv_runner):
            return venv_runner

        print("Local easyeda2kicad venv seems broken. Reinstalling dependencies...")
        repaired_runner = create_and_install_venv(venv_dir)
        if repaired_runner is not None:
            return repaired_runner

    sys_runner = [sys.executable, "-m", "easyeda2kicad"]
    if runner_available(sys_runner):
        return sys_runner

    cli_cmd = shutil.which("easyeda2kicad")
    if cli_cmd and runner_available([cli_cmd]):
        return [cli_cmd]

    print()
    print("easyeda2kicad was not found in this Python environment.")
    if not prompt_yes_no(
        'Create local venv ".easyeda2kicad-venv" and install now? [Y]=Yes [N]=No : '
    ):
        print("Cannot continue without easyeda2kicad.")
        print("Tip: run this script again and choose Y, or install manually.")
        return None

    return create_and_install_venv(venv_dir)


def get_output_dir() -> Path | None:
    print()
    print("Example path:")
    print("  C:\\Projects\\MyPCB\\kicad_lib")
    print()
    print("Tip: spaces are OK.")
    print()

    raw_path = input("Type the destination folder path: ").strip().strip('"').strip("'")
    if not raw_path:
        print("Folder not provided.")
        return None

    output_dir = Path(raw_path).expanduser()

    if not output_dir.exists():
        print()
        print("Folder does not exist:")
        print(f'"{output_dir}"')
        print()
        if not prompt_yes_no("Create this folder? [Y]=Yes [N]=No : "):
            print("Cancelled.")
            return None
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            print("Failed to create folder.")
            return None

    return output_dir


def get_output_dir_from_explorer(initial_dir: Path) -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        print("File explorer is unavailable (tkinter not installed).")
        return None

    try:
        root = tk.Tk()
        root.withdraw()
        root.update()
        selected = filedialog.askdirectory(
            title="Select destination folder",
            initialdir=str(initial_dir),
            mustexist=True,
        )
        root.destroy()
    except Exception:
        print("Could not open the file explorer.")
        return None

    if not selected:
        print("No folder selected.")
        return None

    return Path(selected).expanduser()


def get_output_dir_from_terminal_browser(root_dir: Path) -> Path | None:
    root_dir = root_dir.resolve()
    current_dir = root_dir

    while True:
        print()
        print("Terminal folder browser")
        print(f'Root:    "{root_dir}"')
        print(f'Current: "{current_dir}"')

        try:
            subdirs = sorted(
                [p for p in current_dir.iterdir() if p.is_dir()],
                key=lambda p: p.name.lower(),
            )
        except OSError:
            print("Could not read this folder.")
            return None

        if subdirs:
            for idx, folder in enumerate(subdirs, start=1):
                print(f"[{idx}] {folder.name}")
        else:
            print("(No subfolders)")

        print("[c] Confirm current folder")
        if current_dir != root_dir:
            print("[b] Back")
        print("[q] Cancel")

        choice = input("Select an option: ").strip().lower()
        if choice == "c":
            return current_dir
        if choice == "q":
            return None
        if choice == "b":
            if current_dir == root_dir:
                print("You are already at root folder.")
                continue
            current_dir = current_dir.parent
            continue

        if not choice.isdigit():
            print("Invalid option.")
            continue

        index = int(choice) - 1
        if index < 0 or index >= len(subdirs):
            print("Invalid folder number.")
            continue

        current_dir = subdirs[index]


def run_easyeda2kicad(
    easyeda_runner: list[str], lcsc_id: str, output_dir: Path | None
) -> int:
    cmd = [*easyeda_runner, "--full", "--overwrite", f"--lcsc_id={lcsc_id}"]

    if output_dir is not None:
        cmd.extend(["--output", str(output_dir)])

    return subprocess.run(cmd, check=False).returncode


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    # Keep behavior close to the .bat by running from script directory.
    os.chdir(script_dir)

    print()
    print("==============================")
    print(" easyeda2kicad - downloader")
    print("==============================")
    print()

    easyeda_runner = resolve_easyeda_runner(script_dir)
    if easyeda_runner is None:
        input("Press Enter to exit...")
        return 1

    mode = prompt_choice(
        "Where to save? [1]=Default folder  [2]=Project folder  [3]=Browse folders : ",
        {"1", "2", "3"},
    )

    output_dir: Path | None = None
    if mode == "2":
        output_dir = get_output_dir()
        if output_dir is None:
            input("Press Enter to exit...")
            return 1
    elif mode == "3":
        output_dir = get_output_dir_from_explorer(script_dir)
        if output_dir is None:
            print("Switching to terminal folder browser...")
            output_dir = get_output_dir_from_terminal_browser(script_dir)
        if output_dir is None and prompt_yes_no("Fallback to manual path? [Y]=Yes [N]=No : "):
            output_dir = get_output_dir()
        if output_dir is None:
            input("Press Enter to exit...")
            return 1

    while True:
        print()
        lcsc_id = input("Type the LCSC_ID (e.g. C2040) or 'e' to exit: ").strip()

        if lcsc_id.lower() == "e":
            return 0
        if not lcsc_id:
            print("Please type an ID or 'e' to exit.")
            input("Press Enter to continue...")
            continue

        print()
        if output_dir is not None:
            print(f'Saving INSIDE: "{output_dir}"')
        else:
            print("Saving to easyeda2kicad default folder")

        exit_code = run_easyeda2kicad(easyeda_runner, lcsc_id, output_dir)
        if exit_code != 0:
            print()
            print(f"easyeda2kicad failed with exit code {exit_code}.")

        print()
        input("Press Enter to continue...")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130)
