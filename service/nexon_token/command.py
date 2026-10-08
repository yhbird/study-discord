"""
`븜 넥슨토큰` 명령어 모듈 (2026-10-05, Opus 5.5)

사용자와 봇만 볼 수 있는 비공개 쓰레드에서 Nexon API 토큰을 저장, 삭제한다.
- 쓰레드는 30분 뒤 자동으로 삭제
- 개인정보 수집 동의를 한 사용자만 저장, 삭제 기능 사용 가능
- 토큰은 모달(입력창)로 받아서 채팅 기록에 남지 않음

이 모듈은 메시지와 화면 구성만 담당하고, 데이터 처리는 service.nexon_token.utils에 맡긴다.
"""
from __future__ import annotations

import asyncio

import discord
from discord.ext import commands
from discord.ui import Button, InputText, Modal, Select, View

from bot import BumKkiBot
from bot_logger import log_command, logger, with_timeout
from config import COMMAND_TIMEOUT
from common.dbconnector import AsyncDBConnector
from common_exceptions.command_exceptions import CommandFailure
# 안내 메시지 맵은 exceptions.py로 옮기고 공통 함수 사용 (2026-10-08, Opus 5.5)
from common_exceptions.error_message import (
    UNKNOWN_ERROR_MESSAGE, find_error_message)
from service.nexon_token import utils
from service.nexon_token.consts import NexonTokenVars
from service.nexon_token.exceptions import (
    TOKEN_ERROR_MESSAGES, NexonTokenError, TokenThreadUnavailable)


THREAD_CLOSE_DELAY_SEC = 5


# ── 메시지 구성 ──
def build_agreement_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📋 개인정보 수집 및 이용 동의",
        description=(
            "Nexon Open API 토큰으로 조회하는 데이터는 **대한민국 법령상 개인을 식별할 수 있는 정보**에 "
            "해당해서, 수집 전에 사용자의 동의가 필요해양.\n"
            "**동의한 사용자만** 토큰 저장하기, 삭제하기 기능을 사용할 수 있어양."
        ),
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="수집 항목",
        value=("- 디스코드 사용자 ID\n"
               "- Nexon Open API 토큰 (암호화해서 저장)\n"
               "- 토큰 사용 기록 (등록 일시, 마지막 사용 일시, 호출 횟수, 실패 횟수)"),
        inline=False,
    )
    embed.add_field(
        name="수집 목적",
        value="본인 계정의 메이플스토리 정보(스케줄, 스타포스 강화, 잠재능력 변경 기록 등)를 조회하는 개인화 기능 제공",
        inline=False,
    )
    embed.add_field(
        name="보유 기간",
        value=("- 토큰과 사용 기록: 직접 삭제하거나 동의를 철회할 때까지\n"
               "- 동의, 철회 기록: 동의 사실을 증명하기 위해 별도 보관"),
        inline=False,
    )
    embed.add_field(
        name="동의를 거부할 권리",
        value="동의하지 않아도 되며, 이 경우 토큰이 필요한 개인화 기능만 사용할 수 없어양.",
        inline=False,
    )
    embed.set_footer(text=f"안내문 버전: {NexonTokenVars.POLICY_VERSION}")
    return embed


def build_manage_embed(user_id: int, tokens: list[utils.TokenSummary]) -> discord.Embed:
    embed = discord.Embed(
        title="🔐 넥슨 API 토큰 관리",
        description=(
            "토큰은 최대 2개(메인, 서브)까지 저장할 수 있어양.\n"
            "부계정 키를 서브로 저장하거나, 메인 토큰이 실패할 때 쓸 예비 키로 저장해양.\n"
            f"토큰은 암호화해서 저장하고, 화면에는 앞 {NexonTokenVars.TOKEN_PREVIEW_LEN}자리만 보여줘양."
        ),
        color=discord.Color.gold(),
    )
    if not tokens:
        embed.add_field(name="저장된 토큰", value="아직 저장된 토큰이 없어양!", inline=False)
    for token in tokens:
        embed.add_field(
            name=f"{utils.key_index_label(token.key_index)} · `{token.preview}`",
            value=(f"등록: {token.created_at}\n"
                   f"마지막 사용: {token.latest_at}\n"
                   f"누적 호출: {token.call_counts:,}회"),
            inline=False,
        )

    expires_at = utils.get_thread_expires_at(user_id)
    expires_text = f"이 쓰레드는 {expires_at:%H:%M}에 자동으로 삭제돼양. " if expires_at else ""
    embed.set_footer(text=(f"{expires_text}본인과 봇만 볼 수 있는 쓰레드에양 "
                           f"(스레드 관리 권한이 있는 서버 관리자는 볼 수 있어양)"))
    return embed


