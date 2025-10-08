from __future__ import annotations

import io
import asyncio
import time
import json
import httpx

from urllib.parse import quote
from collections import deque
from datetime import datetime, timedelta
from pytz import timezone

from typing import Optional, Dict, List, Any, Literal
from config import NEOPLE_API_HOME, NEOPLE_API_KEY
from config import NEOPLE_API_RPS_LIMIT
from utils.image import get_image_bytes
from exceptions.client_exceptions import *


class neople_service_url:
    dnf_servers: str = "/df/servers"
    dnf_character: str = "/df/servers/{serverId}/characters"
    dnf_character_info: str = "/df/servers/{serverId}/characters/{characterId}"
    dnf_timeline: str = "/df/servers/{serverId}/characters/{characterId}/timeline"
    dnf_character_image: str =  "https://img-api.neople.co.kr/df/servers/{sid}/characters/{cid}?zoom=1"


class dnf_timeline_codes:
    clear_raid : int = 201 # 레이드 클리어
    clear_region : int = 209 # 레기온 클리어
    item_upgrade: int = 402 # 아이템 강화/증폭/제련
    reward_pot_and_box: int = 504 # 항아리&상자 보상
    reward_clear_raid_card: int = 507 # 레이드 클리어 카드 보상
    upgrade_stone: int = 511 # 융합석 업글레이드
    reward_clear_dungeon_card: int = 513 # 던전 카드 보상


class neople_api_limiter:
    def __init__(self, max_calls: int = NEOPLE_API_RPS_LIMIT, period: float = 1.0):
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self._lock = asyncio.Lock()

    async def acquire(self):
        while True:
            async with self._lock:
                now = time.monotonic()
                while self.calls and (now - self.calls[0]) >= self.period:
                    self.calls.popleft()
                
                if len(self.calls) < self.max_calls:
                    self.calls.append(now)
                    return
                
                wait = self.period - (now - self.calls[0])
                await asyncio.sleep(wait)


_httpx_client: Optional[httpx.AsyncClient] = None
_api_rate_limiter: Dict[str, neople_api_limiter] = {
    NEOPLE_API_KEY: neople_api_limiter(max_calls=NEOPLE_API_RPS_LIMIT, period=1.0)
}


async def _rate_limit_request(request: httpx.Request):
    api_key = request.headers.get("apikey")
    limiter = _api_rate_limiter.get(api_key) or neople_api_limiter(max_calls=NEOPLE_API_RPS_LIMIT, period=1.0)
    await limiter.acquire()


def get_httpx_client() -> httpx.AsyncClient:
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(
            base_url = f"{NEOPLE_API_HOME}",
            timeout = httpx.Timeout(10.0, connect=5.0),
            event_hooks = {
                "request": [_rate_limit_request],
            },
            headers={
                "apikey": f"{NEOPLE_API_KEY}",
            }
        )
    return _httpx_client


async def general_request_handler_neople(request_path: str, headers: Optional[dict] = None) -> dict:
    """Neople API의 일반적인 비동기 요청을 처리하는 함수

    Args:
        request_path (str): 요청할 경로 (base_url 제외)
        headers (Optional[dict], optional): 요청 헤더 (기본값 None)

    Returns:
        dict: 응답 데이터

    Raises:
        Exception: 요청 오류에 대한 예외를 발생

    Reference:
        https://developers.neople.co.kr/contents/guide/pages/all  
        Neople API의 경우 response_status마다 세부적인 error_code가 존재
    """
    client = get_httpx_client()

    request_headers = dict(client.headers)
    if headers:
        request_headers.update(headers)

    response: httpx.Response = await client.get(url=request_path, headers=request_headers)

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        try:
            wait_time = int(retry_after) if retry_after else 1
        except ValueError:
            wait_time = 1
        await asyncio.sleep(wait_time)
        response = await client.get(url=request_path, headers=request_headers)

    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError as e:
            return {"raw": response.text, "status": response.status_code}
        
    neople_api_error_handler(response)


