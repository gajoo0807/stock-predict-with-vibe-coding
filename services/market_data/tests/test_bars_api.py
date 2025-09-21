from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.market_data.app.main import app
from services.market_data.app.adapters.free_source import generate_sample_parquet


def test_internal_bars_basic_and_format(tmp_path: Path, monkeypatch):
    sample_dir = Path(__file__).resolve().parents[2] / "app" / "data" / "sample"
    # Ensure sample data exists
    generate_sample_parquet(sample_dir)

    client = TestClient(app)
    resp = client.get(
        "/internal/bars",
        params={
            "ticker": "TSM,AAPL",
            "start": "2024-01-01",
            "end": "2024-02-01",
            "tf": "1d",
            "adjust": "adj",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["timeframe"] == "1d"
    assert data["adjust"] == "adj"
    assert "results" in data and isinstance(data["results"], dict)
    # At least keys exist
    assert "TSM" in data["results"]
    # Check one row's fields
    if data["results"]["TSM"]:
        row = data["results"]["TSM"][0]
        for k in ["ts", "open", "high", "low", "close", "volume", "rsi14", "macd_signal", "ma20_trend", "vol_vs_avg20"]:
            assert k in row


def test_internal_bars_param_validation(monkeypatch):
    client = TestClient(app)
    # too many tickers
    tickers = ",".join([f"T{i}" for i in range(51)])
    resp = client.get(
        "/internal/bars",
        params={"ticker": tickers, "start": "2020-01-01", "end": "2021-01-01", "tf": "1d"},
    )
    assert resp.status_code == 422

    # timeframe invalid
    resp = client.get(
        "/internal/bars",
        params={"ticker": "TSM", "start": "2020-01-01", "end": "2021-01-01", "tf": "2m"},
    )
    assert resp.status_code == 422

    # window > 5 years
    resp = client.get(
        "/internal/bars",
        params={"ticker": "TSM", "start": "2010-01-01", "end": "2020-01-01", "tf": "1d"},
    )
    assert resp.status_code == 422


def test_internal_bars_weekend_empty(monkeypatch):
    client = TestClient(app)
    resp = client.get(
        "/internal/bars",
        params={"ticker": "TSM", "start": "2024-01-06", "end": "2024-01-07", "tf": "1d"},  # weekend
    )
    assert resp.status_code == 200
    data = resp.json()
    # likely empty array for weekend if no data
    assert isinstance(data["results"]["TSM"], list)


def test_internal_bars_adjust_raw_vs_adj(tmp_path: Path):
    sample_dir = Path(__file__).resolve().parents[2] / "app" / "data" / "sample"
    generate_sample_parquet(sample_dir)

    client = TestClient(app)
    resp_raw = client.get(
        "/internal/bars",
        params={"ticker": "AAPL", "start": "2024-01-01", "end": "2024-02-01", "tf": "1d", "adjust": "raw"},
    )
    resp_adj = client.get(
        "/internal/bars",
        params={"ticker": "AAPL", "start": "2024-01-01", "end": "2024-02-01", "tf": "1d", "adjust": "adj"},
    )
    assert resp_raw.status_code == 200 and resp_adj.status_code == 200
    data_raw = resp_raw.json()["results"]["AAPL"]
    data_adj = resp_adj.json()["results"]["AAPL"]
    # With no corporate actions, raw and adj might be equal; but endpoint must respond properly
    assert isinstance(data_raw, list) and isinstance(data_adj, list)


