from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from easyjlc.core.cache import DiskCache
from easyjlc.core import jlc_api
from easyjlc.core.jlc_api import JlcApiError, JlcClient


def _fake_response(status: int, payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    return resp


def _make_client(tmp_path: Path, session: MagicMock) -> JlcClient:
    cache = DiskCache("test_jlc", root=tmp_path)
    return JlcClient(cache=cache, session=session)


SEARCH_OK = {
    "code": 200,
    "data": {
        "componentPageInfo": {
            "total": 1,
            "list": [{
                "componentCode": "C5213",
                "componentModelEn": "LM358P",
                "componentBrandEn": "TI",
                "componentSpecificationEn": "DIP-8",
                "componentLibraryType": "expand",
                "stockCount": 10,
                "minPurchaseNum": 1,
                "componentPrices": [{"startNumber": 1, "endNumber": -1, "productPrice": 0.2}],
            }],
        }
    },
}


def test_search_empty_query_raises(tmp_path: Path):
    client = _make_client(tmp_path, MagicMock())
    with pytest.raises(JlcApiError):
        client.search("   ")


def test_search_happy_path(tmp_path: Path):
    session = MagicMock()
    session.post.return_value = _fake_response(200, SEARCH_OK)
    client = _make_client(tmp_path, session)

    result = client.search("LM358")
    assert result.total == 1
    assert result.items[0].lcsc_id == "C5213"
    assert session.post.call_count == 1


def test_search_uses_cache_on_second_call(tmp_path: Path):
    session = MagicMock()
    session.post.return_value = _fake_response(200, SEARCH_OK)
    client = _make_client(tmp_path, session)

    client.search("LM358")
    client.search("LM358")
    assert session.post.call_count == 1  # segundo serviço do cache


def test_search_bypasses_cache_when_disabled(tmp_path: Path):
    session = MagicMock()
    session.post.return_value = _fake_response(200, SEARCH_OK)
    client = _make_client(tmp_path, session)

    client.search("LM358")
    client.search("LM358", use_cache=False)
    assert session.post.call_count == 2


def test_search_http_error(tmp_path: Path):
    session = MagicMock()
    session.post.return_value = _fake_response(500, {})
    client = _make_client(tmp_path, session)

    with pytest.raises(JlcApiError):
        client.search("LM358")


def test_search_http_error_exact_lcsc_falls_back(tmp_path: Path):
    session = MagicMock()
    session.post.return_value = _fake_response(403, {})
    client = _make_client(tmp_path, session)

    result = client.search("C129733")
    assert result.total == 1
    assert result.fallback_reason == "HTTP 403 da JLCPCB"
    assert result.items[0].lcsc_id == "C129733"
    assert "Resultado local" in result.items[0].description


def test_search_http_error_uses_stale_cache_for_text(tmp_path: Path):
    session = MagicMock()
    session.post.return_value = _fake_response(200, SEARCH_OK)
    client = _make_client(tmp_path, session)
    client.search("LM358")

    session.post.return_value = _fake_response(403, {})
    result = client.search("LM358", use_cache=False)

    assert result.items[0].lcsc_id == "C5213"
    assert result.fallback_reason is not None
    assert "cache expirado" in result.fallback_reason


def test_search_http_error_uses_local_preview_for_text(tmp_path: Path, monkeypatch):
    previews = tmp_path / "previews" / "C82899"
    previews.mkdir(parents=True)
    (previews / "easyeda2kicad.kicad_sym").write_text(
        """
        (kicad_symbol_lib
          (symbol "ESP32-WROOM-32"
            (property "Value" "ESP32-WROOM-32")
            (property "MPN" "ESP32-WROOM-32-N4")
            (property "Manufacturer" "Espressif")
            (property "Footprint" "easyeda2kicad:WIFIM-SMD_ESP32-WROOM-32-N4")
            (property "LCSC Part" "C82899")))
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(jlc_api, "cache_dir", lambda: tmp_path)

    session = MagicMock()
    session.post.return_value = _fake_response(403, {})
    client = _make_client(tmp_path, session)

    result = client.search("esp32")

    assert result.items[0].lcsc_id == "C82899"
    assert result.items[0].mpn == "ESP32-WROOM-32-N4"
    assert result.items[0].package == "WIFIM-SMD_ESP32-WROOM-32-N4"
    assert result.fallback_reason is not None
    assert "previews locais" in result.fallback_reason


def test_public_fallback_search_for_exact_lcsc(tmp_path: Path):
    client = _make_client(tmp_path, MagicMock())
    result = client.fallback_search("C129733", reason="timeout")

    assert result is not None
    assert result.items[0].lcsc_id == "C129733"
    assert result.fallback_reason == "timeout"


def test_search_api_error_code(tmp_path: Path):
    session = MagicMock()
    session.post.return_value = _fake_response(200, {"code": 101, "message": "oops"})
    client = _make_client(tmp_path, session)

    with pytest.raises(JlcApiError):
        client.search("LM358")


def test_search_network_error(tmp_path: Path):
    session = MagicMock()
    session.post.side_effect = requests.ConnectionError("offline")
    client = _make_client(tmp_path, session)

    with pytest.raises(JlcApiError):
        client.search("LM358")


def test_search_network_error_exact_lcsc_falls_back(tmp_path: Path):
    session = MagicMock()
    session.post.side_effect = requests.ConnectionError("offline")
    client = _make_client(tmp_path, session)

    result = client.search("c129733")
    assert result.items[0].lcsc_id == "C129733"
    assert result.fallback_reason is not None


def test_get_component_by_id(tmp_path: Path):
    session = MagicMock()
    session.post.return_value = _fake_response(200, SEARCH_OK)
    client = _make_client(tmp_path, session)

    comp = client.get_component("C5213")
    assert comp is not None
    assert comp.mpn == "LM358P"


def test_get_component_miss(tmp_path: Path):
    session = MagicMock()
    session.post.return_value = _fake_response(200, SEARCH_OK)
    client = _make_client(tmp_path, session)

    assert client.get_component("C9999") is None
    assert client.get_component("") is None
