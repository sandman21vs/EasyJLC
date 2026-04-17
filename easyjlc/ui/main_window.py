"""Janela principal do EasyJLC (tabview: Download / Histórico / Log)."""

from __future__ import annotations

import logging

import customtkinter as ctk

from easyjlc import __version__
from easyjlc import history as history_module
from easyjlc import settings as settings_module
from easyjlc.core import EasyEdaRunner
from easyjlc.history import History, HistoryEntry
from easyjlc.settings import Settings
from easyjlc.ui.download_tab import DownloadTab
from easyjlc.ui.history_tab import HistoryTab
from easyjlc.ui.log_tab import LogTab

log = logging.getLogger("easyjlc.main_window")


class MainWindow(ctk.CTk):
    def __init__(
        self,
        user_settings: Settings,
        history: History,
        runner: EasyEdaRunner,
    ) -> None:
        super().__init__()
        self.user_settings = user_settings
        self.history = history
        self.runner = runner

        self.title(f"EasyJLC {__version__}")
        self.geometry(user_settings.window_geometry or "960x640")
        self.minsize(720, 480)

        ctk.set_appearance_mode(user_settings.theme)
        ctk.set_default_color_theme("blue")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="EasyJLC",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))

        ctk.CTkLabel(
            header,
            text="Download de símbolos e footprints KiCad via LCSC/EasyEDA",
            font=ctk.CTkFont(size=12),
            text_color="gray70",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 12))
        self.tabs.add("Download")
        self.tabs.add("Histórico")
        self.tabs.add("Log")

        self.log_tab = LogTab(self.tabs.tab("Log"))
        self.log_tab.pack(fill="both", expand=True, padx=6, pady=6)

        self.download_tab = DownloadTab(
            self.tabs.tab("Download"),
            settings=self.user_settings,
            runner=self.runner,
            on_log=self._handle_log,
            on_finished=self._handle_download_finished,
        )
        self.download_tab.pack(fill="both", expand=True, padx=12, pady=12)

        self.history_tab = HistoryTab(
            self.tabs.tab("Histórico"),
            history=self.history,
            on_redownload=self._redownload_from_history,
        )
        self.history_tab.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            self,
            text=f"v{__version__}  •  tema: {self.user_settings.theme}",
            font=ctk.CTkFont(size=10),
            anchor="e",
            text_color="gray60",
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))

    # ---------- Callbacks ----------

    def _handle_log(self, line: str) -> None:
        self.log_tab.append(line)
        log.info(line)

    def _handle_download_finished(
        self, lcsc_id: str, output_dir: str | None, success: bool, message: str
    ) -> None:
        self.history.add(lcsc_id, output_dir, success=success, message=message)
        try:
            history_module.save(self.history)
        except OSError as exc:
            log.warning("Falha ao salvar histórico: %s", exc)
        self.history_tab.refresh()

    def _redownload_from_history(self, entry: HistoryEntry) -> None:
        self.tabs.set("Download")
        self.download_tab.trigger_download(entry.lcsc_id, entry.output_dir)

    def _on_close(self) -> None:
        self.user_settings.window_geometry = self.geometry()
        try:
            settings_module.save(self.user_settings)
        except OSError as exc:
            log.warning("Falha ao salvar settings: %s", exc)
        try:
            history_module.save(self.history)
        except OSError as exc:
            log.warning("Falha ao salvar histórico: %s", exc)
        self.destroy()
