import asyncio
import logging
import time
import traceback

from discord.ext import commands
from typing import Optional, Dict
from dataclasses import dataclass, field

from logging import Logger
from functools import wraps
import inspect

import config as config 
from utils.time import KstFormatter
from exceptions.base import BotWarning

from kafka.helper import build_and_send


# stats class 호출 (log_command 데코레이터 내에서 사용)
@dataclass
class DiscordBotStats:
    command_timeout : float = config.COMMAND_TIMEOUT*2
    command_stats   : Dict[str, dict] = field(default_factory=dict)
    user_stats      : Dict[int, dict] = field(default_factory=dict)

    slowest_command_elapsed : float = 0.0 # 가장 느린 명령어 초기값
    slowest_command_name    : Optional[str] = None
    fastest_command_elapsed : float = float("inf")
    fastest_command_name    : Optional[str] = None

    def reset(self) -> None:
        """discord bot 사용통계 초기화 (봇 가동마다 실행)"""
        self.command_stats.clear()
        self.user_stats.clear()
        self.slowest_command_elapsed = 0.0
        self.slowest_command_name = None
        self.fastest_command_elapsed = float("inf")
        self.fastest_command_name = None

    def update_command_stats(self, func_name: str, elapsed_time: float, func_name_alt: Optional[str] = None) -> None:
        """command_stats에서 slowest/fastest 명령어 갱신"""
        if func_name not in self.command_stats:
            # 최초 호출하는 명령어
            self.command_stats[func_name] = {
                "alt_name" : func_name_alt if func_name_alt else func_name,
                "count"    : 1,
                "fast"     : elapsed_time,
                "slow"     : elapsed_time
            }
        else:
            # 이미 호출된 적 있는 명령어
            self.command_stats[func_name]["count"] += 1
            if elapsed_time > self.command_stats[func_name]["slow"]:
                self.command_stats[func_name]["slow"] = elapsed_time
            if elapsed_time < self.command_stats[func_name]["fast"]:
                self.command_stats[func_name]["fast"] = elapsed_time

        # slowest/fastest 명령어 갱신
        if elapsed_time > self.slowest_command_elapsed:
            self.slowest_command_elapsed = elapsed_time
            self.slowest_command_name = func_name_alt if func_name_alt else func_name

        if elapsed_time < self.fastest_command_elapsed:
            self.fastest_command_elapsed = elapsed_time
            self.fastest_command_name = func_name_alt if func_name_alt else func_name

    def update_user_stats(self, user_id: int, func_name: str, func_name_alt: Optional[str] = None) -> None:
        """user_stats에서 사용자별 명령어 사용 통계 갱신"""
        if user_id is None:
            return False
        
        if user_id not in self.user_stats:
            # 명령어를 처음 사용하는 사용자
            run_func = func_name_alt if func_name_alt else func_name
            self.user_stats[user_id] = {
                "total_count"   : 1,
                "last_command"  : run_func,
                "command_stats" : {run_func: 1}
            }

        else:
            # 기존 명령어 사용자
            user_stat = self.user_stats[user_id]
            run_func = func_name_alt if func_name_alt else func_name
            user_stat["total_count"] += 1
            user_stat["last_command"] = run_func
            # 사용자별 명령어 사용 횟수 갱신
            individual_command_stats: Dict[str, int] = user_stat.get("command_stats", {})
            individual_command_stats[run_func] = individual_command_stats.get(run_func, 0) + 1

    def record_command_usage(self, user_id: int, func_name: str, elapsed_time: float, func_name_alt: Optional[str] = None) -> None:
        """명령어 사용 통계 기록 (command_stats, user_stats 갱신)"""
        self.update_command_stats(func_name, elapsed_time, func_name_alt)
        self.update_user_stats(user_id, func_name, func_name_alt)

# 민감 키 목록 (마스킹 처리용)
SENSITIVE_KEYS = {"token", "password", "passwd", "secret", "key", "apikey", "authorization", "cookie", "session", "bearer"}

