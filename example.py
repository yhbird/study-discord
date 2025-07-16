import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from .env file
assert os.path.exists('token.env'), "token.env file not found"
load_dotenv('token.env')
test_bot_token: str = os.getenv('example_bot_token')

intents = discord.Intents.default()
intents.message_content = True

test_bot = commands.Bot(command_prefix='/', intents=intents)

@test_bot.event
async def on_ready():
    print(f'Logged in as {test_bot.user}!')

# 봇 명령어 테스트 "/ping"
@test_bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

test_bot.run(str(test_bot_token))