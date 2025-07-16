import os
import sys

from dotenv import load_dotenv

from datetime import datetime, timedelta
from pytz import timezone
    
def kst_format_now() -> str:
    """Format datetime in KST."""
    kst = timezone('Asia/Seoul')
    return datetime.now(tz=kst).strftime('%Y-%m-%d %H:%M:%S')

# Token loading
try:
    # Load environment variables from .env file
    assert load_dotenv('token.env'), Exception("token.env file not found")
    assert os.getenv('bot_token'), Exception("bot_token not found in env file")
    BOT_TOKEN: str = os.getenv('bot_token')
except Exception as e:
    print(f"Failed loading bot token!!: {e}")
    sys.exit(1)