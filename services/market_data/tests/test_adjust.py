import pandas as pd
from datetime import datetime, timezone

from services.market_data.app.utils.adjust import apply_splits, apply_dividends


def make_df():
    idx = pd.date_range(start="2024-01-01", periods=3, freq="1D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [10.0, 10.0, 10.0],
            "high": [11.0, 11.0, 11.0],
            "low": [9.0, 9.0, 9.0],
            "close": [10.0, 10.0, 10.0],
            "volume": [100.0, 100.0, 100.0],
        },
        index=idx,
    )
    return df


def test_split_adjust():
    df = make_df()
    actions = [{"ts": datetime(2024, 1, 3, tzinfo=timezone.utc), "ratio": 2.0}]
    adj = apply_splits(df, actions)
    # rows before 2024-01-03 are adjusted
    assert adj.loc["2024-01-01", "close"] == 5.0
    assert adj.loc["2024-01-02", "close"] == 5.0
    assert adj.loc["2024-01-01", "volume"] == 200.0


def test_dividend_adjust_enabled_disabled():
    df = make_df()
    actions = [{"ts": datetime(2024, 1, 3, tzinfo=timezone.utc), "amount": 1.0}]
    adj_disabled = apply_dividends(df, actions, enabled=False)
    assert adj_disabled.equals(df)
    adj_enabled = apply_dividends(df, actions, enabled=True)
    assert adj_enabled.loc["2024-01-01", "close"] == 9.0
    assert adj_enabled.loc["2024-01-03", "close"] == 10.0


