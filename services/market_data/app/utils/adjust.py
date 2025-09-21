from __future__ import annotations

from typing import Dict, List, Any

import pandas as pd


def apply_splits(df: pd.DataFrame, corporate_actions: List[Dict[str, Any]]) -> pd.DataFrame:
    """Apply stock splits to bars dataframe.

    Each corporate action dict should include:
      - 'ts': pd.Timestamp or ISO string of effective date (applies to rows before or on ts)
      - 'ratio': float (e.g., 2.0 for 1→2 split)

    Adjustment rule: price columns ['open','high','low','close'] are divided by ratio,
    and 'volume' is multiplied by ratio, applied to rows strictly before the split timestamp.
    """
    if df.empty or not corporate_actions:
        return df

    adjusted = df.copy()
    price_cols = [c for c in ["open", "high", "low", "close"] if c in adjusted.columns]

    actions_sorted = sorted(corporate_actions, key=lambda x: pd.to_datetime(x["ts"]))
    for action in actions_sorted:
        effective_ts = pd.to_datetime(action["ts"])  # type: ignore[arg-type]
        ratio = float(action["ratio"])  # type: ignore[arg-type]
        if ratio <= 0:
            continue
        mask = adjusted.index < effective_ts
        if price_cols:
            adjusted.loc[mask, price_cols] = adjusted.loc[mask, price_cols] / ratio
        if "volume" in adjusted.columns:
            adjusted.loc[mask, "volume"] = adjusted.loc[mask, "volume"] * ratio
    return adjusted


def apply_dividends(df: pd.DataFrame, corporate_actions: List[Dict[str, Any]], enabled: bool = False) -> pd.DataFrame:
    """Optionally apply dividend adjustments. Default disabled.

    For simplicity in I1, when enabled and a dividend cash amount 'amount' is provided,
    we will subtract amount from the 'close' price for rows before the ex-dividend date.
    This is a simplistic model for testing purposes.
    Corporate action dict fields: 'ts' (timestamp), 'amount' (float).
    """
    if not enabled or df.empty or not corporate_actions:
        return df
    adjusted = df.copy()
    for action in sorted(corporate_actions, key=lambda x: pd.to_datetime(x["ts"])):
        effective_ts = pd.to_datetime(action["ts"])  # type: ignore[arg-type]
        amount = float(action.get("amount", 0.0))  # type: ignore[arg-type]
        if amount == 0.0:
            continue
        mask = adjusted.index < effective_ts
        if "close" in adjusted.columns:
            adjusted.loc[mask, "close"] = adjusted.loc[mask, "close"] - amount
            # ensure no negative prices due to synthetic example
            adjusted.loc[mask, "close"] = adjusted.loc[mask, "close"].clip(lower=0)
    return adjusted



