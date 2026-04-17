"""Caminhos padrão do app (XDG no Linux, AppData no Windows) e logging."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "EasyJLC"
APP_AUTHOR = "EasyJLC"

_dirs = PlatformDirs(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=True)


def config_dir() -> Path:
    path = Path(_dirs.user_config_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = Path(_dirs.user_cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = Path(_dirs.user_log_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    path = Path(_dirs.user_data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return config_dir() / "settings.json"


def history_path() -> Path:
    return data_dir() / "history.json"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("easyjlc")
    if logger.handlers:
        return logger

    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir() / "app.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.propagate = False
    return logger
