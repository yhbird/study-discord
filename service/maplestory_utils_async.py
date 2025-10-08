from __future__ import annotations

import requests
import asyncio
import hashlib
import random
import httpx
import math
import time
import json
import re

from urllib.parse import quote
from collections import deque
from datetime import datetime, timedelta
from pytz import timezone

from config import NEXON_API_KEY, NEXON_API_HOME # Nexon Open API
from config import NEXON_API_RPS_LIMIT # Nexon Open API Rate Limit 방지용 시간 간격
from data.json.fortune_message_table import fortune_message_table_raw

from typing import Literal, Optional, Dict, List, Tuple, Any

from exceptions.client_exceptions import *
from utils.time import parse_iso_string

_httpx_client: Optional[httpx.AsyncClient] = None


class maplestory_service_url:
    ocid : str = "/maplestory/v1/id"
    pop : str = "/maplestory/v1/character/popularity"
    ability : str = "/maplestory/v1/character/ability"
    notice : str = "/maplestory/v1/notice-event"
    notice_detail : str = "/maplestory/v1/notice-event/detail"
    basic_info: str = "/maplestory/v1/character/basic"
    stat_info: str = "/maplestory/v1/character/stat"
    cash_equipment: str = "/maplestory/v1/character/cashitem-equipment"
    beauty_equipment: str = "/maplestory/v1/character/beauty-equipment"


class APIRateLimiter:
    def __init__(self, max_calls: int = NEXON_API_RPS_LIMIT, period: float = 1.0):
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

api_rate_limiter: Dict[str, APIRateLimiter] = {
    NEXON_API_KEY : APIRateLimiter(max_calls=NEXON_API_RPS_LIMIT, period=1.0)
}


async def _rate_limit_request(request: httpx.Request):
    api_key = request.headers.get("x-nxopen-api-key")
    limiter = api_rate_limiter.get(api_key) or APIRateLimiter(max_calls=NEXON_API_RPS_LIMIT, period=1.0)
    await limiter.acquire()


def _raise_nexon_api_error(response: httpx.Response):
    status = response.status_code
    msg = None
    try:
        payload = response.json()
        error = payload.get("error") if isinstance(payload, dict) else None
        msg = (error or {}).get("message")
    except Exception:
        msg = response.text.strip()

    prefix = f"{status} : "
    if status == 400:
        raise NexonAPIBadRequest(f"{prefix}{msg or 'Bad Request'}")
    elif status == 403:
        raise NexonAPIForbidden(f"{prefix}{msg or 'Forbidden'}")
    elif status == 429:
        raise NexonAPITooManyRequests(f"{prefix}{msg or 'Too Many Requests'}")
    elif status == 500:
        raise NexonAPIServiceUnavailable(f"{prefix}{msg or 'Internal Server Error'}")
    else:
        raise NexonAPIError(f"{prefix}{msg or 'Unknown Error'}")


def get_httpx_client() -> httpx.AsyncClient:
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(
            base_url=f"{NEXON_API_HOME}",
            timeout=httpx.Timeout(10.0, connect=5.0),
            event_hooks={"request": [_rate_limit_request]},
            headers={"x-nxopen-api-key": NEXON_API_KEY}
        )
    return _httpx_client


async def general_request_handler_nexon_async(request_path: str, headers: Optional[dict] = None) -> dict:
    """Nexon Open API의 일반적인 요청을 처리하는 비동기 함수(v2)

    Args:
        request_path (str): 요청할 경로
        headers (Optional[dict], optional): 요청 헤더. Defaults to None.

    Returns:
        dict: 응답 데이터
    """
    client = get_httpx_client()

    request_headers = dict(client.headers)
    if headers:
        request_headers.update(headers)

    response = await client.get(request_path, headers=request_headers)

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        try:
            wait_time = int(retry_after) if retry_after else 1
        except ValueError:
            wait_time = 1
        await asyncio.sleep(wait_time)
        response = await client.get(request_path, headers=request_headers)

    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError as e:
            return {"raw": response.text, "status": response.status_code}

    _raise_nexon_api_error(response)


async def get_ocid_async(character_name: str) -> str:
    """character_name의 OCID를 비동기적으로 검색

    Args:
        character_name (str): 캐릭터 이름

    Returns:
        str: OCID (string)

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14

    Raises:
        Reference에 있는 URL 참조
        (예외처리는 함수 밖에서 처리)
    """
    service_url = maplestory_service_url.ocid
    url_encode_name: str = quote(character_name)
    request_url = f"{NEXON_API_HOME}{service_url}?character_name={url_encode_name}"
    try:
        response_data: dict = await general_request_handler_nexon_async(request_url)
    except NexonAPIBadRequest as e:
        raise NexonAPICharacterNotFound("Character not found") from e

    # 정상적으로 OCID를 찾았을 때
    ocid: str = str(response_data.get('ocid'))
    if ocid:
        return ocid
    else:
        raise NexonAPICharacterNotFound("OCID not found in response")
    

