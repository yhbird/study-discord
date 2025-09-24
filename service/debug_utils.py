from discord.ext import tasks

import gc
import os
import psutil

from config import MEMORY_CLEAR_INTERVAL
from bot_logger import logger

# Debug configuration
# 현재 사용중인 메모리 사용량을 MB 단위로 반환 -> 디버그용
def get_memory_usage_mb() -> float:
    """현재 프로세스의 메모리 사용량을 MB 단위로 반환

    Returns:
        float: 현재 프로세스의 메모리 사용량 (MB)
    """
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / 1024**2
    return mem


# 1시간 마다 메모리 정리
@tasks.loop(minutes=MEMORY_CLEAR_INTERVAL)
async def deb_clear_memory():
    mem_usage : float = get_memory_usage_mb()
    logger.info(f"Memory clear")
    gc.collect()
    logger.info(f"Current memory usage: {mem_usage:.2f} MB")

