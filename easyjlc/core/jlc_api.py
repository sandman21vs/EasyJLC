"""Cliente HTTP para a API de peças da JLCPCB."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

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
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

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
            resp = self.session.post(
                SEARCH_URL,
                data=json.dumps(payload),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            fallback = _fallback_exact_result(query, page, page_size, f"Falha de rede: {exc}")
            if fallback is not None:
                return fallback
            raise JlcApiError(f"Falha de rede: {exc}") from exc

        if resp.status_code != 200:
            fallback = _fallback_exact_result(
                query, page, page_size, f"HTTP {resp.status_code} da JLCPCB"
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
            fallback = _fallback_exact_result(
                query, page, page_size, f"JLCPCB recusou a busca: {msg}"
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
