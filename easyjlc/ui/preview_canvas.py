"""Canvas de preview para símbolos KiCad."""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass

import customtkinter as ctk

from easyjlc.core.kicad_parse import Point, SymbolPreview


@dataclass(frozen=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class SymbolCanvas(ctk.CTkFrame):
    def __init__(self, master, title: str = "Símbolo") -> None:
        super().__init__(master)
        self.preview: SymbolPreview | None = None

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

    def show(self, preview: SymbolPreview | None) -> None:
        self.preview = preview
        self._redraw()

    def clear(self, message: str = "Sem símbolo para exibir.") -> None:
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
        bounds = symbol_bounds(self.preview)
        transform = _Transform(bounds, width, height)

        self.canvas.create_text(
            10,
            10,
            text=self.preview.name,
            fill="#e5e7eb",
            anchor="nw",
            font=("TkDefaultFont", 10, "bold"),
        )

        for rect in self.preview.rectangles:
            x1, y1 = transform.point(rect.start)
            x2, y2 = transform.point(rect.end)
            self.canvas.create_rectangle(
                x1, y1, x2, y2, outline="#60a5fa", width=2
            )

        for circle in self.preview.circles:
            cx, cy = transform.point(circle.center)
            radius = circle.radius * transform.scale
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
                coords.extend(transform.point(point))
            if len(coords) >= 4:
                self.canvas.create_line(*coords, fill="#60a5fa", width=2)

        for pin in self.preview.pins:
            start = pin.at
            angle = math.radians(pin.rotation)
            end = Point(
                start.x + math.cos(angle) * pin.length,
                start.y + math.sin(angle) * pin.length,
            )
            x1, y1 = transform.point(start)
            x2, y2 = transform.point(end)
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
        y = self.offset_y + (self.bounds.max_y - point.y) * self.scale
        return x, y
