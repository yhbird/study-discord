import time
import uuid
import functools
import traceback

from kafka.producer import producer
from config import BOT_VERSION

def kafka_log(command_name: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            start = time.time()
            event_id = str(uuid.uuid4())
            try:
                result = await func(ctx, *args, **kwargs)
                latency_ms = int((time.time() - start) * 1000)
                await producer.send(
                    topic="bot.events.command.v1",
                    key=str(getattr(ctx, "author", "unknown")),
                    value={
                        "event_id": event_id,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "guild_id": getattr(getattr(ctx, "guild", None), "id", None),
                        "channel_id": getattr(getattr(ctx, "channel", None), "id", None),
                        "user_id": getattr(getattr(ctx, "author", None), "id", None),
                        "command_name": command_name,
                        "args": repr(args)[:200],
                        "kwargs": {k: repr(v)[:200] for k, v in kwargs.items()},
                        "result_status": "success",
                        "latency_ms": latency_ms,
                        "bot_version": BOT_VERSION,
                    }
                )
                return result

            except Exception as e:
                latency_ms = int((time.time() - start) * 1000)
                trace_back = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                short_msg = str(e)[:1000]
                short_trace_back = trace_back[:40000]
                await producer.send(
                    topic="bot.events.error.v1",
                    key=str(getattr(ctx, "author", "unknown")),
                    value={
                        "event_id": event_id,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "guild_id": getattr(getattr(ctx, "guild", None), "id", None),
                        "channel_id": getattr(getattr(ctx, "channel", None), "id", None),
                        "user_id": getattr(getattr(ctx, "author", None), "id", None),
                        "command_name": command_name,
                        "args": repr(args)[:200],
                        "kwargs": {k: repr(v)[:200] for k, v in kwargs.items()},
                        "result_status": "error",
                        "error_message": str(e)[:200],
                        "error_trace": traceback.format_exc()[:1000],
                        "latency_ms": latency_ms,
                        "bot_version": BOT_VERSION,
                    }
                )
                raise
        return wrapper
    return decorator
