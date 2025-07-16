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
    def __init__(self, images, search_keyword, timeout=600):
        super().__init__(timeout=timeout)
        self.images = images
        self.image_search_keyword = search_keyword
        self.current_index = 0
        self.message = None

        # 버튼 추가
        self.add_item(Button(label="⏮️", style=discord.ButtonStyle.secondary, custom_id="first"))
        self.add_item(Button(label="◀️", style=discord.ButtonStyle.secondary, custom_id="prev"))
        self.add_item(Button(label="▶️", style=discord.ButtonStyle.secondary, custom_id="next"))
        self.add_item(Button(label="⏭️", style=discord.ButtonStyle.secondary, custom_id="last"))
        self.add_item(Button(label="❌", style=discord.ButtonStyle.primary, custom_id="delete"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # 버튼 상호작용 실행
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

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

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
    view = ImageViewer(images=image_urls, search_keyword=image_search_keyword)
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