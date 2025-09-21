from __future__ import annotations
from typing import Dict, List, Optional


TICKER_ALIASES: Dict[str, List[str]] = {
    "TSM": ["TSM", "TSMC", "台積電", "Taiwan Semiconductor", "advanced packaging", "CoWoS", "先進封裝"],
    "AAPL": ["AAPL", "Apple", "蘋果", "A-series", "neural engine"],
    "NVDA": ["NVDA", "NVIDIA", "輝達", "data center", "AI GPUs"],
}


def aliases_for_ticker(ticker: Optional[str]) -> List[str]:
    if not ticker:
        return []
    return TICKER_ALIASES.get(ticker.upper(), [ticker])


def guess_ticker_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    for tk, alias_list in TICKER_ALIASES.items():
        for alias in alias_list:
            if alias.lower() in t:
                return tk
    return None


