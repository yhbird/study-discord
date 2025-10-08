from __future__ import annotations
import asyncio
import time
import threading
from typing import Callable, Dict, Optional, Tuple

from exceptions.client_exceptions import NexonAPICharacterNotFound

class CharacterOCIDResolver:
    """get_ocid 함수의 결과를 캐싱, 단일 비행을 얹는 클래스"""

    def __init__(
        self,
        get_ocid_func: Callable[[str], str],
        ttl_sec: int = 3600,
        negative_ttl_sec: int = 60, # '존재하지 않는 캐릭터'
    ):
        self.getter = get_ocid_func
        self.ttl = ttl_sec
        self.negative_ttl = negative_ttl_sec

        # 정상 데이터 캐시: key -> (ts, ocid)
        self._cache: Dict[str, Tuple[float, str]] = {}
        # 존재하지 않는 캐릭터 캐시: key -> ts
        self._negative_cache: Dict[str, float] = {}

        # 단일 비행 잠금: key -> threading.Lock
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock() # _locks 딕셔너리 보호용

    @staticmethod
    def _norm(name: str) -> str:
        """캐릭터 이름 정규화 함수 (소문자 변환 및 공백 제거)"""
        return name.strip()
    
    def _get_lock(self, key: str) -> threading.Lock:
        """특정 키에 대한 잠금 객체를 반환하는 함수"""
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]
        
    def _get_cache(self, key: str) -> Optional[str]:
        entry = self._cache.get(key)
        if not entry:
            return None
        ts, ocid = entry
        if time.time() - ts > self.ttl:
            self._cache.pop(key, None)
            return None
        return ocid
    
    def _set_cache(self, key: str, ocid: str):
        self._cache[key] = (time.time(), ocid)

    def _in_negative_cache(self, key: str) -> bool:
        ts = self._negative_cache.get(key)
        if not ts:
            return False
        if time.time() - ts > self.negative_ttl:
            self._negative_cache.pop(key, None)
            return False
        return True
    
    def _set_negative_cache(self, key: str):
        self._negative_cache[key] = time.time()

    def ocid_resolve(self, character_name: str, *, force_refresh: bool = False) -> str:
        """동기 get_ocid 동일한 호출 방지, TTL 캐싱

        Args:
            character_name (str): 캐릭터 이름
            force_refresh (bool, optional): 캐시 무시 여부. Defaults to False.

        Returns:
            str: OCID
        """
        key = self._norm(character_name)

        if not force_refresh:
            # 부정 캐시 (존재하지 않는 캐릭터) 확인
            if self._in_negative_cache(key):
                raise NexonAPICharacterNotFound("Character not found (cached)")
            
            # 정상 캐시
            cached = self._get_cache(key)
            if cached:
                return cached
            
        # 단일 비행 잠금 획득
        lock = self._get_lock(key)
        with lock:
            if not force_refresh:
                # Lock 획득 후 다시 캐시 확인 (경쟁 상태 대비)
                if self._in_negative_cache(key):
                    raise NexonAPICharacterNotFound("Character not found (cached)")
                cached = self._get_cache(key)
                if cached:
                    return cached
                
            # 실제 OCID 조회
            try:
                ocid = self.getter(character_name)
            except Exception:
                self._set_negative_cache(key)
                raise

            if not ocid:
                self._set_negative_cache(key)
                raise NexonAPICharacterNotFound("Character not found")
            
            self._set_cache(key, ocid)
            return ocid