async def get_popularity(ocid: str) -> str:
    """OCID에 해당하는 캐릭터의 인기도를 가져오는 함수

    Args:
        ocid (str): 캐릭터 OCID

    Returns:
        str: 캐릭터의 인기도

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    service_url = maplestory_service_url.pop
    request_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}"
    try:
        response_data: dict = await general_request_handler_nexon_async(request_url)
        popularity: int = response_data.get('popularity', "몰라양")
        return popularity
    except NexonAPIError:
        return "몰라양"  # 예외 발생 시 기본값으로 "몰라양" 반환
    

async def get_ability_info_async(ocid: str) -> dict:
    """OCID에 해당하는 캐릭터의 어빌리티 정보를 비동기적으로 가져오는 함수

    Args:
        ocid (str): 캐릭터 OCID

    Returns:
        dict: 캐릭터의 어빌리티 정보
    """
    service_url = maplestory_service_url.ability
    request_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}"
    response_data: dict = await general_request_handler_nexon_async(request_url)
    return response_data


def _compile_patterns():
    compiled = []
    for pat, grade_map in ABILITY_MAX_TABLE.items():
        rx = pat.replace("{n}", r"(?P<value>\d+(?:\,\d+)?)")
        rx = rf"^\s*(?P<head>{rx})\s*$"
        compiled.append((re.compile(rx), grade_map))
    return compiled


# 어빌리티 최대값 테이블 작성
# 등장하지 않는 등급의 경우 -1으로 입력
ABILITY_MAX_TABLE: Dict[str, Dict[str, int]] = {
    r"STR\s{n}\s증가": {"레전드리": 40, "유니크": 30, "에픽": 20, "레어": 10},
    r"DEX\s{n}\s증가": {"레전드리": 40, "유니크": 30, "에픽": 20, "레어": 10},
    r"INT\s{n}\s증가": {"레전드리": 40, "유니크": 30, "에픽": 20, "레어": 10},
    r"LUK\s{n}\s증가": {"레전드리": 40, "유니크": 30, "에픽": 20, "레어": 10},
    r"모든\s능력치\s{n}\s증가": {"레전드리": 40, "유니크": 30, "에픽": 20, "레어": 10},
    r"AP를\s직접\s투자한\sSTR의\s{n}%\s만큼\sDEX\s증가": {"레전드리": 10, "유니크": 8, "에픽": 5, "레어": 3},
    r"AP를\s직접\s투자한\sDEX의\s{n}%\s만큼\sSTR\s증가": {"레전드리": 10, "유니크": 8, "에픽": 5, "레어": 3},
    r"AP를\s직접\s투자한\sINT의\s{n}%\s만큼\sLUK\s증가": {"레전드리": 10, "유니크": 8, "에픽": 5, "레어": 3},
    r"AP를\s직접\s투자한\sLUK의\s{n}%\s만큼\sDEX\s증가": {"레전드리": 10, "유니크": 8, "에픽": 5, "레어": 3},
    r"최대\sHP\s{n}\s증가": {"레전드리": 600, "유니크": 450, "에픽": 300, "레어": 150},
    r"최대\sMP\s{n}\s증가": {"레전드리": 600, "유니크": 450, "에픽": 300, "레어": 150},
    r"방어력\s{n}\s증가": {"레전드리": 400, "유니크": 300, "에픽": 200, "레어": 100},
    r"버프\s스킬의\s지속\s시간\s{n}%\s증가": {"레전드리": 50, "유니크": 38, "에픽": 25, "레어": -1},
    r"일반\s몬스터\s공격\s시\s데미지\s{n}%\s증가": {"레전드리": 10, "유니크": 8, "에픽": 5, "레어": 3},
    r"상태\s이상에\s걸린\s대상\s공격\s시\s데미지\s{n}%\s증가": {"레전드리": 10, "유니크": 8, "에픽": 5, "레어": -1},
    r"메소\s획득량\s{n}%\s증가": {"레전드리": 20, "유니크": 15, "에픽": 10, "레어": 5},
    r"아이템\s드롭률\s{n}%\s증가": {"레전드리": 20, "유니크": 15, "에픽": 10, "레어": 5},
    r"이동속도\s{n}\s증가": {"레전드리": -1, "유니크": 20, "에픽": 14, "레어": 8},
    r"점프력\s{n}\s증가": {"레전드리": -1, "유니크": 20, "에픽": 14, "레어": 8},
    r"공격력\s{n}\s증가": {"레전드리": 30, "유니크": 21, "에픽": 12, "레어": -1},
    r"마력\s{n}\s증가": {"레전드리": 30, "유니크": 21, "에픽": 12, "레어": -1},
    r"크리티컬\s확률\s{n}%\s증가": {"레전드리": 30, "유니크": 20, "에픽": 10, "레어": -1},
    r"보스\s몬스터\s공격\s시\s데미지\s{n}%\s증가": {"레전드리": 20, "유니크": 10, "에픽": -1, "레어": -1},
    r"스킬\s사용\s시\s{n}%\s확률로\s재사용\s대기시간이\s미적용": {"레전드리": 20, "유니크": 10, "에픽": -1, "레어": -1},
    r"최대\sHP\s{n}%\s증가": {"레전드리": 20, "유니크": 10, "에픽": -1, "레어": -1},
    r"최대\sMP\s{n}%\s증가": {"레전드리": 20, "유니크": 10, "에픽": -1, "레어": -1},
    r"방어력의\s{n}%\s만큼\s데미지\s고정값\s증가": {"레전드리": 50, "유니크": 25, "에픽": -1, "레어": -1},
    r"{n}레벨마다\s공격력\s1\s증가": {"레전드리": 10, "유니크": -1, "에픽": -1, "레어": -1},
    r"{n}레벨마다\s마력\s1\s증가": {"레전드리": 10, "유니크": -1, "에픽": -1, "레어": -1}
}

_COMPILED_PATTERNS = _compile_patterns()

DUAL_ABILITY_MAX_N = {"레전드리": 40, "유니크": 30, "에픽": 20, "레어": 10}
_DUAL_NUM_RX = re.compile(
    r"^\s*\S+?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*증가\s*,\s*\S+?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*증가\s*$"
)


def ability_max_value(
        ability_grade: str,
        ability_value: str,
        *,
        already_max: bool = False
    ) -> str:
    """어빌리티의 최대 값을 반환하는 함수

    Args:
        ability_grade (str): 어빌리티 등급 (ability_grade)
        ability_value (str): 어빌리티 값 (ability_value)
        already_max (bool): 이미 최대값이면 최대값 출력 여부

    Returns:
        str: 어빌리티의 최대 값  
        (예: 레전드리 등급에서 STR N 증가의 경우, N의 최대값 = 40)
    
    Exception:
        일부 어빌리티 경우에는 최대값이 없음  
        (예: "공격 속도 N단계 상승"의 경우, 최대값이 없음)

    입력 예:
      - 등급='레전더리', 값='메소 획득량 18% 증가'  → '메소 획득량 18(20)% 증가'
      - 등급='레전더리', 값='STR 37 증가, DEX 19 증가' → 'STR 37(40) 증가, DEX 19(20) 증가'
    """
    ability_grade = ability_grade.strip()
    ability_text = ability_value.strip()

    # 듀얼 어빌리티인 경우
    m2 = _DUAL_NUM_RX.match(ability_text)
    if m2 and ability_grade in DUAL_ABILITY_MAX_N:
        try:
            cur_value1 = int(m2.group(1).replace(",", ""))
            cur_value2 = int(m2.group(2).replace(",", ""))
        except ValueError:
            cur_value1 = cur_value2 = None  # 숫자가 아닌 경우
        
        if cur_value1 is not None:
            max_value1 = DUAL_ABILITY_MAX_N[ability_grade]
            max_value2 = math.ceil(max_value1 / 2)

            def need(cur, max):
                return (cur < max) or (cur == max and not already_max)

            s, e = m2.span(2)
            out = ability_text
            if need(cur_value2, max_value2):
                out = f"{out[:s]}{cur_value2}({max_value2}){out[e:]}"

            m1 = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)", out)
            if m1 and need(cur_value1, max_value1):
                s, e = m1.span(1)
                out = f"{out[:s]}{cur_value1}({max_value1}){out[e:]}"

            return out

    # 듀얼 어빌리티가 아닌 경우
    for rx, grade_max in _COMPILED_PATTERNS:
        m = rx.match(ability_text)
        if not m:
            continue

        # 현재수치
        cur_value = m.group("value").replace(",","")
        try:
            cur_value = int(cur_value)
        except ValueError:
            return ability_text  # 숫자가 아닌 경우 그대로 반환
        
        # 최대수치
        max_value: Optional[int] = grade_max.get(ability_grade)
        max_value_str: str = str(max_value) if max_value is not None else "오류"
        if max_value is None:
            return ability_text

        if (cur_value < max_value) or (cur_value == max_value and not already_max):
            start, end = m.span("value")
            return f"{ability_text[:start]}{cur_value}({max_value_str}){ability_text[end:]}"
        else:
            return ability_text
        
    return ability_text  # 매칭되는 패턴이 없는 경우 그대로 반환


def ability_info_parse(ability_info: List[Dict]) -> str:
    """어빌리티 정보를 문자열로 변환하는 함수

    Args:
        ability_info (dict): 어빌리티 정보 딕셔너리

    Returns:
        str: 변환된 어빌리티 정보 문자열
    """
    result_ability_text = ""
    for idx in ability_info:
        ability_grade: str = (
            str(idx.get("ability_grade")).strip()
            if idx.get("ability_grade") is not None else "몰라양"
        )
        ability_value: str = (
            str(idx.get("ability_value")).strip()
            if idx.get("ability_value") is not None else "몰라양"
        )
        ability_text: str = ability_max_value(
            ability_grade=ability_grade,
            ability_value=ability_value
        )
        ability_grade_symbol: str = maple_convert_grade_text(ability_grade)
        result_ability_text += f"{ability_grade_symbol} {ability_text}\n"

    return result_ability_text.strip() if result_ability_text else "몰라양"


def maple_convert_grade_text(grade_text: str) -> str:
    """메이플 스토리 등급 텍스트를 이모티콘으로 변환하는 함수

    Args:
        grade_text (str): 변환할 등급 텍스트

    Returns:
        str: 변환된 등급 이모티콘
    """
    lgnd_grade_symbol: str = "🟩"
    uniq_grade_symbol: str = "🟨"
    epic_grade_symbol: str = "🟪"
    rare_grade_symbol: str = "🟦"
    grade_mapping = {
        "레전드리": lgnd_grade_symbol,
        "유니크": uniq_grade_symbol,
        "에픽": epic_grade_symbol,
        "레어": rare_grade_symbol,
    }
    return grade_mapping.get(grade_text, "몰라양")


def get_notice(target_event: str = None, recent_notice: bool = True) -> List[dict] | Dict[str, str | Literal["알수없음"]]:
    """Nexon Open API를 통해 메이플스토리 공지사항을 가져오는 함수

    Args:
        target_event (str, optional): 특정 이벤트에 대한 공지사항을 필터링할 수 있음. 기본값은 None.
        recent_notice(bool): True인 경우, 최신 공지사항부터 반환 (list index 0, default: True)

    Returns:
        Dict[str, str | Literal["알수없음"]]: 가장 최근 공지사항 데이터 (recent_notice가 True인 경우)
        list[Dict[str, str | Literal["알수없음"]]]: 공지사항 데이터 목록 (recent_notice가 False인 경우)

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=24
    """
    service_url = maplestory_service_url.notice
    request_url = f"{NEXON_API_HOME}{service_url}"
    response_data: dict = general_request_handler_nexon(request_url)
    notices: list = response_data.get('event_notice', [])
    if target_event is None:
        notice_filter = None
    elif target_event == "pcbang":
        notice_filter = "PC방"
    elif target_event == "sunday":
        notice_filter = "썬데이"

    # 특정 이벤트에 대한 공지사항 필터링
    if target_event:
        notices = [notice for notice in notices if notice_filter in notice.get('title', '')]

    if not notices:
        raise NexonAPIError("No notices found")

    if recent_notice:
        notice_data: dict = notices[0]

        return_data: Dict[str, str | Literal["알수없음"]] = {
            "notice_title" : (
                str(notice_data.get("title")).strip()
                if notice_data.get("title") is not None else "알수없음"
            ),
            "notice_url" : (
                str(notice_data.get("url")).strip()
                if notice_data.get("url") is not None else "알수없음"
            ),
            "notice_id" : (
                str(notice_data.get("notice_id")).strip()
                if notice_data.get("notice_id") is not None else "알수없음"
            ),
            "notice_date" : (
                parse_iso_string(str(notice_data.get("date")).strip())
                if notice_data.get("date") is not None else "알수없음"
            ),
            "notice_start_date" : (
                parse_iso_string(str(notice_data.get("date_event_start")).strip())
                if notice_data.get("date_event_start") is not None else "알수없음"
            ),
            "notice_end_date" : (
                parse_iso_string(str(notice_data.get("date_event_end")).strip())
                if notice_data.get("date_event_end") is not None else "알수없음"
            )
        }

        return return_data
    else:
        return_data: List[Dict[str, str | Literal["알수없음"]]] = []

        for notice_data in notices:
            notice_dict: Dict[str, str | Literal["알수없음"]] = {
                "notice_title" : (
                    str(notice_data.get("title")).strip()
                    if notice_data.get("title") is not None else "알수없음"
                ),
                "notice_url" : (
                    str(notice_data.get("url")).strip()
                    if notice_data.get("url") is not None else "알수없음"
                ),
                "notice_id" : (
                    str(notice_data.get("notice_id")).strip()
                    if notice_data.get("notice_id") is not None else "알수없음"
                ),
                "notice_date" : (
                    parse_iso_string(str(notice_data.get("date")).strip())
                    if notice_data.get("date") is not None else "알수없음"
                ),
                "notice_start_date" : (
                    parse_iso_string(str(notice_data.get("date_event_start")).strip())
                    if notice_data.get("date_event_start") is not None else "알수없음"
                ),
                "notice_end_date" : (
                    parse_iso_string(str(notice_data.get("date_event_end")).strip())
                    if notice_data.get("date_event_end") is not None else "알수없음"
                )
            }
            return_data.append(notice_dict)

        return return_data


def get_notice_details(notice_id: str) -> dict:
    """Nexon Open API를 통해 특정 공지사항의 상세 정보를 가져오는 함수

    Args:
        notice_id (str): 공지사항 ID

    Returns:
        dict: 공지사항 상세 정보

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    service_url = maplestory_service_url.notice_detail
    request_url = f"{NEXON_API_HOME}{service_url}?notice_id={notice_id}"
    response_data: dict = general_request_handler_nexon(request_url)
    return response_data


