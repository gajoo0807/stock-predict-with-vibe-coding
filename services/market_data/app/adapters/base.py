from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict

import pandas as pd


class BarsAdapter(ABC):
    @abstractmethod
    def get_bars(self, tickers: List[str], start: datetime, end: datetime, tf: str) -> Dict[str, pd.DataFrame]:
        """Fetch bars for given tickers and timeframe.

        Returns mapping ticker -> DataFrame indexed by timestamp with columns
        ['open','high','low','close','volume'].
        """
        raise NotImplementedError



