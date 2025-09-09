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
@log_command
async def msg_handle_image(ctx: commands.Context, search_term: str):
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

    sent_message = await ctx.message.channel.send(embed=embed, view=view)
    view.message = sent_message

# 주사위 (0~100)
# 명령어 "븜 블링크빵" 사용
@log_command
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

# "븜 명령어" 리다이렉트
@log_command
async def msg_handle_help_redirection(ctx: commands.Context, category: str = None):
    """사용자에게 도움말을 리다이렉트하는 기능

    Args:
        ctx(commands.Context): 도움말 요청이 포함된 디스코드 메세지
    """
    # 봇 메시지 무시
    if ctx.message.author.bot:
        return

    else:
        # 리다이렉트 명령어 확인
        await msg_handle_help_v2(ctx, category=category)

        # 리다이렉트 명령어 안내
        mention = ctx.message.author.mention
        if category:
            await ctx.message.channel.send(f"{mention} '븜 명령어 {category}'를 입력하세양!")
        else:
            await ctx.message.channel.send(f"{mention} '븜 명령어'를 입력하세양!")

# 명령어 "븜 명령어" 사용
@log_command
async def msg_handle_help(ctx: commands.Context):
    """봇의 사용법을 안내하는 기능 (삭제 예정)
    Args:
        ctx (commands.Context): /help 커맨드 입력

    Raises:
        Exception: 메세지 삭제 권한이 없거나, 메세지 삭제 실패시 발생

    Returns:
        None: 사용법 안내 메시지를 채널에 전송

    Note:
        이 함수는 향후 msg_handle_help_v2로 대체될 예정입니다. (2025.09.11 이후 예정)
    """

    if ctx.message.author.bot:
        return

    embed_description: str = (
        "봇 개발자: 크로아 마법사악 ([github.com](https://github.com/yhbird))\n"
        "븜끼 봇 사용법을 알려드릴게양!\n"
    )
    embed = discord.Embed(
        title=f"븜끼봇 명령어 목록 (븜 명령어)",
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
        value="**[Kakao / 기상청 API]**\n 해당 지역의 날씨 정보를 조회합니다. \n*주소를 입력하면 더 정확하게 나와양\n대신 누군가 찾아올수도...*\n"
    )
    embed.add_field(
        name="븜 블링크빵",
        value="랜덤한 자연수 1~100 랜덤 추출합니다. \n*결과는 날아간 거리로 보여줘양*\n ",
        inline=False
    )
    embed.add_field(
        name="븜 기본정보 <캐릭터 이름>",
        value="**[넥슨 API]**\n 메이플스토리 캐릭터의 기본 정보를 조회합니다.\n ",
        inline=False
    )
    embed.add_field(
        name="븜 상세정보 <캐릭터 이름>",
        value="**[넥슨 API]**\n 메이플스토리 캐릭터의 상세 정보를 조회합니다.\n*기본 정보보다 더 많은 정보를 제공해양*\n ",
        inline=False
    )
    embed.add_field(
        name="븜 어빌리티 <캐릭터 이름>",
        value="**[넥슨 API]**\n 메이플스토리 캐릭터의 어빌리티 정보를 조회합니다.\n*사용중인 어빌리티와 프리셋 정보를 제공해양*\n ",
        inline=False
    )
    embed.add_field(
        name="븜 운세 <캐릭터 이름>",
        value="**[넥슨 API]**\n 오늘의 메이플스토리 캐릭터 운세를 조회합니다.\n*재미로만 봐주세양!!*\n*참고) 5성:5%, 4성:20%, 3성:30%, 2성:40%, 1성:5% 확률로 나와양*\n ",
        inline=False
    )
    embed.add_field(
        name="븜 경험치 <캐릭터 이름>",
        value="**[넥슨 API]**\n 메이플스토리 캐릭터의 경험치 그래프를 조회합니다.\n*최근 7일간 경험치 변화를 그래프로 보여줘양*\n ",
        inline=False
    )
    embed.add_field(
        name="븜 피씨방",
        value="**[넥슨 API]**\n 최근 피씨방 공지사항을 조회합니다.\n*이미지가 길쭉해서 좀 오래걸려양*\n ",
        inline=False
    )
    embed.add_field(
        name="븜 썬데이",
        value="**[넥슨 API]**\n 썬데이 메이플 공지사항을 조회합니다.\n*매주 금요일 오전에 업데이트돼양*\n ",
        inline=False
    )
    embed.add_field(
        name="븜 던파정보 <서버이름> <캐릭터이름>",
        value="**[네오플 API]**\n 던전앤파이터 캐릭터의 정보를 조회합니다.\n*한글로 서버 이름과 캐릭터 이름을 입력해양*\n*예시) 븜 던파정보 카인 마법사악*\n ",
        inline=False
    )
    embed.add_field(
        name="븜 미국주식 <티커>",
        value="**[yahoo finance]**\n 미국 주식의 현재 가격을 조회합니다.\n*아직 실험중인 기능이에양*\n*참고) 티커: BRK.B -> BRK-B* ",
        inline=False
    )
    embed.add_field(
        name="븜 명령어",
        value="명령어 목록을 표시합니다. \n*도움이 필요하면 언제든지 불러양!!*\n ",
        inline=False
    )
    embed_footer:str = (
        f"봇 이름: {ctx.guild.me.name}\n"
        f"봇 버전: {BOT_VERSION}\n"
        f"소스코드: https://github.com/yhbird/study-discord\n"
        "Data based on NEXON Open API\n"
        "Powered by Neople Open API\n"
    )
    embed.set_footer(text=embed_footer)
    await ctx.send(embed=embed)

@log_command
async def msg_handle_help_v2(ctx: commands.Context, category: str = None):
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
            name="[개발중] 븜 주간던파 <서버이름> <캐릭터이름>",
            value="던전앤파이터 캐릭터의 주간 던파를 요약합니다.\n*태초를 몇개 먹었는지 븜미가 친절히 알려줘양*\n**<개발중>**\n ",
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
            name="븜 날씨 <지역명 혹은 주소> (v1)",
            value="**[카카오 / 기상청 API]**\n 해당 지역의 날씨 정보를 조회합니다. \n*주소를 입력하면 더 정확하게 나와양\n대신 누군가 찾아올수도...*\n"
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
        # 명령어 요청자 권한 확인
        if ctx.message.author.guild_permissions.administrator:
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
                value="봇 디버그 모드 전환 (에러로그가 상세하게 표시됩니다.)\n",
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
        f"봇 버전: {BOT_VERSION}\n"
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
        try:
            dm_embed.set_footer(text=embed_footer)
            await ctx.message.author.send(embed=dm_embed)
        except Exception:
            await ctx.message.channel.send(f"{ctx.message.author.mention} DM을 보내는 중에 오류가 발생했어양...")
    else:
        # 메세지 전송
        await ctx.send(embed=embed)