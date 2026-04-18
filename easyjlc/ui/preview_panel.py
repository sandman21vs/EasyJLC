"""Painel combinado de preview KiCad."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from easyjlc.core.artifacts import KiCadArtifacts
from easyjlc.core.kicad_parse import KiCadParseError, parse_footprint_file, parse_symbol_file
from easyjlc.ui.footprint_canvas import FootprintCanvas
from easyjlc.ui.preview_canvas import SymbolCanvas


class PreviewPanel(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master)
        self.grid_columnconfigure((0, 1), weight=1, uniform="preview")
        self.grid_rowconfigure(1, weight=1)

        self.status = ctk.CTkLabel(
            self,
            text="Preview: baixe uma peça com pasta de saída definida.",
            anchor="w",
            text_color="gray70",
            font=ctk.CTkFont(size=11),
        )
        self.status.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(6, 0))

        self.symbol_canvas = SymbolCanvas(self)
        self.symbol_canvas.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=8)

        self.footprint_canvas = FootprintCanvas(self)
        self.footprint_canvas.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=8)

        self.clear()

    def clear(self, message: str | None = None) -> None:
        if message:
            self.status.configure(text=message)
        self.symbol_canvas.clear()
        self.footprint_canvas.clear()

    def show_artifacts(self, artifacts: KiCadArtifacts, lcsc_id: str | None = None) -> list[str]:
        warnings: list[str] = []
        loaded: list[str] = []

        if artifacts.symbol is not None:
            try:
                symbol = parse_symbol_file(artifacts.symbol, lcsc_id=lcsc_id)
                self.symbol_canvas.show(symbol)
                loaded.append(_short_path(artifacts.symbol))
                warnings.append(
                    "Símbolo carregado: "
                    f"{symbol.name} ({len(symbol.pins)} pinos, "
                    f"{len(symbol.rectangles)} retângulos, "
                    f"{len(symbol.circles)} círculos, "
                    f"{len(symbol.polylines)} polylines)"
                )
            except (OSError, KiCadParseError) as exc:
                self.symbol_canvas.clear("Símbolo indisponível.")
                warnings.append(f"Símbolo: {exc}")
        else:
            self.symbol_canvas.clear("Símbolo não encontrado.")

        if artifacts.footprint is not None:
            try:
                footprint = parse_footprint_file(artifacts.footprint)
                self.footprint_canvas.show(footprint)
                loaded.append(_short_path(artifacts.footprint))
                warnings.append(
                    "Footprint carregado: "
                    f"{footprint.name} ({len(footprint.lines)} linhas, "
                    f"{len(footprint.pads)} pads)"
                )
            except (OSError, KiCadParseError) as exc:
                self.footprint_canvas.clear("Footprint indisponível.")
                warnings.append(f"Footprint: {exc}")
        else:
            self.footprint_canvas.clear("Footprint não encontrado.")

        if loaded:
            self.status.configure(text="Preview carregado: " + "  |  ".join(loaded))
        elif warnings:
            self.status.configure(text="Preview não pôde ser carregado.")
        else:
            self.status.configure(text="Preview não encontrou arquivos KiCad nessa pasta.")

        return warnings


def _short_path(path: Path) -> str:
    text = str(path)
    if len(text) <= 70:
        return text
    return "..." + text[-67:]
