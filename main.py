import discord
import gc
from discord.ext import commands, tasks
from config import kst_format_now, get_memory_usage_mb
from config import BOT_TOKEN_PRD, BOT_TOKEN_DEV, MEMORY_CLEAR_INTERVAL
from service.common import logger

# 디스코드 메세지 관련 명령어
import service.msg_command as msg_command
# 디스코드 API 처리 관련 명령어
import service.api_command as api_command

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

# 디버그용 명령어
@bot.command(name="debug")
async def bot_debug(ctx: commands.Context, arg: str = None):
    await ctx.send(f"봇이 정상적으로 작동 중이에양! 현재 시간: {kst_format_now()}")
    if arg == "mem":
        mem_usage: float = get_memory_usage_mb()
        logger.debug(f"Current memory usage: {mem_usage:.2f} MB")
        await ctx.send(f"현재 메모리 사용량: {mem_usage:.2f} MB")

# 1시간 마다 메모리 정리
@tasks.loop(minutes=MEMORY_CLEAR_INTERVAL)
async def clear_memory():
    mem_usage : float = get_memory_usage_mb()
    logger.info(f"Memory clear")
    gc.collect()
    logger.info(f"Current memory usage: {mem_usage:.2f} MB")

# 봇 실행 + 메모리 정리 반복 작업 시작
@bot.event
async def on_ready():
    logger.info(f'Logged in as... {bot.user}!!')
    clear_memory.start()

# 명령어 등록 from service.msg_command
@bot.command(name="블링크빵")
async def run_msg_handle_blinkbang(ctx: commands.Context):
    await msg_command.msg_handle_blinkbang(ctx.message)

# 명령어 등록 from service.api_command
@bot.command(name="기본정보")
async def run_api_basic_info(ctx: commands.Context, character_name: str):
    await api_command.api_basic_info(ctx, character_name)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # 특수 명령어 실행 (from service.msg_command)
    if message.content.startswith('븜 따라해 '):
        await msg_command.msg_handle_repeat(message)
    if message.content.startswith('븜 이미지 '):
        await msg_command.msg_handle_image(message)

    # 봇 명령어 처리
    await bot.process_commands(message)

# 봇 실행!
bot.run(str(BOT_TOKEN_DEV))