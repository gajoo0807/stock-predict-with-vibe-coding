import asyncio
from datetime import datetime, timezone

import pytest
import respx
from httpx import AsyncClient, Response

from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_report_basic_success():
    base_md = str(settings.MARKET_DATA_BASE_URL)
    base_rag = str(settings.RAG_BASE_URL)

    bars_payload = {
        "timeframe": "1d",
        "adjust": "adj",
        "results": {
            "TSM": [
                {
                    "ts": "2024-01-10T00:00:00Z",
                    "open": 100,
                    "high": 110,
                    "low": 95,
                    "close": 108,
                    "volume": 1000,
                    "rsi14": 55.0,
                    "macd_signal": "bullish",
                    "ma20_trend": "up",
                    "vol_vs_avg20": 1.2,
                }
            ]
        },
    }

    peers_payload = {
        "timeframe": "1d",
        "adjust": "adj",
        "results": {
            "TSM": bars_payload["results"]["TSM"] * 20,
            "AAPL": bars_payload["results"]["TSM"] * 20,
            "NVDA": bars_payload["results"]["TSM"] * 20,
            "AMD": bars_payload["results"]["TSM"] * 20,
            "ASML": bars_payload["results"]["TSM"] * 20,
        },
    }

    news_payload = [
        {
            "title": "TSM hits new milestone",
            "ts": "2024-01-10T12:00:00Z",
            "doc_id": "doc-1",
            "url": "http://example.com/news1",
        }
    ]

    with respx.mock(assert_all_called=True) as router:
        router.get(f"{base_md}/internal/bars").mock(return_value=Response(200, json=bars_payload))
        router.get(f"{base_md}/internal/bars").mock(return_value=Response(200, json=peers_payload))
        router.post(f"{base_rag}/search_news").mock(return_value=Response(200, json=news_payload))

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get("/report", params={"ticker": "TSM"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "TSM"
        assert data["spot"] == 108
        assert data["indicators"]["rsi14"] == 55.0
        assert data["indicators"]["macd"]["signal"] in ["bullish", "bearish", "neutral"]
        assert isinstance(data["context"]["top_news"], list) and len(data["context"]["top_news"]) == 1


@pytest.mark.asyncio
async def test_report_weekend_as_of_fallback():
    base_md = str(settings.MARKET_DATA_BASE_URL)

    weekend_as_of = "2024-01-07T00:00:00Z"  # Sunday
    bars_payload = {
        "timeframe": "1d",
        "adjust": "adj",
        "results": {
            "TSM": [
                {
                    "ts": "2024-01-05T00:00:00Z",  # last trading day Fri
                    "open": 100,
                    "high": 110,
                    "low": 95,
                    "close": 108,
                    "volume": 1000,
                    "rsi14": 55.0,
                    "macd_signal": "bullish",
                    "ma20_trend": "up",
                    "vol_vs_avg20": 1.2,
                }
            ]
        },
    }

    peers_payload = bars_payload

    with respx.mock(assert_all_called=True) as router:
        router.get(f"{base_md}/internal/bars").mock(return_value=Response(200, json=bars_payload))
        router.get(f"{base_md}/internal/bars").mock(return_value=Response(200, json=peers_payload))

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get("/report", params={"ticker": "TSM", "as_of": weekend_as_of})
        assert resp.status_code == 200
        data = resp.json()
        assert data["as_of"] == "2024-01-05T00:00:00Z"


@pytest.mark.asyncio
async def test_report_news_timeout_returns_empty():
    base_md = str(settings.MARKET_DATA_BASE_URL)
    base_rag = str(settings.RAG_BASE_URL)

    bars_payload = {
        "timeframe": "1d",
        "adjust": "adj",
        "results": {
            "TSM": [
                {
                    "ts": "2024-01-10T00:00:00Z",
                    "open": 100,
                    "high": 110,
                    "low": 95,
                    "close": 108,
                    "volume": 1000,
                    "rsi14": 55.0,
                    "macd_signal": "bullish",
                    "ma20_trend": "up",
                    "vol_vs_avg20": 1.2,
                }
            ]
        },
    }

    peers_payload = bars_payload

    with respx.mock(assert_all_called=True) as router:
        router.get(f"{base_md}/internal/bars").mock(return_value=Response(200, json=bars_payload))
        router.get(f"{base_md}/internal/bars").mock(return_value=Response(200, json=peers_payload))
        router.post(f"{base_rag}/search_news").mock(side_effect=Exception("timeout"))

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get("/report", params={"ticker": "TSM"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["context"]["top_news"] == []


@pytest.mark.asyncio
async def test_report_peer_strength_percentile_range():
    base_md = str(settings.MARKET_DATA_BASE_URL)

    # Construct 20 bars with monotonic increase for target, varied peers
    def gen_bars(start_close: float) -> list[dict]:
        bars = []
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        for i in range(20):
            bars.append(
                {
                    "ts": (ts).isoformat().replace("+00:00", "Z"),
                    "open": start_close,
                    "high": start_close + 1,
                    "low": start_close - 1,
                    "close": start_close + i * 0.5,
                    "volume": 1000 + i,
                    "rsi14": 50.0,
                    "macd_signal": "neutral",
                    "ma20_trend": "flat",
                    "vol_vs_avg20": 1.0,
                }
            )
            ts = ts + timedelta(days=1)
        return bars

    from datetime import timedelta

    results_peers = {
        "TSM": gen_bars(100),
        "AAPL": gen_bars(90),
        "NVDA": gen_bars(80),
        "AMD": gen_bars(70),
        "ASML": gen_bars(60),
    }

    bars_payload = {
        "timeframe": "1d",
        "adjust": "adj",
        "results": {"TSM": results_peers["TSM"]},
    }
    peers_payload = {"timeframe": "1d", "adjust": "adj", "results": results_peers}

    with respx.mock(assert_all_called=True) as router:
        router.get(f"{base_md}/internal/bars").mock(return_value=Response(200, json=bars_payload))
        router.get(f"{base_md}/internal/bars").mock(return_value=Response(200, json=peers_payload))

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get("/report", params={"ticker": "TSM"})
        assert resp.status_code == 200
        pct = resp.json()["context"]["peer_strength_percentile"]
        assert pct is None or (0.0 <= pct <= 1.0)


@pytest.mark.asyncio
async def test_report_no_bars_404():
    base_md = str(settings.MARKET_DATA_BASE_URL)

    bars_payload = {"timeframe": "1d", "adjust": "adj", "results": {"TSM": []}}

    with respx.mock(assert_all_called=True) as router:
        router.get(f"{base_md}/internal/bars").mock(return_value=Response(200, json=bars_payload))

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get("/report", params={"ticker": "TSM"})
        assert resp.status_code == 404


