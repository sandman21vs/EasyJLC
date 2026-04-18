"""Bindings pequenos reutilizados pela UI."""

from __future__ import annotations


def bind_select_all(entry) -> None:
    """Faz Ctrl+A selecionar todo o texto em um Entry/CTkEntry."""
    widgets = [entry]
    inner = getattr(entry, "_entry", None)
    if inner is not None:
        widgets.append(inner)

    def _select_all(_event):
        target = _target_entry(entry)
        target.focus_set()
        target.select_range(0, "end")
        target.icursor("end")
        setattr(entry, "_easyjlc_all_selected", True)
        return "break"

    def _paste(_event):
        target = _target_entry(entry)
        try:
            text = target.clipboard_get()
        except Exception:
            return "break"
        if getattr(entry, "_easyjlc_all_selected", False):
            target.delete(0, "end")
            setattr(entry, "_easyjlc_all_selected", False)
        else:
            _delete_selection(target)
        target.insert("insert", text)
        return "break"

    def _clear_select_all_flag(_event):
        setattr(entry, "_easyjlc_all_selected", False)

    for widget in widgets:
        widget.bind("<Control-a>", _select_all)
        widget.bind("<Control-A>", _select_all)
        widget.bind("<Control-v>", _paste)
        widget.bind("<Control-V>", _paste)
        widget.bind("<Key>", _clear_select_all_flag, add="+")


def _target_entry(entry):
    return getattr(entry, "_entry", entry)


def _delete_selection(entry) -> None:
    try:
        first = entry.index("sel.first")
        last = entry.index("sel.last")
    except Exception:
        return
    try:
        entry.delete(first, last)
    except Exception:
        return
