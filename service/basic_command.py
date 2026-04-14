"""

디스코드 기본 명령어 처리 모듈

사용 라이브러리: discord.py, ddgs (DuckDuckGo Search API)

"""
import discord
from discord.ext import commands

import random
import time
from ddgs import DDGS

from service.basic_utils import ImageViewer
from service.basic_utils import check_ban, parse_user_list, parse_version_info
from service.basic_utils import rcon_client, rcon_command_retry, rcon_command
from common.text import strip_ansi_escape, parse_tps
from config import COMMAND_TIMEOUT, BOT_COMMAND_PREFIX, MINECRAFT_RCON_PASSWORD, MINECRAFT_PUBLIC_DOMAIN
from bot_logger import log_command, with_timeout

from ddgs.exceptions import DDGSException
from exceptions.client_exceptions import RCON_CLIENT_ERROR
from exceptions.command_exceptions import InvalidCommandFormat, CommandFailure

from typing import Dict

# 샴 따라해 기능 복원
@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 따라해")
async def msg_handle_repeat(ctx: commands.Context, repeat_text: str) -> None:
    """사용자가 보낸 메세지를 그대로 보내는 기능

    Args:
        ctx (commands.Context): "븜 따라해 "로 시작하는 디스코드 메세지
        repeat_text: 디버그용 변수

    Raises:
        Exception: 메세지 삭제 권한이 없거나, 메세지 삭제 실패시 발생
    """
    content_raw: str = ctx.message.content

    if content_raw.startswith(f"{BOT_COMMAND_PREFIX}따라해"):
        output = repeat_text.strip()
        try:
            await ctx.message.delete()

        except discord.Forbidden:
            await ctx.message.channel.send("메세지 삭제 권한이 없어양")
            raise CommandFailure("Forbidden access to delete message")
        
        except discord.HTTPException:
            await ctx.message.channel.send("메세지 삭제 중 오류가 발생했어양")
            raise CommandFailure("HTTP error while deleting message")

        except Exception:
            await ctx.message.channel.send("알 수 없는 오류가 발생했어양")
            raise CommandFailure("Unknown error while deleting message")
        
        if output:
            await ctx.message.channel.send(output)
            return
    
    else:
        return


# 샴 이미지 기능 복원
@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 이미지")
async def msg_handle_image(ctx: commands.Context, search_term: str | None = None):
    """사용자가 요청한 이미지를 검색하여 최대 10개의 이미지를 보여주는 기능

    Args:
        ctx (commands.Context): "븜 이미지 "로 시작하는 디스코드 메세지
        search_term (str): 이미지 검색어 (일부 문자열 금지)

    Raises:
        Exception: 메세지 삭제 권한이 없거나, 메세지 삭제 실패시 발생
        Exception: 이미지 검색 API 호출 실패시 발생
        Warning: 이미지를 찾을 수 없을 때 발생
    
    Note:
        검색 지역 일본(ja-jp)으로 변경 (2025.09.01)
    """

    if ctx.message.author.bot:
        return

    if search_term is None:
        await ctx.message.channel.send("검색어를 입력하세양!!", reference=ctx.message)
        raise InvalidCommandFormat("검색어가 입력되지 않음")
    else:
        image_search_keyword: str = search_term.strip()


    if check_ban(image_search_keyword):
        ban_img: str = "data/img/dnf_4.gif"
        with open(ban_img, "rb") as ban_img_file:
            dnf_file = discord.File(ban_img_file)
            await ctx.send(file=dnf_file, reference=ctx.message)
        return

    results: list[dict] | None = None
    with DDGS() as ddgs:
        try:
            time.sleep(2) # API rate limit 
            results = ddgs.images(
                query=image_search_keyword,
                safesearch="off",
                region="ja-jp",
                num_results=20,
            )
        except DDGSException as e:
            await ctx.message.channel.send(f"이미지 검색 사이트에 오류가 발생했어양...")
            raise CommandFailure(f"DDGS API error: {str(e)}")
        except Exception as e:
            await ctx.message.channel.send(f"검색 중에 오류가 발생했어양...")
            raise CommandFailure(f"Unknown error: {str(e)}")
    
    if not results:
        await ctx.message.channel.send("이미지를 찾을 수 없어양!!")
        return
    else:
        images = [r for r in results if "image" in r and "url" in r]

    image_results = images[0:10]  # 최대 10개 이미지
    view_owner: discord.User = ctx.message.author
    view = ImageViewer(images=image_results, search_keyword=image_search_keyword, requester=view_owner)
    index_indicator: str = f"{view.current_index + 1}/{len(view.images)}"

    embed = discord.Embed(title=f"'{image_search_keyword}' 이미지 검색 결과 에양 ({index_indicator})")
    embed.set_image(url=view.images[view.current_index]["image"])
    embed.description = f"[🔗 원본 보기]({view.images[view.current_index]['url']})"
    embed.set_footer(text="문제가 있는 이미지면 관리자 권한으로 삭제할 수 있어양!")

    sent_message = await ctx.message.channel.send(embed=embed, view=view)
    view.message = sent_message