# 랜덤 시드 기반 메이플스토리 운세 생성 및 경험치 추세 데이터 수집
def generate_fortune_seed(base_seed: int, f_cate: str, salt: str) -> int:
    h = hashlib.md5(f"{base_seed}|{f_cate}|{salt}".encode('utf-8')).hexdigest()
    return int(h, 16)


def fortune_pick_grade(rng: random.Random, grade_table: List[Tuple[int, int]]) -> int:
    roll = rng.randint(1, 100)
    acc = 0
    for g, w in grade_table:
        acc += w
        if roll <= acc:
            return g
    return -1
    

# 운세 메세지 list 생성 (가중치 반영)
def generate_fortune_messages(
        table_name: str,
        msg_table: Dict[str, List[Tuple[str, int]]]
    ) -> List[str]:
    """운세 메세지 list 생성 (가중치 반영)

    Args:
        table_name (str): 운세 메세지 테이블 Key 이름 (예: "StarForce_lv5")
        msg_table (Dict[str, List[Tuple[str, int]]]): 운세 메세지 테이블

    Returns:
        List[str]: 가중치가 반영된 운세 메세지 리스트
    """
    fortune_msg_table = msg_table.get(table_name, {})
    return_msgs = []
    if not fortune_msg_table:
        return []
    else:
        for msg, weight in fortune_msg_table:
            return_msgs.extend([msg] * weight)
    return return_msgs
    

