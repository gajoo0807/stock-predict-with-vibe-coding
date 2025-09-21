# Market Data Service

This service provides market data endpoints.

## I1 完成

已新增指標庫與資料聚合（I1）：

- 支援指標：RSI(14)、MACD(12,26,9)、MA20/MA60 與 MA20 趨勢（up/down/flat）、20 日平均成交量與當日量/均量。
- 調整工具：`apply_splits`（價格除以 ratio、量乘以 ratio）、`apply_dividends`（可選，預設關閉）。
- Bars 來源：優先使用 yfinance；若外網失敗則 fallback 至 `app/data/sample/{ticker}_{tf}.parquet`。
- 參數驗證：ticker 清單長度 ≤ 50；日期窗 ≤ 5 年；timeframe 僅允許 {"1d","1h","5m"}。
- API：`GET /internal/bars?ticker=TSM,AAPL&start=2024-01-01&end=2024-02-01&tf=1d&adjust=adj`。

範例回傳（節錄）：

```json
{
  "as_of":"2025-08-26T00:00:00Z",
  "timeframe":"1d",
  "adjust":"adj",
  "results": {
    "TSM":[
      {"ts":"2024-01-02T00:00:00Z","open":...,"high":...,"low":...,"close":...,"volume":...,
       "rsi14":65.4,"macd_signal":"bullish","ma20_trend":"up","vol_vs_avg20":1.3}
    ]
  }
}
```

### 測試

執行：

```bash
poetry install
pytest -q services/market_data
```



