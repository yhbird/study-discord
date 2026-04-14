from __future__ import annotations

import io
import asyncio
import hashlib
import random
import math
import time
import json
import re

from urllib.parse import quote
from collections import deque
from datetime import datetime, timedelta
from discord import Interaction, ButtonStyle
from discord.ui import View, Button
from pytz import timezone
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from service.maplestory.consts import MapleEquipmentViewerConfig, MapleCodiHistoryConfig
from config import NEXON_API_KEY, NEXON_API_HOME # Nexon Open API
from config import NEXON_API_RPS_LIMIT, NEXON_CHARACTER_IMAGE_URL # Nexon Open API Rate Limit 방지용 시간 간격
from data.json.fortune_message_table import fortune_message_table_raw

from exceptions.client_exceptions import *
from common.image import ImageTools, ImageBaseConfig
from common.time import parse_iso_string
from common.image import convert_image_url_into_bytes

from typing import Literal, Optional, Dict, List, Tuple, Any

API_MAX_DATE_SEARCH_END: datetime = datetime(year=2023, month=12, day=21) # Nexon API 제공 시작일


class MaplestoryUrls:
    OCID = "/maplestory/v1/id"
    POP = "/maplestory/v1/character/popularity"
    ABILITY = "/maplestory/v1/character/ability"
    NOTICE = "/maplestory/v1/notice-event"
    NOTICE_DETAIL = "/maplestory/v1/notice-event/detail"
    BASIC_INFO = "/maplestory/v1/character/basic"
    STAT_INFO = "/maplestory/v1/character/stat"
    ITEM_EQUIPMENT = "/maplestory/v1/character/item-equipment"
    CASH_EQUIPMENT = "/maplestory/v1/character/cashitem-equipment"
    BEAUTY_EQUIPMENT = "/maplestory/v1/character/beauty-equipment"
    CHARACTER_IMAGE_URL = NEXON_CHARACTER_IMAGE_URL


class CordinateVars:
    # 이미지 크기 및 설정
    IMAGE_SIZE : Literal[180] = 180
    CAPTION_HEIGHT : Literal[28] = 28
    IMAGES_GRID_COLS : Literal[4] = 4
    IMAGES_GRID_ROWS : Literal[2] = 2
    CELL_PADDING_SIZE : Literal[16] = 16
    BOARD_MARGIN : Literal[24] = 24
    CELL_RADIUS : Literal[10] = 10
    BG_COLOR = (255, 255, 255, 255)
    FG_COLOR = (33, 37, 41, 255)
    CELL_BG_COLOR = (255, 255, 255, 255)
    CELL_SHADOW = (0, 0, 0, 40)
    SHADOW_OFFSET = (0, 2)
    TITLE_FONT_PATH = "./assets/font/Maplestory_Bold.ttf"
    CAPTION_FONT_PATH = "./assets/font/Maplestory_Light.ttf"
    DEFAULT_FONT_PATH = "./assets/font/NanumGothic.ttf"
    FONT_SIZE : Literal[18] = 18
    TITLE_FONT_PADDING : Literal[12] = 12
    PLACE_HOLDER_IMAGE_PATH = "./assets/image/maple_chara_placeholder.png"


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


# 보스 분배금 계산을 위한 Viewer 정의
class DistributeView(View):
    def __init__(self, distribution_data):
        super().__init__(timeout=60 * 5) # 5분뒤 버튼 비활성화
        self.distribution_data = distribution_data
        self.add_copy_button()

    # button 동적생성
    def add_copy_button(self):
        for party_size, amounts in self.distribution_data.items():
            button = Button(
                label=f"{party_size}인",
                style=ButtonStyle.primary,
                custom_id=f"party_{party_size}"
            )

            # 콜백 함수 (클로저 문제 방지를 위해 기본값 인자 사용)
            async def callback(interaction: Interaction, p_size=party_size, val=amounts):
                # 가독성을 위해 천 단위 콤마 포맷팅
                r5_str = f"{val['r5']:,}"
                r3_str = f"{val['r3']:,}"

                # 복사하기 쉽게 코드 블록(``)으로 감싸서 출력
                msg = (
                    f"**[{p_size}인 파티]** 파티원에게 줄 금액이에양!\n"
                    f"숫자 우측에 클립보드 복사 버튼을 눌러서 복사할 수 있어양!\n\n"
                    f"🔹 **일반 (수수료 5% 적용시)**\n"
                    f"```\n{val['r5']}\n```\n"
                    f"🔸 **MVP (수수료 3% 적용시)**\n"
                    f"```\n{val['r3']}\n```\n"
                    f"💡 상황에 맞는 금액을 복사해서 거래해양!"
                )

                await interaction.response.send_message(msg, ephemeral=True)

            button.callback = callback
            self.add_item(button)

_httpx_client: Optional[httpx.AsyncClient] = None
_api_rate_limiter: Dict[str, APIRateLimiter] = {
    NEXON_API_KEY : APIRateLimiter(max_calls=NEXON_API_RPS_LIMIT, period=1.0)
}