def maple_pick_fortune(seed: int) -> str:
    """메이플스토리 운세를 생성하는 함수

    Args:
        seed (int): 랜덤 시드 값

    Returns:
        str: 운세 결과
    """
    fortune_grade_table: Dict[int, Tuple[str, str]] = {
        5: ("★★★★★", "대박❤️"),
        4: ("★★★★☆", "행운"),
        3: ("★★★☆☆", "평온"),
        2: ("★★☆☆☆", "주의"),
        1: ("★☆☆☆☆", "폭망💥"),
    }
    fortune_grade_weights: List[Tuple[int, int]] = [
        (5, 5),
        (4, 20),
        (3, 30),
        (2, 40),
        (1, 5),
    ]
    fortune_category: Dict[str, str] = {
        "StarForce": "오늘의 스타포스 운세",
        "Cube": "오늘의 큐브 운세",
        "Boss": "오늘의 보스 운세",
        "Cash": "오늘의 캐시 아이템 운세",
        "Hunter": "오늘의 사냥 운세",
    }

    fortune_message_table: Dict[str, List[Tuple[str, int]]] = fortune_message_table_raw

    # 운세 메세지 list 생성 (가중치 반영)
    def generate_fortune_messages(table_name: str) -> List[str]:
        msg_table = fortune_message_table.get(table_name, {})
        return_msgs = []
        if not msg_table:
            return []
        else:
            for msg, weight in msg_table:
                return_msgs.extend([msg] * weight)
        return return_msgs


    fortune_message : Dict[str, Dict[int, List[str]]] = {
        "StarForce": {
            5: generate_fortune_messages("StarForce_lv5"),
            4: generate_fortune_messages("StarForce_lv4"),
            3: generate_fortune_messages("StarForce_lv3"),
            2: generate_fortune_messages("StarForce_lv2"),
            1: generate_fortune_messages("StarForce_lv1"),
        },
        "Cube": {
            5: generate_fortune_messages("Cube_lv5"),
            4: generate_fortune_messages("Cube_lv4"),
            3: generate_fortune_messages("Cube_lv3"),
            2: generate_fortune_messages("Cube_lv2"),
            1: generate_fortune_messages("Cube_lv1"),
        },
        "Boss": {
            5: generate_fortune_messages("Boss_lv5"),
            4: generate_fortune_messages("Boss_lv4"),
            3: generate_fortune_messages("Boss_lv3"),
            2: generate_fortune_messages("Boss_lv2"),
            1: generate_fortune_messages("Boss_lv1"),
        },
        "Cash": {
            5: generate_fortune_messages("Cash_lv5"),
            4: generate_fortune_messages("Cash_lv4"),
            3: generate_fortune_messages("Cash_lv3"),
            2: generate_fortune_messages("Cash_lv2"),
            1: generate_fortune_messages("Cash_lv1"),
        },
        "Hunter": {
            5: generate_fortune_messages("Hunter_lv5"),
            4: generate_fortune_messages("Hunter_lv4"),
            3: generate_fortune_messages("Hunter_lv3"),
            2: generate_fortune_messages("Hunter_lv2"),
            1: generate_fortune_messages("Hunter_lv1"),
        }
    }
    
    fortune_result: List[str] = []
    for f_cate, f_name in fortune_category.items():
        # 행운 등급 결정
        grade_seed: int = generate_fortune_seed(seed, f_cate, "grade")
        random_grade: random.Random = random.Random(grade_seed)
        f_grade = fortune_pick_grade(random_grade, fortune_grade_weights)

        if f_grade != -1:
            # 행운 메세지 결정
            message_seed: int = generate_fortune_seed(seed, f_cate, "message")
            random_message: random.Random = random.Random(message_seed)
            f_result_star, f_result_name = fortune_grade_table[f_grade]
            f_message_dict: Dict[int, List[str]] = fortune_message.get(f_cate)
            f_message: str = random_message.choice(f_message_dict.get(f_grade, []))
            f_text = (
                f"{f_name}\n"
                f"{f_result_star} ({f_result_name}): {f_message}\n"
            )
        else:
            f_text = f"{f_name}\n오늘의 운세를 알 수 없어양...\n"
        fortune_result.append(f_text)

    return "\n".join(fortune_result)


