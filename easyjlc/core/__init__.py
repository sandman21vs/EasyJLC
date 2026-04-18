"""Camada de back-end (sem dependência da GUI)."""

from easyjlc.core.artifacts import KiCadArtifacts, find_kicad_artifacts
from easyjlc.core.cache import DiskCache
from easyjlc.core.easyeda import EasyEdaError, EasyEdaRunner
from easyjlc.core.jlc_api import JlcApiError, JlcClient
from easyjlc.core.kicad_parse import (
    FootprintLine,
    FootprintPad,
    FootprintPreview,
    KiCadParseError,
    Point,
    SymbolCircle,
    SymbolPin,
    SymbolPolyline,
    SymbolPreview,
    SymbolRect,
    parse_footprint,
    parse_footprint_file,
    parse_sexpr,
    parse_symbol,
    parse_symbol_file,
)
from easyjlc.core.models import Component, PriceTier, SearchResult

__all__ = [
    "Component",
    "DiskCache",
    "EasyEdaError",
    "EasyEdaRunner",
    "FootprintLine",
    "FootprintPad",
    "FootprintPreview",
    "JlcApiError",
    "JlcClient",
    "KiCadArtifacts",
    "KiCadParseError",
    "Point",
    "PriceTier",
    "SearchResult",
    "SymbolCircle",
    "SymbolPin",
    "SymbolPolyline",
    "SymbolPreview",
    "SymbolRect",
    "parse_footprint",
    "parse_footprint_file",
    "parse_sexpr",
    "parse_symbol",
    "parse_symbol_file",
    "find_kicad_artifacts",
]