async def _rate_limit_request(request: httpx.Request):
    api_key = request.headers.get("x-nxopen-api-key")
    limiter = _api_rate_limiter.get(api_key) or APIRateLimiter(max_calls=NEXON_API_RPS_LIMIT, period=1.0)
    await limiter.acquire()


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


def get_character_image_url(character_image: str) -> str | None:
    """캐릭터 이미지 URL 생성 함수
    캐릭터 정보로 얻은 이미지 URL을 avatar.maplestory.nexon.com 도메인으로 변경


    Args:
        character_image (str): 캐릭터 이미지 파일명

    Returns:
        str | None: 캐릭터 이미지 URL 또는 None
    """
    if character_image == "" or character_image is None:
        return None
    look_value = character_image.split("/character/look/")[-1].split("?")[0]
    return f"{MaplestoryUrls.CHARACTER_IMAGE_URL}{look_value}.png"


async def general_request_handler_nexon(request_path: str, headers: Optional[dict] = None) -> dict | None:
    """Nexon Open API의 일반적인 요청을 처리하는 비동기 함수(v2)  

    API 초당 호출 횟수 제한 (RPS)에 걸리지 않도록 Rate Limiter 적용

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
    retry_times = 0
    retry_times_limit = 5

    while retry_times < retry_times_limit and response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        try:
            wait_time = int(retry_after) if retry_after else 1
        except ValueError:
            wait_time = 1
        await asyncio.sleep(wait_time)
        response = await client.get(request_path, headers=request_headers)
        retry_times += 1

        if retry_times == retry_times_limit:
            raise NexonAPITooManyRequests("Nexon API 요청 초과로 실패했어양...")

    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"raw": response.text, "status": response.status_code}

    nexon_api_error_handler(response)
    return None


async def get_ocid(character_name: str) -> str:
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
    service_url = MaplestoryUrls.OCID
    url_encode_name: str = quote(character_name)
    request_url = f"{NEXON_API_HOME}{service_url}?character_name={url_encode_name}"
    try:
        response_data: dict = await general_request_handler_nexon(request_url)
    except NexonAPIBadRequest as e:
        raise NexonAPICharacterNotFound("Character not found") from e

    # 정상적으로 OCID를 찾았을 때
    ocid: str = str(response_data.get('ocid'))
    if ocid:
        return ocid
    else:
        raise NexonAPICharacterNotFound("OCID not found in response")


async def get_popularity(ocid: str) -> int | str:
    """OCID에 해당하는 캐릭터의 인기도를 가져오는 함수

    Args:
        ocid (str): 캐릭터 OCID

    Returns:
        str: 캐릭터의 인기도

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    service_url = MaplestoryUrls.POP
    request_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}"
    try:
        response_data: dict = await general_request_handler_nexon(request_url)
        popularity: int | str = response_data.get('popularity', "몰라양")
        return popularity
    except NexonAPIError:
        return "몰라양"  # 예외 발생 시 기본값으로 "몰라양" 반환
    

async def get_ability_info(ocid: str) -> dict:
    """OCID에 해당하는 캐릭터의 어빌리티 정보를 비동기적으로 가져오는 함수

    Args:
        ocid (str): 캐릭터 OCID

    Returns:
        dict: 캐릭터의 어빌리티 정보
    """
    service_url = MaplestoryUrls.ABILITY
    request_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}"
    response_data: dict = await general_request_handler_nexon(request_url)
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


async def get_notice(target_event: str = None,
                     recent_notice: bool = True) -> List[dict] | Dict[str, str | Literal["알수없음"]]:
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
    service_url = MaplestoryUrls.NOTICE
    request_url = f"{NEXON_API_HOME}{service_url}"
    response_data: dict = await general_request_handler_nexon(request_url)
    notices: list = response_data.get('event_notice', [])
    if target_event is None:
        notice_filter = None
    elif target_event == "pcbang":
        notice_filter = "PC방"
    elif target_event == "sunday":
        notice_filter = "썬데이"
    else:
        notice_filter = target_event

    # 특정 이벤트에 대한 공지사항 필터링
    if target_event:
        notices = [notice for notice in notices if notice_filter in notice.get('title', '')]

    if not notices:
        if target_event == "sunday":
            raise NexonAPISundayEventNotFound("No sunday notices found")
        else:
            raise NexonAPINoticeNotFound("No notices found")

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


