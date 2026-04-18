"""Canvas de preview para footprints KiCad."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from easyjlc.core.kicad_parse import FootprintPreview, Point
from easyjlc.ui.preview_canvas import Bounds, _bounds

LAYER_COLORS = {
    "F.Cu": "#f97316",
    "B.Cu": "#38bdf8",
    "F.SilkS": "#e5e7eb",
    "B.SilkS": "#9ca3af",
    "F.Mask": "#22c55e",
    "B.Mask": "#16a34a",
}


class FootprintCanvas(ctk.CTkFrame):
    def __init__(self, master, title: str = "Footprint") -> None:
        super().__init__(master)
        self.preview: FootprintPreview | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.title = ctk.CTkLabel(
            self, text=title, anchor="w", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.title.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))

        self.canvas = tk.Canvas(
            self,
            background="#171717",
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda _event: self._redraw())

    def show(self, preview: FootprintPreview | None) -> None:
        self.preview = preview
        self._redraw()

    def clear(self, message: str = "Sem footprint para exibir.") -> None:
        self.preview = None
        self.canvas.delete("all")
        self.canvas.create_text(
            12,
            12,
            text=message,
            fill="#9ca3af",
            anchor="nw",
            font=("TkDefaultFont", 10),
        )

    def _redraw(self) -> None:
        self.canvas.delete("all")
        if self.preview is None:
            self.clear()
            return

        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        bounds = footprint_bounds(self.preview)
        transform = _Transform(bounds, width, height)

        self.canvas.create_text(
            10,
            10,
            text=self.preview.name,
            fill="#e5e7eb",
            anchor="nw",
            font=("TkDefaultFont", 10, "bold"),
        )

        for line in self.preview.lines:
            x1, y1 = transform.point(line.start)
            x2, y2 = transform.point(line.end)
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=LAYER_COLORS.get(line.layer, "#e5e7eb"),
                width=2,
            )

        for pad in self.preview.pads:
            cx, cy = transform.point(pad.at)
            w = max(pad.size.x * transform.scale, 3)
            h = max(pad.size.y * transform.scale, 3)
            color = _pad_color(pad.layers)
            coords = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            if pad.shape in {"circle", "oval"}:
                self.canvas.create_oval(*coords, fill=color, outline="#111827")
            else:
                self.canvas.create_rectangle(*coords, fill=color, outline="#111827")
            if pad.number:
                self.canvas.create_text(
                    cx,
                    cy,
                    text=pad.number,
                    fill="#111827",
                    font=("TkDefaultFont", 8, "bold"),
                )


def footprint_bounds(preview: FootprintPreview) -> Bounds:
    points: list[Point] = []
    for line in preview.lines:
        points.extend([line.start, line.end])
    for pad in preview.pads:
        half_w = pad.size.x / 2
        half_h = pad.size.y / 2
        points.extend(
            [
                Point(pad.at.x - half_w, pad.at.y - half_h),
                Point(pad.at.x + half_w, pad.at.y + half_h),
            ]
        )
    return _bounds(points)


def _pad_color(layers: list[str]) -> str:
    for layer in layers:
        if layer in LAYER_COLORS:
            return LAYER_COLORS[layer]
    return "#f97316"


class _Transform:
    def __init__(self, bounds: Bounds, width: int, height: int, pad: int = 28) -> None:
        span_x = max(bounds.max_x - bounds.min_x, 1)
        span_y = max(bounds.max_y - bounds.min_y, 1)
        self.scale = min(
            max((width - pad * 2) / span_x, 1),
            max((height - pad * 2) / span_y, 1),
        )
        used_w = span_x * self.scale
        used_h = span_y * self.scale
        self.bounds = bounds
        self.offset_x = (width - used_w) / 2
        self.offset_y = (height - used_h) / 2

    def point(self, point: Point) -> tuple[float, float]:
        x = self.offset_x + (point.x - self.bounds.min_x) * self.scale
        y = self.offset_y + (point.y - self.bounds.min_y) * self.scale
        return x, y
