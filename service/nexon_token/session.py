"""
`븜 넥슨토큰` 쓰레드 세션 저장소 (2026-10-05, Opus 5.5)

사용자당 하나의 토큰 관리 쓰레드만 열리도록 세션을 메모리에 보관한다.
봇이 재시작되면 세션과 쓰레드 삭제 작업이 사라지므로,
남은 쓰레드는 디스코드 자동 보관(60분)으로 닫힌다.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TokenSession:
    user_id: int
    thread_id: int
    expires_at: datetime
    delete_task: asyncio.Task | None = field(default=None, repr=False)


class TokenSessionRegistry:
    """사용자 ID → 토큰 관리 쓰레드 세션"""

    def __init__(self) -> None:
        self._sessions: dict[int, TokenSession] = {}
        self._pending: set[int] = set()  # 쓰레드 생성 중인 사용자 (중복 요청 방지)

    def get(self, user_id: int) -> TokenSession | None:
        return self._sessions.get(user_id)

    def try_reserve(self, user_id: int) -> bool:
        """쓰레드가 없고 생성 중도 아니면 예약하고 True"""
        if user_id in self._sessions or user_id in self._pending:
            return False
        self._pending.add(user_id)
        return True

    def release(self, user_id: int) -> None:
        self._pending.discard(user_id)

    def add(self, session: TokenSession) -> None:
        self._sessions[session.user_id] = session
        self._pending.discard(session.user_id)

    def remove(self, user_id: int, thread_id: int | None = None) -> None:
        """세션 삭제 (thread_id를 주면 같은 쓰레드의 세션일 때만 삭제)"""
        session = self._sessions.get(user_id)
        if session is None:
            return
        if thread_id is not None and session.thread_id != thread_id:
            return
        self._sessions.pop(user_id, None)


token_sessions = TokenSessionRegistry()
