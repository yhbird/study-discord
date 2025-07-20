import logging
from logging import Logger
from functools import wraps

from datetime import datetime, timedelta
from pytz import timezone

class kst_formatter(logging.Formatter):
    """Custom formatter to format datetime in KST."""
    def format_time(self, record, dtformat=None):
        kst = timezone('Asia/Seoul')
        dt = datetime.fromtimestamp(record.created, tz=kst)
        if dtformat:
            return dt.strftime(dtformat)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')
    
# Logger configuration
logger: Logger = logging.getLogger('discord_bot_logger')
logger.setLevel(logging.INFO)
formatter = kst_formatter('[%(asctime)s] %(levelname)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

def log_command(func):
    """Decorator to log command execution."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            logger.info(f"{func.__name__} success")
            return result
        except Warning as w:
            logger.warning(f"{func.__name__} warning ({str(w)})")
        except Exception as e:
            logger.error(f"{func.__name__} error ({str(e)})")
    return wrapper