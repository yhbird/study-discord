import inspect
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

# Base Exception Class
class BotBaseException(Exception):
    """Bot 기본 예외 클래스"""
    def __init__(self, message: str = "알수 없는 오류가 발생 했어양"):
        super().__init__(message)
        self.message = message

class BotConfigFailed(BotBaseException):
    """봇 설정 실패"""
    def __init__(self, message: str = "봇 설정을 불러오는 데 실패했어양"):
        super().__init__(message)
        self.message = message

class BotCommandError(BotBaseException):
    """명령어 실행 중 오류 발생"""
    def __init__(self, message: str = "명령어 실행 중 오류가 발생 했어양"):
        super().__init__(message)
        self.message = message

class BotCommandInvalidError(BotBaseException):
    """명령어 유효성 검사 실패"""
    def __init__(self, message: str = "명령어를 잘못 사용했어양"):
        super().__init__(message)
        self.message = message

class BotCommandResponseError(BotBaseException):
    """명령어 응답 처리 중 오류 발생"""
    def __init__(self, message: str = "명령어 응답 처리 중 오류가 발생 했어양"):
        super().__init__(message)
        self.message = message

class BotWarning(Exception):
    """작업을 중단하지 않고 경고 메시지를 표시할 때 사용"""
    pass

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
    
def preprocess_int_with_korean(input_val: str) -> str:
    """숫자로된 문자열을 한글 단위로 변환

    Args:
        input_val (str): 숫자로된 문자열, 예: "209558569"

    Returns:
        str: 한글 단위로 변환된 문자열, 예: "2억 9558만 8569"
    """
    if isinstance(input_val, str):
        input_val: str = input_val.replace(',', '').replace(' ', '')
    if int(input_val) >= 100_000_000:
        str_100m: str = f"{input_val[:-8]}억" # 억
        str_10k: str = f"{input_val[-8:-4]}만" # 만
        str_floor: str = f"{input_val[-4:]}" # 그 이하
        if str_10k == "0000만":
            str_10k = ""
        if str_floor == "0000":
            str_floor = ""
        return f"{str_100m} {str_10k} {str_floor}".strip()
    elif int(input_val) >= 10_000:
        str_10k: str = f"{input_val[:-4]}만"
        str_floor: str = f"{input_val[-4:]}" # 그 이하
        if str_floor == "0000":
            str_floor = ""
        return f"{str_10k} {str_floor}".strip()
    else:
        return input_val

SENSITIVE_KEYS = {"token", "password", "passwd", "secret", "key", "apikey", "authorization", "cookie", "session", "bearer"}

def _short_str(s: str, max_len: int = 80) -> str:
    s = repr(s)
    return s if len(s) <= max_len else s[:max_len-3] + "..."

def _is_discord_context(x) -> bool:
    try:
        m = x.__class__.__module__
        n = x.__class__.__name__
        return m.startswith("discord") and "Context" in n
    except Exception:
        return False

def _format_arg(x, max_len: int = 80):
    # 원시 타입
    if isinstance(x, (int, float, bool, type(None))):
        return repr(x)
    if isinstance(x, str):
        return _short_str(x, max_len)

    # Discord Context 요약
    if _is_discord_context(x):
        author_id = getattr(getattr(x, "author", None), "id", None) or getattr(getattr(x, "user", None), "id", None)
        guild_id = getattr(getattr(x, "guild", None), "id", None)
        chan_id  = getattr(getattr(x, "channel", None), "id", None)
        return f"<Context guild={guild_id} channel={chan_id} user={author_id}>"

    # dict: 앞의 몇 개 키만
    if isinstance(x, dict):
        items = list(x.items())
        head = ", ".join(f"{k}={_format_arg(v, 40)}" for k, v in items[:5])
        more = f", …+{len(items)-5}" if len(items) > 5 else ""
        return f"<dict {head}{more}>"

    # 시퀀스: 길이와 샘플
    if isinstance(x, (list, tuple, set)):
        seq = list(x)
        head = ", ".join(_format_arg(v, 40) for v in seq[:3])
        more = f", …+{len(seq)-3}" if len(seq) > 3 else ""
        return f"<{type(x).__name__} len={len(seq)} [{head}{more}]>"

    # bytes
    if isinstance(x, (bytes, bytearray, memoryview)):
        return f"<bytes len={len(x)}>"

    # 그 외
    return f"<{type(x).__name__}>"

def _format_bound_args(func, args, kwargs):
    sig = inspect.signature(func)
    bound = sig.bind_partial(*args, **kwargs)
    parts = []
    for k, v in bound.arguments.items():
        # 민감 키 마스킹
        if any(s in k.lower() for s in SENSITIVE_KEYS):
            parts.append(f"{k}=<redacted>")
        else:
            parts.append(f"{k}={_format_arg(v)}")
    return ", ".join(parts)

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
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed_time: float = time.time() - start_time

            # 인자 정보 포맷팅
            try:
                arg_info: str = _format_bound_args(func, args, kwargs)
            except Exception:
                arg_info: str = "<arg-format-error>"

            # 함수 이름과 인자 정보 로깅
            if config.DEBUG_MODE:
                info_log = f"{func_name} success (Elapsed time: {elapsed_time:.3f} seconds)\n[{arg_info}]"
            else:
                info_log = f"{func_name} success (Elapsed time: {elapsed_time:.3f} seconds)"
            logger.info(info_log)
            return result
        
        # 예외 처리 - 경고 메시지 로깅
        except BotWarning as w:
            elapsed_time: float = time.time() - start_time
            # 인자 정보 포맷팅
            try:
                arg_info: str = _format_bound_args(func, args, kwargs)
            except Exception:
                arg_info: str = "<arg-format-error>"

            if config.DEBUG_MODE:
                warn_log = f"{func_name} warning ({str(w)})\n(Elapsed time: {elapsed_time:.3f} seconds)\n{arg_info}"
            else:
                warn_log = f"{func_name} warning ({str(w)}) (Elapsed time: {elapsed_time:.3f} seconds)"
            logger.warning(f"{warn_log}")
            return
        
        # 예외 처리 - 예외 메시지 로깅
        except Exception as e:
            elapsed_time: float = time.time() - start_time
            # 인자 정보 포맷팅
            try:
                arg_info: str = _format_bound_args(func, args, kwargs)
            except Exception:
                arg_info: str = "<arg-format-error>"
                
            if config.DEBUG_MODE:
                traceback_msg: str = traceback.format_exc()
                errr_log = f"{func_name} error ({str(e)})\n(Elapsed time: {elapsed_time:.3f} seconds)\n{arg_info}\n{traceback_msg}"
            else:
                errr_log = f"{func_name} error ({str(e)}) (Elapsed time: {elapsed_time:.3f} seconds)"
            logger.error(f"{errr_log}")
            raise
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