def error_message(error: Exception) -> str:
    return find_error_message(error, TOKEN_ERROR_MESSAGES)


async def send_ephemeral(interaction: discord.Interaction, content: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=True)
    else:
        await interaction.response.send_message(content, ephemeral=True)


# ── 화면 구성 ──
class OwnerOnlyView(View):
    """쓰레드를 연 사용자만 누를 수 있는 View"""

    def __init__(self, db: AsyncDBConnector, owner_id: int) -> None:
        super().__init__(timeout=NexonTokenVars.SESSION_TIMEOUT_SEC)
        self.db = db
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await send_ephemeral(interaction, "토큰 관리 화면은 쓰레드를 연 사람만 사용할 수 있어양!")
            return False
        return True


async def close_thread_with_notice(interaction: discord.Interaction, owner_id: int, notice: str) -> None:
    """안내 메시지를 보내고 잠시 뒤 쓰레드를 삭제"""
    await send_ephemeral(interaction, f"{notice}\n{THREAD_CLOSE_DELAY_SEC}초 뒤에 쓰레드를 삭제할게양!")
    await asyncio.sleep(THREAD_CLOSE_DELAY_SEC)
    if isinstance(interaction.channel, discord.Thread):
        await utils.close_private_thread(interaction.channel, owner_id)


class AgreementView(OwnerOnlyView):
    """개인정보 수집 동의 화면"""

    @discord.ui.button(label="동의합니다", style=discord.ButtonStyle.success)
    async def agree_button(self, button: Button, interaction: discord.Interaction) -> None:
        try:
            await utils.agree(self.db, self.owner_id)
            tokens = await utils.list_tokens(self.db, self.owner_id)
        except Exception as e:
            logger.exception(f"[넥슨토큰] agreement failed: {e}")
            await send_ephemeral(interaction, UNKNOWN_ERROR_MESSAGE)
            return

        self.stop()
        manage_view = TokenManageView(self.db, self.owner_id)
        manage_view.sync_buttons(len(tokens))
        await interaction.response.edit_message(
            embed=build_manage_embed(self.owner_id, tokens), view=manage_view)
        manage_view.message = interaction.message

    @discord.ui.button(label="동의하지 않습니다", style=discord.ButtonStyle.secondary)
    async def disagree_button(self, button: Button, interaction: discord.Interaction) -> None:
        self.stop()
        await close_thread_with_notice(
            interaction, self.owner_id, "동의하지 않으면 토큰 저장, 삭제 기능을 사용할 수 없어양.")