# Logger configuration
bot_stats: Optional[DiscordBotStats] = None
logger: Logger = logging.getLogger('discord_bot_logger')
logger.setLevel(logging.INFO)
formatter = KstFormatter('[%(asctime)s] %(levelname)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


def init_bot_stats() -> DiscordBotStats:
    """봇 가동시 통계 클래스 호출 및 초기화"""
    global bot_stats
    bot_stats = DiscordBotStats()
    bot_stats.reset()
    return bot_stats


def get_discord_user_id(ctx: commands.Context) -> Optional[int]:
    if _is_discord_context(ctx):
        author_id = getattr(getattr(ctx, "author", None), "id", None) or getattr(getattr(ctx, "user", None), "id", None)
        return author_id
    else:
        return None


def _short_str(s: str, max_len: int = 80) -> str:
    s = repr(s)
    return s if len(s) <= max_len else s[:max_len-3] + "..."


def _is_discord_context(x) -> bool:
    try:
        m: str = x.__class__.__module__
        n: str = x.__class__.__name__
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


def _format_bound_args(func, args, kwargs) -> str:
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


def log_command(func: callable = None, *, alt_func_name: str = None, stats: bool = False):
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
            func_name = inner_func.__name__
            start_time = time.time()
            try:
                await inner_func(*args, **kwargs)
                elapsed_time: float = time.time() - start_time
                ctx = kwargs.get("ctx") or (args[0] if args else None)

                # 인자 정보 포맷팅
                try:
                    arg_info: str = _format_bound_args(inner_func, args, kwargs)
                except Exception as e:
                    arg_info: str = "<arg-format-error>"

                # 함수 이름과 인자 정보 로깅
                if config.DEBUG_MODE:
                    info_log = f"{func_name} success (Elapsed time: {elapsed_time:.3f} seconds)\n[{arg_info}]"
                else:
                    info_log = f"{func_name} success (Elapsed time: {elapsed_time:.3f} seconds)"

                if stats and bot_stats is not None:
                    # 명령어 / 사용자 통계 기록
                    if ctx and isinstance(ctx, commands.Context):
                        user_id = get_discord_user_id(ctx)
                        bot_stats.record_command_usage(user_id, func_name, elapsed_time, alt_func_name)
                
                # 정보 로깅
                logger.info(info_log)

                # Kafka로 로그 전송 (성공)
                if config.KAFKA_ACTIVE and stats:
                    asyncio.create_task(
                        build_and_send(
                            ctx=ctx,
                            func_name=func_name,
                            func_name_alt=alt_func_name,
                            elapsed_time=elapsed_time,
                            status="success",
                            args_info={"args": arg_info}
                        )
                    )

                # 정상 종료
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

                # Kafka로 로그 전송 (경고)
                if config.KAFKA_ACTIVE and stats:
                    asyncio.create_task(
                        build_and_send(
                            ctx=ctx,
                            func_name=func_name,
                            func_name_alt=alt_func_name,
                            elapsed_time=elapsed_time,
                            status="warning",
                            args_info={"args": arg_info},
                            warning=w,
                            traceback_msg=traceback.format_exc() if config.DEBUG_MODE else None,
                        )
                    )

                # 정상 종료
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

                # Kafka로 로그 전송 (오류)
                if config.KAFKA_ACTIVE and stats:
                    asyncio.create_task(
                        build_and_send(
                            ctx=ctx,
                            func_name=func_name,
                            func_name_alt=alt_func_name,
                            elapsed_time=elapsed_time,
                            status="error",
                            args_info={"args": arg_info},
                            error=e,
                            traceback_msg=traceback.format_exc() if config.DEBUG_MODE else None,
                        )
                    )

                # 예외 재발생
                raise
        return wrapper

    if func is not None and callable(func):
        return decorator(func)
    
    return decorator


def with_timeout(timeout_seconds: int = config.COMMAND_TIMEOUT):
    """비동기 함수에 타임아웃을 적용하는 데코레이터

    Args:
        timeout_seconds (int): 타임아웃 시간(초)

    Returns:
        callable: 타임아웃이 적용된 비동기 함수
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(ctx: commands.Context, *args, **kwargs):
            try:
                return await asyncio.wait_for(func(ctx, *args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ 명령어 최대 시간({timeout_seconds}초) 초과로 취소되었어양")
        return wrapper
    return decorator