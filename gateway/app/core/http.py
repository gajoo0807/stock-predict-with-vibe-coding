from typing import Any, Dict, Optional

import httpx

from app.core.config import settings


class InternalHttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.timeout = settings.REQUEST_TIMEOUT_SECONDS
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        return await self._client.get(path, params=params)

    async def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> httpx.Response:
        return await self._client.post(path, json=json)

    async def aclose(self) -> None:
        await self._client.aclose()


market_data_client = InternalHttpClient(settings.MARKET_DATA_BASE_URL)
rag_client = InternalHttpClient(settings.RAG_BASE_URL)



