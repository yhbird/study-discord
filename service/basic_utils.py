import os
import discord
from discord.ui import View, Button

from exceptions.base import BotWarning
from dotenv import load_dotenv

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
        # Admin 권한이 있으면 삭제 가능
        if interaction.user.guild_permissions.administrator:
            if action == "delete":
                if self.message:
                    await self.message.delete()
                return False  # View 종료
               
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
        embed.set_footer(text="문제가 있는 이미지면 관리자 권한으로 삭제할 수 있어양!")
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
            
            
def check_ban(image_search_keyword: str) -> bool:
    """금지어 검사

    Args:
        image_search_keyword (str): 이미지 검색어

    Returns:
        bool: 금지어 포함 여부
    """
    load_dotenv("env/ban.env")
    ban_cmd_1 = os.getenv("ban_cmd_1")
    ban_cmd_2 = os.getenv("ban_cmd_2")
    ban_cmd_3 = os.getenv("ban_cmd_3")
    ban_cmd_4 = os.getenv("ban_cmd_4")

    ban_list: list = [ban_cmd_1, ban_cmd_2, ban_cmd_3, ban_cmd_4]

    for ban_word in ban_list:
        if ban_word in image_search_keyword:
            return True
        
    return False