# Gateway Service

## /report API

- Method: GET
- Path: `/report`
- Query params:
  - `ticker` (required): e.g. `TSM`
  - `as_of` (optional ISO8601): e.g. `2025-08-26T00:00:00Z`

### Behavior
- Aggregates latest data from market_data and rag
- If `as_of` falls on weekend/holiday, falls back to the latest available trading day
- If rag is unavailable or times out, `top_news` returns an empty array
- If market_data returns empty bars, responds 404 with `{ "detail": "no bars for ticker in range" }`

### Response Schema

```
{
  "as_of": "2024-01-10T00:00:00Z",
  "ticker": "TSM",
  "spot": 108.0,
  "indicators": {
    "rsi14": 55.0,
    "macd": { "signal": "bullish" },
    "vol_vs_avg20": 1.2,
    "trend_20_60": "up"
  },
  "context": {
    "sector": "Semiconductors",
    "peer_strength_percentile": 0.8,
    "top_news": [
      {"title": "...", "ts": "...", "doc_id": "...", "url": "..."}
    ]
  }
}
```

### Example

```bash
curl "http://localhost:8000/report?ticker=TSM&as_of=2025-08-26T00:00:00Z"
```

### Swagger

Visit `/docs` for interactive documentation.


