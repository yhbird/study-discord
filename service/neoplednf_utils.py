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
    dnf_character_equipment: str = "/df/servers/{serverId}/characters/{characterId}/equip/equipment"
    dnf_item: str = f"/df/items"


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

    adv_name : Optional[str] = response_data.get("characterName")
    c_level : Optional[int] = response_data.get("level")
    c_job_name : Optional[str] = response_data.get("jobName")
    c_job_grow : Optional[str] = response_data.get("jobGrowName")
    c_fame : Optional[int] = response_data.get("fame")
    c_guild_name : Optional[str] = response_data.get("guildName")

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


def _get_memorial_option_data(tune: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """아이템 조율 정보에서 '새겨진 볕의 기억' 옵션 데이터 추출

    Args:
        tune (Dict[str, Any]): 아이템 조율 정보

    Returns:
        List[Dict[str, str]]: '새겨진 볕의 기억' 옵션 데이터 리스트
    """
    memorial_options: Dict[str, str] = {}
    memorial_status: List[Dict[str, str]] = tune.get("status", [])
    for option in memorial_status:
        option_name: str = option.get("name")
        option_value: str = option.get("value")
        if option_name and option_value:
            memorial_options[option_name] = option_value
        else:
            return None
    
    return memorial_options


def _get_tune_status_data(tune: Dict[str, Any]) -> Optional[Dict[str, str | int | bool]]:
    """아이템 조율 정보에서 옵션 데이터 추출

    Args:
        tune (Dict[str, Any]): 아이템 조율 정보

    Returns:
        List[Dict[str, str]]: 옵션 데이터 리스트
    """
    tune_level: int = tune.get("level", 0)
    tune_grade: bool = tune.get("upgrade", False)
    tune_setpoint: int = tune.get("setPoint", 0)
    tune_status: List[Dict[str, str]] = tune.get("status", [])
    tune_option: Dict[str, Any] = {
        "tune_level" : tune_level, # 조율 횟수 (1~3)
        "tune_grade" : tune_grade, # 조율 등급 (True: 업그레이드 가능, False: 불가)
        "tune_setpoint" : tune_setpoint, # 조율포함 아이템의 최종 세트포인트
    }
    if tune_status is not None and not tune_status:
        for option in tune_status:
            option_name: str = option.get("name")
            option_value: str = option.get("value")
            if option_name and option_value:
                tune_option[option_name] = option_value
            else:
                continue

    return tune_option


def _get_upgrade_info_data(upgrade_info: Dict[str, str | int]) -> Dict[str, str | int]:
    """115레벨 시즌 방어구/엑세서리/특수장비 융합석 장착 데이터 추출

    Args:
        upgrade_info (Dict[str, str  |  int]): 융합석 정보

    Returns:
        Dict[str, str | int]: 융합석 장착 데이터
    """
    upgrade_item_id: str = upgrade_info.get("itemId", "")
    upgrade_item_name: str = upgrade_info.get("itemName", "")
    upgrade_item_rarity: str = upgrade_info.get("itemRarity", "")
    upgrade_set_item_id: str = upgrade_info.get("setItemId", "")
    upgrade_set_item_name: str = upgrade_info.get("setItemName", "")
    upgrade_set_item_setpoint: int = upgrade_info.get("setPoint", 0)
    return_data: Dict[str, str | int] = {
        "upgrade_item_id": upgrade_item_id,
        "upgrade_item_name": upgrade_item_name,
        "upgrade_item_rarity": upgrade_item_rarity,
        "upgrade_set_item_id": upgrade_set_item_id,
        "upgrade_set_item_name": upgrade_set_item_name,
        "upgrade_set_item_setpoint": upgrade_set_item_setpoint,
    }
    return return_data


def _get_fusion_option_data(fusion_option: Dict[str, Any]) -> Optional[Dict]:
    """115레벨 시즌 방어구/악세서리/특수장비 융합석 옵션 데이터 추출

    Args:
        item (Dict[str, Any]): 아이템 정보

    Returns:
        Optional[Dict]: 융합석 옵션 데이터
    """
    return_data: Dict[str, str | int] = {}
    fusion_options: List[Dict[str, str | int]] = fusion_option.get("options", [])
    if isinstance(fusion_options, list) and fusion_options:
        option = fusion_options[0]
        fusion_buff: int = option.get("buff", 0)
        fusion_dealer_options: str = option.get("explain", "")
        fusion_buffer_options: str = option.get("buffExplain", "")
    
    return_data = {
        "fusion_buff": fusion_buff,
        "fusion_dealer_options": fusion_dealer_options,
        "fusion_buffer_options": fusion_buffer_options,
    }
    return return_data


def _process_set_item_info(set_item_info: List[Dict[str, Any]]) -> Dict[str, Any]:
    """115레벨 시즌 세트장비 정보 처리

    Args:
        set_item_info (List[Dict[str, Any]]): 세트장비 정보 리스트

    Returns:
        Dict[str, Any]: 세트장비 정보
    """
    return_data: Dict[str, Any] = {}
    set_item_info_dict: Dict[str, Any] = set_item_info[0]
    set_item_id: str | Literal["모름"] = set_item_info_dict.get("setItemId") or "모름"
    set_item_name: str | Literal["모름"] = set_item_info_dict.get("setItemName") or "모름"
    set_item_rarity: str | Literal["모름"] = set_item_info_dict.get("setItemRarityName") or "모름"
    active_option: Dict[str, Any] = set_item_info_dict.get("active") or {}

    if isinstance(active_option, dict) and active_option:
        set_item_explain: str = active_option.get("explain") or "모름"
        set_item_explain_detail: str = active_option.get("explainDetail") or "모름"
        set_item_status: List[Dict[str, str|int]] = active_option.get("status") or []
        set_item_setpoint: Dict[str, int] = active_option.get("setPoint") or {}
        min_setpoint: int = set_item_setpoint.get("min") if set_item_setpoint else 0
        max_setpoint: int = set_item_setpoint.get("max") if set_item_setpoint else 0
        current_setpoint: int = set_item_setpoint.get("current") if set_item_setpoint else 0

        return_data = {
            "set_item_id": set_item_id,
            "set_item_name": set_item_name,
            "set_item_rarity": set_item_rarity,
            "set_item_explain": set_item_explain,
            "set_item_explain_detail": set_item_explain_detail,
            "set_item_status": set_item_status,
            "set_item_setpoint": {
                "min": min_setpoint,
                "max": max_setpoint,
                "current": current_setpoint,
            },
        }
    else:
        return_data = {
            "set_item_id": set_item_id,
            "set_item_name": set_item_name,
            "set_item_rarity": set_item_rarity,
            "set_item_explain": "모름",
            "set_item_explain_detail": "모름",
            "set_item_status": [],
            "set_item_setpoint": {
                "min": 0,
                "max": 0,
                "current": 0,
            },
        }
        
    return return_data


def calculate_final_setpoint(stats: Dict[str, int]) -> tuple[str, int]:
    """던전앤파이터 캐릭터의 최종 세트포인트 계산

    Args:
        stats (Dict[str, int]): 세트포인트 정보

    Returns:
        str: 최종 세트포인트 문자열
    """
    
    unique_setname = "고유 장비"
    unique_setpoint = stats.get(unique_setname, 0)
    best_setname = "없음"
    best_setpoint = 0
    for setname, point in stats.items():
        if setname != unique_setname and point > 0:
            total_setpoint = unique_setpoint + point
            if total_setpoint > best_setpoint:
                best_setpoint = total_setpoint
                best_setname = setname
        else:
            continue

    return best_setname, best_setpoint


def check_setpoint_bonus(setpoint: int) -> str:
    """2550pt를 초과한 세트포인트에 70pt 마다 추가 보너스 효과 부여

    Args:
        setpoint (int): 세트포인트

    Returns:
        str: 보너스 효과 문자열
    """
    if setpoint > 2620:
        bonus = (setpoint - 2550) // 70
        return f"{setpoint}pt (+{bonus*70}pt)"
    return f"{setpoint}pt"


async def get_dnf_character_equipment(sid: str, cid: str) -> Dict[str, Dict[str, str | int | Dict | Literal["..."]]]:
    """던전앤파이터 캐릭터의 장비 slot별 장착 아이템 정보 조회
    
    Args:
        sid (str): 던전앤파이터 서버 ID
        cid (str): 던전앤파이터 캐릭터 ID

    Returns:
        List[Dict[str, Any]]: 던전앤파이터 캐릭터 장비 아이템 정보 리스트

    Reference:
        https://developers.neople.co.kr/contents/apiDocs/df 

    Usage:
        - 캐릭터의 장착 아이템 정보 확인
        - 캐릭터의 세트아이템 정보 확인
    """
    service_url = neople_service_url.dnf_character_equipment.format(
        serverId=sid, characterId=cid
    )
    request_url = f"{NEOPLE_API_HOME}{service_url}?apikey={NEOPLE_API_KEY}"
    response_data: dict = await general_request_handler_neople(request_url)

    equipment_list: List[Dict[str, Any]] = response_data.get("equipment", [])
    equipment_data = {}

    # 장착 아이템별 정보 수집
    for item in equipment_list:

        slot_id: Optional[str] = item.get("slotId")
        slot_name: Optional[str] = item.get("slotName")
        item_id: Optional[str] = item.get("itemId")
        item_name: Optional[str] = item.get("itemName")
        item_type: Optional[str] = item.get("itemType")
        item_type_detail: Optional[str] = item.get("itemTypeDetail")
        item_available_level: Optional[int] = item.get("itemAvailableLevel")
        item_rarity: Optional[str] = item.get("itemRarity")
        set_item_id: Optional[str] = item.get("setItemId")
        set_item_name: Optional[str] = item.get("setItemName")
        item_reinforce: Optional[int] = item.get("reinforce") # 강화/증폭 수치
        if item.get("amplificationName") is None:
            item_reinforce_type = "강화"
        else:
            item_reinforce_type = "증폭"
        item_grade_name: Optional[str] = item.get("itemGradeName")
        enchant_info: Optional[Dict[str, Any]] = item.get("enchant", {})
        item_refine = item.get("refine", 0) # 제련 수치
        item_fusion_option: Optional[Dict[str, Any]] = item.get("fusionOption") # 융합석 효과
        if isinstance(item_fusion_option, dict) and item_fusion_option:
            fusion_options: Optional[Dict] = _get_fusion_option_data(item_fusion_option)
        else:
            fusion_options = {}
        item_tune_info: List[Dict[str, Any]] = item.get("tune") # 조율 정보
        upgrade_info: Dict[str, str | int] = item.get("upgradeInfo")
        memorial_options: Optional[List[Dict[str, str]]] = []
        tune_level = 0
        tune_setpoint = 0
        fusion_setpoint = 0
        tune_options: Optional[Dict[str, str | int | bool]] = {}

        if isinstance(item_tune_info, list) and item_tune_info:
            for tune in item_tune_info:
                # 조율 정보 수집 
                if tune.get("level") is not None and slot_id != "WEAPON":
                    tune_options = _get_tune_status_data(tune)
                    print(tune_options)
                    tune_level = tune_options.get("tune_level", 0)
                    tune_setpoint = tune_options.get("tune_setpoint", 0)

                # "새겨진 볕의 기억" 정보 수집
                elif tune.get("name") == "새겨진 볕의 기억" and slot_id == "WEAPON":
                    memorial_options = _get_memorial_option_data(tune)

                else:
                    continue


        if isinstance(upgrade_info, dict) and upgrade_info:
            # 융합석 정보 수집
            upgrade_data: Dict[str, str | int] = _get_upgrade_info_data(upgrade_info)
        else:
            upgrade_data = {}

        # 최종 세트포인트 계산
        final_setpoint: int = 0
        if isinstance(tune_options, dict) and tune_options:
            tune_setpoint = tune_options.get("tune_setpoint", 0)
            final_setpoint += tune_setpoint
        if isinstance(upgrade_data, dict) and upgrade_data:
            fusion_setpoint = upgrade_data.get("upgrade_set_item_setpoint", 0)
            final_setpoint += fusion_setpoint

        item_data: Dict[str, str | int | Dict | Literal["..."]] = {
            "slot_id": slot_id or "몰라양",
            "slot_name": slot_name or "몰라양",
            "item_id": item_id or "몰라양",
            "tune_level": tune_level or 0,
            "item_name": item_name or "몰라양",
            "item_type": item_type or "몰라양",
            "item_type_detail": item_type_detail or "몰라양",
            "item_available_level": item_available_level or 0,
            "item_rarity": item_rarity or "몰라양",
            "set_item_id": set_item_id or "없음",
            "set_item_name": set_item_name or "없음",
            "item_reinforce": item_reinforce or 0,
            "item_reinforce_type": item_reinforce_type or "강화",
            "item_grade_name": item_grade_name or "몰라양",
            "item_enchant_info": enchant_info or {},
            "item_refine": item_refine or 0,
            "tune_options": tune_options or {},
            "memorial_options": memorial_options or [],
            "upgrade_info": upgrade_data or {},
            "fusion_options": fusion_options or {},
            "fusion_setpoint": fusion_setpoint or 0,
            "tune_setpoint": tune_setpoint or 0,
            "final_setpoint": final_setpoint,
        }
        equipment_data[slot_name] = item_data

    # 세트아이템 정보 수집
    set_item_info_raw: List[Dict[str, Any]] = response_data.get("setItemInfo", [])
    set_item_info = _process_set_item_info(set_item_info_raw) if set_item_info_raw else {}
    equipment_data["set_item_info"] = set_item_info or {}

    return equipment_data


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