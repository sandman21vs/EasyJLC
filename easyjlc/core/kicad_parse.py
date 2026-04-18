"""Parser minimal para previews de arquivos KiCad."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

Sexp = str | list["Sexp"]


class KiCadParseError(ValueError):
    """Erro levantado quando um arquivo KiCad não pode ser interpretado."""


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class SymbolPin:
    name: str
    number: str
    at: Point
    rotation: float
    length: float
    electrical_type: str


@dataclass(frozen=True)
class SymbolRect:
    start: Point
    end: Point


@dataclass(frozen=True)
class SymbolCircle:
    center: Point
    radius: float


@dataclass(frozen=True)
class SymbolPolyline:
    points: list[Point]


@dataclass(frozen=True)
class SymbolPreview:
    name: str
    pins: list[SymbolPin] = field(default_factory=list)
    rectangles: list[SymbolRect] = field(default_factory=list)
    circles: list[SymbolCircle] = field(default_factory=list)
    polylines: list[SymbolPolyline] = field(default_factory=list)


@dataclass(frozen=True)
class FootprintLine:
    start: Point
    end: Point
    layer: str


@dataclass(frozen=True)
class FootprintPad:
    number: str
    kind: str
    shape: str
    at: Point
    rotation: float
    size: Point
    layers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FootprintPreview:
    name: str
    lines: list[FootprintLine] = field(default_factory=list)
    pads: list[FootprintPad] = field(default_factory=list)


def parse_sexpr(text: str) -> Sexp:
    """Converte texto S-expression KiCad para listas/strings Python."""
    tokens = list(_tokens(text))
    if not tokens:
        raise KiCadParseError("Arquivo vazio.")

    stack: list[list[Sexp]] = []
    root: Sexp | None = None

    for token in tokens:
        if token == "(":
            node: list[Sexp] = []
            if stack:
                stack[-1].append(node)
            elif root is not None:
                raise KiCadParseError("Mais de uma expressão raiz.")
            stack.append(node)
            continue

        if token == ")":
            if not stack:
                raise KiCadParseError("Parêntese fechando sem abertura.")
            node = stack.pop()
            if not stack:
                root = node
            continue

        if not stack:
            raise KiCadParseError("Token fora da expressão raiz.")
        stack[-1].append(token)

    if stack:
        raise KiCadParseError("Parêntese aberto sem fechamento.")
    if root is None:
        raise KiCadParseError("Expressão raiz ausente.")
    return root


def parse_symbol_file(
    path: str | Path,
    symbol_name: str | None = None,
    lcsc_id: str | None = None,
) -> SymbolPreview:
    root = parse_sexpr(Path(path).read_text(encoding="utf-8"))
    return parse_symbol(root, symbol_name=symbol_name, lcsc_id=lcsc_id)


def parse_footprint_file(path: str | Path) -> FootprintPreview:
    root = parse_sexpr(Path(path).read_text(encoding="utf-8"))
    return parse_footprint(root)


def parse_symbol(
    root: Sexp,
    symbol_name: str | None = None,
    lcsc_id: str | None = None,
) -> SymbolPreview:
    node = _find_symbol_node(root, symbol_name, lcsc_id)
    if node is None:
        target = f' "{symbol_name}"' if symbol_name else ""
        if lcsc_id:
            target = f' com LCSC "{lcsc_id}"'
        raise KiCadParseError(f"Nenhum símbolo{target} encontrado.")

    name = _atom(node, 1) or ""
    pins: list[SymbolPin] = []
    rectangles: list[SymbolRect] = []
    circles: list[SymbolCircle] = []
    polylines: list[SymbolPolyline] = []

    for child in _walk_lists(node):
        head = _head(child)
        if head == "pin":
            pin = _parse_symbol_pin(child)
            if pin is not None:
                pins.append(pin)
        elif head == "rectangle":
            rect = _parse_symbol_rect(child)
            if rect is not None:
                rectangles.append(rect)
        elif head == "circle":
            circle = _parse_symbol_circle(child)
            if circle is not None:
                circles.append(circle)
        elif head == "polyline":
            polyline = _parse_symbol_polyline(child)
            if polyline is not None:
                polylines.append(polyline)

    return SymbolPreview(
        name=name,
        pins=pins,
        rectangles=rectangles,
        circles=circles,
        polylines=polylines,
    )


def parse_footprint(root: Sexp) -> FootprintPreview:
    if not _is_list(root) or _head(root) not in {"footprint", "module"}:
        raise KiCadParseError("Arquivo não parece ser um footprint KiCad.")

    name = _atom(root, 1) or ""
    lines: list[FootprintLine] = []
    pads: list[FootprintPad] = []

    for child in _children(root):
        head = _head(child)
        if head in {"fp_line", "gr_line"}:
            line = _parse_footprint_line(child)
            if line is not None:
                lines.append(line)
        elif head == "pad":
            pad = _parse_footprint_pad(child)
            if pad is not None:
                pads.append(pad)

    return FootprintPreview(name=name, lines=lines, pads=pads)


def _tokens(text: str):
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch == ";":
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        if ch in "()":
            yield ch
            i += 1
            continue
        if ch == '"':
            i += 1
            buf: list[str] = []
            while i < n:
                ch = text[i]
                if ch == "\\" and i + 1 < n:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                if ch == '"':
                    i += 1
                    break
                buf.append(ch)
                i += 1
            else:
                raise KiCadParseError("String sem fechamento.")
            yield "".join(buf)
            continue

        start = i
        while i < n and not text[i].isspace() and text[i] not in "();":
            i += 1
        yield text[start:i]


def _find_symbol_node(
    root: Sexp,
    symbol_name: str | None,
    lcsc_id: str | None,
) -> list[Sexp] | None:
    if not _is_list(root):
        return None
    if _head(root) == "symbol" and _symbol_matches(root, symbol_name, lcsc_id):
        return root
    for child in _children(root):
        found = _find_symbol_node(child, symbol_name, lcsc_id)
        if found is not None:
            return found
    return None


def _symbol_matches(
    node: list[Sexp],
    symbol_name: str | None,
    lcsc_id: str | None,
) -> bool:
    if symbol_name is not None and _atom(node, 1) != symbol_name:
        return False
    if lcsc_id is not None and _symbol_lcsc_id(node) != lcsc_id.strip().upper():
        return False
    return True


def _symbol_lcsc_id(node: list[Sexp]) -> str | None:
    for child in _children(node):
        if _head(child) != "property":
            continue
        key = (_atom(child, 1) or "").strip().lower()
        value = (_atom(child, 2) or "").strip().upper()
        if key == "lcsc part" and value:
            return value
    return None


def _parse_symbol_pin(node: list[Sexp]) -> SymbolPin | None:
    at = _point_from_child(node, "at")
    if at is None:
        return None
    length = _float_from_child(node, "length", 0.0)
    return SymbolPin(
        name=_text_from_named_child(node, "name"),
        number=_text_from_named_child(node, "number"),
        at=at,
        rotation=_float_from_child(node, "at", 0.0, index=3),
        length=length,
        electrical_type=_atom(node, 1) or "",
    )


def _parse_symbol_rect(node: list[Sexp]) -> SymbolRect | None:
    start = _point_from_child(node, "start")
    end = _point_from_child(node, "end")
    if start is None or end is None:
        return None
    return SymbolRect(start=start, end=end)


def _parse_symbol_circle(node: list[Sexp]) -> SymbolCircle | None:
    center = _point_from_child(node, "center")
    radius = _float_from_child(node, "radius", 0.0)
    if center is None:
        return None
    return SymbolCircle(center=center, radius=radius)


def _parse_symbol_polyline(node: list[Sexp]) -> SymbolPolyline | None:
    pts = _child(node, "pts")
    if pts is None:
        return None
    points = [
        Point(_float(point, 1), _float(point, 2))
        for point in _children(pts)
        if _head(point) == "xy"
    ]
    if not points:
        return None
    return SymbolPolyline(points=points)


def _parse_footprint_line(node: list[Sexp]) -> FootprintLine | None:
    start = _point_from_child(node, "start")
    end = _point_from_child(node, "end")
    if start is None or end is None:
        return None
    return FootprintLine(
        start=start,
        end=end,
        layer=_text_from_named_child(node, "layer"),
    )


def _parse_footprint_pad(node: list[Sexp]) -> FootprintPad | None:
    at = _point_from_child(node, "at")
    size = _point_from_child(node, "size")
    if at is None or size is None:
        return None
    layers_node = _child(node, "layers")
    layers = [_as_atom(item) for item in (layers_node or [])[1:] if _as_atom(item)]
    return FootprintPad(
        number=_atom(node, 1) or "",
        kind=_atom(node, 2) or "",
        shape=_atom(node, 3) or "",
        at=at,
        rotation=_float_from_child(node, "at", 0.0, index=3),
        size=size,
        layers=layers,
    )


def _walk_lists(node: Sexp):
    if not _is_list(node):
        return
    for child in _children(node):
        yield child
        yield from _walk_lists(child)


def _children(node: Sexp) -> list[list[Sexp]]:
    if not _is_list(node):
        return []
    return [item for item in node[1:] if _is_list(item)]


def _child(node: list[Sexp], name: str) -> list[Sexp] | None:
    for child in _children(node):
        if _head(child) == name:
            return child
    return None


def _point_from_child(node: list[Sexp], name: str) -> Point | None:
    child = _child(node, name)
    if child is None or len(child) < 3:
        return None
    return Point(_float(child, 1), _float(child, 2))


def _text_from_named_child(node: list[Sexp], name: str) -> str:
    child = _child(node, name)
    return _atom(child, 1) if child else ""


def _float_from_child(
    node: list[Sexp], name: str, default: float, index: int = 1
) -> float:
    child = _child(node, name)
    if child is None or len(child) <= index:
        return default
    return _float(child, index, default)


def _float(node: list[Sexp], index: int, default: float = 0.0) -> float:
    value = _atom(node, index)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _atom(node: Sexp | None, index: int) -> str | None:
    if not _is_list(node) or len(node) <= index:
        return None
    return _as_atom(node[index])


def _as_atom(value: Sexp) -> str | None:
    return value if isinstance(value, str) else None


def _head(node: Sexp) -> str | None:
    return _atom(node, 0)


def _is_list(value: Sexp | None) -> bool:
    return isinstance(value, list)