# 주사위 (0~100)
# 명령어 "븜 블링크빵" 사용
@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 블링크빵")
async def msg_handle_blinkbang(ctx: commands.Context):
    """랜덤 주사위 0~100 결과를 보여주는 기능

    Args:
        ctx (commands.Context): 븜 블링크빵 커맨드 입력

    Raises:
        Exception: 메세지 삭제 권한이 없거나, 메세지 삭제 실패시 발생
    """
    command_prefix: str = "븜 블링크빵"

    if ctx.message.author.bot:
        return

    if ctx.message.content.startswith(command_prefix):
        mention = ctx.message.author.mention
        result: int = random.randint(0, 100)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.message.channel.send("메세지 삭제 권한이 없어양")
            raise CommandFailure("Forbidden access to delete message")

        await ctx.message.channel.send(f"{mention}님의 블링크빵 결과: {result}미터 만큼 날아갔어양! 💨💨💨")
        return


# 마크 서버 명령어: 서버 정보 조회
@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 마크서버")
async def msg_mcserver_info(ctx: commands.Context) -> None:
    """
    마인크래프트 서버 정보를 조회하는 기능
    
    :param ctx: discord 명령어 컨텍스트
    :type ctx: commands.Context

    :raises Exception: 네트워크 연결 오류, 마인크래프트 서버 offline 상태일 때 발생
    """

    try:
        with rcon_client() as rcon:
            if rcon is None:
                await ctx.message.channel.send("RCON 클라이언트 생성에 실패했어양...")
                raise CommandFailure("RCON 클라이언트 생성 실패")

            login_ok = rcon.login(MINECRAFT_RCON_PASSWORD)
            if not login_ok:
                await ctx.message.channel.send("RCON 로그인에 실패했어양...")
                raise CommandFailure("RCON 로그인 실패")

            version_info = await rcon_command_retry(
                rcon,
                "version",
                retries=5,
                interval=1.0,
                retry_flag="Checking"
            )
            player_list = await rcon_command(rcon, "list")
            tps_text = await rcon_command(rcon, "tps")
            tps_t1, tps_t5, tps_t15 = parse_tps(tps_text)

            version_info_text: str = strip_ansi_escape(version_info)
            player_list_text: str = strip_ansi_escape(player_list)
            player_count, player_names = parse_user_list(player_list_text)
            parse_version_text: str = parse_version_info(version_info_text)

            if player_count == "알 수 없음" or parse_version_text == "Error":
                await ctx.message.channel.send("서버 정보를 불러오는데 실패했어양...")
                raise CommandFailure("플레이어 수 정보 파싱 실패")
            
            if player_count:
                player_info_text: str = f"{player_count}\n{player_names}"
            else:
                player_info_text: str = f"{player_names}"

            info_msg = (
                f"**마인크래프트 서버 정보**\n"
                f"서버 주소: {MINECRAFT_PUBLIC_DOMAIN}\n"
                f"버전: {parse_version_text}\n"
                f"{player_info_text}\n"
                f"TPS(1/5/15분): {tps_t1}, {tps_t5}, {tps_t15}"
            )
    
    except RCON_CLIENT_ERROR as e:
        await ctx.message.channel.send("마인크래프트 서버와의 통신 중 오류가 발생했어양...")
        raise CommandFailure(f"RCON 클라이언트 오류: {str(e)}")
    
    await ctx.message.channel.send(info_msg)
    return


# 이모지출력 toggle 기능 (Admin 전용)
@with_timeout(COMMAND_TIMEOUT)
async def msg_toggle_emoji(ctx: commands.Context) -> None:
    """
    이모지 출력 토글 기능 (관리자 전용)
    
    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트

    Returns:
        None: 이모지 출력 설정이 토글되고, 현재 상태를 안내하는 메시지를 채널에 전송

    Note:
        - 이 명령어는 서버 관리자만 사용할 수 있습니다.
        - 이모지 출력 설정은 서버(guild) 단위로 관리되어 DB서버에 저장됩니다.
        - 서버 내에서 최초로 실행하면 이모지 출력이 활성화(ON)된 상태로 설정됩니다.
        - 기능을 모르는 서버를 위해 최초 안내 메세지를 출력하고 비활성화(OFF) 상태로 설정됩니다.
    """
    if not ctx.guild:
        await ctx.send("이 명령어는 서버 내에서만 사용할 수 있어양!")
        return
    
    # DB 연결 확인
    if not ctx.bot.db:
        await ctx.send("데이터베이스가 연결되어 있지 않아양!")
        raise CommandFailure("Database not connected")
    
    # 서버 정보 가져오기
    guild_id: int = ctx.guild.id
    guild_name: str = ctx.guild.name
    
    try:
        # 이모지 출력 설정 토글
        new_state: bool = await ctx.bot.db.toggle_emoji_convert(guild_id, guild_name)
        
        # 결과 안내 메시지
        status_text = "활성화" if new_state else "비활성화"
        await ctx.send(
            f"'{guild_name}' 서버의 이모지 출력 기능이 **{status_text}** 되었어양!\n"
            f"(웹후크 관리 권한이 필요해양!)"
        )
        
    except Exception as e:
        await ctx.send("이모지 출력 설정을 변경하는 중 오류가 발생했어양...")
        raise CommandFailure(f"Failed to toggle emoji output: {str(e)}")