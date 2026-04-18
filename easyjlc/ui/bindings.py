"""Bindings pequenos reutilizados pela UI."""

from __future__ import annotations


def bind_select_all(entry) -> None:
    """Faz Ctrl+A selecionar todo o texto em um Entry/CTkEntry."""

    def _select_all(_event):
        entry.focus_set()
        entry.select_range(0, "end")
        entry.icursor("end")
        return "break"

    def _paste(_event):
        try:
            text = entry.clipboard_get()
        except Exception:
            return "break"
        try:
            if entry.selection_present():
                entry.delete("sel.first", "sel.last")
        except Exception:
            pass
        entry.insert("insert", text)
        return "break"

    entry.bind("<Control-a>", _select_all)
    entry.bind("<Control-A>", _select_all)
    entry.bind("<Control-v>", _paste)
    entry.bind("<Control-V>", _paste)
