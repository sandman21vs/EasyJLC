"""Janela principal do EasyJLC (placeholder da Sprint 1)."""

from __future__ import annotations

import logging

import customtkinter as ctk

from easyjlc import __version__
from easyjlc import settings as settings_module
from easyjlc.config import setup_logging

log = logging.getLogger("easyjlc.app")


class EasyJLCApp(ctk.CTk):
    def __init__(self, user_settings: settings_module.Settings) -> None:
        super().__init__()
        self.user_settings = user_settings

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

        title = ctk.CTkLabel(
            header,
            text="EasyJLC",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))

        subtitle = ctk.CTkLabel(
            header,
            text="Download de símbolos e footprints KiCad a partir do LCSC/EasyEDA",
            font=ctk.CTkFont(size=12),
        )
        subtitle.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        placeholder = ctk.CTkLabel(
            body,
            text=(
                "Sprint 1 — fundação.\n\n"
                "A GUI real chega na Sprint 2: campo LCSC ID, seletor de pasta,\n"
                "histórico, busca e preview.\n\n"
                "Consulte PLAN.md na raiz do projeto."
            ),
            justify="center",
            font=ctk.CTkFont(size=14),
        )
        placeholder.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

        footer = ctk.CTkLabel(
            self,
            text=f"v{__version__}  •  tema: {self.user_settings.theme}",
            font=ctk.CTkFont(size=10),
            anchor="e",
        )
        footer.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))

    def _on_close(self) -> None:
        self.user_settings.window_geometry = self.geometry()
        try:
            settings_module.save(self.user_settings)
        except OSError as exc:
            log.warning("Falha ao salvar settings: %s", exc)
        self.destroy()


def main() -> int:
    setup_logging()
    user_settings = settings_module.load()
    log.info("Iniciando EasyJLC %s", __version__)
    app = EasyJLCApp(user_settings)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
