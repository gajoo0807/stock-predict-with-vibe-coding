# services/<service>/tests/conftest.py
import sys
from pathlib import Path

# 將該服務根目錄（含 app/）加入匯入路徑
SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))