async def get_notice_details(notice_id: str) -> dict:
    """Nexon Open API를 통해 특정 공지사항의 상세 정보를 가져오는 함수

    Args:
        notice_id (str): 공지사항 ID

    Returns:
        dict: 공지사항 상세 정보

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    service_url = MaplestoryUrls.NOTICE_DETAIL
    request_url = f"{NEXON_API_HOME}{service_url}?notice_id={notice_id}"
    response_data: dict = await general_request_handler_nexon(request_url)
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
    def _generate_fortune_messages(table_name: str) -> List[str]:
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
            5: _generate_fortune_messages("StarForce_lv5"),
            4: _generate_fortune_messages("StarForce_lv4"),
            3: _generate_fortune_messages("StarForce_lv3"),
            2: _generate_fortune_messages("StarForce_lv2"),
            1: _generate_fortune_messages("StarForce_lv1"),
        },
        "Cube": {
            5: _generate_fortune_messages("Cube_lv5"),
            4: _generate_fortune_messages("Cube_lv4"),
            3: _generate_fortune_messages("Cube_lv3"),
            2: _generate_fortune_messages("Cube_lv2"),
            1: _generate_fortune_messages("Cube_lv1"),
        },
        "Boss": {
            5: _generate_fortune_messages("Boss_lv5"),
            4: _generate_fortune_messages("Boss_lv4"),
            3: _generate_fortune_messages("Boss_lv3"),
            2: _generate_fortune_messages("Boss_lv2"),
            1: _generate_fortune_messages("Boss_lv1"),
        },
        "Cash": {
            5: _generate_fortune_messages("Cash_lv5"),
            4: _generate_fortune_messages("Cash_lv4"),
            3: _generate_fortune_messages("Cash_lv3"),
            2: _generate_fortune_messages("Cash_lv2"),
            1: _generate_fortune_messages("Cash_lv1"),
        },
        "Hunter": {
            5: _generate_fortune_messages("Hunter_lv5"),
            4: _generate_fortune_messages("Hunter_lv4"),
            3: _generate_fortune_messages("Hunter_lv3"),
            2: _generate_fortune_messages("Hunter_lv2"),
            1: _generate_fortune_messages("Hunter_lv1"),
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


async def get_weekly_xp_history(character_ocid: str, time_delta: int = 2) -> List[Tuple[str, int, str]]:
    """메이플 스토리 캐릭터의 1주일 간 경험치 추세 데이터 수집
    
    Args:
        character_ocid (str): 캐릭터 고유 ID
        time_delta (int): N일전 날짜부터 조회

    Returns:
        List[Tuple[str, int, float]]: 날짜, 레벨, 경험치 퍼센트 데이터 (1주일치)
        (예: ("2023-10-01", 250, "75.321%"))

    Raises:
        1일전 데이터 호출 실패한 경우: 2일전 데이터 호출
        NexonAPIError: API 호출 오류

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14
    """

    start_date = datetime.now(tz=timezone("Asia/Seoul")).date()
    date_list: List[str] = [
        (start_date - timedelta(days=time_delta + i)).strftime("%Y-%m-%d") for i in range(7)
    ]
    return_data: List[Tuple[str, int, str]] = []

    for param_date in date_list:
        request_service_url: str = MaplestoryUrls.BASIC_INFO
        request_url: str = f"{NEXON_API_HOME}{request_service_url}?ocid={character_ocid}&date={param_date}"
        response_data: dict = await general_request_handler_nexon(request_url)
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


async def get_weekly_xp_history_v2(character_ocid: str, search_end: datetime | None) -> List[Tuple[str, int, str]]:
    """메이플 스토리 캐릭터의 1주일 간 경험치 추세 데이터 수집_v2
    
    Args:
        character_ocid (str): 캐릭터 고유 ID
        search_end (Optional[datetime]): 검색 중단 위치


    Returns:
        List[Tuple[str, int, float]]: 날짜, 레벨, 경험치 퍼센트 데이터 (1주일치)
        (예: ("2023-10-01", 250, "75.321%"))

    Raises:
        1일전 데이터 호출 실패한 경우: 2일전 데이터 호출
        NexonAPIError: API 호출 오류

    Notes:
        search_end는 자동으로 캐릭터의 생성날짜 or API 서비스 오픈날짜로 설정

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14
    """

    kst_now: datetime = datetime.now(tz=timezone("Asia/Seoul"))
    if kst_now.hour < 6:
        time_offset: int = 2
    else:
        time_offset: int = 1
    
    start_date = kst_now.date() - timedelta(days=time_offset)

    if search_end < API_MAX_DATE_SEARCH_END or search_end is None:
        search_end = API_MAX_DATE_SEARCH_END

    search_index_date = start_date
    search_end_date = search_end.date()
    return_data: List[Tuple[str, int, str]] = []
    search_flag_exp = 0

    # 경험치 변동이 있는 최근 7일치 데이터 수집
    while len(return_data) < 7 and search_index_date >= search_end_date:
        index_date: str = search_index_date.strftime("%Y-%m-%d")

        basic_info_data: dict = await get_basic_info(character_ocid, date_param=index_date)
        character_level: int = (
            int(basic_info_data.get("character_level", -1))
            if basic_info_data.get("character_level") is not None
            else -1
        )
        character_exp_rate: str = (
            str(basic_info_data.get("character_exp_rate")).strip()
            if basic_info_data.get("character_exp_rate") is not None
            else "0.000%"
        )
        character_exp: int = (
            int(basic_info_data.get("character_exp", -1))
            if basic_info_data.get("character_exp") is not None
            else -1
        )

        # 경험치가 변동된 경우에만 데이터 추가
        if character_exp != search_flag_exp:
            return_data.append((index_date, character_level, character_exp_rate))
            search_flag_exp = character_exp

        # 7일치 데이터 수집 완료 시 종료
        if len(return_data) >= 7:
            break

        # 검색 종료일 도달 시 종료
        if search_index_date == search_end_date:
            break
        
        # 1일 전으로 이동
        search_index_date -= timedelta(days=1)

    return return_data


async def get_basic_info(ocid: str, date_param: Optional[str] = None) -> Optional[Dict[str, Any]] | bool:
    """메이플스토리 캐릭터 기본 정보 데이터를 가져와서 가공하는 함수

    Args:
        ocid (str): 캐릭터 OCID
        date_param (str | None, default None): 조회 기준 날짜 (None: 실시간 정보)

    Returns:
        dict: 가공된 캐릭터 기본 정보 데이터
    """
    character_ocid: str = ocid

    service_url = MaplestoryUrls.BASIC_INFO
    if date_param is not None and isinstance(date_param, str):
        requests_url = f"{NEXON_API_HOME}{service_url}?ocid={character_ocid}&date={date_param}"
    else:
        requests_url = f"{NEXON_API_HOME}{service_url}?ocid={character_ocid}"

    response_data: dict = await general_request_handler_nexon(requests_url)

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
    else:
        return False

    return return_data


async def get_stat_info(character_ocid: str) -> Optional[Dict[str, Any]] | None:
    """메이플스토리 캐릭터 상세 정보 데이터를 가공하는 함수

    Args:
        character_ocid (str) : 스탯 데이터를 조회할 캐릭터 OCID

    Returns:
        dict: 가공된 캐릭터 상세 정보 데이터
    """
    service_url = MaplestoryUrls.STAT_INFO
    requests_url = f"{NEXON_API_HOME}{service_url}?ocid={character_ocid}"
    response_data: dict = await general_request_handler_nexon(requests_url)
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

    else:
        raise NexonAPIError("Invalid stat data format")


def parse_equipment_info() -> None:
    """캐릭터 장착 장비 아이템 정보 파싱 함수

    Notes:
        - 추후 구현 예정
    """
    pass


async def get_item_equipment_info(
        character_ocid: str,
        date_param: Optional[str] = None
    ) -> Dict[str, Optional[Any]] | None:
    """캐릭터의 장착중인 장비 아이템 정보를 조회/가공하는 함수

    Args:
        character_ocid (str): 메이플스토리 캐릭터 OCID
        date_param (str | None, Optional): 조회 기준 날짜 (None: 실시간 정보). Defaults to None.

    Returns:
        Dict[str, Optional[Any]]: 가공된 캐릭터 장착 장비 아이템 정보
        예시) 
        {
            "모자" : { ... },
        }

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14
    """
    service_url = MaplestoryUrls.ITEM_EQUIPMENT
    if date_param is not None and isinstance(date_param, str):
        request_url = f"{NEXON_API_HOME}{service_url}?ocid={character_ocid}&date={date_param}"
    else:
        request_url = f"{NEXON_API_HOME}{service_url}?ocid={character_ocid}"

    response_data: dict = await general_request_handler_nexon(request_url)

    # 응답데이터 가공
    """장착 슬롯 별로 장비 데이터 정보 추출
    
    - 현재 사용중인 프리셋 번호
    - 현재 장착중인 장비정보
    - 1번 프리셋 장비정보
    - 2번 프리셋 장비정보
    - 3번 프리셋 장비정보
    
    약 1만 줄의 데이터를 모두 파싱, 성능 이슈가 발생하면 추후 개선 필요
    """

    def _parse_equipment_slot_data(equipment_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        장비 슬롯 별 장비 데이터 파싱 내부 함수

        List[Dict[str, Any]] 형태의 장비 데이터를 장착부위별로 Key 설정

        만약 장착하지 않은 빈 슬롯인 경우, None 값으로 설정
        
        Args:
            equipment_data (List[Dict[str, Any]]): 장비 데이터 목록

        Returns:
            Dict[str, Any]: 슬롯명(Key) : 장비정보(Value) 형태의 딕셔너리 데이터
        """
        return_parse_data: Dict[str, Any] = {
            "모자": None,
            "얼굴장식": None,
            "눈장식": None,
            "귀고리": None,
            "상의": None,
            "하의": None,
            "신발": None,
            "장갑": None,
            "망토": None,
            "보조무기": None,
            "무기": None,
            "반지1": None,
            "반지2": None,
            "반지3": None,
            "반지4": None,
            "펜던트": None,
            "훈장": None,
            "벨트": None,
            "어깨장식": None,
            "포켓 아이템": None,
            "기계 심장": None,
            "뱃지": None,
            "엠블렘": None,
            "펜던트2": None,
        }
        for slot in equipment_data:
            slot_name: str = str(slot.get("item_equipment_slot")).strip()
            return_parse_data[slot_name] = slot
        return return_parse_data

    equipment_data: List[Dict[str, Any]] = response_data.get("item_equipment")
    return_data: Dict[str, Any] = _parse_equipment_slot_data(equipment_data=equipment_data)
    return return_data


