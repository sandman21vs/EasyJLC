"""Canvas de preview para footprints KiCad."""

from __future__ import annotations

import math
import tkinter as tk

import customtkinter as ctk

from easyjlc.core.kicad_parse import FootprintPreview, Point
from easyjlc.i18n import t
from easyjlc.ui.preview_canvas import Bounds, _bounds

OVAL_SEGMENTS = 48

LAYER_COLORS = {
    "F.Cu": "#f97316",
    "B.Cu": "#38bdf8",
    "F.SilkS": "#e5e7eb",
    "B.SilkS": "#9ca3af",
    "F.Mask": "#22c55e",
    "B.Mask": "#16a34a",
}

MIN_SCALE = 0.05
MAX_SCALE = 2000.0
WHEEL_FACTOR = 1.15


class FootprintCanvas(ctk.CTkFrame):
    def __init__(self, master, title: str | None = None) -> None:
        super().__init__(master)
        title = title or t("Footprint")
        self.preview: FootprintPreview | None = None
        self._bounds: Bounds | None = None
        self._scale: float = 1.0
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0
        self._user_interacted: bool = False
        self._pan_anchor: tuple[int, int] | None = None

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
            cursor="fleur",
        )
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", self._on_wheel_up)
        self.canvas.bind("<Button-5>", self._on_wheel_down)
        self.canvas.bind("<ButtonPress-1>", self._on_pan_start)
        self.canvas.bind("<B1-Motion>", self._on_pan_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_pan_end)
        self.canvas.bind("<Double-Button-1>", self._on_reset)

    def show(self, preview: FootprintPreview | None) -> None:
        self.preview = preview
        self._user_interacted = False
        if preview is not None:
            self._bounds = footprint_bounds(preview)
            self._fit()
        else:
            self._bounds = None
        self._redraw()

    def clear(self, message: str | None = None) -> None:
        self.preview = None
        self._bounds = None
        self._user_interacted = False
        self.canvas.delete("all")
        self.canvas.create_text(
            12,
            12,
            text=message or t("Sem footprint para exibir."),
            fill="#9ca3af",
            anchor="nw",
            font=("TkDefaultFont", 10),
        )

    def _on_configure(self, _event) -> None:
        if self.preview is None:
            return
        if not self._user_interacted:
            self._fit()
        self._redraw()

    def _fit(self, pad: int = 28) -> None:
        if self._bounds is None:
            return
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        span_x = max(self._bounds.max_x - self._bounds.min_x, 1)
        span_y = max(self._bounds.max_y - self._bounds.min_y, 1)
        self._scale = min(
            max((width - pad * 2) / span_x, 1),
            max((height - pad * 2) / span_y, 1),
        )
        used_w = span_x * self._scale
        used_h = span_y * self._scale
        self._offset_x = (width - used_w) / 2
        self._offset_y = (height - used_h) / 2

    def _project(self, point: Point) -> tuple[float, float]:
        assert self._bounds is not None
        x = self._offset_x + (point.x - self._bounds.min_x) * self._scale
        y = self._offset_y + (point.y - self._bounds.min_y) * self._scale
        return x, y

    def _zoom_at(self, cx: int, cy: int, factor: float) -> None:
        if self._bounds is None:
            return
        new_scale = max(MIN_SCALE, min(MAX_SCALE, self._scale * factor))
        if new_scale == self._scale:
            return
        ratio = new_scale / self._scale
        self._offset_x = cx - (cx - self._offset_x) * ratio
        self._offset_y = cy - (cy - self._offset_y) * ratio
        self._scale = new_scale
        self._user_interacted = True
        self._redraw()

    def _on_wheel(self, event) -> str:
        factor = WHEEL_FACTOR if event.delta > 0 else 1 / WHEEL_FACTOR
        self._zoom_at(event.x, event.y, factor)
        return "break"

    def _on_wheel_up(self, event) -> str:
        self._zoom_at(event.x, event.y, WHEEL_FACTOR)
        return "break"

    def _on_wheel_down(self, event) -> str:
        self._zoom_at(event.x, event.y, 1 / WHEEL_FACTOR)
        return "break"

    def _on_pan_start(self, event) -> None:
        self._pan_anchor = (event.x, event.y)
        self.canvas.focus_set()

    def _on_pan_drag(self, event) -> None:
        if self._pan_anchor is None or self._bounds is None:
            return
        dx = event.x - self._pan_anchor[0]
        dy = event.y - self._pan_anchor[1]
        self._pan_anchor = (event.x, event.y)
        self._offset_x += dx
        self._offset_y += dy
        self._user_interacted = True
        self._redraw()

    def _on_pan_end(self, _event) -> None:
        self._pan_anchor = None

    def _on_reset(self, _event) -> None:
        if self.preview is None:
            return
        self._user_interacted = False
        self._fit()
        self._redraw()

    def _redraw(self) -> None:
        self.canvas.delete("all")
        if self.preview is None or self._bounds is None:
            return

        self.canvas.create_text(
            10,
            10,
            text=self.preview.name,
            fill="#e5e7eb",
            anchor="nw",
            font=("TkDefaultFont", 10, "bold"),
        )

        for line in self.preview.lines:
            x1, y1 = self._project(line.start)
            x2, y2 = self._project(line.end)
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=LAYER_COLORS.get(line.layer, "#e5e7eb"),
                width=2,
            )

        for pad in self.preview.pads:
            self._draw_pad(pad)

    def _draw_pad(self, pad) -> None:
        cx, cy = self._project(pad.at)
        w = max(pad.size.x * self._scale, 3)
        h = max(pad.size.y * self._scale, 3)
        color = _pad_color(pad.layers)
        rotation = pad.rotation or 0.0

        if pad.shape == "circle" or (pad.shape == "oval" and abs(w - h) < 0.5):
            # Círculo é invariante à rotação.
            self.canvas.create_oval(
                cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                fill=color, outline="#111827",
            )
        elif pad.shape == "oval":
            # Elipse rotacionada aproximada por polígono.
            points = _rotated_ellipse(cx, cy, w / 2, h / 2, rotation, OVAL_SEGMENTS)
            self.canvas.create_polygon(points, fill=color, outline="#111827")
        else:
            # Retângulo (inclui "rect", "roundrect") rotacionado nos 4 cantos.
            points = _rotated_rect(cx, cy, w, h, rotation)
            self.canvas.create_polygon(points, fill=color, outline="#111827")

        if pad.number:
            self.canvas.create_text(
                cx, cy, text=pad.number,
                fill="#111827", font=("TkDefaultFont", 8, "bold"),
            )


def _rotate(dx: float, dy: float, angle_deg: float) -> tuple[float, float]:
    rad = math.radians(angle_deg)
    c, s = math.cos(rad), math.sin(rad)
    return dx * c - dy * s, dx * s + dy * c


def _rotated_rect(cx: float, cy: float, w: float, h: float, angle_deg: float) -> list[float]:
    hw, hh = w / 2, h / 2
    corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    flat: list[float] = []
    for dx, dy in corners:
        rx, ry = _rotate(dx, dy, angle_deg)
        flat.extend([cx + rx, cy + ry])
    return flat


def _rotated_ellipse(
    cx: float, cy: float, rx: float, ry: float, angle_deg: float, segments: int
) -> list[float]:
    flat: list[float] = []
    for i in range(segments):
        theta = 2 * math.pi * i / segments
        lx = rx * math.cos(theta)
        ly = ry * math.sin(theta)
        wx, wy = _rotate(lx, ly, angle_deg)
        flat.extend([cx + wx, cy + wy])
    return flat


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
