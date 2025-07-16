import discord
from discord.ext import commands
from service.common import log_command
from config import BOT_TOKEN, kst_format_now

# 디스코드 메세지 관련 명령어
import service.msg_command as msg_command
# 디스코드 API 처리 관련 명령어
# from service.api_command import api_command

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'[{kst_format_now()}] Logged in as {bot.user}!')

# 명령어 등록 from service.msg_command
@bot.command(name="블링크빵")
async def run_blinkbang(ctx: commands.Context):
    await msg_command.handle_blinkbang(ctx.message)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # 특수 명령어 실행 (from service.msg_command)
    if message.content.startswith('븜 따라해 '):
        await msg_command.handle_repeat(message)
    if message.content.startswith('븜 이미지 '):
        await msg_command.handle_image(message)

    # 봇 명령어 처리
    await bot.process_commands(message)

# 봇 실행!
bot.run(str(BOT_TOKEN))