async def get_weekly_xp_history(character_ocid: str, time_delta: int = 2) -> Tuple[str, int, str]:
    """메이플 스토리 캐릭터의 1주일 간 경험치 추세 데이터 수집
    
    Args:
        character_ocid (str): 캐릭터 고유 ID

    Returns:
        List[Tuple[str, int, float]]: 날짜, 레벨, 경험치 퍼센트 데이터 (1주일치)
        (예: ("2023-10-01", 250, "75.321%"))

    Raises:
        1일전 데이터 호출 실패한 경우: 2일전 데이터 호출
        NexonAPIError: API 호출 오류

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14
    """

    start_date: datetime = datetime.now(tz=timezone("Asia/Seoul")).date()
    date_list: List[str] = [
        (start_date - timedelta(days=time_delta + i)).strftime("%Y-%m-%d") for i in range(7)
    ]
    return_data: List[Tuple[str, int, str]] = []

    for param_date in date_list:
        request_service_url: str = maplestory_service_url.basic_info
        request_url: str = f"{NEXON_API_HOME}{request_service_url}?ocid={character_ocid}&date={param_date}"
        response_data: dict = general_request_handler_nexon(request_url)
        character_level: int = (
            int(response_data.get("character_level", -1))
            if response_data.get("character_level") is not None
            else -1
        )
        character_exp_rate: str = (
            str(response_data.get("character_exp_rate")).strip()
            if response_data.get("character_exp_rate") is not None
            else "0.000%"
        )
        return_data.append((param_date, character_level, character_exp_rate))

    return return_data


def get_basic_info(ocid: str) -> Dict[str, str | int | bool | Literal["..."]]:
    """메이플스토리 캐릭터 기본 정보 데이터를 가져와서 가공하는 함수

    Args:
        ocid (str): 캐릭터 OCID

    Returns:
        dict: 가공된 캐릭터 기본 정보 데이터
    """
    character_ocid: str = ocid

    service_url = maplestory_service_url.basic_info
    requests_url = f"{NEXON_API_HOME}{service_url}?ocid={character_ocid}"

    response_data: dict = general_request_handler_nexon(requests_url)

    if isinstance(character_ocid, str):
        return_data: dict = {
            "character_ocid": character_ocid
        }

        # basic info 1. 캐릭터 이름
        character_name: str = (
            str(response_data.get('character_name')).strip()
            if response_data.get('character_name') is not None
            else None
        )

        if character_name is None:
            return False
        else:
            return_data['character_name'] = character_name
        
        # basic info 2. 캐릭터 레벨
        character_level: int = (
            int(response_data.get('character_level'))
            if response_data.get('character_level') is not None
            else -1
        )
        return_data['character_level'] = character_level if character_level != -1 else "몰라양"

        # basic info 3. 캐릭터 소속월드
        character_world: str | Literal["알수없음"] = (
            str(response_data.get('world_name')).strip()
            if response_data.get('world_name') is not None
            else "알수없음"
        )
        return_data['character_world'] = character_world

        # basic info 4. 캐릭터 성별
        character_gender: str | Literal["기타"] = (
            str(response_data.get('character_gender')).strip()
            if response_data.get('character_gender') is not None
            else "기타"
        )
        return_data['character_gender'] = character_gender

        # basic info 5. 캐릭터 직업 & 직업차수
        character_class: str | Literal["알수없음"] = (
            str(response_data.get('character_class')).strip()
            if response_data.get('character_class') is not None
            else "알수없음"
        )
        character_class_level: str | Literal["알수없음"] = (
            str(response_data.get('character_class_level')).strip()
            if response_data.get('character_class_level') is not None
            else "알수없음"
        )
        return_data['character_job'] = f"{character_class} ({character_class_level}차 전직)"
        return_data['character_class'] = character_class
        return_data['character_class_level'] = character_class_level

        # basic info 6. 캐릭터 경험치 & 퍼센트
        character_exp: int = (
            int(response_data.get('character_exp'))
            if response_data.get('character_exp') is not None
            else -1
        )
        character_exp_rate: str | Literal["0.000%"] = (
            str(response_data.get('character_exp_rate')).strip()
            if response_data.get('character_exp_rate') is not None
            else "0.000%"
        )
        return_data['character_exp'] = character_exp
        return_data['character_exp_rate'] = character_exp_rate

        # basic info 7. 캐릭터 소속 길드
        character_guild_name_json = response_data.get('character_guild_name')
        if character_guild_name_json is None:
            character_guild_name = "길드가 없어양!"
        else:
            character_guild_name = str(character_guild_name_json).strip()
        return_data['character_guild_name'] = character_guild_name

        # basic info 8. 캐릭터 외형 이미지 URL
        character_image: str | Literal[""] = (
            str(response_data.get('character_image')).strip()
            if response_data.get('character_image') is not None
            else ""
        )
        return_data['character_image'] = character_image

        # basic info 9. 캐릭터 생성일
        character_date_create: str | Literal["알수없음"] = (
            str(response_data.get('character_date_create')).strip()
            if response_data.get('character_date_create') is not None
            else "알수없음"
        )
        return_data['character_date_create'] = character_date_create

        # basic info 10. 캐릭터 최근 7일 이내 접속 여부 (flag)
        character_access_flag: bool | Literal["알수없음"]  = (
            str(response_data.get('character_access_flag')).strip()
            if response_data.get('character_access_flag') is not None
            else "알수없음"
        )
        if character_access_flag == "true":
            character_access_flag = True
        elif character_access_flag == "false":
            character_access_flag = False
        else:
            character_access_flag = "알수없음"
        return_data['character_access_flag'] = character_access_flag

        # basic info 11. 캐릭터 해방 퀘스트 완료 여부
        character_liberation_quest_clear: str | Literal["알수없음"] = (
            str(response_data.get('liberation_quest_clear')).strip()
            if response_data.get('liberation_quest_clear') is not None
            else "알수없음"
        )
        return_data['liberation_quest_clear'] = character_liberation_quest_clear

    return return_data


