import time
import discord
import difflib
from discord.ext import commands

import asyncio
from config import COMMAND_TIMEOUT

from config import BOT_TOKEN, BOT_DEVELOPER_ID, SECRET_COMMANDS, SECRET_ADMIN_COMMAND
from bot_logger import logger

# Matplotlib 한글 폰트 설정
from utils.plot import set_up_matplotlib_korean
applied = set_up_matplotlib_korean("assets/font/NanumGothic.ttf")

# 디스코드 메세지 관련 명령어
import service.basic_command as basic_command

# 디스코드 API 처리 관련 명령어
import service.maplestory_command as map_command
import service.neoplednf_command as dnf_command
import service.weather_command as wth_command
import service.yfinance_command as yfi_command
import data.hidden.hidden_command as hid_command

# 디스코드 디버그용 명령어
import service.debug_command as deb_command
from service.debug_utils import deb_clear_memory

# 명령어 실행중 발생하는 예외 처리
from exceptions.command_exceptions import InvalidCommandParameter

intents = discord.Intents.default()
intents.message_content = True
bot_command_prefix = "븜 "

bot = commands.Bot(command_prefix=bot_command_prefix, intents=intents, help_command=None)
admin_commands = SECRET_ADMIN_COMMAND


def build_command_help(prefix: str, attempt: str, command: commands.Command) -> str:
    """단일 커맨드의 사용법 (help, usage) 문자열 생성

    Args:
        prefix (str): 명령어 접두사
        attempt (str): 사용자가 입력한 명령어
        command (commands.Command): 명령어 객체

    Returns:
        str: 명령어의 help 문자열
    """
    desc = command.help or "설명이 없어양"

    if command.usage:
        usage = f"`{prefix}{attempt} {command.usage}`"
    else:
        usage = f"`{prefix}{attempt}`"
    return (
        f"**{attempt} 명령어 사용법**\n"
        f"- 사용법: {usage}\n"
        f"- 설명: {desc}\n"
    )


def resolve_command(bot: commands.Bot, attempt: str):
    norm = attempt.strip()
    if not norm:
        return None, ""
    
    invoke = norm.split()[0]
    cmd = bot.get_command(invoke)
    return cmd, invoke


def build_command_hint(bot: commands.Bot, attempt: str) -> str:
    """없는 명령어 입력시 유사한 명령어를 찾아 힌트 문자열 생성

    Args:
        bot (commands.Bot): discord 봇 인스턴스
        attempt (str): 사용자가 입력한 명령어

    Returns:
        str: 유사한 명령어 힌트 문자열
    """
    all_names = []
    for c in bot.commands:
        all_names.append(c.name)
        all_names.extend(c.aliases)
    commands = difflib.get_close_matches(attempt, all_names, n=3, cutoff=0.6)
    return f"혹시 '{', '.join(commands)}' 명령어를 말하시는 거에양?" if commands else ""


# 디버그용 명령어 등록 from service.debug_command as deb_command
@bot.command(name="디버그", usage="명령어", help="봇의 디버그용 명령어입니다. 관리자 권한이 필요합니다. 예: `븜 디버그 [명령어]`")
async def bot_debug(ctx: commands.Context, arg: str = None):
    # 사용자 권한 검사
    author_info: discord.Member = ctx.message.author
    if not author_info.guild_permissions.administrator and author_info.id != BOT_DEVELOPER_ID:  # 특정 사용자 예외
        await ctx.send(f"{ctx.message.author.mention}님은 관리자 권한이 없어양! 이 명령어는 관리자만 사용할 수 있어양!")
    else:
        if arg == admin_commands.get("deb_memory_usage"):
            await deb_command.deb_memory_usage(ctx)
        if arg == admin_commands.get("deb_bot_info"):
            await deb_command.deb_bot_info(ctx, bot_name=bot.user.name)
        if arg == admin_commands.get("deb_switch"):
            await deb_command.deb_switch(ctx)
        if arg == admin_commands.get("deb_command_stats"):
            await deb_command.deb_command_stats(ctx)
        if arg == admin_commands.get("deb_user_stats"):
            await deb_command.deb_user_stats(ctx)
        if arg == admin_commands.get("deb_reset_stats"):
            await deb_command.deb_reset_stats(ctx)
        if arg is None:
            await ctx.send(f"{ctx.message.author.mention}님, 디버그 명령어 사용법: `븜 디버그 [명령어]` 입력 혹은 `븜 명령어 관리자` 참고")
    return

