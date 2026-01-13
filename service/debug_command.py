"""

디스코드 봇 디버그용 명령어 모듈

성능 테스트 및 디버깅을 위한 명령어를 사용

"""
import discord
from discord.ext import commands
from datetime import datetime, timedelta

from typing import Dict, Optional

from service.debug_utils import *
from utils.text import rank_to_emoji
from exceptions.command_exceptions import CommandFailure

from bot_logger import logger, log_command, with_timeout
from utils.time import kst_format_now, kst_format_now
import config as config
import bot_logger as bl


# 전역 변수 설정
command_timeout: int = config.COMMAND_TIMEOUT
bot_developer_id: int = config.BOT_DEVELOPER_ID
bot_version: str = config.BOT_VERSION


# 메모리 사용량 조회
@with_timeout(command_timeout)
@log_command(stats=False, alt_func_name="봇 메모리 사용량 조회")
async def deb_memory_usage(ctx: commands.Context):
    # 채팅창에 명령어가 노출되지 않도록 삭제
    await ctx.message.delete()

    mem_usage: float = get_memory_usage_mb()
    logger.debug(f"Current memory usage: {mem_usage:.2f} MB")
    await ctx.send(f"현재 메모리 사용량: {mem_usage:.2f} MB")
    return


 # 봇 정보 조회
@with_timeout(command_timeout)
@log_command(stats=False, alt_func_name="봇 정보")
async def deb_bot_info(ctx: commands.Context, bot_name: str = None):
    # 채팅창에 명령어가 노출되지 않도록 삭제
    await ctx.message.delete()

    if bot_name is None:
        bot_name = "Unknown Bot"
    bot_info: str = (
        f"**봇 이름:** {bot_name}\n"
        f"**봇 시작 시간:** {config.BOT_START_DT.strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}"
    )
    now_dt: datetime = kst_format_now()
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
    return


# 디버그 모드 ON/OFF
@with_timeout(command_timeout)
@log_command(stats=False, alt_func_name="븜 디버그 모드 전환")
async def deb_switch(ctx: commands.Context):
    # 채팅창에 명령어가 노출되지 않도록 삭제
    await ctx.message.delete()

    # 디버그 모드 토글
    config.DEBUG_MODE = not config.DEBUG_MODE
    debug_status = "ON" if config.DEBUG_MODE else "OFF"
    await ctx.send(f"디버그 모드가 {debug_status}으로 설정되었어양!")
    return


# "븜 명령어" 리다이렉트
@with_timeout(command_timeout)
@log_command(stats=False, alt_func_name="븜 명령어 리다이렉트")
async def deb_help_redirection(ctx: commands.Context, category: str = None):
    """사용자에게 도움말을 리다이렉트하는 기능

    Args:
        ctx(commands.Context): 도움말 요청이 포함된 디스코드 메세지
    """
    # 봇 메시지 무시
    if ctx.message.author.bot:
        return

    else:
        # 리다이렉트 명령어 확인
        await deb_help(ctx, category=category)

        # 리다이렉트 명령어 안내
        mention = ctx.message.author.mention
        if category:
            await ctx.message.channel.send(f"{mention} '븜 명령어 {category}'를 입력하세양!")
            return
        else:
            await ctx.message.channel.send(f"{mention} '븜 명령어'를 입력하세양!")
            return


