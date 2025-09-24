import os
import sys
import psutil

from dotenv import load_dotenv

from datetime import datetime
from pytz import timezone

import matplotlib
from matplotlib import font_manager
from pathlib import Path

from utils.time import kst_format_now
from exceptions.base import BotConfigFailed

# Discord Bot Token loading
try:
    # Load environment variables from .env file
    assert load_dotenv('./env/token.env'), BotConfigFailed("token.env file not found")
    assert os.getenv('bot_token_dev'), BotConfigFailed("bot_token not found in env file")
    BOT_TOKEN_RUN: str = os.getenv('PYTHON_RUN_ENV', 'dev')
    BOT_TOKEN = os.getenv(f'bot_token_{BOT_TOKEN_RUN}', None)
# Discord 봇 토큰을 제대로 불러오지 못하면 실행 불가
except BotConfigFailed as e:
    print(f"Failed loading bot token!!: {e}")
    sys.exit(1)

# Nexon Open API Key loading
try:
    assert load_dotenv('./env/nexon.env'), BotConfigFailed("nexon.env file not found")
    assert os.getenv('NEXON_API_TOKEN_LIVE'), BotConfigFailed("NEXON_API_TOKEN_LIVE not found in env file")
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
    print(f"Failed loading Nexon API key!!: {e}")
    sys.exit(1)

# weather API Key loading
try:
    assert load_dotenv('./env/weather.env'), BotConfigFailed("weather.env file not found")
    assert os.getenv('kko_token_api'), BotConfigFailed("kko_token_api not found in env file")
    assert os.getenv('wth_data_api'), BotConfigFailed("wth_data_api not found in env file")
    KKO_LOCAL_API_KEY: str = os.getenv('kko_token_api', None)
    KKO_API_HOME: str = os.getenv('kko_api_url', None)
    WTH_DATA_API_KEY: str = os.getenv('wth_data_api', None)
    WTH_API_HOME: str = os.getenv('wth_data_url', None)
# weather API 키를 제대로 불러오지 못하면 실행 불가
except BotConfigFailed as e:
    print(f"Failed loading weather API key!!: {e}")
    sys.exit(1)

# 금지 및 히든명령어 loading
if load_dotenv('./env/ban.env'):
    BAN_CMD_1 = os.getenv('ban_cmd_1', '')
    BAN_CMD_2 = os.getenv('ban_cmd_2', '')
    BAN_CMD_3 = os.getenv('ban_cmd_3', '')
    BAN_COMMANDS = [BAN_CMD_1, BAN_CMD_2, BAN_CMD_3]

# 봇 명령어 timeout 설정 (초)
COMMAND_TIMEOUT: int = 30  # seconds


# configuration variables
# 메모리 정리 주기 (분)
MEMORY_CLEAR_INTERVAL: int = 60  # minutes
NEXON_API_REFRESH_INTERVAL: int = 15  # minutes

# Bot 시작 시간 기록
BOT_START_TIME_STR: str = kst_format_now()
BOT_START_DT: datetime = datetime.strptime(BOT_START_TIME_STR, '%Y-%m-%d %H:%M:%S')
BOT_VERSION: str = f"v20250924-{BOT_TOKEN_RUN}"
BOT_DEVELOPER_ID: int = int(os.getenv('bot_developer_id', '0'))

# matplotlib 한글 폰트 설정
def set_up_matploylib_korean(font_path: str = "assets/font/NanumGothic.ttf"):
    """matplotlib에서 한글 폰트를 설정하는 함수

    Args:
        font_path (str, optional): 한글 폰트 파일 경로. Defaults to "assets/font/NanumGothic.ttf".
    """
    os.environ.setdefault("MPLCONFIGDIR", "./tmp/matplotlib")
    font_path = Path(font_path).resolve()

    if not Path(font_path).is_file():
        print(f"Font file not found: {font_path}")
        sys.exit(1)

    # 런타임 등록
    font_manager.fontManager.addfont(str(font_path))
    prop = font_manager.FontProperties(fname=str(font_path))
    family = prop.get_name()

    # 전역 설정
    matplotlib.rcParams['font.family'] = family
    matplotlib.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

    try:
        import matplotlib.pyplot as plt
    except Exception:
        matplotlib.use('Agg')

    return family


# 디버그 모드 설정
if BOT_TOKEN_RUN == 'dev':
    DEBUG_MODE: bool = True 
else:
    # 운영 환경에서는 디버그 모드 OFF
    # (디버그 모드가 켜져있으면, 봇 명령어 실행 시 로깅이 더 자세하게 기록됨)
    DEBUG_MODE: bool = False