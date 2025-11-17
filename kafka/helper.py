from typing import Any, Dict, Optional, Literal

from discord.ext import commands

from kafka.producer import send_log_to_kafka

async def build_and_send(
    *,
    ctx: Optional[commands.Context],
    func_name: str,
    func_name_alt: Optional[str] = None,
    elapsed_time: float,
    status: Literal["success", "error", "warning"],
    args_info: Dict[str, Any],
    warning: Optional[BaseException] = None,
    error: Optional[BaseException] = None,
    traceback_msg: Optional[str] = None,
) -> None:
    """log_command 데코레이터를 통해 수집된 로그를 Kafka로 전송합니다."""
    guild_id: Optional[int] = getattr(ctx.guild, "id", None) if ctx else 0
    guild_name: Optional[str] = str(ctx.guild) if ctx and ctx.guild else None
    channel_id: Optional[int] = getattr(ctx.channel, "id", None) if ctx else 0
    channel_name: Optional[str] = str(ctx.channel) if ctx and ctx.channel else None
    user_id: Optional[int] = getattr(ctx.author, "id", None) if ctx else 0
    user_name: Optional[str] = str(ctx.author) if ctx and ctx.author else None
    payload: Dict[str, Any] = {
        "guild_id": guild_id,
        "guild_name": guild_name,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "user_id": user_id,
        "user_name": user_name,
        "command_name": func_name,
        "command_name_alt": func_name_alt or func_name,
        "args_json": args_info,
        "result" : status,
        "elapsed_time_ms": int(elapsed_time * 1000),
        "error_code": None,
        "error_type": type(error).__name__ if error else None,
        "error_message": str(error) if error else None,
        "traceback": traceback_msg,
        "etc_1": {},
    }

    if warning is not None:
        payload.update(
            {
                "error_type": type(warning).__name__,
                "error_message": str(warning),
                "traceback" : traceback_msg,
            }
        )

    if error is not None:
        payload.update(
            {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback" : traceback_msg,
            }
        )

    await send_log_to_kafka(payload)