# 븜 help, 븜 도움말 -> 븜 명령어 리다이렉트
@bot.command(name="help")
async def run_deb_help_redirection(ctx: commands.Context, category: str = None):
    await deb_command.deb_help_redirection(ctx, category)

@bot.command(name="도움말")
async def run_deb_help_redirection(ctx: commands.Context, category: str = None):
    await deb_command.deb_help_redirection(ctx, category)

@bot.command(name="명령어")
async def run_deb_help(ctx: commands.Context, category: str = None):
    await deb_command.deb_help(ctx, category)

# 봇 실행 + 메모리 정리 반복 작업 시작
@bot.event
async def on_ready():
    logger.info(f'Logged in as... {bot.user}!!')
    deb_clear_memory.start()
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="븜 명령어")
    )

# 명령어 등록 from service.msg_command
@bot.command(name="블링크빵")
async def run_msg_handle_blinkbang(ctx: commands.Context):
    await basic_command.msg_handle_blinkbang(ctx)

@bot.command(name="따라해", usage="메세지", help="사용자가 보낸 메세지를 그대로 따라해양. 예: `븜 따라해 안녕!`")
async def run_msg_handle_repeat(ctx: commands.Context, *, text: str):
    await basic_command.msg_handle_repeat(ctx, text)

@bot.command(name="이미지", usage="검색어", help="이미지를 검색해양. 예: `븜 이미지 븜미`")
async def run_msg_handle_image(ctx: commands.Context, *, search_term: str):
    await basic_command.msg_handle_image(ctx, search_term)

# 메이플스토리 명령어 등록 from service.maplestory_command as map_command
@bot.command(name="기본정보", usage="캐릭터명", help="메이플스토리 캐릭터의 기본 정보를 조회해양. 예: `븜 기본정보 마법사악`")
async def run_api_basic_info(ctx: commands.Context, character_name: str):
    await map_command.maple_basic_info(ctx, character_name)

@bot.command(name="상세정보", usage="캐릭터명", help="메이플스토리 캐릭터의 상세 정보를 조회해양. 예: `븜 상세정보 마법사악`")
async def run_api_detail_info(ctx: commands.Context, character_name: str):
    await map_command.maple_detail_info(ctx, character_name)
    
@bot.command(name="피씨방")
async def run_api_pcbang_notice(ctx: commands.Context):
    await map_command.maple_pcbang_notice(ctx)

@bot.command(name="썬데이")
async def run_api_sunday_notice(ctx: commands.Context):
    await map_command.maple_sunday_notice(ctx)

@bot.command(name="어빌리티", usage="캐릭터명", help="메이플스토리 캐릭터의 어빌리티 정보를 조회해양. 예: `븜 어빌리티 마법사악`")
async def run_api_ability_info(ctx: commands.Context, character_name: str):
    await map_command.maple_ability_info(ctx, character_name)

@bot.command(name="운세", usage="캐릭터명", help="메이플스토리 캐릭터의 오늘 운세를 조회해양. 예: `븜 운세 마법사악`")
async def run_api_maple_fortune_today(ctx: commands.Context, character_name: str):
    await map_command.maple_fortune_today(ctx, character_name)

@bot.command(name="경험치", usage="캐릭터명", help="메이플스토리 캐릭터의 1주간 경험치 히스토리를 조회해양. 예: `븜 경험치 마법사악`")
async def run_api_maple_xp_history(ctx: commands.Context, character_name: str):
    await map_command.maple_xp_history(ctx, character_name)

