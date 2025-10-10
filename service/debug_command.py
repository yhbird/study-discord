"""

디스코드 봇 디버그용 명령어 모듈

성능 테스트 및 디버깅을 위한 명령어를 사용

"""
import discord
from discord.ext import commands
from datetime import datetime, timedelta

from service.debug_utils import *

from bot_logger import logger, log_command, with_timeout
from utils.time import kst_format_now, kst_format_now
import config as config
import bot_logger as bl

# 메모리 사용량 조회
@with_timeout(config.COMMAND_TIMEOUT)
@log_command(stats=False, alt_func_name="봇 메모리 사용량 조회")
async def deb_memory_usage(ctx: commands.Context):
    # 채팅창에 명령어가 노출되지 않도록 삭제
    await ctx.message.delete()

    mem_usage: float = get_memory_usage_mb()
    logger.debug(f"Current memory usage: {mem_usage:.2f} MB")
    await ctx.send(f"현재 메모리 사용량: {mem_usage:.2f} MB")
    return


 # 봇 정보 조회
@with_timeout(config.COMMAND_TIMEOUT)
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
@with_timeout(config.COMMAND_TIMEOUT)
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
@with_timeout(config.COMMAND_TIMEOUT)
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
@with_timeout(config.COMMAND_TIMEOUT)
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
            name="븜 코디 <캐릭터 이름> (개발중)",
            value="메이플스토리 캐릭터의 코디(외형) 정보를 조회합니다.\n*캐릭터가 착용중인 코디 아이템을 보여줘양*\n ",
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
            name="븜 날씨 <지역명 혹은 주소> (v2 Beta)",
            value="**[카카오 / 기상청 API]**\n 현재 날씨와 예보정보를 조회합니다. \n*주소를 입력하면 더 정확하게 나와양\n대신 누군가 찾아올수도...*\n"
        )
        embed.add_field(
            name="븜 블링크빵",
            value="랜덤한 자연수 1~100 랜덤 추출합니다. \n*결과는 날아간 거리로 보여줘양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 미국주식 <티커>",
            value="**[yahoo finance]**\n 미국 주식의 현재 가격을 조회합니다.\n*아직 실험중인 기능이에양*\n*참고) 티커: BRK.B -> BRK-B* ",
            inline=False
        )
    elif category == "관리자":
        is_admin: bool = False
        # 명령어 요청자 권한 확인
        if ctx.message.author.guild_permissions.administrator or ctx.message.author.id == config.BOT_DEVELOPER_ID:
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
        f"봇 버전: {config.BOT_VERSION}\n"
        f"소스코드: https://github.com/yhbird/study-discord\n"
        "------\n"
        "Data based on NEXON Open API\n"
        "Powered by Neople Open API\n"
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


# 가장 오래 / 빨리 실행된 명령어 조회
@with_timeout(config.COMMAND_TIMEOUT)
async def deb_command_stats(ctx: commands.Context) -> None:
    # 채팅창에 명령어가 노출되지 않도록 삭제
    await ctx.message.delete()

    # 명령어 통계 출력
    what_is_slowest = (
        f"가장 오래 걸리는 명령어: {bl.SLOWEST_COMMAND_NAME} ({bl.SLOWEST_COMMAND_ELAPSED:.3f}초)\n"
    )
    what_is_fastest = (
        f"가장 빨리 끝나는 명령어: {bl.FASTEST_COMMAND_NAME} ({bl.FASTEST_COMMAND_ELAPSED:.3f}초)\n"
    )

    # 명령어 순위 통계 (상위 10개)
    command_stats_raw: dict = bl.COMMAND_STATS
    top10_commands: list = sorted(command_stats_raw.items(), key=lambda item: item[1]['count'], reverse=True)[:10]
    if not command_stats_raw:
        await ctx.send("아직 통계에 집계된 데이터가 없어양...")
        return

    rank_emoji: list = ["🥇", "🥈", "🥉"]
    command_stats = "\n".join(
        f"{(rank_emoji[idx] if idx < 3 else f'{idx+1}등')} "
        f"{info['alt_name'] or cmd_name}: {info['count']}회 "
        f"(최고: {info['fast']:.3f}초, 최저: {info['slow']:.3f}초)"
        for idx, (cmd_name, info) in enumerate(top10_commands)
    )

    now_kst: str = kst_format_now().strftime('%Y-%m-%d %H:%M:%S')
    bot_start: str = config.BOT_START_DT.strftime('%Y-%m-%d %H:%M:%S')
    embed_title = f"븜끼봇 명령어 통계"
    stats_message = (
        f"통계 집계 기준: {bot_start} (KST) 이후\n"
        f"현재 시간: {now_kst} (KST)\n\n"
        f"지금 까지 실행된 상위 10개 명령어 통계에양!\n"
        f"```ini\n"
        f"[상위 명령어 통계 top 10]\n"
        f"{what_is_slowest}"
        f"{what_is_fastest}\n"
        f"[명령어별 실행 횟수 및 시간]\n"
        f"{command_stats}\n"
        f"```"
    )
    embed_footer_text = (
        f"봇 버전: {config.BOT_VERSION} | 봇 이름: {ctx.guild.me.name}\n"
        f"명령어를 성공적으로 호출한 경우에만 통계에 반영돼양!"
    )

    embed: discord.Embed = discord.Embed(
        title=embed_title,
        description=stats_message,
        color=discord.Color.blue()
    )
    embed.set_footer(text=embed_footer_text)

    await ctx.send(embed=embed)
    return


