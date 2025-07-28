import logging
from logging import Logger
from functools import wraps

from datetime import datetime
from dateutil import parser
from pytz import timezone

import time
import traceback
import config 

class kst_formatter(logging.Formatter):
    """logging.Formatter이 KST 포맷을 사용하도록 커스텀

    Args:
        logging (Formatter): 기본 logging.Formatter 클래스
        dtformat (str): 날짜 포맷 문자열, 기본값은 '%Y-%md-%d %H:%M:%S'

    Returns:
        str: KST로 포맷된 날짜 문자열
    """
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

def safe_float(input_val, digits: int = 2) -> str:
    try:
        return f"{float(input_val):.{digits}f}"
    except (ValueError, TypeError):
        return "몰라양"
    
def safe_percent(input_val, digits: int = 2) -> str:
    try:
        return f"{float(input_val) * 100:.{digits}f} %"
    except (ValueError, TypeError):
        return "몰라양"

def log_command(func):
    """Docker 컨테이너에 실행한 봇 명령어를 기록하고, 소요시간 및 예외를 로깅

    Args:
        func (Callable): api_command.py 및 msg_command.py에서 사용되는 함수
        debug_mode (bool): 디버그 모드 여부, 기본값은 False
          - 

    Returns:
        logger (Logger): 로깅된 함수의 결과를 반환

    Example:
        ```python
        @log_command
        async def my_command(ctx):
            # command logic here
            return "Command executed successfully"
        ```
          - [2025-07-21 17:30:00] INFO : my_command success (Elapsed time: 0.123 seconds)
    Raises:
        Warning: 경고 메시지를 로깅합니다.
          - [2025-07-21 17:30:00] WARNING : my_command warning (Warning message)

        Exception: 예외 메시지를 로깅합니다.
          - [2025-07-21 17:30:00] ERROR : my_command error (Exception message)
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        args_text = '. '.join(
            repr(args) if isinstance(arg, (str, int, float)) else f"<{type(arg).__name__}>"
            for arg in args
        )
        kwargs_text = '. '.join(
            f"{k}={v!r}" for k, v in kwargs.items()
        )
        arg_info = f"[args: {args_text}" + (f", kwargs: {kwargs_text}" if kwargs else "") + "]"
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            # 함수 소요 시간 계산
            elapsed_time: float = time.time() - start_time

            # 함수 이름과 인자 정보 로깅
            if config.DEBUG_MODE:
                info_log = f"{func_name} success (Elapsed time: {elapsed_time:.3f} seconds)\n{arg_info}"
            else:
                info_log = f"{func_name} success (Elapsed time: {elapsed_time:.3f} seconds)"
            logger.info(info_log)
            return result
        
        # 예외 처리 - 경고 메시지 로깅
        except Warning as w:
            elapsed_time: float = time.time() - start_time
            if config.DEBUG_MODE:
                warn_log = f"{func_name} warning ({str(w)})\n(Elapsed time: {elapsed_time:.3f} seconds)\n{arg_info}"
            else:
                warn_log = f"{func_name} warning ({str(w)}) (Elapsed time: {elapsed_time:.3f} seconds)"
            logger.warning(f"{warn_log}")
        
        # 예외 처리 - 예외 메시지 로깅
        except Exception as e:
            elapsed_time: float = time.time() - start_time
            if config.DEBUG_MODE:
                traceback_msg: str = traceback.format_exc()
                errr_log = f"{func_name} error ({str(e)})\n(Elapsed time: {elapsed_time:.3f} seconds)\n{arg_info}\n{traceback_msg}"
            else:
                errr_log = f"{func_name} error ({str(e)}) (Elapsed time: {elapsed_time:.3f} seconds)"
            logger.error(f"{errr_log}")
    return wrapper

def parse_iso_string(iso_string: str) -> str:
    """국제기준(ISO) 날짜 문자열을 KST로 변환

    Args:
        date_str (str): 변환할 날짜 문자열

    Returns:
        str: KST로 변환된 날짜 문자열

    Example:
        ```python
        date_str = "2025-07-21T17:30+09:00"
        kst_date = date_to_kst(date_str)
        print(kst_date)  # "2025-07-21 17:30:00"
        ```"
    """
    dt = parser.isoparse(iso_string)
    kst = timezone('Asia/Seoul')
    return_string = f"{dt.year}년 {dt.month}월 {dt.day}일 {dt.hour}:{dt.minute:02d} (KST)"
    return return_string