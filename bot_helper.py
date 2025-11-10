import os
import gc
import random
import discord
import psutil
import difflib

from discord.ext import commands
from discord.ext import tasks

from bot_logger import logger
from config import MEMORY_CLEAR_INTERVAL
from config import PRESENCE_UPDATE_INTERVAL
from config import SECRET_COMMANDS
from typing import List


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
        activity=discord.Game(name=f"븜 명령어 | {random_game}")
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


def build_command_hint(bot: commands.Bot, attempt: str) -> str:
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