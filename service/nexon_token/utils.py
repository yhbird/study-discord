"""
`븜 넥슨토큰` 데이터 처리 모듈 (2026-10-05, Opus 5.5)

- 개인정보 수집 동의 확인, 등록, 철회
- Nexon API 토큰 암호화(Fernet), 유효성 검사, 저장, 삭제, 목록 조회
- 비공개 쓰레드 생성과 30분 뒤 자동 삭제

command.py는 이 모듈의 함수만 호출하고, DB나 암호화 방식은 알지 않는다.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

import discord
from cryptography.fernet import Fernet, InvalidToken
from pytz import timezone

from bot_logger import logger
from common.dbconnector import AsyncDBConnector
from common.time import kst_format_now
from common_exceptions.client_exceptions import (
    NexonAPIBadRequest, NexonAPIError, NexonAPIForbidden)
from config import NEXON_TOKEN_ENC_KEY
from service.maplestory.utils import general_request_handler_nexon
from service.nexon_token.consts import NexonTokenUrls, NexonTokenVars
from service.nexon_token.exceptions import (
    TokenAgreementRequired, TokenDuplicated, TokenEncryptionUnavailable,
    TokenFormatInvalid, TokenInvalid, TokenLimitExceeded, TokenNotFound,
    TokenThreadUnavailable, TokenValidationFailed)
from service.nexon_token.session import TokenSession, token_sessions

KST = timezone("Asia/Seoul")
_cipher: Fernet | None = None


@dataclass(frozen=True)
class TokenSummary:
    """토큰 목록 표시용 정보 (토큰 원문은 포함하지 않음)"""
    key_index: str
    preview: str
    created_at: str
    latest_at: str
    call_counts: int


# ── 암호화 ──
def _get_cipher() -> Fernet:
    """Fernet 객체를 한 번만 만들어서 재사용"""
    global _cipher
    if _cipher is None:
        if not NEXON_TOKEN_ENC_KEY:
            raise TokenEncryptionUnavailable("NEXON_TOKEN_ENC_KEY not set")
        try:
            _cipher = Fernet(NEXON_TOKEN_ENC_KEY.encode())
        except (ValueError, TypeError) as e:
            raise TokenEncryptionUnavailable(f"NEXON_TOKEN_ENC_KEY invalid: {e}")
    return _cipher


def is_token_feature_available(db: AsyncDBConnector | None) -> tuple[bool, str]:
    """기능 사용 가능 여부와 불가능한 이유 ("db", "encryption")를 반환"""
    if not db or not db.is_available():
        return False, "db"
    try:
        _get_cipher()
    except TokenEncryptionUnavailable:
        return False, "encryption"
    return True, ""


def _encrypt_token(token: str) -> str:
    return _get_cipher().encrypt(token.encode()).decode()


def _decrypt_token(encrypted_token: str) -> str | None:
    """복호화 실패시 None (암호화 키가 바뀐 경우)"""
    try:
        return _get_cipher().decrypt(encrypted_token.encode()).decode()
    except InvalidToken:
        return None


# ── 전처리 ──
def _normalize_token(raw_token: str) -> str:
    """복사, 붙여넣기 과정에서 섞인 공백과 따옴표를 제거하고 형식을 확인"""
    token = raw_token.strip().strip("\"'`")
    if not (NexonTokenVars.TOKEN_MIN_LEN <= len(token) <= NexonTokenVars.TOKEN_MAX_LEN):
        raise TokenFormatInvalid(f"token length {len(token)}")
    if not token.isascii() or any(c.isspace() for c in token):
        raise TokenFormatInvalid("token contains invalid characters")
    return token


def _mask_token(token: str | None) -> str:
    if token is None:
        return "(복호화 실패)"
    return f"{token[:NexonTokenVars.TOKEN_PREVIEW_LEN]}…"


def _format_kst(value: datetime | None) -> str:
    if value is None:
        return "사용 기록 없음"
    return value.astimezone(KST).strftime("%Y-%m-%d %H:%M")


def key_index_label(key_index: str) -> str:
    return NexonTokenVars.KEY_INDEX_LABEL.get(key_index, key_index)


# ── 수집 동의 ──
async def has_agreement(db: AsyncDBConnector, discord_id: int) -> bool:
    record = await db.get_active_agreement(discord_id, NexonTokenVars.SERVICE_CODE)
    return record is not None


async def agree(db: AsyncDBConnector, discord_id: int) -> None:
    await db.insert_agreement(discord_id, NexonTokenVars.SERVICE_CODE, NexonTokenVars.POLICY_VERSION)


async def withdraw_agreement(db: AsyncDBConnector, discord_id: int) -> int:
    """동의를 철회하고 저장된 토큰을 모두 삭제, 삭제한 토큰 개수를 반환"""
    return await db.withdraw_nexon_token_agreement(discord_id, NexonTokenVars.SERVICE_CODE)


async def _require_agreement(db: AsyncDBConnector, discord_id: int) -> None:
    if not await has_agreement(db, discord_id):
        raise TokenAgreementRequired(f"user {discord_id} has no agreement")


# ── 토큰 관리 ──
async def list_tokens(db: AsyncDBConnector, discord_id: int) -> list[TokenSummary]:
    rows = await db.get_nexon_api_tokens(discord_id)
    return [
        TokenSummary(
            key_index=row["key_index"],
            preview=_mask_token(_decrypt_token(row["api_token"])),
            created_at=_format_kst(row["created_at"]),
            latest_at=_format_kst(row["latest_at"]),
            call_counts=row["call_counts"] or 0,
        )
        for row in rows
    ]


async def _validate_token(token: str) -> None:
    """사용자 토큰으로 Nexon Open API를 호출해서 유효한 토큰인지 확인"""
    yesterday: str = (kst_format_now() - timedelta(days=1)).strftime("%Y-%m-%d")
    request_path = f"{NexonTokenUrls.TOKEN_VALIDATION}?count=10&date={yesterday}"
    try:
        await general_request_handler_nexon(request_path, headers={"x-nxopen-api-key": token})
    except (NexonAPIBadRequest, NexonAPIForbidden) as e:
        raise TokenInvalid(str(e))
    except NexonAPIError as e:
        raise TokenValidationFailed(str(e))
    except Exception as e:
        raise TokenValidationFailed(f"{type(e).__name__}: {e}")


async def register_token(db: AsyncDBConnector, discord_id: int, raw_token: str) -> str:
    """토큰을 검사, 암호화해서 저장하고 저장된 key_index(main, sub)를 반환"""
    await _require_agreement(db, discord_id)
    token = _normalize_token(raw_token)

    rows = await db.get_nexon_api_tokens(discord_id)
    if len(rows) >= len(NexonTokenVars.KEY_INDEXES):
        raise TokenLimitExceeded(f"user {discord_id} already has {len(rows)} tokens")
    if any(_decrypt_token(row["api_token"]) == token for row in rows):
        raise TokenDuplicated(f"user {discord_id} duplicated token")

    await _validate_token(token)

    key_index = await db.insert_nexon_api_token(discord_id, _encrypt_token(token))
    if key_index is None:
        raise TokenLimitExceeded(f"user {discord_id} has no empty key_index")
    return key_index


async def remove_token(db: AsyncDBConnector, discord_id: int, key_index: str) -> None:
    await _require_agreement(db, discord_id)
    if not await db.delete_nexon_api_token(discord_id, key_index):
        raise TokenNotFound(f"user {discord_id} has no {key_index} token")


# ── 비공개 쓰레드 ──
def get_open_thread_id(user_id: int) -> int | None:
    """사용자에게 열려 있는 토큰 관리 쓰레드 ID (없으면 None)"""
    session = token_sessions.get(user_id)
    return session.thread_id if session else None


def get_thread_expires_at(user_id: int) -> datetime | None:
    """토큰 관리 쓰레드가 자동 삭제되는 시각 (KST)"""
    session = token_sessions.get(user_id)
    return session.expires_at if session else None


async def open_private_thread(channel: discord.abc.Messageable, user: discord.abc.User,
                              thread_name: str) -> discord.Thread | None:
    """사용자와 봇만 볼 수 있는 비공개 쓰레드를 만들고, 30분 뒤 삭제를 예약

    Returns:
        discord.Thread | None: 만든 쓰레드 (이미 열려 있거나 생성 중이면 None)
    """
    if not isinstance(channel, discord.TextChannel):
        raise TokenThreadUnavailable(f"channel type {type(channel).__name__} not supported")
    if not token_sessions.try_reserve(user.id):
        return None

    thread: discord.Thread | None = None
    try:
        thread = await channel.create_thread(
            name=thread_name[:100],
            type=discord.ChannelType.private_thread,
            auto_archive_duration=NexonTokenVars.THREAD_AUTO_ARCHIVE_MIN,
            invitable=False,
        )
        await thread.add_user(user)
    except discord.HTTPException as e:
        token_sessions.release(user.id)
        if thread is not None:  # 쓰레드는 만들었지만 사용자 추가에 실패한 경우
            try:
                await thread.delete()
            except discord.HTTPException:
                pass
        raise TokenThreadUnavailable(f"failed to open private thread ({type(e).__name__}): {e}")

    expires_at = kst_format_now() + timedelta(seconds=NexonTokenVars.SESSION_TIMEOUT_SEC)
    session = TokenSession(user_id=user.id, thread_id=thread.id, expires_at=expires_at)
    session.delete_task = asyncio.create_task(
        _delete_thread_later(thread, user.id, NexonTokenVars.SESSION_TIMEOUT_SEC))
    token_sessions.add(session)
    return thread


async def close_private_thread(thread: discord.Thread, user_id: int) -> None:
    """쓰레드를 바로 삭제하고 세션을 정리 (삭제 권한이 없으면 보관 + 잠금)"""
    session = token_sessions.get(user_id)
    if session and session.thread_id == thread.id and session.delete_task \
            and session.delete_task is not asyncio.current_task():
        session.delete_task.cancel()
    token_sessions.remove(user_id, thread.id)

    try:
        await thread.delete()
    except discord.NotFound:
        pass
    except discord.Forbidden:
        try:
            await thread.edit(archived=True, locked=True)
        except discord.HTTPException as e:
            logger.warning(f"Failed to archive token thread {thread.id}: {e}")
    except discord.HTTPException as e:
        logger.warning(f"Failed to delete token thread {thread.id}: {e}")


async def _delete_thread_later(thread: discord.Thread, user_id: int, delay_sec: int) -> None:
    try:
        await asyncio.sleep(delay_sec)
    except asyncio.CancelledError:
        return
    await close_private_thread(thread, user_id)
