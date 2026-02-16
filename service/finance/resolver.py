from __future__ import annotations

import asyncio
import time
from typing import Callable, Awaitable, Dict, Optional, Tuple, Any

class AsyncConcurrencyCodeResolver:
    """
    동일한 통화단위, API 중복 호출을 방지하기 위한 동일 통화 요청을 하나로 묶어 처리하는 클래스

    해당 요청 통화단위의 환율정보가 실제로 존재하는지 확인한다.
    """

    def __init__(self,
                 get_rate_func: Callable[[str], Awaitable[Optional[Dict[str, Any]]]],
                 positive_ttl_sec: int = 60,
                 negative_ttl_sec: int = 600
    ):
        self.getter = get_rate_func
        self.pos_ttl = positive_ttl_sec
        self.neg_ttl = negative_ttl_sec

        self._positive_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._negative_cache: Dict[str, float] = {}

        self._inflight: Dict[str, asyncio.Future[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _norm(code: str) -> str:
        """ 통화 코드 정규화 (대분자 변환, 공백 제거)"""
        return code.upper().strip()

    def _get_cache_unlocked(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self._positive_cache.get(key)
        if not entry:
            return None
        ts, data = entry
        if time.time() - ts > self.pos_ttl:
            self._positive_cache.pop(key, None)
            return None
        return data