# 도움말 명령어
@with_timeout(command_timeout)
@log_command(alt_func_name="븜 명령어")
async def deb_help(ctx: commands.Context, category: str = None):
    """봇의 사용법을 안내하는 기능 (카테고리별)

    Args:
        ctx (commands.Context): /help 커맨드 입력
        category (str, optional): 도움말 카테고리. Defaults to None.

    Raises:
        Exception: 메세지 삭제 권한이 없거나, 메세지 삭제 실패시 발생

    Returns:
        None: 사용법 안내 메시지를 채널에 전송 (None: 카테고리 목록 표시)
    """

    if ctx.message.author.bot:
        return

    # 카테고리 분기 처리
    if category is None:
        # 카테고리 없음 -> 카테고리 목록 표시
        description_prefix: str = (
            "도움말 카테고리 목록이에양. 원하는 카테고리를 선택해양!\n"
            "(예시: '븜 명령어 메이플')\n"
        )
    else:
        if category not in ["메이플", "던파", "기타", "관리자"]:
            # 잘못된 카테고리 -> 카테고리 목록 표시
            description_prefix: str = (
                "지원하지 않는 카테고리에양. 아래 목록에서 선택해양!\n"
                "(예시: '븜 명령어 메이플')\n"
            )
            category = None
        elif category == "관리자":
            description_prefix: str = (
                "'관리자' 카테고리는 관리자 전용이에양!\n"
                "서버 관리자면 DM으로 명령어 목록을 보내드릴게양!\n"
            )
        else:
            description_prefix: str = f"'{category}' 카테고리 도움말이에양!\n"

    description_text: str = (
        "봇 개발자: 크로아 마법사악 ([github.com](https://github.com/yhbird))\n"
        "다양한 븜끼 봇 사용법을 알려드릴게양!\n"
        f"{description_prefix}"
    )
    
    if category is None:
        # 카테고리 없음 -> 카테고리 목록 표시
        embed = discord.Embed(
            title=f"븜끼봇 명령어 카테고리 목록 (븜 명령어 <카테고리>)",
            description=description_text,
            color=discord.Color.blue()
        )
        embed.add_field(
            name="메이플",
            value="메이플스토리 관련 명령어 모음이에양!\n",
            inline=False
        )
        embed.add_field(
            name="던파",
            value="던전앤파이터 관련 명령어 모음이에양!\n",
            inline=False
        )
        embed.add_field(
            name="기타",
            value="기타 여러가지 명령어 모음이에양! (주식, 날씨 등)\n",
            inline=False
        )
        embed.add_field(
            name="관리자",
            value="관리자 전용 명령어 모음이에양! (서버 관리자만 사용 가능)\n",
            inline=False
        )
    elif category == "메이플":
        # 메이플 카테고리 도움말
        embed = discord.Embed(
            title=f"븜끼봇 명령어 - 메이플스토리",
            description=f"{description_text}**[넥슨 Open API 기반]**",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="븜 기본정보 <캐릭터 이름>",
            value="메이플스토리 캐릭터의 기본 정보를 조회합니다.\n ",
            inline=False
        )
        embed.add_field(
            name="븜 상세정보 <캐릭터 이름>",
            value="메이플스토리 캐릭터의 상세 정보를 조회합니다.\n*기본 정보보다 더 많은 정보를 제공해양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 어빌리티 <캐릭터 이름>",
            value="메이플스토리 캐릭터의 어빌리티 정보를 조회합니다.\n*사용중인 어빌리티와 프리셋 정보를 제공해양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 운세 <캐릭터 이름>",
            value="오늘의 메이플스토리 캐릭터 운세를 조회합니다.\n*재미로만 봐주세양!!*\n*참고) 5성:5%, 4성:20%, 3성:30%, 2성:40%, 1성:5% 확률로 나와양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 경험치 <캐릭터 이름>",
            value="메이플스토리 캐릭터의 경험치 그래프를 조회합니다.\n*최근 7일간 경험치 변화를 그래프로 보여줘양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 경험치v1 <캐릭터 이름>",
            value="메이플스토리 캐릭터의 경험치 그래프를 조회합니다. (구버전)\n*최근 7일간 경험치 변화를 그래프로 보여줘양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 코디 <캐릭터 이름>",
            value="메이플스토리 캐릭터의 코디(외형) 정보를 조회합니다.\n*캐릭터가 착용중인 코디 아이템을 보여줘양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 컬렉션 <캐릭터 이름>",
            value="메이플스토리 캐릭터의 컬렉션 정보를 조회합니다.\n*최대 8개의 컬렉션을 보여줘양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 피씨방",
            value="최근 피씨방 공지사항을 조회합니다.\n*이미지가 길쭉해서 좀 오래걸려양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 썬데이",
            value="썬데이 메이플 공지사항을 조회합니다.\n*매주 금요일 오전에 업데이트돼양*\n ",
            inline=False
        )
    elif category == "던파":
        # 던파 카테고리 도움말
        embed = discord.Embed(
            title=f"븜끼봇 명령어 - 던전앤파이터",
            description=f"{description_text}**[네오플 Open API 기반]**",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="븜 던파정보 <서버이름> <캐릭터이름>",
            value="던전앤파이터 캐릭터의 정보를 조회합니다.\n*한글로 서버 이름과 캐릭터 이름을 입력해양*\n*예시) 븜 던파정보 카인 마법사악*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 주간던파 <서버이름> <캐릭터이름>",
            value="던전앤파이터 캐릭터의 주간 던파를 요약합니다.\n*레이드 클리어 기록, 태초획득 기록까지 븜미가 친절히 알려줘양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 던파장비 <서버이름> <캐릭터이름>",
            value="던전앤파이터 캐릭터의 장비 정보를 조회합니다.\n*장비 아이템명, 등급, 강화수치, 세트포인트 등을 보여줘양*\n ",
            inline=False
        )
    elif category == "기타":
        # 기타 카테고리 도움말
        embed = discord.Embed(
            title=f"븜끼봇 명령어 - 기타 (날씨, 주식 등)",
            description=description_text,
            color=discord.Color.blue()
        )
        embed.add_field(
            name="븜 이미지 <검색어>",
            value="이미지를 검색해서 최대 10개의 이미지를 보여줍니다.\n(사용하는 검색엔진: https://duckduckgo.com/)\n***참고로, 야한건... 안돼양!!!***\n ",
            inline=False
        )
        embed.add_field(
            name="븜 따라해 <메세지>",
            value="입력한 메세지를 그대로 따라합니다. \n*마크다운을 지원해양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 날씨 <지역명 혹은 주소> (v3 개발중)",
            value="**[카카오 / 기상청 API]**\n 현재 날씨와 예보정보를 조회합니다. \n*주소를 입력하면 더 정확하게 나와양\n대신 누군가 찾아올수도...*\n",
            inline=False
        )
        embed.add_field(
            name="븜 블링크빵",
            value="랜덤한 자연수 1~100 랜덤 추출합니다. \n*결과는 날아간 거리로 보여줘양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 미국주식 <티커>",
            value="미국 주식의 현재 가격을 조회합니다.\n*참고) 티커: BRK.B -> BRK-B* ",
            inline=False
        )
        embed.add_field(
            name="븜 미국차트 <티커> <기간>",
            value="미국 주식의 가격 차트를 조회합니다.\n기간 옵션: 1주, 1개월, 3개월, 6개월, 1년, 5년, 최대\n*참고) 티커: BRK.B -> BRK-B* ",
            inline=False
        )
        embed.add_field(
            name="븜 한국주식 <종목명 또는 종목코드>",
            value="한국 주식의 현재 가격을 조회합니다.\n*종목명이나 종목코드를 입력해양* ",
            inline=False
        )
        embed.add_field(
            name="븜 한국차트 <종목명 또는 종목코드> <기간>",
            value="한국 주식의 가격 차트를 조회합니다.\n기간 옵션: 1주, 1개월, 3개월, 6개월, 1년, 5년, 최대\n*종목명이나 종목코드를 입력해양* ",
            inline=False
        )
        embed.add_field(
            name="븜 명령어통계",
            value="서버 내에서 가장 오래/빨리 실행된 명령어와 순위를 집계합니다.\n*DB에 연결되어 있어야해양!*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 사용자통계",
            value="서버 내에서 가장 많이 명령어를 호출한 사용자 통계를 조회합니다.\n*DB에 연결되어 있어야해양!*\n ",
            inline=False
        )
    elif category == "관리자":
        is_admin: bool = False
        # 명령어 요청자 권한 확인
        if ctx.message.author.guild_permissions.administrator or ctx.message.author.id == bot_developer_id:
            is_admin: bool = True
            # 관리자 권한 있음 -> DM으로 명령어 전송
            embed = discord.Embed(
                title="관리자 전용 명령어",
                description="DM으로 명령어 목록을 보내드릴게양!",
                color=discord.Color.green()
            )
            dm_embed = discord.Embed(
                title=f"븜끼봇 명령어 - 관리자 전용 (븜 디버그)",
                description="서버 관리자를 위한 관리자 전용 명령어 목록이에양!\n",
                color=discord.Color.blue()
            )
            dm_embed.add_field(
                name="븜 디버그 info",
                value="봇의 현재 상태 및 가동 시간 표시\n",
                inline=False
            )
            dm_embed.add_field(
                name="븜 디버그 mem",
                value="봇의 현재 메모리 사용량 표시\n",
                inline=False
            )
            dm_embed.add_field(
                name="븜 디버그 switch",
                value="봇 디버그 모드 전환 (에러로그가 상세하게 표시됩니다. 기본: OFF)\n",
                inline=False
            )
            dm_embed.add_field(
                name="븜 디버그 stats",
                value="상위 10개 가장 많이 실행된 명령어와 수행시간 조회\n",
                inline=False
            )
            dm_embed.add_field(
                name="븜 디버그 userstats",
                value="상위 3명 가장 많이 명령어를 호출한 사용자의 통계 조회\n**사용자 멘션 포함 주의!**\n",
                inline=False
            )
            dm_embed.add_field(
                name="븜 디버그 resetstats",
                value="봇의 사용자 및 명령어 통계 초기화\n *봇 재시작시 자동 초기화, 메모리 사용량이 높으면 사용*\n",
                inline=False
            )
        else:
            # 관리자 권한 없음 -> 권한 없음 안내
            embed = discord.Embed(
                title="관리자 전용 명령어",
                description="서버 관리자가 아니면 사용할 수 없어양!",
                color=discord.Color.red()
            )

    # 공통 푸터
    embed_footer:str = (
        "------\n"
        f"봇 이름: {ctx.guild.me.name}\n"
        f"봇 버전: {bot_version}\n"
        f"소스코드: https://github.com/yhbird/study-discord\n"
        "------\n"
        "Data based on NEXON Open API\n"
        "Powered by Neople Open API\n"
        "주식 데이터 Yahoo Finance 제공\n"
    )
    embed.set_footer(text=embed_footer)

    if category == "관리자":
        # 요청한 채널에 embed 전송
        await ctx.send(embed=embed)

        # 관리자 권한 있으면 DM 전송 시도
        if is_admin:
            dm_embed.set_footer(text=embed_footer)
            await ctx.message.author.send(embed=dm_embed)
    else:
        # 메세지 전송
        await ctx.send(embed=embed)
    return


