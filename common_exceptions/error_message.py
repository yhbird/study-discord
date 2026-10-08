"""
common_exceptions/error_message.py

예외 → 사용자 안내 메시지 공통 모듈 (2026-10-08, Opus 5.5)

각 서비스의 exceptions.py에 `{예외 클래스: 안내 메시지}` 딕셔너리를 정의한다.
command.py는 except 블록 하나로 안내 메시지 전송과 CommandFailure 발생을 처리한다.

Example:
    ```python
    try:
        ...
    except NexonAPIError as e:
        await handle_command_error(
            ctx, e, NEXON_API_ERROR_MESSAGES,
            default=MapleErrorMessage.BASIC_INFO_NOT_FOUND,
            character_name=character_name)
    ```
"""
from __future__ import annotations

from typing import Mapping

from discord.ext import commands

from common_exceptions.command_exceptions import CommandFailure

ErrorMessageMap = Mapping[type[BaseException], str]

UNKNOWN_ERROR_MESSAGE = "처리 중에 오류가 발생했어양... 잠시 후 다시 시도해주세양"


class _KeepMissing(dict):
    """format_map에서 값을 넘기지 않은 placeholder는 그대로 남김"""
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def find_error_message(error: BaseException, messages: ErrorMessageMap,
                       default: str = UNKNOWN_ERROR_MESSAGE,
                       **fmt: object) -> str:
    """예외에 맞는 안내 메시지를 찾는다

    가장 구체적인 클래스부터 부모 클래스 순서(MRO)로 찾는다.
    하위 예외를 등록하지 않으면 부모 예외의 메시지를 사용한다.
    그래서 except 순서에 영향을 받지 않는다.

    Args:
        error: 발생한 예외
        messages: {예외 클래스: 안내 메시지} 딕셔너리
        default: 등록된 예외가 없을 때 사용할 메시지
        **fmt: 메시지의 {placeholder}에 넣을 값 (예: character_name)
    """
    message = next(
        (messages[cls] for cls in type(error).__mro__ if cls in messages),
        default)
    return message.format_map(_KeepMissing(fmt))


async def handle_command_error(
        ctx: commands.Context, error: BaseException,
        messages: ErrorMessageMap, *,
        default: str = UNKNOWN_ERROR_MESSAGE,
        expected: tuple[type[BaseException], ...] = (),
        reply: bool = False, **fmt: object) -> None:
    """안내 메시지를 보내고 CommandFailure를 발생시킨다

    Args:
        ctx: Discord 명령어 컨텍스트
        error: 발생한 예외
        messages: {예외 클래스: 안내 메시지} 딕셔너리
        default: 등록된 예외가 없을 때 사용할 메시지
        expected: 실패로 기록하지 않을 예외 (예: 없는 캐릭터 검색).
            메시지만 보내고 반환하므로 호출 뒤 return 필요
        reply: True면 ctx.reply, False면 ctx.send로 전송
        **fmt: 메시지의 {placeholder}에 넣을 값

    Raises:
        CommandFailure: expected에 없는 예외
    """
    send = ctx.reply if reply else ctx.send
    await send(find_error_message(error, messages, default, **fmt))
    if isinstance(error, expected):
        return
    raise CommandFailure(f"{type(error).__name__}: {error}") from error
