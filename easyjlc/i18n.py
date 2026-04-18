"""Catálogo simples de traduções (gettext-like).

Design:
- As chaves de tradução são as próprias strings em pt-BR (idioma-fonte do
  projeto). Isso mantém o código legível (`t("Baixar")` em vez de
  `t("ui.download.button")`) e dispensa um passo de extração.
- Cada idioma suportado tem um JSON em `resources/i18n/<lang>.json` com o
  mapeamento `pt-BR → tradução`. pt-BR é identidade (catálogo vazio).
- `t(key, **kwargs)` busca no catálogo ativo; se não achar, devolve a chave.
  Com `kwargs`, aplica `str.format(**kwargs)` no resultado.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("easyjlc.i18n")

DEFAULT_LANGUAGE = "pt-BR"
SUPPORTED_LANGUAGES: tuple[str, ...] = ("pt-BR", "en", "de")

_catalog: dict[str, str] = {}
_current: str = DEFAULT_LANGUAGE


def _catalog_path(lang: str) -> Path:
    return Path(__file__).parent / "resources" / "i18n" / f"{lang}.json"


def init(language: str) -> None:
    """Carrega o catálogo do idioma informado. Faz fallback para pt-BR."""
    global _catalog, _current
    if language not in SUPPORTED_LANGUAGES:
        log.warning("Idioma %r não suportado; usando %r", language, DEFAULT_LANGUAGE)
        language = DEFAULT_LANGUAGE
    _current = language
    if language == DEFAULT_LANGUAGE:
        _catalog = {}
        return
    path = _catalog_path(language)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Falha ao carregar catálogo %s (%s): %s", language, path, exc)
        _catalog = {}
        return
    if not isinstance(data, dict):
        log.warning("Catálogo %s inválido (esperava dict)", language)
        _catalog = {}
        return
    _catalog = {str(k): str(v) for k, v in data.items() if v}


def t(key: str, **kwargs: Any) -> str:
    value = _catalog.get(key, key)
    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return value
    return value


def current() -> str:
    return _current


def available() -> tuple[str, ...]:
    return SUPPORTED_LANGUAGES
