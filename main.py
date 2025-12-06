import discord
from discord.ext import commands

# bot logging 추가
from bot_logger import logger, init_bot_stats

# bot 유틸리티 함수
from bot_helper import build_command_help, resolve_command, build_command_hint #도움말 예외처리
from bot_helper import auto_clear_memory, update_bot_presence # 메모리 정리, 봇 상태 갱신

# Kafka 초기화
from kafka.producer import init_kafka_producer, close_kafka_producer
from kafka.consumer import consume_kafka_logs

# 봇 설정값 불러오기
from config import BOT_TOKEN, BOT_DEVELOPER_ID, BOT_COMMAND_PREFIX
from config import SECRET_COMMANDS, SECRET_ADMIN_COMMAND
from config import KAFKA_ACTIVE, DB_USE
from typing import Literal

# Matplotlib 한글 폰트 설정
from utils.plot import set_up_matplotlib_korean
applied = set_up_matplotlib_korean("assets/font/NanumGothic.ttf")

# 디스코드 메세지 관련 명령어
import service.basic_command as basic_command

# 디스코드 API 처리 관련 명령어
import service.maplestory_command as map_command
import service.neoplednf_command as dnf_command
import service.weather_command as wth_command
import service.stock_command as stk_command
import data.hidden.hidden_command as hid_command

# 디스코드 디버그용 명령어
import service.debug_command as deb_command

# 명령어 실행중 발생하는 예외 처리
from exceptions.command_exceptions import InvalidCommandParameter

intents = discord.Intents.default()
intents.message_content = True
bot_command_prefix = BOT_COMMAND_PREFIX

bot = commands.Bot(command_prefix=bot_command_prefix, intents=intents, help_command=None)
admin_commands = SECRET_ADMIN_COMMAND

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
        if arg == admin_commands.get("deb_reset_stats"):
            await deb_command.deb_reset_stats(ctx)
        if arg is None:
            await ctx.send(f"{ctx.message.author.mention}님, 디버그 명령어 사용법: `븜 디버그 [명령어]` 입력 혹은 `븜 명령어 관리자` 참고")
    return

@bot.command(name="명령어통계", help="서버 내 명령어 사용 통계를 조회해양. 예: `븜 명령어통계` (DB가 연결되어 있어야 사용 가능)")
async def run_deb_command_stats(ctx: commands.Context):
    if DB_USE:
        await deb_command.deb_command_stats_v2(ctx)
        return
    else:
        await ctx.send(f"해당 기능은 데이터베이스와 연결되어 있어야 사용 가능해양!", reference=ctx.message)
        return
    
@bot.command(name="사용자통계", help="서버 내 사용자별 명령어 사용 통계를 조회해양. 예: `븜 사용자통계` (DB가 연결되어 있어야 사용 가능)")
async def run_deb_user_stats(ctx: commands.Context):
    if DB_USE:
        await deb_command.deb_user_stats_v2(ctx)
        return
    else:
        await ctx.send(f"해당 기능은 데이터베이스와 연결되어 있어야 사용 가능해양!", reference=ctx.message)
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


# 명령어 등록 from service.msg_command
@bot.command(name="블링크빵")
async def run_msg_handle_blinkbang(ctx: commands.Context):
    await basic_command.msg_handle_blinkbang(ctx)

@bot.command(name="따라해", usage="메세지", help="사용자가 보낸 메세지를 그대로 따라해양. 예: `븜 따라해 안녕!`")
async def run_msg_handle_repeat(ctx: commands.Context, *, repeat_text: str):
    await basic_command.msg_handle_repeat(ctx, repeat_text)

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
    await map_command.maple_xp_history_v2(ctx, character_name)

@bot.command(name="경험치v1", usage="캐릭터명", help="메이플스토리 캐릭터의 1주간 경험치 히스토리를 조회해양. (구버전) 예: `븜 경험치 마법사악`")
async def run_api_maple_xp_history_v1(ctx: commands.Context, character_name: str):
    await map_command.maple_xp_history(ctx, character_name)

@bot.command(name="코디", usage="캐릭터명", help="메이플스토리 캐릭터의 현재 코디 이미지를 조회해양. 예: `븜 코디 마법사악`")
async def run_api_maple_cash_equipment_info(ctx: commands.Context, character_name: str):
    await map_command.maple_cash_equipment_info(ctx, character_name)