# 가장 많이 명령어를 호출한 사용자 조회
@with_timeout(config.COMMAND_TIMEOUT)
async def deb_user_stats(ctx: commands.Context) -> None:
    """사용자별 명령어 호출 통계를 조회합니다.

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트

    Note:
        USER_STATS 딕셔너리에서 사용자 ID를 키로 사용하여
        각 사용자의 명령어 호출 횟수를 저장합니다.
        {user_id: {'total_count': int, 'last_command': str, 'command_counts': {command_name: int, ...}}} 형태
    """

    # 채팅창에 명령어가 노출되지 않도록 삭제
    await ctx.message.delete()

    # 사용자 통계 출력 (상위 3명, mention 포함)
    user_stats_raw = bl.USER_STATS
    if not user_stats_raw:
        await ctx.send("아직 통계에 집계된 데이터가 없어양...")
        return
    
    rank_emoji: list = ["🥇", "🥈", "🥉"]
    top3_users: list = sorted(user_stats_raw.items(), key=lambda item: item[1]['total_count'], reverse=True)[:3]
    user_stats = "\n".join(
        f"{(rank_emoji[idx] if idx < 3 else f'{idx+1}등 ')}"
        f"<@{user_id}>: {info['total_count']}회\n"
        f"- 최근 사용 명령어: {info.get('last_command', '몰라양')}\n"
        f"- 많이 사용한 명령어: {max(info['command_counts'], key=info['command_counts'].get, default='몰라양')} "
        f"({max(info['command_counts'].values(), default=0)}회)\n"
        for idx, (user_id, info) in enumerate(top3_users)
    )
    now_kst: str = kst_format_now().strftime('%Y-%m-%d %H:%M:%S')
    bot_start: str = config.BOT_START_DT.strftime('%Y-%m-%d %H:%M:%S')
    embed_title = f"븜끼봇 사용자 통계"
    stats_message = (
        f"통계 집계 기준: {bot_start} (KST) 이후\n"
        f"현재 시간: {now_kst} (KST)\n\n"
        f"지금 까지 명령어를 가장 많이 호출한 사용자 통계에양!\n"
        f"\n[상위 사용자 3명 명령어 통계]\n"
        f"{user_stats}\n"
        f""
    )
    embed_footer_text = (
        f"봇 버전: {config.BOT_VERSION} | 봇 이름: {ctx.guild.me.name}\n"
        f"명령어를 성공적으로 호출한 경우에만 통계에 반영돼양!"
    )

    embed: discord.Embed = discord.Embed(
        title=embed_title,
        description=stats_message,
        color=discord.Color.blue()
    )
    embed.set_footer(text=embed_footer_text)

    await ctx.send(embed=embed)
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
    bl.FASTEST_COMMAND_ELAPSED = 30.0

    logger.info("Command statistics have been reset.")
    await ctx.send("명령어 통계가 초기화되었어양!")
    return