# 서버(guild)내에서 가장 오래/빨리 실행된 명령어 조회
@with_timeout(command_timeout)
@log_command(stats=False, alt_func_name="븜 명령어 통계 조회")
async def deb_command_stats_v2(ctx: commands.Context) -> None:
    """서버(guild) 내 가장 오래/빨리 실행된 명령어와 순위를 집계합니다.

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트

    Raises:
        CommandFailure: DB_CONNECTION_ERROR(DB 접속 실패)시 발생
        CommandFailure: DB_DATA_NOT_FOUND(데이터 없음)시 발생

    Note:
        명령어 통계는 명령어가 성공적으로 실행된 경우에만 집계됩니다.
        통계 데이터는 PostgreSQL 데이터베이스에서 조회합니다.
        데이터 없음 오류 발생시 성공처리로 간주하고 안내 메시지 전송
    """
    # 채팅창에 명령어가 노출되지 않도록 삭제
    await ctx.message.delete()

    # 서버(guild) id 조회
    guild_id: int = getattr(getattr(ctx, "guild", None), "id", None)
    if guild_id is None:
        await ctx.send("서버 정보를 불러오는데 실패했어양...")
        raise CommandFailure("Failed to get guild ID from context.")
    
    # 명령어 통계 데이터 호출
    try:
        command_stats = get_command_stats(guild_id)

    except DB_CONNECTION_ERROR as e:
        await ctx.send("데이터베이스 연결에 실패했어양")
        raise CommandFailure("Database connection error.") from e
    
    except DB_DATA_NOT_FOUND as e:
        await ctx.send("현재 서버에서 명령어 사용 기록이 없어양...")
        return
    
    # 명령어 통계 출력
    else:
        embed = discord.Embed(title="븜끼봇 서버내 명령어 통계")
        slowest_command: Dict[str, str | float | int] = command_stats.get("slowest_command", {})
        fastest_command: Dict[str, str | float | int] = command_stats.get("fastest_command", {})
        
        if slowest_command:
            slowest_command_nam : str   = slowest_command.get("command_name") or "몰라양"
            slowest_command_avg : float = slowest_command.get("average_elapsed")/1000 or 0.000
            slowest_command_slo : float = slowest_command.get("slowest_elapsed")/1000 or 0.000
            slowest_command_fas : float = slowest_command.get("fastest_elapsed")/1000 or 0.000
            slowest_command_cnt : int   = slowest_command.get("call_count", 0) or 0
            embed.add_field(
                name  = "가장 오래 걸린 명령어",
                value = (
                    f"**{slowest_command_nam}**\n"
                    f"- 평균 실행 시간: {slowest_command_avg:.3f}초\n"
                    f"- 최장 실행 시간: {slowest_command_slo:.3f}초\n"
                    f"- 최단 실행 시간: {slowest_command_fas:.3f}초\n"
                    f"- 명령어 실행 횟수: {slowest_command_cnt}회\n"
                )
            )

        if fastest_command:
            fastest_command_nam : str   = fastest_command.get("command_name") or "몰라양"
            fastest_command_avg : float = fastest_command.get("average_elapsed")/1000 or 0.000
            fastest_command_slo : float = fastest_command.get("slowest_elapsed")/1000 or 0.000
            fastest_command_fas : float = fastest_command.get("fastest_elapsed")/1000 or 0.000
            fastest_command_cnt : int   = fastest_command.get("call_count", 0) or 0
            embed.add_field(
                name  = "가장 빨리 끝난 명령어",
                value = (
                    f"**{fastest_command_nam}**\n"
                    f"- 평균 실행 시간: {fastest_command_avg:.3f}초\n"
                    f"- 최장 실행 시간: {fastest_command_slo:.3f}초\n"
                    f"- 최단 실행 시간: {fastest_command_fas:.3f}초\n"
                    f"- 명령어 실행 횟수: {fastest_command_cnt}회\n"
                )
            )

        lines = []
        top10_commands: List[Dict[str, str | int | float]] = command_stats.get("top10_commands", [])
        if top10_commands:
            for i, command in enumerate(top10_commands, start = 1):
                command_rank    : str   = f"{i}위:" if i > 3 else rank_to_emoji(i)
                command_name    : str   = command["command_name"] or "몰라양"
                command_count   : int   = command["call_count"] or 0
                average_elapsed : float = command["average_elapsed"]/1000 or 0.000
                lines.append(
                    f"**{command_rank} {command_name}** - "
                    f"{command_count}회 호출, "
                    f"평균 {average_elapsed:.3f}초 소요"
                )

            if lines:
                embed.add_field(
                    name  = "명령어별 실행 횟수 및 시간 (Top 10)",
                    value = "\n".join(lines),
                    inline=False
                )

        server_name: str = getattr(getattr(ctx, "guild", None), "name", "몰라양")
        footer_test = (
            f"봇 버전: {bot_version} | 봇 이름: {ctx.guild.me.name}\n"
            f"서버 이름: {server_name}\n"
            f"집계 기준: 전체 기간\n"
            f"명령어를 성공적으로 호출한 경우에만 통계에 반영"
        )
        embed.set_footer(text=footer_test)
        await ctx.send(content="서버내 명령어 통계에양!!", embed=embed)
        return