def get_stat_info(ocid: str) -> Dict[str, str | int | Literal["알수없음"]]:
    """메이플스토리 캐릭터 상세 정보 데이터를 가공하는 함수

    Args:
        raw_data (dict): 메이플스토리 캐릭터 상세 정보 데이터

    Returns:
        dict: 가공된 캐릭터 상세 정보 데이터
    """
    service_url = maplestory_service_url.stat_info
    requests_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}"
    response_data: dict = general_request_handler_nexon(requests_url)
    stat_list: List[dict] = response_data.get('final_stat', [])
    
    if isinstance(stat_list, list) and stat_list:
        character_stat_info: dict = {}
        for stat in stat_list:
            stat_name: str = str(stat.get('stat_name')).strip()
            stat_value: str | None = stat.get('stat_value')
            if stat_name:
                character_stat_info[stat_name] = stat_value
            else:
                continue
    else:
        raise NexonAPIError("Invalid stat data format")
    
    if character_stat_info != {}:
        stat_attack_min: str | Literal["알수없음"] = (
            str(character_stat_info.get("최소 스탯공격력")).strip()
            if character_stat_info.get("최소 스탯공격력") is not None
            else "알수없음"
        )
        stat_attack_max: str | Literal["알수없음"] = (
            str(character_stat_info.get("최대 스탯공격력")).strip()
            if character_stat_info.get("최대 스탯공격력") is not None
            else "알수없음"
        )
        stat_damage: str | Literal["알수없음"] = (
            str(character_stat_info.get("데미지")).strip()
            if character_stat_info.get("데미지") is not None
            else "알수없음"
        )
        stat_boss_damage: str | Literal["알수없음"] = (
            str(character_stat_info.get("보스 몬스터 데미지")).strip()
            if character_stat_info.get("보스 몬스터 데미지") is not None
            else "알수없음"
        )
        stat_final_damage: str | Literal["알수없음"] = (
            str(character_stat_info.get("최종 데미지")).strip()
            if character_stat_info.get("최종 데미지") is not None
            else "알수없음"
        )
        stat_ignore_def: str | Literal["알수없음"] = (
            str(character_stat_info.get("방어율 무시")).strip()
            if character_stat_info.get("방어율 무시") is not None
            else "알수없음"
        )
        stat_crit_rate: str | Literal["알수없음"] = (
            str(character_stat_info.get("크리티컬 확률")).strip()
            if character_stat_info.get("크리티컬 확률") is not None
            else "알수없음"
        )
        stat_crit_damage: str | Literal["알수없음"] = (
            str(character_stat_info.get("크리티컬 데미지")).strip()
            if character_stat_info.get("크리티컬 데미지") is not None
            else "알수없음"
        )
        stat_status_resist: str | Literal["알수없음"] = (
            str(character_stat_info.get("상태이상 내성")).strip()
            if character_stat_info.get("상태이상 내성") is not None
            else "알수없음"
        )
        stat_stance: str | Literal["알수없음"] = (
            str(character_stat_info.get("스탠스")).strip()
            if character_stat_info.get("스탠스") is not None
            else "알수없음"
        )
        stat_defense: str | Literal["알수없음"] = (
            str(character_stat_info.get("방어력")).strip()
            if character_stat_info.get("방어력") is not None
            else "알수없음"
        )
        stat_move_speed: str | Literal["알수없음"] = (
            str(character_stat_info.get("이동속도")).strip()
            if character_stat_info.get("이동속도") is not None
            else "알수없음"
        )
        stat_jump: str | Literal["알수없음"] = (
            str(character_stat_info.get("점프력")).strip()
            if character_stat_info.get("점프력") is not None
            else "알수없음"
        )
        stat_starforce: str | Literal["알수없음"] = (
            str(character_stat_info.get("스타포스")).strip()
            if character_stat_info.get("스타포스") is not None
            else "알수없음"
        )
        stat_arcane_force: str | Literal["알수없음"] = (
            str(character_stat_info.get("아케인포스")).strip()
            if character_stat_info.get("아케인포스") is not None
            else "알수없음"
        )
        stat_authentic_force: str | Literal["알수없음"] = (
            str(character_stat_info.get("어센틱포스")).strip()
            if character_stat_info.get("어센틱포스") is not None
            else "알수없음"
        )
        stat_str: int = (
            int(character_stat_info.get("STR"))
            if character_stat_info.get("STR") is not None
            else 0
        )
        stat_dex: int = (
            int(character_stat_info.get("DEX"))
            if character_stat_info.get("DEX") is not None
            else 0
        )
        stat_int: int = (
            int(character_stat_info.get("INT"))
            if character_stat_info.get("INT") is not None
            else 0
        )
        stat_luk: int = (
            int(character_stat_info.get("LUK"))
            if character_stat_info.get("LUK") is not None
            else 0
        )
        stat_hp: int = (
            int(character_stat_info.get("HP"))
            if character_stat_info.get("HP") is not None
            else 0
        )
        stat_mp: int = (
            int(character_stat_info.get("MP"))
            if character_stat_info.get("MP") is not None
            else 0
        )
        stat_str_ap: int = (
            int(character_stat_info.get("AP 배분 STR"))
            if character_stat_info.get("AP 배분 STR") is not None
            else 0
        )
        stat_dex_ap: int = (
            int(character_stat_info.get("AP 배분 DEX"))
            if character_stat_info.get("AP 배분 DEX") is not None
            else 0
        )
        stat_int_ap: int = (
            int(character_stat_info.get("AP 배분 INT"))
            if character_stat_info.get("AP 배분 INT") is not None
            else 0
        )
        stat_luk_ap: int = (
            int(character_stat_info.get("AP 배분 LUK"))
            if character_stat_info.get("AP 배분 LUK") is not None
            else 0
        )
        stat_hp_ap: int = (
            int(character_stat_info.get("AP 배분 HP"))
            if character_stat_info.get("AP 배분 HP") is not None
            else 0
        )
        stat_mp_ap: int = (
            int(character_stat_info.get("AP 배분 MP"))
            if character_stat_info.get("AP 배분 MP") is not None
            else 0
        )
        stat_item_drop: str | Literal["알수없음"] = (
            str(character_stat_info.get("아이템 드롭률")).strip()
            if character_stat_info.get("아이템 드롭률") is not None
            else "알수없음"
        )
        stat_mesos: str | Literal["알수없음"] = (
            str(character_stat_info.get("메소 획득량")).strip()
            if character_stat_info.get("메소 획득량") is not None
            else "알수없음"
        )
        stat_buff_duration: str | Literal["알수없음"] = (
            str(character_stat_info.get("버프 지속시간")).strip()
            if character_stat_info.get("버프 지속시간") is not None
            else "알수없음"
        )
        stat_attack_speed: str | Literal["알수없음"] = (
            str(character_stat_info.get("공격속도")).strip()
            if character_stat_info.get("공격속도") is not None
            else "알수없음"
        )
        stat_mob_damage: str | Literal["알수없음"] = (
            str(character_stat_info.get("일반 몬스터 데미지")).strip()
            if character_stat_info.get("일반 몬스터 데미지") is not None
            else "알수없음"
        )
        stat_cooltime_reduction_sec: str | Literal["알수없음"] = (
            str(character_stat_info.get("재사용 대기시간 감소 (초)")).strip()
            if character_stat_info.get("재사용 대기시간 감소 (초)") is not None
            else "알수없음"
        )
        stat_cooltime_reduction_per: str | Literal["알수없음"] = (
            str(character_stat_info.get("재사용 대기시간 감소 (%)")).strip()
            if character_stat_info.get("재사용 대기시간 감소 (%)") is not None
            else "알수없음"
        )
        stat_cooltime_avoid: str | Literal["알수없음"] = (
            str(character_stat_info.get("재사용 대기시간 미적용")).strip()
            if character_stat_info.get("재사용 대기시간 미적용") is not None
            else "알수없음"
        )
        stat_ignore_element: str | Literal["알수없음"] = (
            str(character_stat_info.get("속성 내성 무시")).strip()
            if character_stat_info.get("속성 내성 무시") is not None
            else "알수없음"
        )
        stat_status_damage: str | Literal["알수없음"] = (
            str(character_stat_info.get("상태이상 추가 데미지")).strip()
            if character_stat_info.get("상태이상 추가 데미지") is not None
            else "알수없음"
        )
        stat_weapon_mastery: str | Literal["알수없음"] = (
            str(character_stat_info.get("무기 숙련도")).strip()
            if character_stat_info.get("무기 숙련도") is not None
            else "알수없음"
        )
        stat_bonus_exp: str | Literal["알수없음"] = (
            str(character_stat_info.get("추가 경험치 획득")).strip()
            if character_stat_info.get("추가 경험치 획득") is not None
            else "알수없음"
        )
        stat_attack: str | Literal["알수없음"] = (
            str(character_stat_info.get("공격력")).strip()
            if character_stat_info.get("공격력") is not None
            else "알수없음"
        )
        stat_magic: str | Literal["알수없음"] = (
            str(character_stat_info.get("마력")).strip()
            if character_stat_info.get("마력") is not None
            else "알수없음"
        )
        stat_battle_power: str | Literal["알수없음"] = (
            str(character_stat_info.get("전투력")).strip()
            if character_stat_info.get("전투력") is not None
            else "알수없음"
        )
        stat_familiar_duration: str | Literal["알수없음"] = (
            str(character_stat_info.get("소환수 지속시간 증가")).strip()
            if character_stat_info.get("소환수 지속시간 증가") is not None
            else "알수없음"
        )

        processed_stat_info: Dict[str, str | int | Literal["알수없음"]] = {
            "stat_attack_min": stat_attack_min,
            "stat_attack_max": stat_attack_max,
            "stat_damage": stat_damage,
            "stat_boss_damage": stat_boss_damage,
            "stat_final_damage": stat_final_damage,
            "stat_ignore_def": stat_ignore_def,
            "stat_crit_rate": stat_crit_rate,
            "stat_crit_damage": stat_crit_damage,
            "stat_status_resist": stat_status_resist,
            "stat_stance": stat_stance,
            "stat_defense": stat_defense,
            "stat_move_speed": stat_move_speed,
            "stat_jump": stat_jump,
            "stat_starforce": stat_starforce,
            "stat_arcane_force": stat_arcane_force,
            "stat_authentic_force": stat_authentic_force,
            "stat_str": stat_str,
            "stat_dex": stat_dex,
            "stat_int": stat_int,
            "stat_luk": stat_luk,
            "stat_hp": stat_hp,
            "stat_mp": stat_mp,
            "stat_str_ap": stat_str_ap,
            "stat_dex_ap": stat_dex_ap,
            "stat_int_ap": stat_int_ap,
            "stat_luk_ap": stat_luk_ap,
            "stat_hp_ap": stat_hp_ap,
            "stat_mp_ap": stat_mp_ap,
            "stat_item_drop": stat_item_drop,
            "stat_mesos": stat_mesos,
            "stat_buff_duration": stat_buff_duration,
            "stat_attack_speed": stat_attack_speed,
            "stat_mob_damage": stat_mob_damage,
            "stat_cooltime_reduction_sec": stat_cooltime_reduction_sec,
            "stat_cooltime_reduction_per": stat_cooltime_reduction_per,
            "stat_cooltime_avoid": stat_cooltime_avoid,
            "stat_ignore_element": stat_ignore_element,
            "stat_status_damage": stat_status_damage,
            "stat_weapon_mastery": stat_weapon_mastery,
            "stat_bonus_exp": stat_bonus_exp,
            "stat_attack": stat_attack,
            "stat_magic": stat_magic,
            "stat_battle_power": stat_battle_power,
            "stat_familiar_duration": stat_familiar_duration,
        }
        return processed_stat_info
    

