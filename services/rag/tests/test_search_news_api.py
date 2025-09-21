from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.ingest.sample_loader import load_samples


def test_search_news_with_samples():
    load_samples()
    as_of = datetime.now(timezone.utc)
    with TestClient(app) as client:
        resp = client.post("/search_news", json={
            "ticker": "TSM",
            "as_of": as_of.isoformat(),
            "top_k": 3,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data.get("results", [])) >= 1
    for item in data["results"]:
        assert "doc_id" in item and "url" in item


def test_as_of_filter():
    load_samples()
    as_of = datetime.now(timezone.utc) - timedelta(days=19)
    with TestClient(app) as client:
        resp = client.post("/search_news", json={
            "ticker": "TSM",
            "as_of": as_of.isoformat(),
            "top_k": 3,
        })
    assert resp.status_code == 200
    data = resp.json()
    for item in data.get("results", []):
        if item.get("published_at"):
            assert datetime.fromisoformat(item["published_at"]) <= as_of


def test_since_filter():
    load_samples()
    as_of = datetime.now(timezone.utc)
    since = as_of - timedelta(days=15)
    with TestClient(app) as client:
        resp = client.post("/search_news", json={
            "ticker": "TSM",
            "as_of": as_of.isoformat(),
            "since": since.isoformat(),
            "top_k": 10,
        })
    assert resp.status_code == 200
    data = resp.json()
    for item in data.get("results", []):
        if item.get("published_at"):
            assert datetime.fromisoformat(item["published_at"]) >= since


def test_top_k_cap():
    load_samples()
    as_of = datetime.now(timezone.utc)
    with TestClient(app) as client:
        resp = client.post("/search_news", json={
            "ticker": "TSM",
            "as_of": as_of.isoformat(),
            "top_k": 999,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["top_k"] <= 10
    assert len(data["results"]) <= 10


def test_query_without_ticker():
    load_samples()
    as_of = datetime.now(timezone.utc)
    with TestClient(app) as client:
        resp = client.post("/search_news", json={
            "query": "先進封裝",
            "as_of": as_of.isoformat(),
            "top_k": 3,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("results", []), list)
    assert len(data.get("results", [])) >= 1


