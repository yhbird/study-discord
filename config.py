import os
import sys
import psutil

from dotenv import load_dotenv

from datetime import datetime, timedelta
from pytz import timezone
    
def kst_format_now() -> str:
    """현재 시각을 KST 포맷으로 반환 (년-월-일 24시:분:초)"""
    kst = timezone('Asia/Seoul')
    return datetime.now(tz=kst).strftime('%Y-%m-%d %H:%M:%S')

# Discord Bot Token loading
try:
    # Load environment variables from .env file
    assert load_dotenv('./env/token.env'), Exception("token.env file not found")
    assert os.getenv('bot_token'), Exception("bot_token not found in env file")
    BOT_TOKEN: str = os.getenv('bot_token')
except Exception as e:
    print(f"Failed loading bot token!!: {e}")
    sys.exit(1)

# Nexon Open API Key loading
try:
    assert load_dotenv('./env/nexon.env'), Exception("nexon.env file not found")
    assert os.getenv('NEXON_API_TOKEN_LIVE'), Exception("NEXON_API_TOKEN_LIVE not found in env file")
    NEXON_API_KEY: str = os.getenv('NEXON_API_TOKEN_LIVE')
except Exception as e:
    print(f"Failed loading Nexon API key!!: {e}")
    sys.exit(1)

# Debug configuration
# 현재 사용중인 메모리 사용량을 MB 단위로 반환 -> 디버그용
def get_memory_usage_mb() -> float:
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / 1024**2
    return mem

# configuration variables
# 메모리 정리 주기 (분)
MEMORY_CLEAR_INTERVAL: int = 60  # minutes