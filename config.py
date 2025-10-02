import os
import sys
from typing import List

from dotenv import load_dotenv

from datetime import datetime
from pytz import timezone

from exceptions.base import BotConfigFailed, BotInitializationError

# Discord Bot Token loading
try:
    # Load environment variables from .env file
    assert load_dotenv('./env/token.env'), BotConfigFailed("token.env file not found")
    assert os.getenv('bot_token_dev'), BotInitializationError("bot_token not found in env file")
    BOT_TOKEN_RUN: str = os.getenv('PYTHON_RUN_ENV', 'dev')
    BOT_TOKEN = os.getenv(f'bot_token_{BOT_TOKEN_RUN}', None)
# Discord 봇 토큰을 제대로 불러오지 못하면 실행 불가
except BotConfigFailed as e:
    print(f"Failed Bot loading during Discord Token loading: {e}")
    sys.exit(True)
except BotInitializationError as e:
    print(f"Bot token loading failed: {e}")
    sys.exit(True)

# Nexon Open API Key loading
try:
    assert load_dotenv('./env/nexon.env'), BotConfigFailed("nexon.env file not found")
    assert os.getenv('NEXON_API_TOKEN_LIVE'), BotInitializationError("NEXON_API_TOKEN_LIVE not found in env file")
    if BOT_TOKEN_RUN == 'dev':
        NEXON_API_RUN_ENV = 'TEST'
    else:
        NEXON_API_RUN_ENV = 'LIVE'
    NEXON_API_KEY: str = os.getenv(f'NEXON_API_TOKEN_{NEXON_API_RUN_ENV}', None)
    NEOPLE_API_KEY: str = os.getenv(f'NEOPLE_API_TOKEN_{NEXON_API_RUN_ENV}', None)
    NEXON_API_HOME: str = os.getenv('NEXON_API_HOME')
    NEOPLE_API_HOME: str = os.getenv('NEOPLE_API_HOME')
# Nexon Open API 키를 제대로 불러오지 못하면 실행 불가
except BotConfigFailed as e:
    print(f"Failed Bot loading during Nexon API Key loading: {e}")
    sys.exit(True)
except BotInitializationError as e:
    print(f"Nexon API Key loading failed: {e}")
    sys.exit(True)

# weather API Key loading
try:
    assert load_dotenv('./env/weather.env'), BotConfigFailed("weather.env file not found")
    assert os.getenv('kko_token_api'), BotInitializationError("kko_token_api not found in env file")
    assert os.getenv('wth_data_api'), BotInitializationError("wth_data_api not found in env file")
    KKO_LOCAL_API_KEY: str = os.getenv('kko_token_api', None)
    KKO_API_HOME: str = os.getenv('kko_api_url', None)
    WTH_DATA_API_KEY: str = os.getenv('wth_data_api', None)
    WTH_API_HOME: str = os.getenv('wth_data_url', None)
# weather API 키를 제대로 불러오지 못하면 실행 불가
except BotConfigFailed as e:
    print(f"Failed loading weather API key!!: {e}")
    sys.exit(True)
except BotInitializationError as e:
    print(f"Weather API Key loading failed: {e}")
    sys.exit(True)

# 히든변수 및 히든명령어 loading
if load_dotenv('./env/secret.env'):
    BAN_CMD_1 = os.getenv('ban_cmd_1', '')
    BAN_CMD_2 = os.getenv('ban_cmd_2', '')
    BAN_CMD_3 = os.getenv('ban_cmd_3', '')
    SECRET_COMMANDS: List[str] = [BAN_CMD_1, BAN_CMD_2, BAN_CMD_3]
    BOT_DEVELOPER_ID: int = int(os.getenv('discord_bot_developer', '0'))
    SECRET_ADMIN_COMMAND: dict = {
        "deb_memory_usage" : os.getenv('admin_cmd_1'),
        "deb_bot_info" : os.getenv('admin_cmd_2'),
        "deb_switch" : os.getenv('admin_cmd_3'),
        "deb_command_stats" : os.getenv('admin_cmd_4'),
        "deb_user_stats" : os.getenv('admin_cmd_5'),
        "deb_reset_stats" : os.getenv('admin_cmd_6'),
    }
else:
    raise BotInitializationError("Failed loading secret.env file!!")

# 봇 명령어 timeout 설정 (초)
COMMAND_TIMEOUT: int = 30  # seconds


# configuration variables
# 메모리 정리 주기 (분)
MEMORY_CLEAR_INTERVAL: int = 60  # minutes
NEXON_API_REFRESH_INTERVAL: int = 15  # minutes
if BOT_TOKEN_RUN == 'dev':
    NEXON_API_LIMIT_PER_SEC: int = 5  # 개발 환경에서는 낮은 제한
    NEXON_API_TIME_SLEEP: float = 1.0 / NEXON_API_LIMIT_PER_SEC - 1
else:
    NEXON_API_LIMIT_PER_SEC: int = 500  # 운영 환경에서는 높은 제한
NEXON_API_TIME_SLEEP: float = 1.0 / NEXON_API_LIMIT_PER_SEC if not locals().get('NEXON_API_TIME_SLEEP') else NEXON_API_TIME_SLEEP

# Bot 시작 시간 기록
BOT_START_DT: datetime = datetime.now(timezone('Asia/Seoul'))
BOT_START_TIME_STR: str = BOT_START_DT.strftime('%Y-%m-%d %H:%M:%S')
BOT_VERSION: str = f"v20250928-{BOT_TOKEN_RUN}"


# 디버그 모드 설정
if BOT_TOKEN_RUN == 'dev':
    DEBUG_MODE: bool = True 
else:
    # 운영 환경에서는 디버그 모드 OFF
    # (디버그 모드가 켜져있으면, 봇 명령어 실행 시 로깅이 더 자세하게 기록됨)
    DEBUG_MODE: bool = False