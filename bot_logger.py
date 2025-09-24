import logging
import time
import traceback

from logging import Logger
from functools import wraps
import inspect

import config as config 
from utils.time import KstFormatter
from exceptions.base import BotWarning

# global variables
SENSITIVE_KEYS = {"token", "password", "passwd", "secret", "key", "apikey", "authorization", "cookie", "session", "bearer"}
SLOWEST_COMMAND_ELAPSED : float = 0.0 # 가장 느린 명령어 초기값
SLOWEST_COMMAND_NAME : str = ""
FASTEST_COMMAND_ELAPSED : float = 30.0 # 가장 빠른 명령어 초기값
FASTEST_COMMAND_NAME : str = ""
COMMAND_STATS: dict = {} # 명령어별 실행 횟수 및 총 소요 시간 기록
USER_STATS: dict = {} # 사용자별 명령어 사용 횟수 기록

# Logger configuration
logger: Logger = logging.getLogger('discord_bot_logger')
logger.setLevel(logging.INFO)
formatter = KstFormatter('[%(asctime)s] %(levelname)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


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


def _format_arg(x, max_len: int = 80, stats: bool = True):
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

        if author_id and author_id not in USER_STATS and stats:
            USER_STATS[author_id] = {'count': 0}
        if author_id and author_id in USER_STATS and stats:
            USER_STATS[author_id]['count'] += 1

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


def _format_bound_args(func, args, kwargs, stats_flag: bool = True) -> str:
    sig = inspect.signature(func)
    bound = sig.bind_partial(*args, **kwargs)
    parts = []
    for k, v in bound.arguments.items():
        # 민감 키 마스킹
        if any(s in k.lower() for s in SENSITIVE_KEYS):
            parts.append(f"{k}=<redacted>")
        else:
            parts.append(f"{k}={_format_arg(v, stats=stats_flag)}")
    return ", ".join(parts)


def log_command(func: callable = None, *, alt_func_name: str = None, stats: bool = True):
    """Docker 컨테이너에 실행한 봇 명령어를 기록하고, 소요시간 및 예외를 로깅

    Args:
        func (callable, optional): 로깅할 비동기 함수. Defaults to None.
        alt_func_name (str, optional): 함수 이름 대신 사용할 대체 이름. (통계 표시 활용)
        stats (bool, optional): 명령어 통계 기록 여부. Defaults to True.

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
    def decorator(inner_func):
        @wraps(inner_func)
        async def wrapper(*args, **kwargs):
            global SLOWEST_COMMAND_ELAPSED, SLOWEST_COMMAND_NAME
            global FASTEST_COMMAND_ELAPSED, FASTEST_COMMAND_NAME
            global COMMAND_STATS
            func_name = inner_func.__name__
            start_time = time.time()
            try:
                await inner_func(*args, **kwargs)
                elapsed_time: float = time.time() - start_time

                # 인자 정보 포맷팅
                try:
                    arg_info: str = _format_bound_args(inner_func, args, kwargs, stats_flag=stats)
                except Exception as e:
                    arg_info: str = "<arg-format-error>"

                # 함수 이름과 인자 정보 로깅
                if config.DEBUG_MODE:
                    info_log = f"{func_name} success (Elapsed time: {elapsed_time:.3f} seconds)\n[{arg_info}]"
                else:
                    info_log = f"{func_name} success (Elapsed time: {elapsed_time:.3f} seconds)"

                # 명령어 통계 업데이트
                if func_name not in COMMAND_STATS and stats:
                    COMMAND_STATS[func_name] = {'alt_name': alt_func_name, 'count': 0, 'fast': 30.0, 'slow': 0.0}
                if func_name in COMMAND_STATS and stats:
                    COMMAND_STATS[func_name]['count'] += 1
                    if elapsed_time > COMMAND_STATS[func_name]['slow']:
                        COMMAND_STATS[func_name]['slow'] = elapsed_time
                    if elapsed_time < COMMAND_STATS[func_name]['fast']:
                        COMMAND_STATS[func_name]['fast'] = elapsed_time

                if stats:
                    if elapsed_time > SLOWEST_COMMAND_ELAPSED:
                        SLOWEST_COMMAND_ELAPSED = elapsed_time
                        SLOWEST_COMMAND_NAME = alt_func_name or func_name

                    if elapsed_time < FASTEST_COMMAND_ELAPSED:
                        FASTEST_COMMAND_ELAPSED = elapsed_time
                        FASTEST_COMMAND_NAME = alt_func_name or func_name

                logger.info(info_log)
                return
            
            # 예외 처리 - 경고 메시지 로깅
            except BotWarning as w:
                elapsed_time: float = time.time() - start_time
                # 인자 정보 포맷팅
                try:
                    arg_info: str = _format_bound_args(inner_func, args, kwargs)
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
                    arg_info: str = _format_bound_args(inner_func, args, kwargs)
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

    if func is not None and callable(func):
        return decorator(func)
    
    return decorator