def get_cash_equipment_info(ocid: str) -> Dict[str, str | int | List[dict] | Literal["기타"] | None]:
    """캐릭터의 장착중인 장착효과 및 외형 캐시 아이템 정보를 조회하는 함수

    Args:
        ocid (str): 캐릭터 OCID

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14
    """
    service_url = maplestory_service_url.cash_equipment
    request_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}"
    response_data: dict = general_request_handler_nexon(request_url)
    
    return_data = {
        "character_gender": (
            str(response_data.get("character_gender")).strip()
            if response_data.get("character_gender") is not None
            else "기타"
        ),
        "character_class": (
            str(response_data.get("character_class")).strip()
            if response_data.get("character_class") is not None
            else "기타"
        ),
        "character_look_mode": (
            str(response_data.get("character_look_mode")).strip()
            if response_data.get("character_look_mode") is not None
            else "0"  # 기본 외형 모드
        ),
        "current_preset_no": (
            int(response_data.get("preset_no"))
            if response_data.get("preset_no") is not None
            else None
        ),
        "equipment_base_list": (
            response_data.get("cash_item_equipment_base", [])
        ),
        "additional_equipment_base_list": (
            response_data.get("additional_cash_item_equipment_base", [])
        )
    }
    preset = return_data.get("current_preset_no") or 1
    if return_data["character_look_mode"] == "1":
        # 드레스업 혹은 베타 모드인 경우, additional_preset 사용
        target_key_name = f"additional_cash_item_equipment_preset"
    else:
        target_key_name = f"cash_item_equipment_preset"
    return_data["equipment_look_list"] = (
        response_data.get(f"{target_key_name}_{preset}", [])
    )
    
    return return_data


