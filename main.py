import discord
import gc
from discord.ext import commands

from config import BOT_TOKEN, BOT_DEVELOPER_ID
from service.common import logger

# Matplotlib 한글 폰트 설정
from config import set_up_matploylib_korean
applied = set_up_matploylib_korean("assets/font/NanumGothic.ttf")

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

bot = commands.Bot(command_prefix='븜 ', intents=intents, help_command=None)
# 디버그용 명령어
@bot.command(name="디버그")
async def bot_debug(ctx: commands.Context, arg: str = None):
    # 사용자 권한 검사
    author_info: discord.Member = ctx.message.author
    if not author_info.guild_permissions.administrator and author_info.id != BOT_DEVELOPER_ID:  # 특정 사용자 예외
        await ctx.send(f"{ctx.message.author.mention}님은 관리자 권한이 없어양! 이 명령어는 관리자만 사용할 수 있어양!")
        return
    else:
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
    await msg_command.msg_handle_blinkbang(ctx)

@bot.command(name="따라해")
async def run_msg_handle_repeat(ctx: commands.Context, *, text: str):
    await msg_command.msg_handle_repeat(ctx, text)

@bot.command(name="이미지")
async def run_msg_handle_image(ctx: commands.Context, *, search_term: str):
    await msg_command.msg_handle_image(ctx, search_term)

@bot.command(name="명령어")
async def run_msg_handle_help(ctx: commands.Context, category: str = None):
    await msg_command.msg_handle_help_v2(ctx, category)

# 명령어 등록 from service.api_command
@bot.command(name="기본정보")
async def run_api_basic_info(ctx: commands.Context, character_name: str):
    await api_command.api_basic_info(ctx, character_name)

@bot.command(name="상세정보")
async def run_api_detail_info(ctx: commands.Context, character_name: str):
    await api_command.api_detail_info(ctx, character_name)
    
@bot.command(name="피씨방")
async def run_api_pcbang_notice(ctx: commands.Context):
    await api_command.api_pcbang_notice(ctx)

@bot.command(name="썬데이")
async def run_api_sunday_notice(ctx: commands.Context):
    await api_command.api_sunday_notice(ctx)

@bot.command(name="어빌리티")
async def run_api_ability_info(ctx: commands.Context, character_name: str):
    await api_command.api_ability_info(ctx, character_name)

@bot.command(name="운세")
async def run_api_maple_fortune_today(ctx: commands.Context, character_name: str):
    await api_command.api_maple_fortune_today(ctx, character_name)

@bot.command(name="경험치")
async def run_api_maple_xp_history(ctx: commands.Context, character_name: str):
    await api_command.api_maple_xp_history(ctx, character_name)

@bot.command(name="날씨")
async def run_api_weather(ctx: commands.Context, location: str):
    await api_command.api_weather(ctx, location)

@bot.command(name="던파정보")
async def run_api_dnf_characters(ctx: commands.Context, server_name: str, character_name: str):
    await api_command.api_dnf_characters(ctx, server_name, character_name)

@bot.command(name="주간던파")
async def run_api_timeline_weekly(ctx: commands.Context, server_name: str, character_name: str):
    await api_command.api_dnf_timeline_weekly(ctx, server_name, character_name)

# 명령어 등록 from service.stk_command
@bot.command(name="미국주식")
async def run_stk_us_stock_price(ctx: commands.Context, ticker: str):
    await stk_command.stk_us_stock_price(ctx, ticker)

# 븜 help, 븜 도움말 -> 븜 명령어 리다이렉트
@bot.command(name="help")
async def run_msg_handle_help_redirection(ctx: commands.Context, category: str = None):
    await msg_command.msg_handle_help_redirection(ctx, category)

@bot.command(name="도움말")
async def run_msg_handle_help_redirection(ctx: commands.Context, category: str = None):
    await msg_command.msg_handle_help_redirection(ctx, category)

@bot.event
async def on_message(message: discord.Message):
    # 봇 명령어 처리
    await bot.process_commands(message)
    

# 봇 실행!
bot.run(str(BOT_TOKEN))