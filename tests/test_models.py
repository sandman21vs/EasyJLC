from easyjlc.core.models import Component, PriceTier, SearchResult


def test_price_tier_from_api_with_open_range():
    tier = PriceTier.from_api({"startNumber": 1000, "endNumber": -1, "productPrice": "0.05"})
    assert tier.qty_min == 1000
    assert tier.qty_max is None
    assert tier.unit_usd == 0.05
    assert tier.contains(5000)
    assert not tier.contains(500)


def test_price_tier_from_api_closed_range():
    tier = PriceTier.from_api({"startNumber": 1, "endNumber": 49, "productPrice": 0.2133})
    assert tier.qty_max == 49
    assert tier.contains(1)
    assert tier.contains(49)
    assert not tier.contains(50)


SAMPLE = {
    "componentCode": "C5213",
    "componentModelEn": "LM358P",
    "componentBrandEn": "Texas Instruments",
    "componentSpecificationEn": "DIP-8",
    "componentLibraryType": "expand",
    "stockCount": 25107,
    "minPurchaseNum": 1,
    "describe": "Operational Amplifier DIP-8",
    "firstSortName": "Operational Amplifier",
    "componentTypeEn": "Operational Amplifier",
    "dataManualUrl": "https://example.com/lm358.pdf",
    "minImageAccessId": "123abc",
    "componentPrices": [
        {"startNumber": 1, "endNumber": 49, "productPrice": 0.2133},
        {"startNumber": 50, "endNumber": 149, "productPrice": 0.1704},
        {"startNumber": 5000, "endNumber": -1, "productPrice": 0.1128},
    ],
    "attributes": [
        {"attribute_name_en": "Channels", "attribute_value_name": "2"},
        {"attribute_name_en": "Supply", "attribute_value_name": "-"},
        {"attribute_name_en": "", "attribute_value_name": "ignored"},
    ],
}


def test_component_from_api_basic_fields():
    c = Component.from_api(SAMPLE)
    assert c.lcsc_id == "C5213"
    assert c.mpn == "LM358P"
    assert c.manufacturer == "Texas Instruments"
    assert c.package == "DIP-8"
    assert c.stock == 25107
    assert c.datasheet_url == "https://example.com/lm358.pdf"


def test_component_is_basic_and_image_url():
    c = Component.from_api({**SAMPLE, "componentLibraryType": "base"})
    assert c.is_basic is True
    assert c.image_url is not None
    assert "123abc" in c.image_url

    expanded = Component.from_api(SAMPLE)
    assert expanded.is_basic is False


def test_component_prices_sorted_and_lookup():
    c = Component.from_api(SAMPLE)
    assert [t.qty_min for t in c.prices] == [1, 50, 5000]
    assert c.unit_price_for(1) == 0.2133
    assert c.unit_price_for(75) == 0.1704
    assert c.unit_price_for(10_000) == 0.1128


def test_component_attributes_filter_empty_and_dashes():
    c = Component.from_api(SAMPLE)
    names = [n for n, _ in c.attributes]
    assert names == ["Channels"]  # "Supply": "-" excluído, nome vazio excluído


def test_search_result_from_api_pagination():
    payload = {
        "data": {
            "componentPageInfo": {
                "total": 204,
                "list": [SAMPLE, {**SAMPLE, "componentCode": "C5423"}],
            }
        }
    }
    result = SearchResult.from_api(payload, page=1, page_size=25)
    assert result.total == 204
    assert result.total_pages == 9  # ceil(204/25)
    assert len(result.items) == 2
    assert result.items[1].lcsc_id == "C5423"


def test_search_result_empty():
    result = SearchResult.from_api({"data": {"componentPageInfo": {"total": 0, "list": []}}}, 1, 25)
    assert result.items == []
    assert result.total_pages == 1
