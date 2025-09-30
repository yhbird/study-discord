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
from service.basic_utils import check_ban
from config import COMMAND_TIMEOUT

from exceptions.command_exceptions import InvalidCommandFormat
from ddgs.exceptions import DDGSException
from bot_logger import log_command, with_timeout


# 샴 따라해 기능 복원
@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 따라해")
async def msg_handle_repeat(ctx: commands.Context, repeat_text: str):
    """사용자가 보낸 메세지를 그대로 보내는 기능

    Args:
        ctx (commands.Context): "븜 따라해 "로 시작하는 디스코드 메세지

    Raises:
        Exception: 메세지 삭제 권한이 없거나, 메세지 삭제 실패시 발생
    """
    command_prefix: str = "븜 따라해 "

    if ctx.message.author.bot:
        return

    if ctx.message.content.startswith(command_prefix):
        output = ctx.message.content[len(command_prefix):]
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.message.channel.send("메세지 삭제 권한이 없어양")
            return
        except discord.HTTPException as e:
            await ctx.message.channel.send("메세지 삭제 중 오류가 발생했어양")
            return

        if output:
            await ctx.message.channel.send(output)


# 샴 이미지 기능 복원
@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 이미지")
async def msg_handle_image(ctx: commands.Context, search_term: str = None):
    """사용자가 요청한 이미지를 검색하여 최대 10개의 이미지를 보여주는 기능

    Args:
        ctx (commands.Context): "븜 이미지 "로 시작하는 디스코드 메세지

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

    results: list[dict] = None
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
            return
        except Exception as e:
            await ctx.message.channel.send(f"검색 중에 오류가 발생했어양...")
            return
    
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
            return

        await ctx.message.channel.send(f"{mention}님의 블링크빵 결과: {result}미터 만큼 날아갔어양! 💨💨💨")