@bot.command(name="컬렉션", usage="캐릭터명", help="메이플스토리 캐릭터의 코디 모음 이미지를 만들어줘양(최대 8개). 예: `븜 컬렉션 마법사악`")
async def run_api_maple_cordinate_history(ctx: commands.Context, character_name: str):
    await map_command.maple_cordinate_history(ctx, character_name)

# 던전앤파이터 명령어 등록 from service.neoplednf_command as dnf_command
@bot.command(name="던파정보", usage="서버명 캐릭터명", help="던전앤파이터 캐릭터의 기본 정보를 조회해양. 예: `븜 던파정보 카인 마법사악`")
async def run_api_dnf_characters(ctx: commands.Context, server_name: str, character_name: str):
    await dnf_command.api_dnf_characters(ctx, server_name, character_name)

@bot.command(name="주간던파", usage="서버명 캐릭터명", help="던전앤파이터 주간 던파 기록을 조회해양. 예: `븜 주간던파 카인 마법사악`")
async def run_api_timeline_weekly(ctx: commands.Context, server_name: str, character_name: str):
    await dnf_command.api_dnf_timeline_weekly(ctx, server_name, character_name)

@bot.command(name="던파장비", usage="서버명 캐릭터명", help="던전앤파이터 캐릭터의 장비 정보를 조회해양. 예: `븜 던파장비 카인 마법사악`")
async def run_api_dnf_equipment(ctx: commands.Context, server_name: str, character_name: str):
    await dnf_command.api_dnf_equipment(ctx, server_name, character_name)


# 날씨 명령어 등록 from service.weather_command as wth_command
@bot.command(name="날씨", usage="지역명", help="특정 지역의 날씨를 조회해양. 예: `븜 날씨 서울`")
async def run_api_weather(ctx: commands.Context, location: str):
    await wth_command.api_weather(ctx, location)

# 주식 명령어 등록 from service.stock_command as stk_command
@bot.command(name="미국주식", usage="티커(대문자)", help="미국 주식 시세를 티커를 통해 조회해양. 예: `븜 미국주식 AAPL`")
async def run_stk_us_price(ctx: commands.Context, ticker: str):
    await stk_command.stk_us_price(ctx, ticker)

@bot.command(name="미국차트", usage="티커(대문자) 기간(1주/1개월/3개월/1년/5년/전체)", help="미국 주식 차트를 티커와 기간을 통해 조회해양. 예: `븜 미국차트 AAPL 1년`")
async def run_stk_us_chart(ctx: commands.Context, ticker: str, period: Literal["1주", "1개월", "3개월", "1년", "5년", "전체"]):
    await stk_command.stk_us_chart(ctx, ticker, period)

@bot.command(name="한국주식", usage="종목명 또는 종목코드", help="한국 주식 시세를 종목명이나 종목코드를 통해 조회해양. 예: `븜 한국주식 삼성전자` 또는 `븜 한국주식 005930`")
async def run_stk_kr_price(ctx: commands.Context, stock: str):
    await stk_command.stk_kr_price(ctx, stock)

@bot.command(name="한국차트", usage="종목명 또는 종목코드 기간(1주/1개월/3개월/1년/5년/전체)", help="한국 주식 차트를 종목명이나 종목코드와 기간을 통해 조회해양. 예: `븜 한국차트 삼성전자 1년` 또는 `븜 한국차트 005930 1년`")
async def run_stk_kr_chart(ctx: commands.Context, stock: str, period: Literal["1주", "1개월", "3개월", "1년", "5년", "전체"]):
    await stk_command.stk_kr_chart(ctx, stock, period)

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


# 봇 실행 + 메모리 정리 반복 작업 시작
@bot.event
async def on_ready():
    logger.info(f"Initializing bot... {bot.user}")

    if KAFKA_ACTIVE and DB_USE:
        await init_kafka_producer()

        if not getattr(bot, "kafka_consumer_started", False):
            bot.loop.create_task(consume_kafka_logs())
            bot.kafka_consumer_started = True
            logger.info("Apache-Kafka Active: Kafka consumer task started.")

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="븜 명령어 | 메이플스토리")
    )
    
    # init_bot_stats()
    auto_clear_memory.start()
    update_bot_presence.start(bot)
    logger.info(f'Logged in as... {bot.user}!!')

    
@bot.event
async def on_close():
    logger.info("Bot is shutting down...")
    if KAFKA_ACTIVE:
        await close_kafka_producer()
    logger.info("Bot has been shut down.")


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