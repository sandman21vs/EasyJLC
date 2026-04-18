"""Cliente HTTP para a API de peças da JLCPCB."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import requests

from easyjlc.config import cache_dir
from easyjlc.core.cache import DiskCache
from easyjlc.core.models import Component, SearchResult

log = logging.getLogger("easyjlc.jlc_api")

SEARCH_URL = (
    "https://jlcpcb.com/api/overseas-pcb-order/v1"
    "/shoppingCart/smtGood/selectSmtComponentList"
)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://jlcpcb.com",
    "Referer": "https://jlcpcb.com/parts",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
}

LCSC_ID_RE = re.compile(r"^C\d+$", re.IGNORECASE)


class JlcApiError(RuntimeError):
    """Erro levantado por falhas de rede ou API."""


class JlcClient:
    def __init__(
        self,
        cache: DiskCache | None = None,
        timeout: float = 15.0,
        session: requests.Session | None = None,
    ) -> None:
        self.cache = cache if cache is not None else DiskCache("jlc_search", ttl_seconds=6 * 3600)
        self.timeout = timeout
        # Injetado em testes; em produção fica None e cada chamada HTTP usa
        # requests.post() direto, sem sessão compartilhada entre threads.
        self._session = session

    def _post(self, url: str, payload: dict[str, Any]) -> requests.Response:
        data = json.dumps(payload)
        if self._session is not None:
            return self._session.post(
                url, data=data, headers=DEFAULT_HEADERS, timeout=self.timeout
            )
        return requests.post(
            url, data=data, headers=DEFAULT_HEADERS, timeout=self.timeout
        )

    def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 25,
        use_cache: bool = True,
    ) -> SearchResult:
        query = (query or "").strip()
        if not query:
            raise JlcApiError("Busca vazia.")

        cache_key = f"search::{query}::p{page}::s{page_size}"
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return SearchResult.from_api(cached, page, page_size)

        payload = {
            "keyword": query,
            "currentPage": page,
            "pageSize": page_size,
        }

        try:
            resp = self._post(SEARCH_URL, payload)
        except requests.RequestException as exc:
            fallback = self._fallback_result(query, page, page_size, cache_key, f"Falha de rede: {exc}")
            if fallback is not None:
                return fallback
            raise JlcApiError(f"Falha de rede: {exc}") from exc

        if resp.status_code != 200:
            fallback = self._fallback_result(
                query, page, page_size, cache_key, f"HTTP {resp.status_code} da JLCPCB"
            )
            if fallback is not None:
                return fallback
            raise JlcApiError(f"HTTP {resp.status_code} da JLCPCB.")

        try:
            data: dict[str, Any] = resp.json()
        except ValueError as exc:
            raise JlcApiError(f"Resposta inválida (não-JSON): {exc}") from exc

        if data.get("code") != 200:
            msg = data.get("message") or "erro desconhecido"
            fallback = self._fallback_result(
                query, page, page_size, cache_key, f"JLCPCB recusou a busca: {msg}"
            )
            if fallback is not None:
                return fallback
            raise JlcApiError(f"JLCPCB recusou a busca: {msg}")

        if use_cache:
            self.cache.set(cache_key, data)

        return SearchResult.from_api(data, page, page_size)

    def get_component(self, lcsc_id: str, use_cache: bool = True) -> Component | None:
        """Busca exata por LCSC ID — usa o mesmo endpoint de search."""
        lcsc_id = (lcsc_id or "").strip().upper()
        if not lcsc_id:
            return None
        try:
            result = self.search(lcsc_id, page=1, page_size=10, use_cache=use_cache)
        except JlcApiError:
            return None
        for item in result.items:
            if item.lcsc_id.upper() == lcsc_id:
                return item
        return None

    def _fallback_result(
        self,
        query: str,
        page: int,
        page_size: int,
        cache_key: str,
        reason: str,
    ) -> SearchResult | None:
        exact = _fallback_exact_result(query, page, page_size, reason)
        if exact is not None:
            return exact

        cached = self.cache.get_stale(cache_key)
        if cached is not None:
            result = SearchResult.from_api(cached, page, page_size)
            result.fallback_reason = f"{reason}; exibindo cache expirado"
            return result

        local = _fallback_local_previews(query, page, page_size, reason)
        if local is not None:
            return local

        return None

    def fallback_search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 25,
        reason: str = "Fallback local",
    ) -> SearchResult | None:
        cache_key = f"search::{query.strip()}::p{page}::s{page_size}"
        return self._fallback_result(query.strip(), page, page_size, cache_key, reason)


def _fallback_exact_result(
    query: str,
    page: int,
    page_size: int,
    reason: str,
) -> SearchResult | None:
    if page != 1 or not LCSC_ID_RE.match(query.strip()):
        return None
    lcsc_id = query.strip().upper()
    return SearchResult(
        items=[Component.fallback_lcsc(lcsc_id, reason)],
        page=page,
        page_size=page_size,
        total=1,
        fallback_reason=reason,
    )


def _fallback_local_previews(
    query: str,
    page: int,
    page_size: int,
    reason: str,
) -> SearchResult | None:
    if page != 1:
        return None

    term = query.strip().upper()
    if not term:
        return None

    items: list[Component] = []
    previews_root = cache_dir() / "previews"
    if not previews_root.exists():
        return None

    for part_dir in sorted(previews_root.iterdir()):
        if not part_dir.is_dir():
            continue
        component = _component_from_preview_dir(part_dir)
        if component is None:
            continue
        haystack = " ".join(
            [
                component.lcsc_id,
                component.mpn,
                component.manufacturer,
                component.package,
                component.description,
            ]
        ).upper()
        if term in haystack:
            items.append(component)

    if not items:
        return None

    return SearchResult(
        items=items[:page_size],
        page=page,
        page_size=page_size,
        total=len(items),
        fallback_reason=f"{reason}; exibindo previews locais",
    )


def _component_from_preview_dir(part_dir: Path) -> Component | None:
    symbol_files = sorted(part_dir.glob("*.kicad_sym"))
    if not symbol_files:
        return None
    text = symbol_files[0].read_text(encoding="utf-8", errors="ignore")
    lcsc_id = _property_value(text, "LCSC Part") or part_dir.name.upper()
    footprint = _property_value(text, "Footprint") or ""
    return Component(
        lcsc_id=lcsc_id,
        mpn=_property_value(text, "MPN") or _property_value(text, "Value") or "",
        manufacturer=_property_value(text, "Manufacturer") or "",
        package=footprint.split(":")[-1] if footprint else "",
        description="Resultado local de preview em cache.",
        category="",
        library_type="",
        stock=0,
        min_purchase=1,
    )


def _property_value(text: str, name: str) -> str | None:
    pattern = re.compile(
        r'\(property\s+"'
        + re.escape(name)
        + r'"\s+"([^"]+)"',
        re.IGNORECASE,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else None
