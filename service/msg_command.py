"""

디스코드 기본 명령어 처리 모듈

사용 라이브러리: discord.py, ddgs (DuckDuckGo Search API)

"""
import discord
from discord.ext import commands
from discord.ui import View, Button

from ddgs import DDGS
import time
import random

from service.common import log_command
from config import BOT_VERSION

from service.common import (
    BotWarning
)
from ddgs.exceptions import DDGSException

# 샴 이미지 이미지 뷰어 클래스 정의
class ImageViewer(View):
    def __init__(self, images: list[dict], search_keyword: str, requester: discord.User, timeout: int = 600):
        super().__init__(timeout=timeout)
        self.images = images
        self.image_search_keyword = search_keyword
        self.current_index = 0
        self.view_owner: discord.User = requester
        self.message = None

        # 버튼 추가
        self.add_item(Button(label="⏮️", style=discord.ButtonStyle.secondary, custom_id="first"))
        self.add_item(Button(label="◀️", style=discord.ButtonStyle.secondary, custom_id="prev"))
        self.add_item(Button(label="▶️", style=discord.ButtonStyle.secondary, custom_id="next"))
        self.add_item(Button(label="⏭️", style=discord.ButtonStyle.secondary, custom_id="last"))
        self.add_item(Button(label="❌", style=discord.ButtonStyle.primary, custom_id="delete"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # 상호작용한 사용자가 뷰의 소유자와 일치하는지 확인
        if interaction.user != self.view_owner:
            await interaction.response.send_message("이 기능은 검색한 사람만 사용할 수 있어양!", ephemeral=True)
            return False
        
        # 상호작용한 사용자와 뷰의 소유자가 일치하면 버튼 상호작용 실행
        action = interaction.data["custom_id"]
        if action == "first":
            self.current_index = 0
        elif action == "prev":
            self.current_index = max(0, self.current_index - 1)
        elif action == "next":
            self.current_index = min(len(self.images) - 1, self.current_index + 1)
        elif action == "last":
            self.current_index = len(self.images) - 1
        elif action == "delete":
            if self.message:
                await self.message.delete()
            return False  # View 종료
        await self.update_msg(interaction)
        return True

    async def update_msg(self, interaction: discord.Interaction):
        index = f"{self.current_index + 1}/{len(self.images)}"
        embed = discord.Embed(title=f"'{self.image_search_keyword}' 이미지 검색 결과 에양 ({index})")
        embed.set_image(url=self.images[self.current_index]["image"])
        embed.description = f"[🔗 원본 보기]({self.images[self.current_index]['url']})"
        if interaction.response.is_done():
            await interaction.followup.edit_message(message_id=self.message.id, embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    # 10분 후 타임아웃 처리
    async def on_timeout(self):
        # 모든 버튼 비활성화
        for item in self.children:
            item.disabled = True

        # 메시지가 존재하면 업데이트 (이미 삭제되면 무시)
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                raise BotWarning

# 샴 따라해 기능 복원
@log_command
async def msg_handle_repeat(ctx: commands.Context, repeat_text: str):
    """사용자가 보낸 메세지를 그대로 보내는 기능

    Args:
        message (Discord.ctx): "븜 따라해 "로 시작하는 디스코드 메세지

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
@log_command
async def msg_handle_image(ctx: commands.Context, search_term: str):
    """사용자가 요청한 이미지를 검색하여 최대 10개의 이미지를 보여주는 기능

    Args:
        message (Discord.ctx): "븜 이미지 "로 시작하는 디스코드 메세지

    Raises:
        Exception: 메세지 삭제 권한이 없거나, 메세지 삭제 실패시 발생
        Exception: 이미지 검색 API 호출 실패시 발생
        Warning: 이미지를 찾을 수 없을 때 발생
    """
    command_prefix: str = "븜 이미지 "

    if ctx.message.author.bot:
        return

    if ctx.message.content.startswith(command_prefix):
        image_search_keyword: str = ctx.message.content[len(command_prefix):]

    results: list[dict] = None
    with DDGS() as ddgs:
        try:
            time.sleep(2) # API rate limit 
            results = ddgs.images(
                query=image_search_keyword,
                safesearch="off",
                num_results=10,
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

    image_results = [r for r in results if "image" in r and "url" in r]
    view_owner: discord.User = ctx.message.author
    view = ImageViewer(images=image_results, search_keyword=image_search_keyword, requester=view_owner)
    index_indicator: str = f"{view.current_index + 1}/{len(view.images)}"

    embed = discord.Embed(title=f"'{image_search_keyword}' 이미지 검색 결과 에양 ({index_indicator})")
    embed.set_image(url=view.images[view.current_index]["image"])
    embed.description = f"[🔗 원본 보기]({view.images[view.current_index]['url']})"

    sent_message = await ctx.message.channel.send(embed=embed, view=view)
    view.message = sent_message

# 주사위 (0~100)
# 명령어 "븜 블링크빵" 사용
@log_command
async def msg_handle_blinkbang(ctx: commands.Context):
    """랜덤 주사위 0~100 결과를 보여주는 기능

    Args:
        message (discord.Message): /블링크빵 커맨드 입력

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

# 명령어 "븜 명령어" 사용
@log_command
async def msg_handle_help(ctx: commands.Context):
    """봇의 사용법을 안내하는 기능
    Args:
        message (discord.Message): /help 커맨드 입력

    Raises:
        Exception: 메세지 삭제 권한이 없거나, 메세지 삭제 실패시 발생

    Returns:
        None: 사용법 안내 메시지를 채널에 전송
    """
    command_prefix: str = "븜 명령어"

    if ctx.message.author.bot:
        return

    if ctx.message.content.startswith(command_prefix):
        embed_description: str = (
            "봇 개발자: yhbird ([github.com](https://github.com/yhbird))\n"
            "Data based on NEXON Open API\n"
            "븜끼 봇 사용법을 알려드릴게양!\n"
        )
        embed = discord.Embed(
            title=f"븜끼 사용설명서 ({BOT_VERSION})",
            description=embed_description,
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
            name="븜 날씨 <지역명 혹은 주소> (v1)",
            value="**[Kakao / 기상청 API 연동]**\n 해당 지역의 날씨 정보를 조회합니다. \n*주소를 입력하면 더 정확하게 나와양\n대신 누군가 찾아올수도...*\n"
        )
        embed.add_field(
            name="븜 블링크빵",
            value="랜덤한 자연수 1~100 랜덤 추출합니다. \n*결과는 날아간 거리로 보여줘양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 기본정보 <캐릭터 이름>",
            value="**[Nexon OPEN API 연동]**\n 메이플스토리 캐릭터의 기본 정보를 조회합니다.\n ",
            inline=False
        )
        embed.add_field(
            name="븜 상세정보 <캐릭터 이름>",
            value="**[Nexon OPEN API 연동]**\n 메이플스토리 캐릭터의 상세 정보를 조회합니다.\n*기본 정보보다 더 많은 정보를 제공해양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 피씨방",
            value="**[Nexon OPEN API 연동]**\n 최근 피씨방 공지사항을 조회합니다.\n*이미지가 길쭉해서 좀 오래걸려양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 썬데이",
            value="**[Nexon OPEN API 연동]**\n 썬데이 메이플 공지사항을 조회합니다.\n*매주 금요일 오전에 업데이트돼양*\n ",
            inline=False
        )
        embed.add_field(
            name="븜 미국주식 <티커>",
            value="**[yahoo finance API 연동]**\n 미국 주식의 현재 가격을 조회합니다.\n*아직 실험중인 기능이에양*\n*참고) 티커: BRK.B -> BRK-B* ",
            inline=False
        )
        embed.add_field(
            name="븜 명령어",
            value="명령어 목록을 표시합니다. \n*도움이 필요하면 언제든지 불러양!!*\n ",
            inline=False
        )
        embed_footer:str = (
            f"봇 이름: {ctx.message.guild.me.name}\n"
            f"봇 버전: {BOT_VERSION}\n"
            f"소스코드: https://github.com/yhbird/study-discord"
        )
        embed.set_footer(text=embed_footer)
        await ctx.message.channel.send(embed=embed)