async def get_cash_equipment_info(
        character_ocid: str,
        date_param: Optional[str] = None,
        look_mode_pin: Optional[str] = None
    ) -> Dict[str, Optional[Any]]:
    """캐릭터의 장착중인 장착효과 및 외형 캐시 아이템 정보를 조회하는 함수

    Args:
        character_ocid (str): 메이플스토리 캐릭터 OCID
        date_param (str | None, Optional): 조회 기준 날짜 (None: 실시간 정보). Defaults to None.
        look_mode_pin (str | None, Optional): 외형 모드 값 (0: 기본, 1: 드레스업/베타). Defaults to None.

    Returns:
        Dict[str, Optional[Any]]: 가공된 캐릭터 장착중인 캐시 아이템 정보

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14
    """
    service_url = MaplestoryUrls.CASH_EQUIPMENT
    if date_param is not None and isinstance(date_param, str):
        request_url = f"{NEXON_API_HOME}{service_url}?ocid={character_ocid}&date={date_param}"
    else:
        request_url = f"{NEXON_API_HOME}{service_url}?ocid={character_ocid}"
    response_data: dict = await general_request_handler_nexon(request_url)

    
    return_data = {
        # 캐릭터 성별
        "character_gender": (
            str(response_data.get("character_gender")).strip()
            if response_data.get("character_gender") is not None
            else "기타"
        ),
        # 캐릭터 직업
        "character_class": (
            str(response_data.get("character_class")).strip()
            if response_data.get("character_class") is not None
            else "기타"
        ),
        # 캐릭터 외형 모드 (0: 기본, 1: 드레스업/베타)
        "character_look_mode": (
            look_mode_pin
            if look_mode_pin is not None and isinstance(look_mode_pin, str)
            else response_data.get("character_look_mode")  # 기본 외형 모드
        ),

        # 현재 프리셋 번호
        "current_preset_no": (
            int(response_data.get("preset_no"))
            if response_data.get("preset_no") is not None
            else None
        ),
        # 장착중인 캐시 아이템 정보
        "equipment_base_list": (
            response_data.get("cash_item_equipment_base", [])
        ),
        "additional_equipment_base_list": (
            response_data.get("additional_cash_item_equipment_base", [])
        )
    }
    if return_data["character_look_mode"] is None:
        return_data["character_look_mode"] = "0"
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


