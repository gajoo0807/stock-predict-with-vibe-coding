from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from app.core.http import market_data_client, rag_client
from app.domain.report_schema import (
    ContextModel,
    IndicatorsModel,
    MacdModel,
    NewsItem,
    ReportResponse,
)
from app.domain.sector_map import SECTOR_BY_TICKER


def _isoformat_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


async def _fetch_bars(ticker: str, start: str, end: str) -> Dict[str, List[Dict[str, Any]]]:
    params = {
        "ticker": ticker,
        "start": start,
        "end": end,
        "tf": "1d",
        "adjust": "adj",
    }
    resp = await market_data_client.get("/internal/bars", params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"market_data error: {resp.status_code}")
    data = resp.json()
    return data.get("results", {})


def _extract_latest_trading_as_of(bars: List[Dict[str, Any]]) -> Optional[datetime]:
    if not bars:
        return None
    latest_ts = bars[-1]["ts"]
    try:
        # Expect ISO8601
        dt = datetime.fromisoformat(latest_ts.replace("Z", "+00:00"))
    except Exception:
        return None
    return dt.astimezone(timezone.utc)


def _bars_close_list(bars: List[Dict[str, Any]]) -> List[float]:
    return [float(x.get("close")) for x in bars if x.get("close") is not None]


def _compute_twenty_day_return(bars: List[Dict[str, Any]]) -> Optional[float]:
    closes = _bars_close_list(bars)
    if len(closes) < 20:
        return None
    try:
        return closes[-1] / closes[-20] - 1.0
    except ZeroDivisionError:
        return None


def _percentile_rank(value: float, population: List[float]) -> Optional[float]:
    vals = [v for v in population if v is not None]
    if not vals:
        return None
    vals_sorted = sorted(vals)
    try:
        rank = len([v for v in vals_sorted if v <= value])
        return rank / len(vals_sorted)
    except Exception:
        return None


async def _peer_strength_percentile(ticker: str, as_of_day: datetime) -> Tuple[Optional[str], Optional[float]]:
    mapping = SECTOR_BY_TICKER.get(ticker.upper())
    if not mapping:
        return None, None
    sector, peers = mapping
    start = (as_of_day - timedelta(days=90)).date().isoformat()
    end = as_of_day.date().isoformat()
    peer_csv = ",".join(peers)
    results = await _fetch_bars(peer_csv, start, end)

    returns: List[Optional[float]] = []
    my_return: Optional[float] = None
    for sym in peers:
        sym_bars = results.get(sym, [])
        r = _compute_twenty_day_return(sym_bars)
        returns.append(r)
        if sym.upper() == ticker.upper():
            my_return = r

    if my_return is None:
        return sector, None
    pct = _percentile_rank(my_return, [r for r in returns if r is not None])
    return sector, pct


async def _fetch_latest_news(ticker: str, as_of: datetime) -> List[NewsItem]:
    try:
        payload = {"query": ticker, "as_of": _isoformat_utc(as_of), "limit": 1}
        resp = await rag_client.post("/search_news", json=payload)
        if resp.status_code != 200:
            return []
        data = resp.json()
        items = data if isinstance(data, list) else data.get("results", [])
        if not items:
            return []
        item = items[0]
        return [
            NewsItem(
                title=item.get("title", ""),
                ts=item.get("ts", _isoformat_utc(as_of)),
                doc_id=item.get("doc_id", ""),
                url=item.get("url"),
            )
        ]
    except Exception:
        return []


def _map_ma_trend(trend_value: Any) -> str:
    # Accept already normalized values or map basic signals
    if trend_value in {"up", "flat", "down"}:
        return trend_value
    try:
        v = float(trend_value)
        if v > 0:
            return "up"
        if v < 0:
            return "down"
        return "flat"
    except Exception:
        return "flat"


def _map_macd_signal(value: Any) -> str:
    val = str(value).lower()
    if val in {"bullish", "bearish", "neutral"}:
        return val
    try:
        v = float(value)
        if v > 0:
            return "bullish"
        if v < 0:
            return "bearish"
        return "neutral"
    except Exception:
        return "neutral"


async def get_report(ticker: str, as_of: Optional[datetime]) -> ReportResponse:
    # 1) parse as_of (UTC)
    as_of_utc = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start_day = (as_of_utc - timedelta(days=90)).date().isoformat()
    end_day = as_of_utc.date().isoformat()

    # 2) fetch bars for target ticker
    results = await _fetch_bars(ticker, start_day, end_day)
    bars: List[Dict[str, Any]] = results.get(ticker.upper()) or results.get(ticker) or []
    if not bars:
        raise HTTPException(status_code=404, detail="no bars for ticker in range")

    # fallback to last trading day returned
    last_trade_dt = _extract_latest_trading_as_of(bars)
    effective_as_of = last_trade_dt or as_of_utc

    last_bar = bars[-1]
    spot = float(last_bar.get("close"))
    rsi14 = float(last_bar.get("rsi14", 0.0))
    macd_signal = _map_macd_signal(last_bar.get("macd_signal"))
    trend_20_60 = _map_ma_trend(last_bar.get("ma20_trend"))
    vol_vs_avg20 = float(last_bar.get("vol_vs_avg20", 0.0))

    # 3) sector and peer percentile
    sector, peer_pct = await _peer_strength_percentile(ticker, effective_as_of)

    # 4) news
    news_items = await _fetch_latest_news(ticker, effective_as_of)

    return ReportResponse(
        as_of=_isoformat_utc(effective_as_of),
        ticker=ticker.upper(),
        spot=spot,
        indicators=IndicatorsModel(
            rsi14=rsi14,
            macd=MacdModel(signal=macd_signal),
            vol_vs_avg20=vol_vs_avg20,
            trend_20_60=trend_20_60,  # type: ignore[arg-type]
        ),
        context=ContextModel(
            sector=sector,
            peer_strength_percentile=peer_pct,
            top_news=news_items,
        ),
    )



