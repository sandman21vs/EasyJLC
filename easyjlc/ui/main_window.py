"""Janela principal do EasyJLC (tabview: Buscar / Download / Histórico / Log)."""

from __future__ import annotations

import logging
from tkinter import messagebox

import customtkinter as ctk

from easyjlc import __version__
from easyjlc import history as history_module
from easyjlc import settings as settings_module
from easyjlc.core import EasyEdaRunner, JlcClient
from easyjlc.history import History, HistoryEntry
from easyjlc.i18n import SUPPORTED_LANGUAGES, t
from easyjlc.settings import Settings
from easyjlc.ui.docs_tab import DocsTab
from easyjlc.ui.download_tab import DownloadTab
from easyjlc.ui.history_tab import HistoryTab
from easyjlc.ui.log_tab import LogTab
from easyjlc.ui.search_tab import SearchTab

log = logging.getLogger("easyjlc.main_window")


class MainWindow(ctk.CTk):
    def __init__(
        self,
        user_settings: Settings,
        history: History,
        runner: EasyEdaRunner,
        jlc_client: JlcClient | None = None,
    ) -> None:
        super().__init__()
        self.user_settings = user_settings
        self.history = history
        self.runner = runner
        self.jlc_client = jlc_client or JlcClient()

        self.title(f"EasyJLC {__version__}")
        self.geometry(user_settings.window_geometry or "1100x720")
        self.minsize(820, 520)

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
            text=t("Busca, preço, estoque e download KiCad via JLCPCB/LCSC"),
            font=ctk.CTkFont(size=12),
            text_color="gray70",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        self._lang_var = ctk.StringVar(value=self.user_settings.language)
        ctk.CTkOptionMenu(
            header,
            values=list(SUPPORTED_LANGUAGES),
            variable=self._lang_var,
            command=self._on_language_change,
            width=90,
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(8, 16), pady=12)

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 12))
        # Guardamos as chaves originais pt-BR para set()/tab() porque o
        # CTkTabview indexa pelo texto exibido (que muda conforme o idioma).
        self._tab_names = {
            "search": t("Buscar"),
            "download": t("Download direto"),
            "history": t("Histórico"),
            "docs": t("Documentação"),
            "log": t("Log"),
        }
        for name in self._tab_names.values():
            self.tabs.add(name)

        self.log_tab = LogTab(self.tabs.tab(self._tab_names["log"]))
        self.log_tab.pack(fill="both", expand=True, padx=6, pady=6)

        self.download_tab = DownloadTab(
            self.tabs.tab(self._tab_names["download"]),
            settings=self.user_settings,
            runner=self.runner,
            on_log=self._handle_log,
            on_finished=self._handle_download_finished,
        )
        self.download_tab.pack(fill="both", expand=True, padx=12, pady=12)

        self.search_tab = SearchTab(
            self.tabs.tab(self._tab_names["search"]),
            client=self.jlc_client,
            runner=self.runner,
            on_download=self._download_from_search,
            on_log=self._handle_log,
        )
        self.search_tab.pack(fill="both", expand=True, padx=12, pady=12)

        self.history_tab = HistoryTab(
            self.tabs.tab(self._tab_names["history"]),
            history=self.history,
            on_redownload=self._redownload_from_history,
        )
        self.history_tab.pack(fill="both", expand=True, padx=12, pady=12)

        self.docs_tab = DocsTab(self.tabs.tab(self._tab_names["docs"]))
        self.docs_tab.pack(fill="both", expand=True, padx=12, pady=12)

        self.tabs.set(self._tab_names["search"])

        ctk.CTkLabel(
            self,
            text=t("v{ver}  •  tema: {theme}", ver=__version__, theme=self.user_settings.theme),
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

    def _download_from_search(self, lcsc_id: str) -> None:
        self.tabs.set(self._tab_names["download"])
        self.download_tab.trigger_download(lcsc_id, None)

    def _redownload_from_history(self, entry: HistoryEntry) -> None:
        self.tabs.set(self._tab_names["download"])
        self.download_tab.trigger_download(entry.lcsc_id, entry.output_dir)

    def _on_language_change(self, language: str) -> None:
        if language == self.user_settings.language:
            return
        self.user_settings.language = language
        try:
            settings_module.save(self.user_settings)
        except OSError as exc:
            log.warning("Falha ao salvar settings: %s", exc)
        msg = t("Idioma alterado para {lang}. Reinicie o app para aplicar.", lang=language)
        self._handle_log(msg)
        messagebox.showinfo(t("Reiniciar necessário"), msg, parent=self)

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