async def get_dnf_server_id(server_name: str) -> str:
    """네오플 API 연동하여 dnf 서버 name - code 변환

    Args:
        server_name (str): dnf 서버 이름 (한글)

    Returns:
        str: dnf 서버 코드 (쿼리에 사용할 영어명)

    Reference:
        https://developers.neople.co.kr/contents/apiDocs/df
    """
    service_url = neople_service_url.dnf_servers
    request_url = f"{NEOPLE_API_HOME}{service_url}?apikey={NEOPLE_API_KEY}"
    response_data: dict = await general_request_handler_neople(request_url)
    
    search_server_name = server_name.strip()
    return_server_id: str = ""
    dnf_server_list: List[dict] = response_data.get("rows", [])

    # ServerId 조회
    if dnf_server_list:
        dnf_server_dict: dict = {}
        for server in dnf_server_list:
            server_name_kr = server.get("serverName", "")
            server_name_en = server.get("serverId", "")
            dnf_server_dict[server_name_kr] = server_name_en
        return_server_id = dnf_server_dict.get(search_server_name, "")
    else:
        raise DNFServerNotFound(f"던전앤파이터 서버 정보를 찾을 수 없어양")

    # ServerId 조회를 못한 경우
    if return_server_id == "":
        raise DNFServerNotFound(f"던파에 {search_server_name} 서버가 없어양")

    return return_server_id


async def get_dnf_character_id(server_name: str, character_name: str) -> str:
    """던전앤파이터 캐릭터의 고유 ID를 가져오는 함수

    Args:
        server_name (str): 서버 이름
        character_name (str): 캐릭터 이름

    Returns:
        str: 캐릭터 코드

    Raises:
        NeopleAPIError: API 호출 오류
    """
    server_id = await get_dnf_server_id(server_name)
    character_name_encode = quote(character_name.strip())
    service_url = neople_service_url.dnf_character.format(serverId=server_id)
    request_url = f"{NEOPLE_API_HOME}{service_url}?characterName={character_name_encode}&apikey={NEOPLE_API_KEY}"
    response_data: dict = await general_request_handler_neople(request_url)
    character_list: List[dict] = response_data.get("rows", [])
    character_info = character_list[0] if character_list else None
    if character_info:
        cid: str = character_info.get("characterId", "")
        if cid:
            return cid
        else:
            raise DNFCIDNotFound(f"모험가 정보를 찾는데 실패했어양...")
    else:
        raise DNFCharacterNotFound(f"{server_name}서버 {character_name}모험가 정보를 찾을 수 없어양")


async def get_dnf_character_info(sid: str, cid: str) -> Dict[str, Any]:
    """던전앤파이터 캐릭터의 기본 정보 조회
    
    Args:
        sid (str): 던전앤파이터 서버 ID
        cid (str): 던전앤파이터 캐릭터 ID

    Returns:
        dict: 던전앤파이터 캐릭터 기본 정보

    Reference:
        https://developers.neople.co.kr/contents/apiDocs/df    
    """
    service_url = neople_service_url.dnf_character_info.format(
        serverId=sid, characterId=cid
    )
    request_url = f"{NEOPLE_API_HOME}{service_url}?apikey={NEOPLE_API_KEY}"
    response_data: dict = await general_request_handler_neople(request_url)

    adv_name : str | None = response_data.get("characterName")
    c_level : int | None = response_data.get("level")
    c_job_name : str | None = response_data.get("jobName")
    c_job_grow : str | None = response_data.get("jobGrowName")
    c_fame : int | None = response_data.get("fame")
    c_guild_name : str | None = response_data.get("guildName")

    return_data = {
        "adventure_name": adv_name or "몰라양",
        "level": c_level or 0,
        "job_name": c_job_name or "모름",
        "job_grow": c_job_grow or "모름",
        "fame": c_fame or 0,
        "guild_name": c_guild_name or "길드가 없어양!",

    }
    return return_data

