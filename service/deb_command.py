"""

디스코드 봇 디버그용 명령어 모듈

성능 테스트 및 디버깅을 위한 명령어를 사용

"""
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from service.common import logger, log_command
import gc
import config

# 1시간 마다 메모리 정리
@tasks.loop(minutes=config.MEMORY_CLEAR_INTERVAL)
async def deb_clear_memory():
    mem_usage : float = config.get_memory_usage_mb()
    logger.info(f"Memory clear")
    gc.collect()
    logger.info(f"Current memory usage: {mem_usage:.2f} MB")

# 메모리 사용량 조회
@log_command
async def deb_memory_usage(ctx: commands.Context):
    mem_usage: float = config.get_memory_usage_mb()
    logger.debug(f"Current memory usage: {mem_usage:.2f} MB")
    await ctx.send(f"현재 메모리 사용량: {mem_usage:.2f} MB")

 # 봇 정보 조회
@log_command
async def deb_bot_info(ctx: commands.Context, bot_name: str = None):
    if bot_name is None:
        bot_name = "Unknown Bot"
    bot_info: str = (
        f"**봇 이름:** {bot_name}\n"
        f"**봇 시작 시간:** {config.BOT_START_DT.strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}"
    )
    now_dt: datetime = datetime.strptime(config.kst_format_now(), '%Y-%m-%d %H:%M:%S')
    uptime: timedelta = now_dt - config.BOT_START_DT
    # uptime의 일, 시간, 분, 초 계산
    up_d: int = uptime.days
    up_h: int = uptime.seconds // 3600
    up_m: int = (uptime.seconds % 3600) // 60
    up_s: int = uptime.seconds % 60
    if up_d > 0:
        debug_msg = f"bot uptime: {up_d}일 {up_h}시간 {up_m}분 {up_s}초"
        send_msg = f"**봇 가동 시간:** {up_d}일 {up_h}시간 {up_m}분 {up_s}초"
    elif up_h > 0:
        debug_msg = f"bot uptime: {up_h}시간 {up_m}분 {up_s}초"
        send_msg = f"**봇 가동 시간:** {up_h}시간 {up_m}분 {up_s}초"
    elif up_m > 0:
        debug_msg = f"bot uptime: {up_m}분 {up_s}초"
        send_msg = f"**봇 가동 시간:** {up_m}분 {up_s}초"
    else:
        debug_msg = f"bot uptime: {up_s}초"
        send_msg = f"**봇 가동 시간:** {up_s}초"
    logger.debug(debug_msg)
    info_msg = f"{bot_info}\n{send_msg}"
    await ctx.send(info_msg)

# 디버그 모드 ON/OFF
@log_command
async def deb_switch(ctx: commands.Context):
    config.DEBUG_MODE = not config.DEBUG_MODE
    debug_status = "ON" if config.DEBUG_MODE else "OFF"
    await ctx.send(f"디버그 모드가 {debug_status}으로 설정되었어양!")
