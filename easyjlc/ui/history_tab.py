"""Aba Histórico — lista de downloads com ações."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from easyjlc.history import History, HistoryEntry
from easyjlc.i18n import t


class HistoryTab(ctk.CTkFrame):
    def __init__(
        self,
        master,
        history: History,
        on_redownload: Callable[[HistoryEntry], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.history = history
        self.on_redownload = on_redownload

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=t("Downloads recentes"),
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(header, text=t("Limpar tudo"), width=110, command=self._clear).grid(
            row=0, column=1, sticky="e"
        )

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        self.empty_label = ctk.CTkLabel(
            self.scroll,
            text=t("Nenhum download ainda."),
            text_color="gray60",
        )
        self.refresh()

    def refresh(self) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()

        if not self.history.entries:
            self.empty_label = ctk.CTkLabel(
                self.scroll,
                text=t("Nenhum download ainda."),
                text_color="gray60",
            )
            self.empty_label.grid(row=0, column=0, pady=24)
            return

        for idx, entry in enumerate(self.history.entries):
            self._build_row(idx, entry)

    def _build_row(self, idx: int, entry: HistoryEntry) -> None:
        row = ctk.CTkFrame(self.scroll)
        row.grid(row=idx, column=0, sticky="ew", pady=4, padx=2)
        row.grid_columnconfigure(2, weight=1)

        status_color = "#2ecc71" if entry.success else "#e74c3c"
        status_char = "✓" if entry.success else "✗"
        ctk.CTkLabel(
            row,
            text=status_char,
            text_color=status_color,
            font=ctk.CTkFont(size=16, weight="bold"),
            width=24,
        ).grid(row=0, column=0, padx=(10, 6), pady=8)

        ctk.CTkLabel(
            row,
            text=entry.lcsc_id,
            font=ctk.CTkFont(size=13, weight="bold"),
            width=90,
            anchor="w",
        ).grid(row=0, column=1, padx=(0, 8), pady=8)

        when = entry.timestamp.replace("T", " ").split("+")[0]
        where = entry.output_dir or t("(pasta default)")
        details = ctk.CTkLabel(
            row,
            text=f"{when}  •  {where}",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
        )
        details.grid(row=0, column=2, sticky="ew", pady=8)

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.grid(row=0, column=3, padx=(0, 8))

        ctk.CTkButton(
            actions, text=t("Rebaixar"), width=90,
            command=lambda e=entry: self.on_redownload(e),
        ).grid(row=0, column=0, padx=2)

        if entry.output_dir:
            ctk.CTkButton(
                actions, text=t("Abrir pasta"), width=100,
                command=lambda p=entry.output_dir: _open_folder(p),
            ).grid(row=0, column=1, padx=2)

        ctk.CTkButton(
            actions, text=t("Copiar ID"), width=90,
            command=lambda i=entry.lcsc_id: self._copy(i),
        ).grid(row=0, column=2, padx=2)

    def _copy(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)

    def _clear(self) -> None:
        self.history.clear()
        self.refresh()


def _open_folder(path: str) -> None:
    p = Path(path)
    if not p.exists():
        return
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(p)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
    except OSError:
        pass
