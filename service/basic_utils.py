import os
import discord
import asyncio
from discord.ui import View, Button

from dotenv import load_dotenv
from config import BOT_DEVELOPER_ID
from config import MINECRAFT_RCON_HOST, MINECRAFT_RCON_PORT, MINECRAFT_RCON_PASSWORD
from mctools import RCONClient
from contextlib import contextmanager
from typing import Generator

from exceptions.client_exceptions import RCON_CLIENT_ERROR

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


    def is_owner(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.view_owner.id
    

    def is_admin(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        
        perms = interaction.user.guild_permissions
        return perms.administrator or interaction.user.id == BOT_DEVELOPER_ID
    

    def has_permission(self, interaction: discord.Interaction, action: str) -> bool:
        if action == "delete":
            return self.is_owner(interaction) or self.is_admin(interaction)
        
        owner_only_actions = {"first", "prev", "next", "last"}
        if action in owner_only_actions:
            return self.is_owner(interaction)
        
        return False
    

    async def _send_no_permission_message(self, interaction: discord.Interaction, action: str) -> None:
        if action == "delete":
            send_msg = "이 기능은 검색한 사람이나 관리자만 사용할 수 있어양!"
        else:
            send_msg = "이 기능은 검색한 사람만 사용할 수 있어양!"

        if not interaction.response.is_done():
            await interaction.response.send_message(send_msg, ephemeral=True)
            return
        else:
            await interaction.followup.send(send_msg, ephemeral=True)
            return


    async def interaction_check(self, interaction: discord.Interaction) -> bool:               
        action = interaction.data["custom_id"]

        if not self.has_permission(interaction, action):
            await self._send_no_permission_message(interaction, action)
            return False
        
        if action == "first":
            self.current_index = 0
        elif action == "prev":
            self.current_index = max(0, self.current_index - 1)
        elif action == "next":
            self.current_index = min(len(self.images) - 1, self.current_index + 1)
        elif action == "last":
            self.current_index = len(self.images) - 1
        elif action == "delete":
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            if self.message:
                try:
                    await self.message.delete()
                except discord.NotFound:
                    pass
            self.stop()
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
            return
        else:
            await interaction.response.edit_message(embed=embed, view=self)
            return

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
            
            
def check_ban(image_search_keyword: str) -> bool:
    """금지어 검사

    Args:
        image_search_keyword (str): 이미지 검색어

    Returns:
        bool: 금지어 포함 여부
    """
    load_dotenv("env/secret.env")
    ban_cmd_1 = os.getenv("BAN_CMD_1")
    ban_cmd_2 = os.getenv("BAN_CMD_2")
    ban_cmd_3 = os.getenv("BAN_CMD_3")
    ban_cmd_4 = os.getenv("BAN_CMD_4")

    ban_list: list = [ban_cmd_1, ban_cmd_2, ban_cmd_3, ban_cmd_4]

    for ban_word in ban_list:
        if ban_word in image_search_keyword:
            return True
        
    return False


@contextmanager
def rcon_client(
    host: str = MINECRAFT_RCON_HOST,
    port: int = MINECRAFT_RCON_PORT,
    password: str = MINECRAFT_RCON_PASSWORD
) -> Generator[RCONClient, None, None]:
    """
    RCON 클라이언트 생성 및 반환
    
    :return: RCON 클라이언트 인스턴스
    :rtype: RCONClient
    """
    rcon_client = None
    try:
        rcon_client = RCONClient(host, port=port)
        print(f"try connect to {host}:{port} ...")
        if not rcon_client.login(password):
            raise RCON_CLIENT_ERROR("RCON 로그인 실패")
        yield rcon_client
    except Exception as e:
        raise RCON_CLIENT_ERROR(f"RCON 클라이언트 오류: {str(e)}")
    finally:
        if rcon_client is not None:
            try:
                rcon_client.stop()
            except Exception:
                pass


async def rcon_command(
    rcon: RCONClient, 
    cmd: str
) -> str:
    """
    RCON 명령어를 실행하는 함수

    :param rcon: RCON 클라이언트 인스턴스
    :type rcon: RCONClient
    :param cmd: 실행할 명령어
    :type cmd: str
    :return: 명령어 실행 결과
    :rtype: str
    """
    return await asyncio.to_thread(rcon.command, cmd)


async def rcon_command_retry(
    rcon: RCONClient, 
    cmd: str, 
    *, 
    retries: int = 3, 
    interval: float = 0.5, 
    retry_flag: str | None = None
) -> str:
    """
    RCON 명령어를 재시도 로직을 통해 실행하는 함수

    Args:
        rcon (RCONClient): RCON 클라이언트 인스턴스
        cmd (str): 실행할 명령어
        retries (int, optional): 재시도 횟수. Defaults to 3.
        interval (float, optional): 재시도 간격(초). Defaults to 0.5.
        retry_flag (str | None, optional): 재시도 플래그 문자열. 응답에 이 문자열이 포함되면 재시도함. Defaults to None.
    """
    last = ""
    for attempt in range(retries):
        last = await asyncio.to_thread(rcon.command, cmd)
        if retry_flag and retry_flag in last:
            await asyncio.sleep(interval * (attempt + 1))
            continue
        return last
    return last


def parse_user_list(list_text: str) -> tuple[str | int, str]:
    """
    현재 접속자 목록(list 명령어 결과)을 파싱하는 함수

    Args:
        list_text (str): list 명령어 결과 문자열

    Returns:
        tuple[str, str]: (현재 접속자 수, 접속자 목록 문자열)
    """
    try:
        split_text: list[str] = list_text.split(":")
        count_part = split_text[0].strip()
        users_part = split_text[1].strip() if len(split_text) > 1 else ""

        # 현재 접속한 유저가 없는 경우
        if users_part == "":
            return (0, "접속한 유저가 없어양!")

        # 현재 접속자 수 추출 (There are X of a max of 20 players online)
        else:
            current_users = count_part.split(" ")[2]
            max_users = count_part.split(" ")[5]
            count_part_text = f"현재 접속자 수: {current_users}/{max_users}명"
            users_part_text = f"접속자 목록: {users_part.replace(' ', ', ')}"
            return (count_part_text, users_part_text)
        
    except Exception:
        return ("알 수 없음", "접속자 목록을 불러오는 중 오류가 발생했어양...")


def parse_version_info(version_text: str) -> str:
    """
    마인크래프트 버전 정보를 파싱하는 함수

    Args:
        version_text (str): version 명령어 결과 문자열

    Returns:
        str: 파싱된 버전 정보 문자열
    """
    try:
        # 예시: "This server is running Paper version 1.21.11-39-main@... ""
        split_text: list[str] = version_text.split("@")
        version_info = split_text[0].replace("This server is running ", "").strip()
        return version_info
    except Exception:
        return "Error"