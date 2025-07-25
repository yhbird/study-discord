import os
import sys
import psutil

from dotenv import load_dotenv

from datetime import datetime
from pytz import timezone
    
def kst_format_now() -> str:
    """현재 시각을 KST로 포맷팅

    Returns:
        str: KST로 포맷된 현재 시각 문자열
    """
    kst = timezone('Asia/Seoul')
    return datetime.now(tz=kst).strftime('%Y-%m-%d %H:%M:%S')

# Discord Bot Token loading
try:
    # Load environment variables from .env file
    assert load_dotenv('./env/token.env'), Exception("token.env file not found")
    assert os.getenv('bot_token_dev'), Exception("bot_token not found in env file")
    BOT_TOKEN_RUN: str = os.getenv('PYTHON_RUN_ENV', 'dev')
    BOT_TOKEN = os.getenv(f'bot_token_{BOT_TOKEN_RUN}', None)
# Discord 봇 토큰을 제대로 불러오지 못하면 실행 불가
except Exception as e:
    print(f"Failed loading bot token!!: {e}")
    sys.exit(1)

# Nexon Open API Key loading
try:
    assert load_dotenv('./env/nexon.env'), Exception("nexon.env file not found")
    assert os.getenv('NEXON_API_TOKEN_LIVE'), Exception("NEXON_API_TOKEN_LIVE not found in env file")
    if BOT_TOKEN_RUN == 'dev':
        NEXON_API_RUN_ENV = 'TEST'
    else:
        NEXON_API_RUN_ENV = 'LIVE'
    NEXON_API_KEY: str = os.getenv(f'NEXON_API_TOKEN_{NEXON_API_RUN_ENV}', None)
    NEXON_API_HOME: str = os.getenv('NEXON_API_HOME')
# Nexon Open API 키를 제대로 불러오지 못하면 실행 불가
except Exception as e:
    print(f"Failed loading Nexon API key!!: {e}")
    sys.exit(1)

# Debug configuration
# 현재 사용중인 메모리 사용량을 MB 단위로 반환 -> 디버그용
def get_memory_usage_mb() -> float:
    """현재 프로세스의 메모리 사용량을 MB 단위로 반환

    Returns:
        float: 현재 프로세스의 메모리 사용량 (MB)
    """
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / 1024**2
    return mem

# configuration variables
# 메모리 정리 주기 (분)
MEMORY_CLEAR_INTERVAL: int = 60  # minutes
NEXON_API_REFRESH_INTERVAL: int = 15  # minutes

# Bot 시작 시간 기록
BOT_START_TIME_STR: str = kst_format_now()
BOT_START_DT: datetime = datetime.strptime(BOT_START_TIME_STR, '%Y-%m-%d %H:%M:%S')
BOT_VERSION: str = "dev 2025-07-22"