async def get_dnf_character_image(sid: str, cid: str) -> io.BytesIO:
    """던전앤파이터 캐릭터의 프로필 이미지 URL 조회

    Args:
        sid (str): 던전앤파이터 서버 ID
        cid (str): 던전앤파이터 캐릭터 ID

    Returns:
        str: 던전앤파이터 캐릭터 프로필 이미지 URL

    Reference:
        https://developers.neople.co.kr/contents/apiDocs/df    
    """
    c_image_url = neople_service_url.dnf_character_image.format(sid=sid, cid=cid)
    image_bytes: io.BytesIO = get_image_bytes(c_image_url)
    return image_bytes


async def get_dnf_weekly_timeline(sid: str, cid: str) -> Dict[str, Any]:
    """던전앤파이터 캐릭터의 주간 타임라인 정보 조회

    Args:
        server_name (str): dnf 서버 이름 (한글)
        character_name (str): dnf 캐릭터 이름 (한글)

    Returns:
        dict: 던전앤파이터 캐릭터 타임라인 정보

    Notes:
        수집할 타임라인 정보
        - 획득한 아이템
        - 클리어한 던전/레이드/레기온
        - 강화/증폭/제련 성공 및 내역
        타임라인 범위: 지난주 목요일 6시 부터 ~ 현재시간 까지
    """
    # 목요일 6시 부터 ~ 현재시간 까지 범위 설정
    now_kst: datetime = datetime.now(tz=timezone("Asia/Seoul"))
    if now_kst.weekday() == 3 and now_kst.hour < 6:
        # 오늘이 목요일인데, 6시 이전인 경우 -> 지난주 목요일로 설정
        timeline_date_start: datetime = now_kst - timedelta(days=7 + 4)  # 지난주 목요일
    elif now_kst.weekday() == 3 and now_kst.hour >= 6:
        # 오늘이 목요일이고, 6시 이후인 경우 -> 오늘 목요일로 설정
        timeline_date_start: datetime = now_kst
    elif now_kst.weekday() < 3:
        # 오늘이 월,화,수 인 경우 -> 지난주 목요일로 설정
        timeline_date_start: datetime = now_kst - timedelta(days=now_kst.weekday() + 4)  # 지난주 목요일
    else:
        # 오늘이 금,토,일 인 경우 -> 이번주 목요일로 설정
        timeline_date_start: datetime = now_kst - timedelta(days=now_kst.weekday() - 3)  # 이번주 목요일
    timeline_date_end: datetime = now_kst

    # 타임라인 조회 쿼리 생성
    start_date_str: str = timeline_date_start.strftime("%Y%m%dT0600")
    end_date_str: str = timeline_date_end.strftime("%Y%m%dT%H%M")
    timeline_date_query: str = f"&startDate={start_date_str}&endDate={end_date_str}"

    # 타임라인 조회 (API 호출)
    service_url = neople_service_url.dnf_timeline.format(serverId=sid, characterId=cid)
    request_url = f"{NEOPLE_API_HOME}{service_url}?limit=100{timeline_date_query}&apikey={NEOPLE_API_KEY}"
    response_data: dict = await general_request_handler_neople(request_url)

    # 타임라인 데이터 반환
    return response_data


def dnf_get_clear_flag(flag: bool, clear_date: Optional[str] = None) -> str:
    """클리어 여부 및 클리어 날짜 반환

    Args:
        flag (bool): 클리어 여부
        clear_date (str): 클리어 시간 (YYYY-MM-DD HH:MM 형식)

    Returns:
        str: 클리어 여부 및 날짜 문자열
    """
    if flag:
        if clear_date is None:
            return f"✅ 완료"
        else:
            return f"✅ 완료 ({clear_date})"
    else:
        return "❌ 미완료"
    

def dnf_convert_grade_text(grade: str) -> str:
    """던전앤파이터 아이템 한글 등급을 이모지로 변환

    Args:
        grade (str): 아이템 등급 (한글)

    Returns:
        str: 아이템 등급 (둥그라미 이모티콘)
    """
    grade_mapping: Dict[str, str] = {
        "태초" : "🟢",
        "신화" : "🟢",
        "에픽" : "🟡",
        "레전더리" : "🟠",
        "유니크" : "🟣",
        "크로니클" : "🔴",
        "언커먼" : "🔵",
        "커먼" : "⚪",
    }
    return grade_mapping.get(grade.lower(), grade)