def get_current_beauty_equipment_info(
        current_beauty_equipment_data: Dict[str, str | Dict[str, str] | None],
        look_mode: str = "0"
    ) -> Dict[str, Dict[str, str]]:
    """캐릭터의 뷰티(헤어/성형) 정보 가공하는 함수

    Args:
        current_beauty_equipment_data (Dict[str, str | Dict[str, str] | None]): 캐릭터 뷰티 장비 정보
        look_mode (str, optional): 캐릭터 외형 모드 (0: 기본, 1: 드레스업/베타). Defaults to "0".

    Returns:
        Dict[str, str]: 가공된 뷰티 장비 정보
    """
    if look_mode == "0":
        hair_info = current_beauty_equipment_data.get("character_hair")
        face_info = current_beauty_equipment_data.get("character_face")
        skin_info = current_beauty_equipment_data.get("character_skin")
    else:
        hair_info = current_beauty_equipment_data.get("additional_character_hair")
        face_info = current_beauty_equipment_data.get("additional_character_face")
        skin_info = current_beauty_equipment_data.get("additional_character_skin")

    return_info: Dict[str, Dict[str, str]] = {
        "hair" : hair_info,
        "face" : face_info,
        "skin" : skin_info
    }

    return return_info


def get_current_cash_equipment_info(
        current_cash_equipment_data: Dict[str, Optional[Any]]
    ) -> Dict[str, Dict[str, str]]:
    """캐릭터의 장착중인 캐시 아이템 정보를 가공하는 함수

    Args:
        current_cash_equipment_data (Dict[str, Optional[Any]]): 캐릭터 장착중인 캐시 아이템 정보

        장착 아이템 -> 외형 아이템(프리셋) 순서로 데이터 덮어쓰기 처리

    Returns:
        Dict[str, Dict[str, str]]: 부위별 장착 캐시 아이템 정보
    """
    return_info: Dict[str, Dict[str, str]] = {}
    base_equipment_map: List[Dict[str, Any]] = current_cash_equipment_data.get("equipment_base_list")
    for base in base_equipment_map:
        part_name: str = base.get("cash_item_equipment_part", "알수없음") # 장착 장비 종류
        slot_name: str = base.get("cash_item_equipment_slot", "알수없음") # 장착 부위
        item_name: str = base.get("cash_item_name", "알수없음") # 캐시 아이템 이름
        item_icon: str = base.get("cash_item_icon", "") # 캐시 아이템 아이콘 URL
        item_label: str = base.get("cash_item_label") or "없음"
        item_coloring_prism: str = base.get("cash_item_coloring_prism") or "없음"
        item_gender: str = base.get("item_gender") or "공용"
        freestyle_flag: str = base.get("freestyle_flag") or "0" # 프리스타일 쿠폰 사용 여부

        return_info[slot_name] = {
            "part_name": part_name,
            "item_name": item_name,
            "item_icon": item_icon,
            "item_label": item_label,
            "item_coloring_prism": item_coloring_prism,
            "item_gender": item_gender,
            "freestyle_flag": freestyle_flag
        }

    look_equipment_map: List[Dict[str, Any]] = current_cash_equipment_data.get("equipment_look_list")
    for look in look_equipment_map:
        part_name: str = look.get("cash_item_equipment_part", "알수없음") # 장착 장비 종류
        slot_name: str = look.get("cash_item_equipment_slot", "알수없음") # 장착 부위
        item_name: str = look.get("cash_item_name", "알수없음") # 캐시 아이템 이름
        item_icon: str = look.get("cash_item_icon", "") # 캐시 아이템 아이콘 URL
        item_label: str = look.get("cash_item_label") or "없음"
        item_coloring_prism: str = look.get("cash_item_coloring_prism") or "없음"
        item_gender: str = look.get("item_gender") or "공용"
        freestyle_flag: str = look.get("freestyle_flag") or "0" # 프리스타일 쿠폰 사용 여부

        # 덮어쓰기 처리
        return_info[slot_name] = {
            "part_name": part_name,
            "item_name": item_name,
            "item_icon": item_icon,
            "item_label": item_label,
            "item_coloring_prism": item_coloring_prism,
            "item_gender": item_gender,
            "freestyle_flag": freestyle_flag
        }

    return return_info


