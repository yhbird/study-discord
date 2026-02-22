import asyncio
from datetime import datetime
import os
import gc
import random
import re
import discord
from numpy import resize
import psutil
import difflib

from discord.ext import commands
from discord.ext import tasks

from bot_logger import logger
from config import MEMORY_CLEAR_INTERVAL
from config import PRESENCE_UPDATE_INTERVAL
from config import SECRET_COMMANDS
from typing import List, Literal
    
# Emoji 메시지 처리 함수
from exceptions.client_exceptions import WebhookETCError, WebhookNoPermissionError
from utils.image import async_convert_image_url_into_bytes, async_upscale_emoji_image
from utils.webhook import send_msg_as_pretend_user

CUSTOM_EMOJI_PATTERN = re.compile(r'^<(a?):(\w+):(\d+)>$')


games: List[str] = [
    "MapleStory",
    "던전앤파이터",
    "DJMAX RESPECT V",
    "Persona 5 Royal",
    "StarCraft",
    "Overwatch 2",
    "Apex Legends",
    "VALORANT",
    "League of Legends",
    "PUBG: BATTLEGROUNDS",
    "Valheim",
    "Delta Force",
    "Minecraft",
    "Needy Streamer Overload",
    "VRChat",
    "Lost Ark",
    "Hearthstone",
    "Sid Meier's Civilization V",
    "BlueStacks 5",
    "Battlefield 6",
]


# 1시간 마다 메모리 정리
@tasks.loop(minutes=MEMORY_CLEAR_INTERVAL)
async def auto_clear_memory():
    process = psutil.Process(os.getpid())
    mem_usage : float = process.memory_info().rss / 1024**2
    logger.info(f"Memory clear")
    gc.collect()
    logger.info(f"Current memory usage: {mem_usage:.2f} MB")


# 봇 현재상태 주기적 갱신
@tasks.loop(minutes=PRESENCE_UPDATE_INTERVAL)
async def update_bot_presence(bot: commands.Bot):
    random_game = random.choice(games)
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name=f"뭄 명령어 | {random_game}")
    )


def build_command_help(prefix: str, attempt: str, command: commands.Command) -> str:
    """단일 커맨드의 사용법 (help, usage) 문자열 생성

    Args:
        prefix (str): 명령어 접두사
        attempt (str): 사용자가 입력한 명령어
        command (commands.Command): 명령어 객체

    Returns:
        str: 명령어의 help 문자열
    """
    desc = command.help or "설명이 없어양"

    if command.usage:
        usage = f"`{prefix}{attempt} {command.usage}`"
    else:
        usage = f"`{prefix}{attempt}`"
    return (
        f"**{attempt} 명령어 사용법**\n"
        f"- 사용법: {usage}\n"
        f"- 설명: {desc}\n"
    )


def resolve_command(bot: commands.Bot, attempt: str):
    norm = attempt.strip()
    if not norm:
        return None, ""
    
    invoke = norm.split()[0]
    cmd = bot.get_command(invoke)
    return cmd, invoke


def build_command_hint(bot: commands.Bot, attempt: str) -> str | Literal[""]:
    """없는 명령어 입력시 유사한 명령어를 찾아 힌트 문자열 생성

    Args:
        bot (commands.Bot): discord 봇 인스턴스
        attempt (str): 사용자가 입력한 명령어

    Returns:
        str: 유사한 명령어 힌트 문자열
    """
    all_names = []
    for c in bot.commands:
        all_names.append(c.name)
        all_names.extend(c.aliases)
    commands = difflib.get_close_matches(attempt, all_names, n=3, cutoff=0.6)
    if any(cmd in commands for cmd in SECRET_COMMANDS):
        return ""
    else:
        return f"혹시 '{', '.join(commands)}' 명령어를 말하시는 거에양?" if commands else ""


async def expand_custom_emoji(bot: commands.Bot, msg: discord.Message) -> None:
    """
    사용자가 입력한 단일 커스텀 이모지를 거대한 이미지로 확장하여 반환하는 함수

    Args:
        bot (commands.Bot): discord 봇 인스턴스
        ctx (discord.Message): discord 메세지 컨텍스트
    """
    # DB에서 이모지 출력 설정 확인
    if bot.db:
        server_config = await bot.db.get_emoji_convert_server(msg.guild.id)
        
        # 설정이 없거나 OFF 상태면 이모지 처리하지 않음
        if server_config is None:
            await bot.db.register_server_default_off(msg.guild.id, msg.guild.name)
            await msg.channel.send(
                "이 서버에서는 이모지 출력 기능이 활성화되어 있지 않아양! \n"
                "이모지 이미지를 큰 이미지로 출력하려면 `뭄 이모지출력` "
                "명령어로 기능을 활성화해보세양! \n**(주의: 서버 역할에 웹후크 관리 권한 필요해양!)**"
            )
            await bot.process_commands(msg)
            return
        
        if not server_config['emoji_convert']: # 설정이 OFF 상태면 이모지 처리하지 않음
            await bot.process_commands(msg)
            return
        
        match = CUSTOM_EMOJI_PATTERN.match(msg.content.strip())
        if server_config['emoji_convert'] and match: # 설정은 ON인데 웹후크 권한이 없으면 안내 메시지 보내고 처리하지 않음
            animated = match.group(1) == 'a'
            emoji_id = match.group(3)
            ext = "gif" if animated else "png"
            emoji_error_msg = "\n(Tip: 다른 discord 봇과 기능이 중복되면 \"뭄 이모지출력\" 명령어를 사용해보세양!)"
            emoji_url = f'https://cdn.discordapp.com/emojis/{emoji_id}.{ext}'

            try:
                image_buffer, ext = await async_upscale_emoji_image(emoji_url)
                
                filename = f"{emoji_id}_upscaled.{ext}"
                attach_file = discord.File(image_buffer, filename=filename)
                
                # 원본 메시지 삭제
                await msg.delete()
                
                # 더미 채널에 업로드하여 CDN URL 획득
                dummy_channel_id = 1473003830399733974
                dummy_channel = bot.get_channel(dummy_channel_id)
                
                if not dummy_channel:
                    raise Exception("더미 채널을 찾을 수 없습니다")
                
                temp_msg = await dummy_channel.send(file=attach_file)
                
                if temp_msg.attachments:
                    image_url = temp_msg.attachments[0].url
                    
                    # CDN URL을 content 텍스트로 전송
                    # Discord가 URL을 auto-embed하여 컴팩트한 이미지 카드로 표시
                    await send_msg_as_pretend_user(
                        channel=msg.channel,
                        user=msg.author,
                        content=image_url
                    )

            except WebhookNoPermissionError as e:
                logger.error(f"Webhook Permission Error: {e}")
                await msg.channel.send(
                    f"이모지 이미지를 처리하려면 `Manage Webhooks` 권한이 필요해양!"
                    f" 관리자에게 문의해보세양! {emoji_error_msg}"
                )
            except Exception as e:
                logger.error(f"Error Processing Emoji: {e}")
                await msg.channel.send(
                    f"이모지 이미지를 처리하는 중 오류가 발생했어양! {emoji_error_msg}"
                )
            return
        else:
            await bot.process_commands(msg)
            return