import discord
import gc
from discord.ext import commands, tasks

from config import BOT_TOKEN, MEMORY_CLEAR_INTERVAL
from service.common import logger

# 디스코드 메세지 관련 명령어
import service.msg_command as msg_command
# 디스코드 API 처리 관련 명령어
import service.api_command as api_command
# 디스코드 주식 관련 명령어
import service.stk_command as stk_command
# 디스코드 디버그용 명령어
import service.deb_command as deb_command

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents, help_command=None)
# 디버그용 명령어
@bot.command(name="debug")
async def bot_debug(ctx: commands.Context, arg: str = None):
    if arg == "mem":
        await deb_command.deb_memory_usage(ctx)
    if arg == "info":
        await deb_command.deb_bot_info(ctx, bot_name=bot.user.name)
    if arg == "switch":
        await deb_command.deb_switch(ctx)

# 봇 실행 + 메모리 정리 반복 작업 시작
@bot.event
async def on_ready():
    logger.info(f'Logged in as... {bot.user}!!')
    deb_command.deb_clear_memory.start()

# 명령어 등록 from service.msg_command
@bot.command(name="블링크빵")
async def run_msg_handle_blinkbang(ctx: commands.Context):
    await msg_command.msg_handle_blinkbang(ctx.message)

@bot.command(name="help")
async def run_msg_handle_help(ctx: commands.Context):
    await msg_command.msg_handle_help(ctx.message)
    
# 명령어 등록 from service.api_command
@bot.command(name="기본정보")
async def run_api_basic_info(ctx: commands.Context, character_name: str):
    await api_command.api_basic_info(ctx, character_name)

@bot.command(name="피시방")
async def run_api_pcbang_notice(ctx: commands.Context):
    await api_command.api_pcbang_notice(ctx)

@bot.command(name="선데이")
async def run_api_sunday_notice(ctx: commands.Context):
    await api_command.api_sunday_notice(ctx)

# 명령어 등록 from service.stk_command
@bot.command(name="미국주식")
async def run_stk_us_stock(ctx: commands.Context, ticker: str):
    await stk_command.stk_us_stock_price(ctx, ticker)

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
bot.run(str(BOT_TOKEN))