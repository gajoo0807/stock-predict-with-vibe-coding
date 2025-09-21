## RAG Service - News Retrieval

### 環境變數
- DATABASE_URL: `postgresql+psycopg://postgres:postgres@db:5432/market`
- OPENAI_API_KEY: 可留空（本地模型 fallback）
- EMBEDDING_BACKEND: auto|openai|local（預設 auto）
- EMBEDDING_MODEL_LOCAL: sentence-transformers/all-MiniLM-L6-v2
- MAX_TOP_K: 10
- DEFAULT_TOP_K: 3
- REQUEST_TIMEOUT_SECONDS: 10

### 啟動
- 服務啟動會自動執行 Alembic 升級

### 載入樣本
```bash
docker exec -it rag python -m app.ingest.sample_loader
```

或透過 API：
```bash
curl -X POST http://localhost:8002/ingest_samples
```

### 查詢 API
```bash
curl -X POST http://localhost:8002/search_news \
  -H "Content-Type: application/json" \
  -d '{"ticker":"TSM","as_of":"2025-08-26T00:00:00Z","top_k":3}'
```

回應包含 `doc_id` 與 `url` 等欄位。


