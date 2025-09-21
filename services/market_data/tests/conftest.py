# services/market_data/tests/conftest.py
import sys
from pathlib import Path

# 將 services/market_data 放到匯入路徑最前面
SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))
