"""Bindings pequenos reutilizados pela UI."""

from __future__ import annotations


def bind_select_all(entry) -> None:
    """Faz Ctrl+A selecionar todo o texto em um Entry/CTkEntry."""

    def _select_all(_event):
        entry.select_range(0, "end")
        entry.icursor("end")
        return "break"

    entry.bind("<Control-a>", _select_all)
    entry.bind("<Control-A>", _select_all)
