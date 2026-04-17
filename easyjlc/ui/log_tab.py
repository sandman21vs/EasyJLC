"""Aba Log — textbox rolagem automática com append thread-safe."""

from __future__ import annotations

import customtkinter as ctk


class LogTab(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.textbox = ctk.CTkTextbox(self, wrap="none", font=ctk.CTkFont(family="monospace", size=11))
        self.textbox.grid(row=0, column=0, sticky="nsew")
        self.textbox.configure(state="disabled")

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        toolbar.grid_columnconfigure(0, weight=1)

        clear_btn = ctk.CTkButton(toolbar, text="Limpar", width=90, command=self.clear)
        clear_btn.grid(row=0, column=1, sticky="e")

    def append(self, line: str) -> None:
        self.textbox.configure(state="normal")
        self.textbox.insert("end", line.rstrip("\n") + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self) -> None:
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