# 던전앤파이터 명령어 등록 from service.neoplednf_command as dnf_command
@bot.command(name="던파정보", usage="서버명 캐릭터명", help="던전앤파이터 캐릭터의 기본 정보를 조회해양. 예: `븜 던파정보 카인 마법사악`")
async def run_api_dnf_characters(ctx: commands.Context, server_name: str, character_name: str):
    await dnf_command.api_dnf_characters(ctx, server_name, character_name)

@bot.command(name="주간던파", usage="서버명 캐릭터명", help="던전앤파이터 주간 던파 기록을 조회해양. 예: `븜 주간던파 카인 마법사악`")
async def run_api_timeline_weekly(ctx: commands.Context, server_name: str, character_name: str):
    await dnf_command.api_dnf_timeline_weekly(ctx, server_name, character_name)

# 날씨 명령어 등록 from service.weather_command as wth_command
@bot.command(name="날씨", usage="지역명", help="특정 지역의 날씨를 조회해양. 예: `븜 날씨 서울`")
async def run_api_weather(ctx: commands.Context, location: str):
    await wth_command.api_weather(ctx, location)

# 명령어 등록 from service.yfinance_command as yfi_command
@bot.command(name="미국주식", usage="티커(대문자)", help="미국 주식 시세를 티커를 통해 조회해양. 예: `븜 미국주식 AAPL`")
async def run_stk_us_stock_price(ctx: commands.Context, ticker: str):
    await yfi_command.stk_us_stock_price(ctx, ticker)

# 히든 명령어 등록 from data/hidden/hidden_command as hid_command
@bot.command(name=SECRET_COMMANDS[0])
async def run_hidden_command_1(ctx: commands.Context):
    await hid_command.hidden_command_1(ctx, text=SECRET_COMMANDS[0])

@bot.command(name=SECRET_COMMANDS[1])
async def run_hidden_command_2(ctx: commands.Context):
    await hid_command.hidden_command_2(ctx, text=SECRET_COMMANDS[1])

@bot.command(name=SECRET_COMMANDS[2])
async def run_hidden_command_3(ctx: commands.Context):
    await hid_command.hidden_command_3(ctx, text=SECRET_COMMANDS[2])

@bot.event
async def on_message(message: discord.Message):
    # 봇이 보낸 메시지에는 반응하지 않음
    if message.author.bot:
        return
    
    # 명령어 처리
    raw = message.content
    command_prefix = bot_command_prefix

    # "븜 <명령어>" 형식 확인
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if hasattr(ctx.command, 'on_error'):
        return
    
    prefix = bot_command_prefix

    # 없는 명령어 처리
    if isinstance(error, commands.CommandNotFound):
        raw = ctx.message.content
        attempt_command = raw[len(prefix):].split(" ", 1)[0] if raw.startswith(prefix) else raw
        hint = build_command_hint(bot, attempt_command)
        await ctx.send(f"'{attempt_command}' 명령어는 없어양! {hint}", reference=ctx.message)
        return

    # 인자누락 처리
    if isinstance(error, commands.MissingRequiredArgument):
        attempt_command = ctx.invoked_with or (ctx.command.name if ctx.command else "")
        cmd, invoke = resolve_command(bot, attempt_command)

        if cmd:
            help_msg = build_command_help(bot_command_prefix, invoke, cmd)
            await ctx.send(f"뒤에 인자가 부족해양!\n{help_msg}", reference=ctx.message)
        else:
            await ctx.send(f"'{attempt_command}' 명령어는 없어양! `븜 명령어`로 사용법을 확인해보세양!", reference=ctx.message)
        return
    
    # 공백만 인자 등 커스텀 예외
    if isinstance(error, commands.BadArgument):
        await ctx.send(f"인자를 잘못 입력 했어양! `븜 명령어`로 사용법을 확인해보세양!", reference=ctx.message)
        return

# 봇 실행!
bot.run(str(BOT_TOKEN))