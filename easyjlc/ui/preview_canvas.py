"""Canvas de preview para símbolos KiCad."""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass

import customtkinter as ctk

from easyjlc.core.kicad_parse import Point, SymbolPreview
from easyjlc.i18n import t

MIN_SCALE = 0.05
MAX_SCALE = 2000.0
WHEEL_FACTOR = 1.15


@dataclass(frozen=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class SymbolCanvas(ctk.CTkFrame):
    def __init__(self, master, title: str | None = None) -> None:
        super().__init__(master)
        title = title or t("Símbolo")
        self.preview: SymbolPreview | None = None
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

    def show(self, preview: SymbolPreview | None) -> None:
        self.preview = preview
        self._user_interacted = False
        if preview is not None:
            self._bounds = symbol_bounds(preview)
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
            text=message or t("Sem símbolo para exibir."),
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
        y = self._offset_y + (self._bounds.max_y - point.y) * self._scale
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

        for rect in self.preview.rectangles:
            x1, y1 = self._project(rect.start)
            x2, y2 = self._project(rect.end)
            self.canvas.create_rectangle(
                x1, y1, x2, y2, outline="#60a5fa", width=2
            )

        for circle in self.preview.circles:
            cx, cy = self._project(circle.center)
            radius = circle.radius * self._scale
            self.canvas.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline="#60a5fa",
                width=2,
            )

        for polyline in self.preview.polylines:
            coords: list[float] = []
            for point in polyline.points:
                coords.extend(self._project(point))
            if len(coords) >= 4:
                self.canvas.create_line(*coords, fill="#60a5fa", width=2)

        for pin in self.preview.pins:
            start = pin.at
            angle = math.radians(pin.rotation)
            end = Point(
                start.x + math.cos(angle) * pin.length,
                start.y + math.sin(angle) * pin.length,
            )
            x1, y1 = self._project(start)
            x2, y2 = self._project(end)
            self.canvas.create_line(x1, y1, x2, y2, fill="#fbbf24", width=2)
            self.canvas.create_oval(x1 - 2, y1 - 2, x1 + 2, y1 + 2, fill="#fbbf24")

            label = pin.number or pin.name
            if label:
                self.canvas.create_text(
                    x1,
                    y1 - 7,
                    text=label,
                    fill="#fde68a",
                    anchor="s",
                    font=("TkDefaultFont", 8),
                )


def symbol_bounds(preview: SymbolPreview) -> Bounds:
    points: list[Point] = []
    for rect in preview.rectangles:
        points.extend([rect.start, rect.end])
    for circle in preview.circles:
        points.extend(
            [
                Point(circle.center.x - circle.radius, circle.center.y - circle.radius),
                Point(circle.center.x + circle.radius, circle.center.y + circle.radius),
            ]
        )
    for polyline in preview.polylines:
        points.extend(polyline.points)
    for pin in preview.pins:
        points.append(pin.at)
        angle = math.radians(pin.rotation)
        points.append(
            Point(
                pin.at.x + math.cos(angle) * pin.length,
                pin.at.y + math.sin(angle) * pin.length,
            )
        )
    return _bounds(points)


def _bounds(points: list[Point]) -> Bounds:
    if not points:
        return Bounds(-1, -1, 1, 1)
    min_x = min(point.x for point in points)
    min_y = min(point.y for point in points)
    max_x = max(point.x for point in points)
    max_y = max(point.y for point in points)
    if min_x == max_x:
        min_x -= 1
        max_x += 1
    if min_y == max_y:
        min_y -= 1
        max_y += 1
    return Bounds(min_x, min_y, max_x, max_y)