@with_timeout(command_timeout)
@log_command(stats=False, alt_func_name="봇 사용자 통계 조회")
async def deb_user_stats_v2(ctx: commands.Context) -> None:
    # 채팅창에 명령어가 노출되지 않도록 삭제
    await ctx.message.delete()

    # 서버(guild) id 조회
    guild_id: int = getattr(getattr(ctx, "guild", None), "id", None)
    if guild_id is None:
        await ctx.send("서버 정보를 불러오는데 실패했어양...")
        raise CommandFailure("Failed to get guild ID from context.")
    
    # 사용자 통계 데이터 호출
    try:
        user_stats = get_user_stats(guild_id)

    except DB_CONNECTION_ERROR as e:
        await ctx.send("데이터베이스 연결에 실패했어양")
        raise CommandFailure("Database connection error.") from e
    
    except DB_DATA_NOT_FOUND as e:
        await ctx.send("현재 서버에서 사용자 명령어 사용 기록이 없어양...")
        return

    # 사용자 통계 출력
    else:
        embed = discord.Embed(title="븜끼봇 서버내 사용자 명령어 통계")
        
        lines = []
        top10_users: List[Dict[str, str | int]] = user_stats.get("user_stats", [])
        if top10_users:
            for i, user in enumerate(top10_users, start = 1):
                user_rank      : str = f"{i}위." if i > 3 else rank_to_emoji(i)
                user_name      : str = user["user_name"] or "몰라양"
                user_count     : int = user["usage_count"] or 0
                last_command   : str = user["last_command"] or "몰라양"
                last_command_t : str = user["last_command_time"].split(".")[0] or "몰라양"
                most_command   : str = user["most_command_name"] or "몰라양"
                most_command_c : int = user["most_command_count"] or 0
                lines.append(
                    f"**{user_rank} {user_name}** - {user_count}회 호출\n"
                    f"- 최근 사용한 명령어: {last_command} @{last_command_t}\n"
                    f"- 많이 사용한 명령어: {most_command} ({most_command_c}회)\n"
                )

            if lines:
                embed.add_field(
                    name  = "사용자별 명령어 호출 통계 (Top 5)",
                    value = "\n".join(lines),
                    inline=False
                )
        else:
            await ctx.send("현재 서버에서 명령어를 사용한 사람이 너무 적어양...")
            return

        server_name: str = getattr(getattr(ctx, "guild", None), "name", "몰라양")
        footer_test = (
            f"------\n"
            f"봇 버전: {bot_version} | 봇 이름: {ctx.guild.me.name}\n"
            f"서버 이름: {server_name}\n"
            f"집계 기준: 전체 기간\n"
            f"명령어를 성공적으로 호출한 경우에만 통계에 반영"
        )
        embed.set_footer(text=footer_test)
        await ctx.send(content="서버내 사용자 명령어 통계에양!!", embed=embed)
        return


# 통계 초기화 (메모리 사용량 감소 목적)
@with_timeout(config.COMMAND_TIMEOUT)
async def deb_reset_stats(ctx: commands.Context) -> None:
    # 채팅창에 명령어가 노출되지 않도록 삭제
    await ctx.message.delete()

    # 명령어 통계 초기화
    bl.COMMAND_STATS = {}
    bl.USER_STATS = {}
    bl.SLOWEST_COMMAND_NAME = None
    bl.SLOWEST_COMMAND_ELAPSED = 0.01
    bl.FASTEST_COMMAND_NAME = None
    bl.FASTEST_COMMAND_ELAPSED = 60.0

    logger.info("Command statistics have been reset.")
    await ctx.send("명령어 통계가 초기화되었어양!")
    return