async def get_beauty_equipment_info(
        ocid: str,
        param_date: Optional[str] = None,
    ) -> Dict[str, Optional[str | Dict[str, str]]]:
    """캐릭터의 뷰티(헤어/성형) 정보 조회

    Args:
        ocid (str): 캐릭터 OCID
        param_date (Optional[str]): 조회날짜 (None = 실시간)
    """
    service_url = MaplestoryUrls.BEAUTY_EQUIPMENT
    if param_date is not None and isinstance(param_date, str):
        request_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}&date={param_date}"
    else:
        request_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}"
    response_data: dict = await general_request_handler_nexon(request_url)

    return response_data


async def get_cordinate_collections(ocid: str, search_end: datetime | None) -> List[Tuple[str, str]]:
    """캐릭터의 코디 목록 조회 (최대 8개, 멮지지 컬렉션 기능 참고)

    Args:
        ocid (str): 캐릭터 OCID
        search_end (Optional[datetime]): 검색 중단 위치

    Returns:
        io.BytesIO: 캐릭터 코디 목록 이미지

    Notes:
        search_end는 자동으로 캐릭터 생성 날짜 or API 서비스 오픈 날짜로 변경
    """
    kst_now: datetime = datetime.now(tz=timezone("Asia/Seoul"))

    if kst_now.hour < 6:
        time_offset: int = 2
    else:
        time_offset: int = 1

    search_start_date = kst_now.date() - timedelta(days=time_offset)

    if search_end < API_MAX_DATE_SEARCH_END or search_end is None:
        search_end = API_MAX_DATE_SEARCH_END

    # 1일전 캐릭터 외형 이미지 URL 수집
    search_index_date = search_start_date
    search_end_date = search_end.date()

    cordinate_collections: List[Tuple[str, str]] = []
    collections_length: int = 4 if NEXON_API_RPS_LIMIT == 5 else 8 # dev 환경에선 4개로 제한
    daily_cordinate_info_list: List[Dict[str, Any]] = []
    current_cash_info = await get_cash_equipment_info(ocid)
    look_mode_pin: str = current_cash_info.get("character_look_mode", "0")

    while len(cordinate_collections) < collections_length and search_index_date >= search_end_date:
        index_date: str = search_index_date.strftime("%Y-%m-%d")

        # index_date 기준 캐릭터 장착중인 캐시 아이템 정보 조회 -> 외형 모드 확인
        cash_equipment_data: dict = await get_cash_equipment_info(ocid, date_param=index_date)
        cash_equipment_data["character_look_mode"] = look_mode_pin  # 외형 모드 고정
        beauty_equipment_data: dict = await get_beauty_equipment_info(ocid, param_date=index_date)

        # 캐릭터 외관을 구성하는 정보 가공
        cash_info = get_current_cash_equipment_info(cash_equipment_data)
        beauty_info = get_current_beauty_equipment_info(beauty_equipment_data, look_mode=look_mode_pin)
        # 중복을 체크하기 위한 형태로 변환
        daily_cordinate_info = {
            "cash_info": cash_info,
            "beauty_info": beauty_info
        }

        # index_date 기준 캐릭터 기본 정보 조회 -> 이미지 URL 추출
        basic_info_data: dict = await get_basic_info(ocid, date_param=index_date)
        character_image: str = basic_info_data.get("character_image", "")
        character_image_url = get_character_image_url(character_image)

        # (중복체크) 중복하지 않은 dictionary 데이터만 리스트에 추가
        if daily_cordinate_info not in daily_cordinate_info_list and character_image_url != "":
            collections = (index_date, character_image_url)
            cordinate_collections.append(collections)
            daily_cordinate_info_list.append(daily_cordinate_info)

        # 4개 코디 데이터 수집 완료 혹은 검색 종료일 도달 시 종료
        if len(cordinate_collections) >= collections_length:
            break

        if search_index_date == search_end_date:
            break

        # 1일 전으로 이동
        search_index_date -= timedelta(days=1)

    # 코디 데이터가 없는 경우, 빈 리스트 반환
    if not cordinate_collections:
        return []
    else:
        return cordinate_collections


