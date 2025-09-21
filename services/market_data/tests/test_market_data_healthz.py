import pytest
from services.market_data.app.api.routers import health_check

@pytest.mark.asyncio
async def test_health_check():
    resp = await health_check()
    assert resp == {"status": "ok", "service": "market_data"}
