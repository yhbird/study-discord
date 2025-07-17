import discord
from discord.ext import commands
from discord.ui import View, Button

from ddgs import DDGS
from ddgs.exceptions import DDGSException
import time
import random
import asyncio
from service.common import log_command

# 샴 이미지 이미지 뷰어 클래스 정의
class ImageViewer(View):
    def __init__(self, images, search_keyword, requester: discord.User, timeout=600):
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
        embed.set_image(url=self.images[self.current_index])
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
                pass

# 샴 따라해 기능 복원
@log_command
async def handle_repeat(message: discord.Message):
    command_prefix: str = "븜 따라해 "

    if message.author.bot:
        return
    
    if message.content.startswith(command_prefix):
        output = message.content[len(command_prefix):]
        try:
            await message.delete()
        except discord.Forbidden:
            await message.channel.send("메세지 삭제 권한이 없어양")
            raise Exception("permission denied to delete message")
        except discord.HTTPException as e:
            raise Exception(f"Failed to delete message: {e}")

        if output:
            await message.channel.send(output)

# 샴 이미지 기능 복원
@log_command
async def handle_image(message: discord.Message):
    command_prefix: str = "븜 이미지 "
    
    if message.author.bot:
        return
    
    if message.content.startswith(command_prefix):
        image_search_keyword: str = message.content[len(command_prefix):]

    results = None
    with DDGS() as ddgs:
        try:
            time.sleep(2) # API rate limit 
            results = ddgs.images(
                query=image_search_keyword,
                safesearch="off",
                num_results=10,
            )
        except DDGSException as e:
            await message.channel.send(f"이미지 검색 사이트에 오류가 발생했어양...")
            raise Exception(f"Failed to search images: {e}")
        except Exception as e:
            await message.channel.send(f"검색 중에 오류가 발생했어양...")
            raise Exception(f"Unexpected error during image search: {e}")
    
    if not results:
        await message.channel.send("이미지를 찾을 수 없어양!!")
        raise Warning(f"No images found keyword: {image_search_keyword}")
    
    image_urls = [r["image"] for r in results if "image" in r]
    view_owner: discord.User = message.author
    view = ImageViewer(images=image_urls, search_keyword=image_search_keyword, requester=view_owner)
    index_indicator: str = f"{view.current_index + 1}/{len(view.images)}"

    embed = discord.Embed(title=f"'{image_search_keyword}' 이미지 검색 결과 에양 ({index_indicator})")
    embed.set_image(url=view.images[view.current_index])

    sent_message = await message.channel.send(embed=embed, view=view)
    view.message = sent_message

# 주사위 (0~100)
# 명령어 "/블링크빵" 사용
@log_command
async def handle_blinkbang(message: discord.Message):
    command_prefix: str = "/블링크빵"

    if message.author.bot:
        return
    
    if message.content.startswith(command_prefix):
        username: str  = message.author.display_name
        mention = message.author.mention
        result: int = random.randint(0, 100)
        try:
            await message.delete()
        except discord.Forbidden:
            await message.channel.send("메세지 삭제 권한이 없어양")
            raise Exception("permission denied to delete message")

        await message.channel.send(f"{mention}님의 블링크빵 결과: {result}미터 만큼 날아갔어양! 💨💨💨")