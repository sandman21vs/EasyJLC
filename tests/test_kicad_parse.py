from pathlib import Path

import pytest

from easyjlc.core.kicad_parse import (
    KiCadParseError,
    parse_footprint,
    parse_footprint_file,
    parse_sexpr,
    parse_symbol,
    parse_symbol_file,
)


SYMBOL_TEXT = """
(kicad_symbol_lib
  (version 20231120)
  (generator "easyeda2kicad")
  (symbol "LM358P"
    (rectangle (start -5.08 5.08) (end 5.08 -5.08)
      (stroke (width 0.254) (type default)) (fill (type none)))
    (circle (center 0 0) (radius 1.27)
      (stroke (width 0.254) (type default)) (fill (type none)))
    (polyline
      (pts (xy -1 -1) (xy 0 1) (xy 1 -1))
      (stroke (width 0.254) (type default)) (fill (type none)))
    (pin input line (at -7.62 2.54 0) (length 2.54)
      (name "IN+" (effects (font (size 1.27 1.27))))
      (number "1" (effects (font (size 1.27 1.27)))))
    (pin output line (at 7.62 0 180) (length 2.54)
      (name "OUT" (effects (font (size 1.27 1.27))))
      (number "7" (effects (font (size 1.27 1.27)))))
  )
)
"""


FOOTPRINT_TEXT = """
(footprint "SOIC-8"
  (version 20240108)
  (generator "easyeda2kicad")
  (fp_line (start -2.5 -3.9) (end 2.5 -3.9)
    (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
  (fp_line (start 2.5 -3.9) (end 2.5 3.9)
    (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
  (pad "1" smd rect (at -3.3 -2.625 0) (size 1.5 0.6)
    (layers "F.Cu" "F.Paste" "F.Mask"))
  (pad "8" smd roundrect (at 3.3 -2.625 180) (size 1.5 0.6)
    (layers "F.Cu" "F.Paste" "F.Mask"))
)
"""


def test_parse_sexpr_handles_comments_and_quoted_strings():
    root = parse_sexpr('(root "quoted value" ; ignored\n (child escaped\\ token))')
    assert root == ["root", "quoted value", ["child", "escaped\\", "token"]]


def test_parse_symbol_extracts_preview_primitives():
    root = parse_sexpr(SYMBOL_TEXT)
    symbol = parse_symbol(root)

    assert symbol.name == "LM358P"
    assert len(symbol.pins) == 2
    assert symbol.pins[0].name == "IN+"
    assert symbol.pins[0].number == "1"
    assert symbol.pins[0].at.x == -7.62
    assert symbol.pins[1].rotation == 180
    assert len(symbol.rectangles) == 1
    assert symbol.rectangles[0].end.y == -5.08
    assert len(symbol.circles) == 1
    assert symbol.circles[0].radius == 1.27
    assert len(symbol.polylines) == 1
    assert len(symbol.polylines[0].points) == 3


def test_parse_symbol_can_select_by_name():
    text = """
    (kicad_symbol_lib
      (symbol "A" (pin input line (at 0 0 0) (length 1) (name "A") (number "1")))
      (symbol "B" (pin input line (at 2 0 0) (length 1) (name "B") (number "2")))
    )
    """
    symbol = parse_symbol(parse_sexpr(text), symbol_name="B")
    assert symbol.name == "B"
    assert symbol.pins[0].number == "2"


def test_parse_symbol_file(tmp_path: Path):
    path = tmp_path / "part.kicad_sym"
    path.write_text(SYMBOL_TEXT, encoding="utf-8")
    assert parse_symbol_file(path).name == "LM358P"


def test_parse_footprint_extracts_lines_and_pads():
    footprint = parse_footprint(parse_sexpr(FOOTPRINT_TEXT))

    assert footprint.name == "SOIC-8"
    assert len(footprint.lines) == 2
    assert footprint.lines[0].layer == "F.SilkS"
    assert footprint.lines[0].start.x == -2.5
    assert len(footprint.pads) == 2
    assert footprint.pads[0].number == "1"
    assert footprint.pads[0].kind == "smd"
    assert footprint.pads[0].shape == "rect"
    assert footprint.pads[0].size.x == 1.5
    assert footprint.pads[1].rotation == 180
    assert footprint.pads[1].layers == ["F.Cu", "F.Paste", "F.Mask"]


def test_parse_footprint_file(tmp_path: Path):
    path = tmp_path / "part.kicad_mod"
    path.write_text(FOOTPRINT_TEXT, encoding="utf-8")
    assert parse_footprint_file(path).name == "SOIC-8"


def test_parse_errors_on_malformed_input():
    with pytest.raises(KiCadParseError):
        parse_sexpr("(root (missing)")


def test_parse_errors_when_symbol_is_missing():
    with pytest.raises(KiCadParseError):
        parse_symbol(parse_sexpr('(kicad_symbol_lib (symbol "A"))'), symbol_name="B")