def _load_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        if font_path:
            return ImageFont.truetype(font_path, size)
        else:
            return ImageFont.truetype(ImageBaseConfig.DEFAULT_FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()
    
# Image 객체 생성
def _rounded(im: Image.Image, rad: int) -> Image.Image:
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    w, h = im.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([(0, 0), (w, h)], radius=rad, fill=255)
    return_im = Image.new("RGBA", (w, h))
    return_im.paste(im, (0, 0), mask)
    return return_im

async def _fetch_image(client: httpx.AsyncClient, url: str) -> Optional[Image.Image]:
    try:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGBA")
        return image
    except (httpx.HTTPError, UnidentifiedImageError):
        return None

def _placeholder() -> Image.Image:
    return Image.open(CordinateVars.PLACE_HOLDER_IMAGE_PATH).convert("RGBA")


async def generate_cordinate_collection_image(collection: List[Tuple[str, str]], title: str) -> io.BytesIO:
    """캐릭터의 코디 목록 이미지 생성

    Args:
        collection (List[Tuple[str, str]]): 캐릭터 코디 목록 데이터
        title (str): 이미지 상단에 표시할 제목

    Returns:
        io.BytesIO: 캐릭터 코디 목록 이미지
    """
    if not isinstance(collection, list) or not collection:
        raise ValueError("collection must be a non-empty list")

    if not isinstance(title, str) or not title:
        raise ValueError("title must be a non-empty string")

    items = (collection[:8] or [])[: MapleCodiHistoryConfig.IMAGE_GRID_COLS * MapleCodiHistoryConfig.IMAGE_GRID_ROWS]

    # 캔버스 크기 계산
    cell_w = MapleCodiHistoryConfig.IMAGE_SIZE
    cell_h = MapleCodiHistoryConfig.IMAGE_SIZE + MapleCodiHistoryConfig.CAPTION_HEIGHT

    n = len(items)
    rows = math.ceil(n / MapleCodiHistoryConfig.IMAGE_GRID_COLS)
    grid_w = (MapleCodiHistoryConfig.IMAGE_GRID_COLS * cell_w +
             (MapleCodiHistoryConfig.IMAGE_GRID_COLS - 1) * MapleCodiHistoryConfig.CELL_PADDING_SIZE)
    grid_h = rows * cell_h + (rows - 1) * MapleCodiHistoryConfig.CELL_PADDING_SIZE
    title_h = 0
    font_title = None
    if title:
        title_font_size = MapleCodiHistoryConfig.FONT_SIZE + 6
        font_title = ImageTools.load_font(font_path=MapleCodiHistoryConfig.TITLE_FONT_PATH,
                                          font_size=title_font_size)
        title_h = title_font_size + MapleCodiHistoryConfig.TITLE_FONT_PADDING

    canvas_w = grid_w + 2 * MapleCodiHistoryConfig.BOARD_MARGIN
    canvas_h = grid_h + 2 * MapleCodiHistoryConfig.BOARD_MARGIN + title_h

    # 캔버스 생성
    canvas = Image.new("RGBA", (canvas_w, canvas_h), MapleCodiHistoryConfig.BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # 제목 렌더링
    if title and font_title:
        tb = draw.textbbox((0, 0), title, font=font_title)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        tx = (canvas_w - tw) // 2
        ty = MapleCodiHistoryConfig.BOARD_MARGIN
        draw.text((tx, ty), title, font=font_title, fill=MapleCodiHistoryConfig.FG_COLOR)
        grid_origin_y = MapleCodiHistoryConfig.BOARD_MARGIN + title_h
    else:
        grid_origin_y = MapleCodiHistoryConfig.BOARD_MARGIN

    # 이미지 다운로드
    font_caption = ImageTools.load_font(font_path=MapleCodiHistoryConfig.CAPTION_FONT_PATH,
                                        font_size=MapleCodiHistoryConfig.FONT_SIZE)

    # 셀 안에 이미지 및 캡션 렌더링
    for idx, (date_str, url) in enumerate(items):
        row = idx // MapleCodiHistoryConfig.IMAGE_GRID_COLS
        col = idx % MapleCodiHistoryConfig.IMAGE_GRID_COLS
        x = MapleCodiHistoryConfig.BOARD_MARGIN + col * (cell_w + MapleCodiHistoryConfig.CELL_PADDING_SIZE)
        y = grid_origin_y + row * (cell_h + MapleCodiHistoryConfig.CELL_PADDING_SIZE)

        # 카드 배경 + 그림자
        # 그림자 렌더링
        shadow_offset = MapleCodiHistoryConfig.SHADOW_OFFSET
        shadow_rect = [x + shadow_offset[0], y + shadow_offset[1], x + cell_w, y+ cell_h]
        draw.rounded_rectangle(shadow_rect,
                               radius=MapleCodiHistoryConfig.CELL_RADIUS,
                               fill=MapleCodiHistoryConfig.CELL_SHADOW_COLOR)

        # 카드 배경 렌더링
        cord_rect = [x, y, x + cell_w, y + cell_h]
        draw.rounded_rectangle(cord_rect,
                               radius=MapleCodiHistoryConfig.CELL_RADIUS,
                               fill=MapleCodiHistoryConfig.CELL_BG_COLOR)

        # 이미지 렌더링
        im_bytes: io.BytesIO = convert_image_url_into_bytes(url)
        im = Image.open(im_bytes).convert("RGBA")
        thumb = ImageOps.fit(image=im,
                             size=(MapleCodiHistoryConfig.IMAGE_SIZE, MapleCodiHistoryConfig.IMAGE_SIZE),
                             method=Image.Resampling.LANCZOS)
        thumb = ImageTools.make_rounded(thumb, radius=MapleCodiHistoryConfig.CELL_RADIUS)
        canvas.paste(thumb, (x, y), thumb)

        # 캡션 렌더링
        caption_y = y + MapleCodiHistoryConfig.IMAGE_SIZE + (MapleCodiHistoryConfig.CAPTION_HEIGHT // 2)
        tb = draw.textbbox((0, 0), date_str, font=font_caption)
        tw = tb[2] - tb[0]
        draw.text(xy= (x + (cell_w - tw) // 2, caption_y - MapleCodiHistoryConfig.FONT_SIZE // 2),
                  text=date_str, font=font_caption, fill=MapleCodiHistoryConfig.FG_COLOR)

    # 이미지 저장
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


async def generate_item_equipment_image(collection: Dict[str, Any], preset: int | None = None) -> io.BytesIO:
    """
    메이플스토리 장비창 이미지 생성

    Args:
        collection (dict): 현재 메이플스토리 캐릭터 장착 장비
        preset      (int): 조회하고 싶은 장비 프리셋 번호 (기본값: 현재장착중인 장비로 설정)

    Returns:
        equipment_image: 메이플스토리 장비창 이미지
    """
    cell_w = 1


def parse_distribution_meso(reward: str) -> int:
    """
    메이플스토리 보스 분배금을 파싱하는 함수

    Args:
        reward       (str): 디스코드 메세지에 포함된 보상내용

    Returns:
        party_reward (int): 파싱 함수가 인식한 최종 보상내용

    Notes:
        - 메이플스토리 소지 환도: (2조 - 1)메소
        - 1,200,000메소 -> 1_200_000 (int)로 변환
        - 33억 메소 -> 3_300_000_000 (int)로 변환
    """
    # 1. "," "메소" 문구 삭제, strip
    if "메소" in reward:
        reward_str: str = reward.split("메소")[0].replace(",", "").strip()
    else:
        reward_str: str = reward.replace(",", "").strip()

    # 1. 진행 후 단순 숫자만 남아 있다면 바로 return
    if reward_str.isdigit():
        party_reward = int(reward_str)
        return party_reward

    # 2. 아니라면, 조, 억, 만 단위를 구분해서 변환
    else:
        total_reward = 0
        units = {
            "조": 1_000_000_000_000,
            "억":       100_000_000,
            "만":            10_000,
        }

        current_num = ""
        for char in reward_str:
            if char.isdigit() or char == '.':
                current_num += char
            elif char in units:
                if current_num:
                    total_reward += int(float(current_num) * units[char])
                    current_num = ""

        if current_num:  # 단위 없이 끝에 남은 숫자 처리
            total_reward += int(current_num)

        party_reward = total_reward
        return party_reward


# 테스트 코드 실행
def main():
    import os
    test_api_key: str = os.environ.get("NEXON_API_TOKEN_TEST")
    test_ocid: str = os.environ.get("NEXON_API_DEBUG_OCID")

    test_item_equipment_info = asyncio.run(get_item_equipment_info(test_ocid))
    print(test_api_key, test_ocid)

if __name__ == "__main__":
    main()