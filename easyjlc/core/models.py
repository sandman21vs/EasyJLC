"""Modelos de dados para componentes retornados pela JLCPCB."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

IMAGE_URL_TEMPLATE = "https://jlcpcb.com/api/file/downloadByFileSystemAccessId/{access_id}"


@dataclass
class PriceTier:
    qty_min: int
    qty_max: int | None  # None = faixa aberta ("1000+")
    unit_usd: float

    def contains(self, qty: int) -> bool:
        if qty < self.qty_min:
            return False
        if self.qty_max is None:
            return True
        return qty <= self.qty_max

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "PriceTier":
        qmax = raw.get("endNumber")
        return cls(
            qty_min=int(raw.get("startNumber", 1) or 1),
            qty_max=None if qmax in (None, -1) else int(qmax),
            unit_usd=float(raw.get("productPrice", 0.0) or 0.0),
        )


@dataclass
class Component:
    lcsc_id: str
    mpn: str
    manufacturer: str
    package: str
    description: str
    category: str
    library_type: str  # "base" (Basic JLC) ou "expand" (Extended)
    stock: int
    min_purchase: int
    prices: list[PriceTier] = field(default_factory=list)
    datasheet_url: str | None = None
    image_access_id: str | None = None
    attributes: list[tuple[str, str]] = field(default_factory=list)

    @property
    def is_basic(self) -> bool:
        return self.library_type == "base"

    @property
    def image_url(self) -> str | None:
        if not self.image_access_id:
            return None
        return IMAGE_URL_TEMPLATE.format(access_id=self.image_access_id)

    def unit_price_for(self, qty: int = 1) -> float | None:
        for tier in self.prices:
            if tier.contains(qty):
                return tier.unit_usd
        if self.prices:
            # Se o qty está abaixo do mínimo, usa o primeiro tier.
            return self.prices[0].unit_usd
        return None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "Component":
        prices_raw = raw.get("componentPrices") or []
        prices = [PriceTier.from_api(p) for p in prices_raw if isinstance(p, dict)]
        prices.sort(key=lambda t: t.qty_min)

        attrs_raw = raw.get("attributes") or []
        attributes: list[tuple[str, str]] = []
        for a in attrs_raw:
            if not isinstance(a, dict):
                continue
            name = str(a.get("attribute_name_en") or "").strip()
            value = str(a.get("attribute_value_name") or "").strip()
            if name and value and value != "-":
                attributes.append((name, value))

        return cls(
            lcsc_id=str(raw.get("componentCode") or ""),
            mpn=str(raw.get("componentModelEn") or ""),
            manufacturer=str(raw.get("componentBrandEn") or ""),
            package=str(raw.get("componentSpecificationEn") or ""),
            description=str(raw.get("describe") or raw.get("componentTypeEn") or ""),
            category=str(
                raw.get("firstSortName")
                or raw.get("componentTypeEn")
                or ""
            ),
            library_type=str(raw.get("componentLibraryType") or "").lower(),
            stock=int(raw.get("stockCount") or 0),
            min_purchase=int(raw.get("minPurchaseNum") or 1),
            prices=prices,
            datasheet_url=(raw.get("dataManualUrl") or None),
            image_access_id=(
                raw.get("minImageAccessId")
                or raw.get("productBigImageAccessId")
                or None
            ),
            attributes=attributes,
        )


@dataclass
class SearchResult:
    items: list[Component]
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 1
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @classmethod
    def from_api(cls, payload: dict[str, Any], page: int, page_size: int) -> "SearchResult":
        data = payload.get("data") or {}
        info = data.get("componentPageInfo") or {}
        raw_list = info.get("list") or []
        items = [Component.from_api(r) for r in raw_list if isinstance(r, dict)]
        total = int(info.get("total") or 0)
        return cls(items=items, page=page, page_size=page_size, total=total)