class TokenManageView(OwnerOnlyView):
    """토큰 저장, 삭제 화면 (쓰레드에 하나만 띄우고 변경될 때마다 갱신)"""

    def sync_buttons(self, token_count: int) -> None:
        self.register_button.disabled = token_count >= len(NexonTokenVars.KEY_INDEXES)
        self.delete_button.disabled = token_count == 0

    async def refresh(self) -> None:
        tokens = await utils.list_tokens(self.db, self.owner_id)
        self.sync_buttons(len(tokens))
        if self.message:
            await self.message.edit(embed=build_manage_embed(self.owner_id, tokens), view=self)

    @discord.ui.button(label="토큰 저장하기", style=discord.ButtonStyle.primary, emoji="💾")
    async def register_button(self, button: Button, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TokenRegisterModal(self))

    @discord.ui.button(label="토큰 삭제하기", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_button(self, button: Button, interaction: discord.Interaction) -> None:
        try:
            tokens = await utils.list_tokens(self.db, self.owner_id)
        except Exception as e:
            logger.exception(f"[넥슨토큰] token list failed: {e}")
            await send_ephemeral(interaction, UNKNOWN_ERROR_MESSAGE)
            return
        if not tokens:
            await send_ephemeral(interaction, "삭제할 토큰이 없어양!")
            return
        await interaction.response.send_message(
            "삭제할 토큰을 골라주세양! 앞자리와 날짜를 보고 어떤 캐릭터의 키인지 확인해양.",
            view=TokenDeleteView(self, tokens), ephemeral=True)

    @discord.ui.button(label="동의 철회", style=discord.ButtonStyle.secondary, row=1)
    async def withdraw_button(self, button: Button, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "동의를 철회하면 저장된 토큰이 **모두 삭제**되고 쓰레드가 닫혀양. 정말 철회할까양?",
            view=WithdrawConfirmView(self), ephemeral=True)

    @discord.ui.button(label="쓰레드 닫기", style=discord.ButtonStyle.secondary, row=1)
    async def close_button(self, button: Button, interaction: discord.Interaction) -> None:
        self.stop()
        await close_thread_with_notice(interaction, self.owner_id, "토큰 관리를 마쳤어양.")


class TokenRegisterModal(Modal):
    """토큰 입력창 (입력한 토큰은 채팅에 남지 않음)"""

    def __init__(self, panel: TokenManageView) -> None:
        super().__init__(title="넥슨 API 토큰 저장하기", timeout=300)
        self.panel = panel
        self.add_item(InputText(
            label="Nexon Open API 토큰",
            placeholder="넥슨 Open API 사이트에서 복사한 키를 붙여넣어 주세양",
            style=discord.InputTextStyle.short,
            min_length=NexonTokenVars.TOKEN_MIN_LEN,
            max_length=NexonTokenVars.TOKEN_MAX_LEN,
        ))

    async def callback(self, interaction: discord.Interaction) -> None:
        # 토큰 유효성 검사(API 호출)가 3초를 넘길 수 있어서 먼저 응답을 미룸
        await interaction.response.defer(ephemeral=True, invisible=False)
        try:
            key_index = await utils.register_token(
                self.panel.db, self.panel.owner_id, self.children[0].value or "")
        except NexonTokenError as e:
            logger.info(f"[넥슨토큰] register rejected: {type(e).__name__}")
            await interaction.followup.send(error_message(e), ephemeral=True)
            return
        except Exception as e:
            logger.exception(f"[넥슨토큰] register failed: {type(e).__name__}")
            await interaction.followup.send(UNKNOWN_ERROR_MESSAGE, ephemeral=True)
            return

        await interaction.followup.send(
            f"토큰을 **{utils.key_index_label(key_index)}** 토큰으로 저장했어양!", ephemeral=True)
        await self.panel.refresh()


class TokenDeleteSelect(Select):
    def __init__(self, tokens: list[utils.TokenSummary]) -> None:
        options = [
            discord.SelectOption(
                label=f"{utils.key_index_label(t.key_index)} · {t.preview}",
                description=f"등록 {t.created_at} · 마지막 사용 {t.latest_at} · {t.call_counts:,}회"[:100],
                value=t.key_index,
            )
            for t in tokens
        ]
        super().__init__(placeholder="삭제할 토큰을 선택하세양", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        view: TokenDeleteView = self.view
        key_index = self.values[0]
        try:
            await utils.remove_token(view.panel.db, view.panel.owner_id, key_index)
        except NexonTokenError as e:
            await interaction.response.edit_message(content=error_message(e), view=None)
            return
        except Exception as e:
            logger.exception(f"[넥슨토큰] delete failed: {e}")
            await interaction.response.edit_message(content=UNKNOWN_ERROR_MESSAGE, view=None)
            return

        view.stop()
        notice = f"**{utils.key_index_label(key_index)}** 토큰을 삭제했어양!"
        if key_index == "main":
            notice += " 서브 토큰이 있었다면 메인 토큰으로 바뀌었어양."
        await interaction.response.edit_message(content=notice, view=None)
        await view.panel.refresh()


class TokenDeleteView(View):
    def __init__(self, panel: TokenManageView, tokens: list[utils.TokenSummary]) -> None:
        super().__init__(timeout=120)
        self.panel = panel
        self.add_item(TokenDeleteSelect(tokens))


class WithdrawConfirmView(View):
    def __init__(self, panel: TokenManageView) -> None:
        super().__init__(timeout=60)
        self.panel = panel

    @discord.ui.button(label="동의 철회하기", style=discord.ButtonStyle.danger)
    async def confirm_button(self, button: Button, interaction: discord.Interaction) -> None:
        self.stop()
        try:
            deleted_count = await utils.withdraw_agreement(self.panel.db, self.panel.owner_id)
        except Exception as e:
            logger.exception(f"[넥슨토큰] withdraw failed: {e}")
            await interaction.response.edit_message(content=UNKNOWN_ERROR_MESSAGE, view=None)
            return

        self.panel.stop()
        await interaction.response.edit_message(
            content=f"동의를 철회하고 저장된 토큰 {deleted_count}개를 삭제했어양.", view=None)
        await close_thread_with_notice(interaction, self.panel.owner_id, "다음에 다시 동의하면 사용할 수 있어양.")


# ── 명령어 ──
@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 넥슨토큰")
async def nexon_token_manage(ctx: commands.Context[BumKkiBot]) -> None:
    """사용자의 Nexon API 토큰을 관리하는 비공개 쓰레드를 여는 명령어 (2026-10-05, Opus 5.5)

    Args:
        ctx (commands.Context): "븜 넥슨토큰" 디스코드 메세지

    Raises:
        CommandFailure: 서버 밖에서 사용, DB 또는 암호화 키 없음, 쓰레드 생성 실패

    Note:
        - 쓰레드는 사용자와 봇만 볼 수 있고(스레드 관리 권한이 있는 관리자 제외) 30분 뒤 자동 삭제
        - 봇 권한 필요: 비공개 스레드 만들기, 스레드에서 메시지 보내기, 스레드 관리(삭제)
        - 봇이 재시작되면 삭제 예약이 사라져서, 남은 쓰레드는 60분 뒤 디스코드 자동 보관으로 닫힘
    """
    if ctx.message.author.bot:
        return

    if not ctx.guild:
        await ctx.send("이 명령어는 서버 채널에서만 사용할 수 있어양!")
        raise CommandFailure("Nexon token command used outside guild")

    available, reason = utils.is_token_feature_available(ctx.bot.db)
    if not available:
        if reason == "db":
            await ctx.reply("지금은 데이터베이스에 연결되어 있지 않아서 사용할 수 없어양...")
        else:
            await ctx.reply("토큰 암호화 설정이 되어 있지 않아서 사용할 수 없어양... 봇 관리자에게 문의해주세양")
        raise CommandFailure(f"Nexon token feature unavailable: {reason}")

    db: AsyncDBConnector = ctx.bot.db
    user = ctx.author

    opened_thread_id = utils.get_open_thread_id(user.id)
    if opened_thread_id:
        await ctx.reply(f"이미 열려 있는 토큰 관리 쓰레드가 있어양! <#{opened_thread_id}>")
        return

    try:
        thread = await utils.open_private_thread(
            ctx.channel, user, f"🔐 {user.display_name}님의 넥슨토큰 관리")
    except TokenThreadUnavailable as e:
        await ctx.reply(
            "이 채널에서는 비공개 쓰레드를 만들 수 없어양!\n"
            "일반 텍스트 채널에서 사용하고, 봇에게 `비공개 스레드 만들기`, `스레드 관리` 권한이 있는지 확인해주세양")
        raise CommandFailure(f"Private thread unavailable: {e}")

    if thread is None:
        await ctx.reply("토큰 관리 쓰레드를 만들고 있어양! 잠시만 기다려주세양")
        return

    await ctx.reply(
        f"{thread.mention} 쓰레드를 만들었어양! 본인과 봇만 볼 수 있고 "
        f"{NexonTokenVars.SESSION_TIMEOUT_SEC // 60}분 뒤 자동으로 삭제돼양.")

    try:
        agreed = await utils.has_agreement(db, user.id)
        if agreed:
            tokens = await utils.list_tokens(db, user.id)
            manage_view = TokenManageView(db, user.id)
            manage_view.sync_buttons(len(tokens))
            await thread.send(user.mention, embed=build_manage_embed(user.id, tokens), view=manage_view)
        else:
            await thread.send(user.mention, embed=build_agreement_embed(), view=AgreementView(db, user.id))
    except Exception as e:
        await thread.send(UNKNOWN_ERROR_MESSAGE)
        raise CommandFailure(f"Failed to open token panel: {type(e).__name__}: {e}")
