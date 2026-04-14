import discord
from discord.ext import commands
from common.dbconnector import AsyncDBConnector


class BumKkiBot(commands.Bot):
    """쁨끼봇 커스텀 클래스 - db 속성 추가됨 (2026.04.15)"""
    db: AsyncDBConnector | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db: AsyncDBConnector | None = None