def parse_equipment_info(equipment_data: List[Dict[str, Any]]) -> Dict[str, str]:
    """캐릭터의 장착중인 캐시 아이템 정보를 가공하는 함수

    Args:
        equipment_data (List[Dict[str, Any]]): 장비 아이템 정보 리스트

    Returns:
        Dict[str, str]: 부위별 장착 캐시 아이템 정보
    """
    equipment_slots = [
        "눈장식", "장갑", "무기", "반지1", "반지2", "반지3", "반지4",
        "보조무기", "모자", "망토", "얼굴장식", "상의", "신발", "귀고리", "하의"
    ]
    if isinstance(equipment_data, list) and equipment_data:
        equipment_info: Dict[str, str] = {}
        for item in equipment_data:
            item_part: str = (
                str(item.get("cash_item_equipment_part")).strip()
                if item.get("cash_item_equipment_part") is not None else "알수없음"
            )
            item_slot: str = (
                str(item.get("cash_item_equipment_slot")).strip()
                if item.get("cash_item_equipment_slot") is not None else "알수없음"
            )
            if item_slot in equipment_slots:
                item_name: str = (
                    str(item.get("cash_item_name")).strip()
                    if item.get("cash_item_name") is not None else "알수없음"
                )
                item_label: str = (
                    str(item.get("cash_item_label")).strip()
                    if isinstance(item.get("cash_item_label"), str) else "알수없음"
                )
                # 아이템 기간제 여부 확인
                item_date_expire: Optional[str] = (
                    item.get("date_expire")
                    if isinstance(item.get("date_expire"), str) else None
                )
                # 아이템 옵션 및 기간 정보
                item_options: Optional[List[Dict[str, str]]] = (
                    item.get("cash_item_option")
                    if isinstance(item.get("cash_item_option"), list) else None
                )
                item_options_expire: Optional[str] = (
                    item.get("date_option_expire")
                    if isinstance(item.get("date_option_expire"), str) else None
                )
                # 컬러링 프리즘 정보
                item_color: Optional[Dict[str, str]] = (
                    item.get("cash_item_color")
                    if isinstance(item.get("cash_item_color"), dict) else None
                )

                display_slot_name = f"{item_slot} ({item_part})"
                display_item_name = f"[{item_label}] {item_name}" if item_label != "알수없음" else item_name
                equipment_info[item_slot] = {
                    "slot_name": display_slot_name,
                    "item_name": display_item_name,

                }


def get_beauty_equipment_info(ocid: str) -> Dict[str, Optional[str | Dict[str, str]]]:
    """캐릭터의 뷰티(헤어/성형) 정보 조회

    Args:
        ocid (str): 캐릭터 OCID
    """
    service_url = maplestory_service_url.beauty_equipment
    request_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}"
    response_data: dict = general_request_handler_nexon(request_url)

    return response_data