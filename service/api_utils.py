import hashlib
import math
import random
from matplotlib import patches
import matplotlib.axes
import requests
import io
import re
import time
from urllib.parse import quote
from datetime import datetime, timedelta
from pytz import timezone

from config import NEXON_API_HOME, NEXON_API_KEY # NEXON OPEN API
from config import KKO_LOCAL_API_KEY, KKO_API_HOME # KAKAO Local API
from config import WTH_DATA_API_KEY, WTH_API_HOME # Weather API
from config import NEOPLE_API_KEY, NEOPLE_API_HOME # Neople Developers API
from service.api_exception import *

from typing import Optional, Dict, List, Tuple, Any


def general_request_handler_neople(request_url: str, headers: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    """Neople API의 일반적인 요청을 처리하는 함수

    Args:
        request_url (str): 요청할 URL
        headers (Optional[dict], optional): 요청 헤더 (기본값 None)
        params (Optional[dict], optional): 요청 파라미터 (기본값 None)

    Returns:
        dict: 응답 데이터

    Raises:
        Exception: 요청 오류에 대한 예외를 발생

    Reference:
        https://developers.neople.co.kr/contents/guide/pages/all  
        Neople API의 경우 response_status마다 세부적인 error_code가 존재
    """
    if headers is None:
        headers = {
            "apikey": f"{NEOPLE_API_KEY}",
        }

    response: requests.Response = requests.get(url=request_url, headers=headers)

    if response.status_code != 200:
        response_data: dict = response.json()
        error_data: dict = response_data.get('error', {})
        neople_api_error_code: str = str(error_data.get('code', 'Unknown'))
        neople_api_error_handler(error_code=neople_api_error_code)
    else:
        response_data: dict = response.json()
        return response_data


def general_request_handler_nexon(request_url: str, headers: Optional[dict] = None) -> dict:
    """Nexon Open API의 일반적인 요청을 처리하는 함수  
    요청 URL과 헤더를 받아서 GET 요청을 수행하고, 응답 데이터를 반환함

    Args:
        request_url (str): 요청할 URL
        headers (Optional[dict], optional): 요청 헤더. Defaults to None.

    Returns:
        dict: 응답 데이터

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    if headers is None:
        headers = {
            "x-nxopen-api-key": NEXON_API_KEY,
        }

    response: requests.Response = requests.get(url=request_url, headers=headers)

    # general_request_error_handler 함수 통합 (2025.09.01)
    if response.status_code != 200:
        response_status_code: str = str(response.status_code)
        exception_msg_prefix: str = f"{response_status_code} : "
        response_data: dict = response.json()
        exception_msg: dict = response_data.get('error')
        if response.status_code == 400:
            default_exception_msg = "Bad Request"
            exception_msg = f"{exception_msg_prefix}{exception_msg.get('message', default_exception_msg)}"
            raise NexonAPIBadRequest(exception_msg)
        elif response.status_code == 403:
            default_exception_msg = "Forbidden"
            exception_msg = f"{exception_msg_prefix}{exception_msg.get('message', default_exception_msg)}"
            raise NexonAPIForbidden(exception_msg)
        elif response.status_code == 429:
            default_exception_msg = "Too Many Requests"
            exception_msg = f"{exception_msg_prefix}{exception_msg.get('message', default_exception_msg)}"
            raise NexonAPITooManyRequests(exception_msg)
        elif response.status_code == 500:
            default_exception_msg = "Internal Server Error"
            exception_msg = f"{exception_msg_prefix}{exception_msg.get('message', default_exception_msg)}"
            raise NexonAPIServiceUnavailable(exception_msg)
        else:
            if not exception_msg.get('message'):
                raise NexonAPIError
            else :
                exception_msg = f"{exception_msg_prefix}{exception_msg.get('message')}"
                raise NexonAPIError(exception_msg)
    return response.json()


def get_ocid(character_name: str) -> str:
    """character_name의 OCID를 검색

    Args:
        character_name (str): 캐릭터 이름
        캐릭터 이름을 base64로 인코딩하여 Nexon Open API를 통해 OCID를 검색

    Returns:
        str: OCID (string)

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14

    Raises:
        Reference에 있는 URL 참조
        (예외처리는 함수 밖에서 처리)
    """
    service_url = f"/maplestory/v1/id"
    url_encode_name: str = quote(character_name)
    request_url = f"{NEXON_API_HOME}{service_url}?character_name={url_encode_name}"
    response_data: dict = general_request_handler_nexon(request_url)
    
    # 정상적으로 OCID를 찾았을 때
    ocid: str = str(response_data.get('ocid'))
    if ocid:
        return ocid
    else:
        raise NexonAPIOCIDNotFound("OCID not found in response")


def get_character_popularity(ocid: str) -> str:
    """OCID에 해당하는 캐릭터의 인기도를 가져오는 함수

    Args:
        ocid (str): 캐릭터 OCID

    Returns:
        str: 캐릭터의 인기도

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    service_url = f"/maplestory/v1/character/popularity"
    request_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}"
    try:
        response_data: dict = general_request_handler_nexon(request_url)
        popularity: int = response_data.get('popularity', "몰라양")
        return popularity
    except NexonAPIError:
        return "몰라양"  # 예외 발생 시 기본값으로 "몰라양" 반환


def get_character_ability_info(ocid: str) -> dict:
    """OCID에 해당하는 캐릭터의 어빌리티 정보를 가져오는 함수

    Args:
        ocid (str): 캐릭터 OCID

    Returns:
        dict: 캐릭터의 어빌리티 정보
    """
    service_url = f"/maplestory/v1/character/ability"
    request_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}"
    response_data: dict = general_request_handler_nexon(request_url)
    return response_data


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
def _compile_patterns():
    compiled = []
    for pat, grade_map in ABILITY_MAX_TABLE.items():
        rx = pat.replace("{n}", r"(?P<value>\d+(?:\,\d+)?)")
        rx = rf"^\s*(?P<head>{rx})\s*$"
        compiled.append((re.compile(rx), grade_map))
    return compiled

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


def get_notice(target_event: str = None) -> list[dict]:
    """Nexon Open API를 통해 메이플스토리 공지사항을 가져오는 함수

    Args:
        target_event (str, optional): 특정 이벤트에 대한 공지사항을 필터링할 수 있음. 기본값은 None.

    Returns:
        list[dict]: 공지사항 목록

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=24
    """
    service_url = f"/maplestory/v1/notice-event"
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

    return notices


def get_notice_details(notice_id: str) -> dict:
    """Nexon Open API를 통해 특정 공지사항의 상세 정보를 가져오는 함수

    Args:
        notice_id (str): 공지사항 ID

    Returns:
        dict: 공지사항 상세 정보

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    service_url = f"/maplestory/v1/notice-event/detail"
    request_url = f"{NEXON_API_HOME}{service_url}?notice_id={notice_id}"
    response_data: dict = general_request_handler_nexon(request_url)
    return response_data


def get_image_bytes(image_url: str) -> bytes:
    """이미지 URL로부터 이미지 바이트를 가져오는 함수

    Args:
        image_url (str): 이미지 URL

    Returns:
        bytes: 이미지 바이트

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    response = requests.get(image_url)
    if response.status_code != 200:
        raise BotCommandError(f"Failed to fetch image from {image_url}")
    else:
        image_bytes = io.BytesIO(response.content)
    
    return image_bytes


def convert_grid(lat: float, lon: float) -> tuple:
    """ 위도/경도를 기상청 기준 격자 좌표로 반환

    Args:
        lat (float): 위도 (local_y)
        lon (float): 경도 (local_x)

    Returns:
        tuple: 변환된 격자 좌표 (con_x, con_y)
        con_x (int): 위도에서 변환된 x 좌표
        con_y (int): 경도에서 변환된 y 좌표

    Reference:
        https://gist.github.com/fronteer-kr/14d7f779d52a21ac2f16
        https://www.data.go.kr/data/15084084/openapi.do
    """
    pi = math.pi
    # 예시로 단순히 입력값을 그대로 반환
    RE = 6371.00877  # 지구 반지름 (km)
    GRID = 5.0       # 격자 크기 (km)
    SLAT1 = 30.0     # 기준 위도 1 (degrees)
    SLAT2 = 60.0     # 기준 위도 2 (degrees)
    OLON = 126.0     # 기준 경도 (degrees)
    OLAT = 38.0      # 기준 위도 (degrees)
    XO = 43          # 기준 격자 x 좌표
    YO = 136         # 기준 격자 y 좌표

    DEGRAD = pi / 180.0
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(pi * 0.25 + slat2 * 0.5) / math.tan(pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(pi * 0.25 + slat1 * 0.5)
    sf = (sf ** sn) * math.cos(slat1) / sn
    ro = math.tan(pi * 0.25 + olat * 0.5)
    ro = re * sf / (ro ** sn)
    ra = math.tan(pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / (ra ** sn)
    theta = lon * DEGRAD - olon

    if theta > pi:
        theta -= 2.0 * pi
    if theta < -pi:
        theta += 2.0 * pi
    theta *= sn

    con_x = int(ra * math.sin(theta) + XO + 0.5)
    con_y = int(ro - ra * math.cos(theta) + YO + 0.5)
    return con_x, con_y


def get_local_info(local_name: str) -> dict:
    """ KAKAO API를 통해 지역의 위치 정보 조회

    Args:
        str (local_name): 지역 이름 혹은 주소

    Returns:
        dict: 지역의 위치 정보

    Reference:
        https://developers.kakao.com/docs/latest/ko/local/dev-guide#search-by-address
    """
    url = f"{KKO_API_HOME}.json?query={local_name}"
    headers = {
        "Authorization": f"KakaoAK {KKO_LOCAL_API_KEY}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        status_code: int = response.status_code
        error_info: dict = response.json()
        error_type: str = error_info.get('errorType', 'Unknown Error')
        error_text: str = error_info.get('message', 'No message provided')
        exception_msg: str = f"[{status_code}] {error_type}: {error_text}"
        raise KKO_LOCAL_API_ERROR(exception_msg)
    else:
        response_data: dict = response.json()
        local_info = response_data.get('documents')
        # 검색 결과가 없는 경우
        if not local_info:
            raise KKO_NO_LOCAL_INFO("해당 지역 정보를 찾을 수 없어양")
        # 검색 결과가 있는 경우 첫 번째 결과 반환
        else:
            return local_info[0]
        

def process_weather_ncst(raw: dict) -> dict:
    """기상청 API로부터 받은 초단기실황 데이터를 전처리하는 함수

    Args:
        raw (dict): 기상청 API로부터 받은 초단기실황 데이터

    Returns:
        dict: 전처리된 날씨 정보
    """
    ncst_local_data: List[dict] = raw.get("item", [])
    ncst_data: dict = {}

    for item in ncst_local_data:
        # 자료구분 코드 (PTY, REH, RN1, T1H, UUU, VVV, VEC, WSD)
        category: str = item.get("category")
        value: str = item.get("obsrValue")
        ncst_data[category] = value

    # 발표일자 및 시각
    base_date: str = (
        str(item.get('baseDate'))
        if item.get('baseDate') is not None
        else '알수없음'
    )
    base_time: str = (
        str(item.get('baseTime'))
        if item.get('baseTime') is not None
        else '알수없음'
    )
    base_date_ymd: str = f"{base_date[:4]}년 {base_date[4:6]}월 {base_date[6:]}일"
    base_time_hm: str = f"{base_time[:2]}시 {base_time[2:]}분"

    # 전처리 결과 데이터 생성
    return_data: dict = {}
    return_data["ncst_time"] = f"{base_date_ymd} {base_time_hm}"

    # PTY: 강수 형태 코드
    rainsnow_flag: str = ncst_data.get("PTY", "몰라양")
    return_data["rainsnow_type"] = rainsnow_flag
    if rainsnow_flag == "0":
        return_data["rainsnow_type"] = "없음"
    elif rainsnow_flag == "1":
        return_data["rainsnow_type"] = "비"
    elif rainsnow_flag == "2":
        return_data["rainsnow_type"] = "비/눈"
    elif rainsnow_flag == "3":
        return_data["rainsnow_type"] = "눈"
    elif rainsnow_flag == "5":
        return_data["rainsnow_type"] = "빗방울"
    elif rainsnow_flag == "6":
        return_data["rainsnow_type"] = "빗방울/눈날림"
    elif rainsnow_flag == "7":
        return_data["rainsnow_type"] = "눈날림"
    else:
        return_data["rainsnow_type"] = "알수없음"

    # REH: 습도 (%)
    return_data["humidity"] = f"{ncst_data.get('REH', '알수없음')}%"

    # RN1: 1시간 강수량 (mm)
    rains: str = ncst_data.get('RN1', '알수없음')
    return_data["rain_1h_value"] = rains

    if rains == "0":
        return_data["rain_1h_desc"] = "없음"
    else:
        rains_float: float = float(rains)
        if rains_float < 3.0:
            return_data["rain_1h_desc"] = "약한 비"
        elif rains_float < 15.0:
            return_data["rain_1h_desc"] = "보통 비"
        elif rains_float < 30.0:
            return_data["rain_1h_desc"] = "강한 비"
        elif rains_float < 50.0:
            return_data["rain_1h_desc"] = "매우 강한 비"
        else:
            return_data["rain_1h_desc"] = "⚠️ 폭우 ⚠️"

    # T1H: 기온 (℃)
    return_data["temperature"] = f"{ncst_data.get('T1H', '알수없음')}℃"

    # VEC: 풍향 (도, deg), WSD: 풍속 (m/s)
    vec: str = ncst_data.get('VEC', '알수없음')
    wsd: str = ncst_data.get('WSD', '알수없음')
    if vec == "999":
        return_data["wind_direction"] = "알수없음"
    else:
        return_data["wind_direction"] = get_wind_direction(wind_degree=float(vec))

    if wsd == "-998.9":
        return_data["wind_speed"] = "알수없음"
    else:
        return_data["wind_speed"] = f"{wsd} m/s"

    return return_data


def process_weather_fcst(raw: dict) -> dict:
    """기상청 API로부터 받은 초단기예보 데이터를 전처리하는 함수

    Args:
        raw (dict): 기상청 API로부터 받은 초단기예보 데이터

    Returns:
        dict: 전처리된 날씨 정보
    """
    fcst_local_data: List[dict] = raw.get("item", [])
    fcst_data: dict = {}

    for item in fcst_local_data:
        # 자료구분 코드 (PTY, REH, RN1, T1H, UUU, VVV, VEC, WSD, SKY)
        catgeory_check: str = item.get("category")
        if not fcst_data or catgeory_check not in fcst_data:
            fcst_data[catgeory_check] = []
        
        value: str = item.get("fcstValue")
        fcst_datetime_str: str = f"{item.get('fcstDate')}-{item.get('fcstTime')}"
        fcst_datetime: datetime = datetime.strptime(fcst_datetime_str, '%Y%m%d-%H%M')
        item_data: dict = {
            "fcst_datetime_str": fcst_datetime_str,
            "fcst_datetime": fcst_datetime,
            "value": value
        }
        try:
            fcst_data[catgeory_check].append(item_data)
        except KeyError:
            fcst_data[catgeory_check] = [item_data]

    # 기준 일자 및 시각
    base_date: str = (
        str(item.get('baseDate'))
        if item.get('baseDate') is not None
        else '알수없음'
    )
    base_time: str = (
        str(item.get('baseTime'))
        if item.get('baseTime') is not None
        else '알수없음'
    )
    base_date_ymd: str = f"{base_date[:4]}년 {base_date[4:6]}월 {base_date[6:]}일"
    base_time_hm: str = f"{base_time[:2]}시 {base_time[2:]}분"
    fcst_data["fcst_time"] = f"{base_date_ymd} {base_time_hm}"

    return fcst_data


def get_weather_info(local_x: str, local_y: str) -> dict:
    """기상청 API를 통해 지역의 날씨 정보 조회

    Args:
        local_x (str): weather API용 지역의 x 좌표 (경도)
        local_y (str): weather API용 지역의 y 좌표 (위도)

    Returns:
        dict: weather API를 통해 조회한 지역의 날씨 정보

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://www.data.go.kr/data/15084084/openapi.do
    """
    local_x: float = round(float(local_x), 6)
    local_y: float = round(float(local_y), 6)
    nx, ny = convert_grid(lat=local_y, lon=local_x)
    kst_now: datetime = datetime.now(timezone('Asia/Seoul'))

    # ncst 시간 보정 (15분 전)
    ncst_base_date: datetime = kst_now - timedelta(minutes=15)
    ncst_query_base_date: datetime = ncst_base_date.replace(second=0, microsecond=0)
    ncst_query_date: str = ncst_query_base_date.strftime('%Y%m%d')
    ncst_query_time: str = ncst_query_base_date.strftime('%H%M')

    # 초단기실황 조회 (getUltraSrtNcst)
    ncst_request_url = f"{WTH_API_HOME}/getUltraSrtNcst"
    ncst_request_params = {
        'ServiceKey': WTH_DATA_API_KEY,
        'numOfRows': 1000,
        'pageNo': 1,
        'dataType': 'JSON',
        'base_date': ncst_query_date,
        'base_time': ncst_query_time,
        'nx': nx,
        'ny': ny
    }
    ncst_response = requests.get(ncst_request_url, params=ncst_request_params)
    # 에러가 발생한 경우 (기상청은 에러가 발생해도 200을 반환함)
    ncst_response_json: dict = ncst_response.json()
    ncst_response_content: dict = ncst_response_json.get('response')
    ncst_response_result: dict = ncst_response_content.get('header')

    if ncst_response_result.get('resultCode') != '00':
        error_code: str = (
            str(ncst_response_result.get('resultCode')).strip()
            if ncst_response_result.get('resultCode') is not None
            else 'Unknown Error'
        )
        error_text: str = (
            str(ncst_response_result.get('resultMsg')).strip()
            if ncst_response_result.get('resultMsg') is not None
            else 'Unknown Error'
        )
        weather_exception_handler(error_code, error_text)
    else:
        # 정상적으로 응답이 온 경우
        ncst_response_data: dict = ncst_response_content.get("body")
        ncst_weather_data: dict = ncst_response_data.get("items", {})
        if ncst_weather_data:
            ncst_raw_data: dict = ncst_weather_data 
        else:
            raise WeatherAPIError("WTH_NO_WEATHER_DATA")

    # fcst 시간 보정 (30분 전, 30분 단위 절사)
    fcst_base_date: datetime = kst_now - timedelta(minutes=30)
    min_value: int = (fcst_base_date.minute // 30) * 30
    fcst_query_base_date: datetime = fcst_base_date.replace(minute=min_value, second=0, microsecond=0)
    fcst_query_date: str = fcst_query_base_date.strftime('%Y%m%d')
    fcst_query_time: str = fcst_query_base_date.strftime('%H%M')

    # 초단기예보 조회 (getUltraSrtFcst)
    fcst_request_url = f"{WTH_API_HOME}/getUltraSrtFcst"
    fcst_request_params = {
        'ServiceKey': WTH_DATA_API_KEY,
        'numOfRows': 1000,
        'pageNo': 1,
        'dataType': 'JSON',
        'base_date': fcst_query_date,
        'base_time': fcst_query_time,
        'nx': nx,
        'ny': ny
    }
    fcst_response = requests.get(fcst_request_url, params=fcst_request_params)
    # 에러가 발생한 경우 (기상청은 에러가 발생해도 200을 반환함)
    fcst_response_json: dict = fcst_response.json()
    fcst_response_content: dict = fcst_response_json.get('response')
    fcst_response_result: dict = fcst_response_content.get('header')

    if fcst_response_result.get('resultCode') != '00':
        error_code: str = (
            str(fcst_response_result.get('resultCode')).strip()
            if fcst_response_result.get('resultCode') is not None
            else 'Unknown Error'
        )
        error_text: str = (
            str(fcst_response_result.get('resultMsg')).strip()
            if fcst_response_result.get('resultMsg') is not None
            else 'Unknown Error'
        )
        weather_exception_handler(error_code, error_text)
    else:
        # 정상적으로 응답이 온 경우
        fcst_response_data: dict = fcst_response_content.get("body")
        fcst_weather_data: dict = fcst_response_data.get("items", {})
        if fcst_weather_data:
            fcst_raw_data: dict = fcst_weather_data
        else:
            raise WeatherAPIError("WTH_NO_WEATHER_DATA")
        
    # 초단기실황과 초단기예보 데이터를 전처리, 병합하여 반환
    ncst_data = process_weather_ncst(raw=ncst_raw_data)
    ncst_data["ncst_datetime_str"] = f"{ncst_query_base_date.strftime('%Y%m%d-%H%M')}"
    ncst_data["ncst_datetime"] = ncst_query_base_date
    fcst_data = process_weather_fcst(raw=fcst_raw_data)

    weather_data: dict = {
        "ncst": ncst_data,
        "fcst": fcst_data
    }
    return weather_data


def get_wind_direction(wind_degree: float) -> str:
    """기상청 API로부터 얻은 풍향 데이터 변환

    Args:
        wind_degree (float): 풍향 (도, deg)

    Returns:
        str: 풍향 (북, 북동, 동, 남동, 남, 남서, 서, 북서)
    """
    if isinstance(wind_degree, str):
        wind_degree = wind_degree.replace("m/s", "").strip()
        wind_degree = float(wind_degree)

    wind_directions = [
        "북", "북동", "동", "남동",
        "남", "남서", "서", "북서"
    ]

    idx = int((wind_degree + 22.5) % 360 // 45)
    return wind_directions[idx]


def get_sky_icon(sky_code: str) -> str:
    """기상청 API로부터 얻은 하늘 상태 코드에 따른 이모티콘 반환

    Args:
        sky_code (str): 하늘 상태 코드 (0~5: 맑음, 6~8: 구름많음, 9~10: 흐림)

    Returns:
        str: 하늘 상태에 따른 이모티콘
    """
    if not isinstance(sky_code, int):
        sky_code: int = int(sky_code)

    if 0 <= sky_code <= 5:
        return "맑음 ☀️"  # 맑음
    elif 6 <= sky_code <= 8:
        return "구름많음 ⛅"  # 구름많음
    elif 9 <= sky_code <= 10:
        return "흐림 ☁️"  # 흐림
    else:
        return f"알수없음 ❓ ({sky_code})"  # 알수없음


def get_fcst_text(fcst_text: str) -> str:
    """기상청 API로부터 얻은 예보 텍스트 변환

    Args:
        fcst_text (str): 예보 텍스트

    Returns:
        str: 변환된 예보 텍스트
    """
    return f"{fcst_text.strip()}\n" if fcst_text else ""


def neople_dnf_server_parse(server_name: str) -> str:
    """네오플 API 연동하여 dnf 서버 name - code 변환

    Args:
        server_name (str): dnf 서버 이름 (한글)

    Returns:
        str: dnf 서버 코드 (쿼리에 사용할 영어명)

    Reference:
        https://developers.neople.co.kr/contents/apiDocs/df
    """
    request_url = f"{NEOPLE_API_HOME}/df/servers?apikey={NEOPLE_API_KEY}"
    response_data: dict = general_request_handler_neople(request_url)
    
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
        raise NeopleAPIError(f"던전앤파이터 서버 정보를 찾을 수 없어양")

    # ServerId 조회를 못한 경우
    if return_server_id == "":
        raise NeopleAPIError(f"던파에 {search_server_name} 서버가 없어양")

    return return_server_id


def neople_dnf_get_character_id(server_name: str, character_name: str) -> str:
    """던전앤파이터 캐릭터의 고유 ID를 가져오는 함수

    Args:
        server_name (str): 서버 이름
        character_name (str): 캐릭터 이름

    Returns:
        str: 캐릭터 코드

    Raises:
        NeopleAPIError: API 호출 오류
    """
    server_id = neople_dnf_server_parse(server_name)
    character_name_encode = quote(character_name.strip())
    request_url = f"{NEOPLE_API_HOME}/df/servers/{server_id}/characters?characterName={character_name_encode}&apikey={NEOPLE_API_KEY}"
    response_data: dict = general_request_handler_neople(request_url)
    character_list: List[dict] = response_data.get("rows", [])
    character_info = character_list[0] if character_list else None
    if character_info:
        character_code = character_info.get("characterId", "")
        if character_code:
            return character_code
        else:
            raise NeopleAPIError(f"모험가 정보를 찾는데 실패했어양...")
    else:
        raise NeopleDNFInvalidCharacterInfo(f"{server_name}서버 {character_name}모험가 정보를 찾을 수 없어양")
    
def _mix_seed(base_seed: int, f_cate: str, salt: str) -> int:
    h = hashlib.md5(f"{base_seed}|{f_cate}|{salt}".encode('utf-8')).hexdigest()
    return int(h, 16)

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
    # 운세 메세지 작성 (메세지 * 가중치 -> 리스트에 저장 후 랜덤 선택)
    default_message_lv5: str = "오늘 운세가 매우 ㅆㅅㅌㅊ에양!!"
    default_message_lv4: str = "오늘 운세가 ㅅㅌㅊ에양!"
    default_message_lv3: str = "오늘 운세가 그냥 ㅍㅌㅊ에양."
    default_message_lv2: str = "오늘 운세가 ㅎㅌㅊ에양.."
    default_message_lv1: str = "오늘 운세가 ㅆㅎㅌㅊ에양 ㅋㅋ"
    DEFAULT_MESSAGE_COUNT_CONST: int = 3
    fortune_message_table: Dict[str, List[Tuple[str, int]]] = {
        # 스타포스 운세 메세지
        "StarForce_lv5": [
            (default_message_lv5, DEFAULT_MESSAGE_COUNT_CONST),
            ("오늘 엄청난 행운이 느껴져양! 지금 바로 스타포스 강화해양!", 5),
            ("오늘은 한방에 ⭐22성 가기 좋은 날씨에양!", 5),
            ("모두에게 장비를 자랑할 수 있는 절호의 기회에양!", 5),
            ("용사님의 클라스를 보여줄 최고의 기회에양!!", 5),
            ("온 우주가 스타포스 강화를 도와주는 날이에양!", 5),
            ("행운의 여신이 용사님에게 미소를 짓는 날이에양!", 5),
            ("눈감고 딸각 눌러도 성공하는 날이에양!!!", 5),
            ("스타포스해서 부자되면 븜미랑 신혼집 장만해양!!!🏩", 1),
        ],
        "StarForce_lv4": [
            (default_message_lv4, DEFAULT_MESSAGE_COUNT_CONST),
            ("잘하면? 22성? 갈 수 있을것? 같아양!", 5),
            ("오늘 스타포스 해보는게 어때양? 행운이 느껴져양!", 5),
            ("별빛의 기운이 용사님을 도와줄거에양!⭐", 5),
            ("여유있게 스타포스를 눌러보는게 어떨까양?", 5),
            ("오늘은 제가 강화해도 성공하는 날이에양!", 5),
            ("왠지 대박의 기운이 느껴져양. 성공하면 저한테 뽀찌주세양!🤑", 5),
        ],
        "StarForce_lv3": [
            (default_message_lv3, DEFAULT_MESSAGE_COUNT_CONST),
            ("오늘은 무난한 날이에양. 스타포스도 무난하게 붙을거에양.", 5),
            ("별(⭐) 일 없을 거에양.", 7),
            ("스타포스 성공하거나 실패하거나 파괴되거나에양.", 5),
            ("겁내지 말고 딱 한번만 눌러봐양.", 5),
            ("아무일 없듯이 지나갈 거에양.", 5),
            ("평범하게 스타포스 눌러보세양.", 5),
        ],
        "StarForce_lv2": [
            (default_message_lv2, DEFAULT_MESSAGE_COUNT_CONST),
            ("스타포스 누를 돈으로 저한테 맛있는거 사주세양!", 5),
            ("오늘은 스타포스 누르지 않는게 좋겠어양...", 5),
            ("💸스타포스 1조 클럽 가입하기 좋은 날이에양", 5),
            ("안좋은 쪽으로 큰일이 일어날 것 같은 예감이 들어양...", 5),
            ("스타포스 하다가 거지될 수도 있어양", 5),
        ],
        "StarForce_lv1": [
            (default_message_lv1, DEFAULT_MESSAGE_COUNT_CONST),
            ("장비를 정지... 켁 파괴됐어양!!!", 5),
            ("스타포스 누르지도 않았는데 장비가 터졌어양!!!", 5),
            ("돈 버리고 싶으면 스타포스 해보세양 ㅋㅋ", 5),
            ("오늘은 진짜 레알로 스타포스 누르지 않는게 좋겠어양...", 5),
            ("스타포스 누를 돈으로 맛있는거 사드세양!", 5),
            ("장비가 다 터져서 저처럼 벗고 다녀야 해양...🩲", 1),
            ("메소를 스타포스 하는데 커녕 장비 복구하는데 다 쓰고 말거에양", 5),
        ],

        # 큐브 운세 메세지
        "Cube_lv5": [
            (default_message_lv5, DEFAULT_MESSAGE_COUNT_CONST),
            ("딸각 한번에 모든게 레전더리가 되는 날이에양!", 5),
            ("오늘 에마삼/에공삼 오너가 되는 날이에양!", 5),
            ("모두에게 개쩌는 잠재옵션을 보여주는 날이에양!", 5),
            ("오늘은 모든게 레전더리가 되는 날이에양!", 5),
            ("용사님의 이쁜 잠재옵션이 기대되양", 2),
            ("왜 혼자서 미라클 타임을 즐기고 있어양?🌈", 3),
            ("보보보, 드드드, 메메메의 냄새가 느껴져양!", 5),
            ("제꺼도 좀 돌려주세양...", 1),
        ],
        "Cube_lv4": [
            (default_message_lv4, DEFAULT_MESSAGE_COUNT_CONST),
            ("큐브의 신이 함께하는 날이에양", 4),
            ("원하는 옵션이 금방 나올거에양", 4),
            ("오늘 저랑 (잠재)두줄 만들어봐양...❤️", 1),
            ("오늘은 제가 돌려도 잘 나오는 날이에양!", 4),
            ("왠지 대박의 기운이 느껴져양. 성공하면 저한테 뽀찌주세양!🤑", 2),
            ("대박 옵션을 노려보는게 어떨까양?", 2),
            ("이쁜 두줄이 나올 것 같아양!", 4),
            ("잠재를 돌려 쌀먹을 해봐양!", 2),
        ],
        "Cube_lv3": [
            (default_message_lv3, DEFAULT_MESSAGE_COUNT_CONST),
            ("돌리다보면 괜찮은 옵션이 나올지도...♻️", 4),
            ("무난하게 두줄을 노려봐양", 4),
            ("오늘은 무난한 날이에양. 큐브도 무난하게 돌릴거에양.", 4),
            ("이벤트 큐브 잘 모으고 있어양?", 3),
            ("누구처럼 이상한 옵션가지고 세줄이라하면 혼나양!", 1),
            ("신중하게 큐브를 돌릴지 생각해봐양", 3),
            ("잠재옵션이 바뀌지 않을 수도 있어양", 3),
        ],
        "Cube_lv2": [
            (default_message_lv2, DEFAULT_MESSAGE_COUNT_CONST),
            ("하루 종일 잠재만 돌리다가 하루 다 갈거에양...", 3),
            ("오늘은 큐브 돌리지 않는게 좋겠어양...", 3),
            ("오늘은 두줄도 못 볼수도 있어양", 3),
            ("등급이 오르기라도 하면 다행이에양", 3),
            ("천장의 냄새가 나는 날이에양...", 3),
            ("존버가 답이에양!!! 큐브를 최대한 아껴봐양", 3),
            ("큐브 돌리다가 거지될 수도 있어양", 3),
        ],
        "Cube_lv1": [
            (default_message_lv1, DEFAULT_MESSAGE_COUNT_CONST),
            ("천장을 치고 엉엉 우는 모습이 보여양", 3),
            ("오늘은 진짜 레알로 큐브하지 않는게 좋을것 같아양", 4),
            ("스펙이 내려가지 않았다면 그걸로 다행이에양", 5),
            ("천장 칠 메소는 가지고 계신거에양?💰", 5),
            ("원하는 옵션 보지도 못할 거에양", 3),
            ("큐브 아까워양...", 5),
            ("큐브 돌리다가 거지될 수도 있어양", 5),
            ("옵션도 띄우지 못하는 허접이에양..?", 1),
        ],

        # 보스 운세 메세지
        "Boss_lv5": [
            (default_message_lv5, DEFAULT_MESSAGE_COUNT_CONST),
            ("이번달 임대료는 낼 것 같아양!", 5),
            ("오늘 주보 잡으면 엄청날 행운이 찾아올거에양!", 7),
            ("설마 주보 다 잡은건 아니겠지양?", 2),
            ("저를 데리고 주보 잡으러 가양!❤️", 3),
            ("블링크빵 전승각이 보이는 날이에양!", 5),
            ("오늘 보스가 겜 접는날이라고 템뿌린데양!", 5),
            ("보스 다 잡으면 저도 공략해 주세양!❤️", 1),
            ("오늘 주보 맛좋누", 4),
            ("치킨점.", 2),
        ],
        "Boss_lv4": [
            (default_message_lv4, DEFAULT_MESSAGE_COUNT_CONST),
            ("이번달 전기세는 낼 것 같아양!", 5),
            ("오늘 보스 패턴이 이상해도 참아야해양!", 3),
            ("어서 주보 잡으러 가세양!", 3),
            ("얼른 도핑거리 사고 보스가양!", 5),
            ("깨고 싶었던 보스가 바로 한방에 클리어?!", 5),
            ("오늘 주보 맛좋겠누", 2),
        ],
        "Boss_lv3": [
            (default_message_lv3, DEFAULT_MESSAGE_COUNT_CONST),
            ("오늘 식비라도 나올거에양.", 5),
            ("오늘도 뭐 그렇저럭 이에양", 5),
            ("언제나 늘 칠흑이 안뜨는 법이에양", 5),
            ("칠흑을 원한다면 다른날에 가는게 어때양?", 5),
            ("오늘 반지상자라도 뜨면 좋겠어양", 7),
            ("오늘은 무난한 날이에양. 보스도 무난하게 잡을거에양.", 3),
            ("도핑 거리를 잘 챙겨봐양", 5),
            ("보스 잡다가 실수 할 수도 있어양...", 3),
            ("무난한 득템", 5),
        ],
        "Boss_lv2": [
            (default_message_lv2, DEFAULT_MESSAGE_COUNT_CONST),
            ("사냥 하는게 더 좋을 수도 있어양...", 5),
            ("오늘 태초의 정수도 못볼 수도 있어양", 5),
            ("반빨별이라도 뜨면 다행이에양", 5),
            ("보스 잡다가 실수 할 수도 있어양...", 5),
            ("오늘은 그냥 사냥이나 하세양", 5),
        ],
        "Boss_lv1": [
            (default_message_lv1, DEFAULT_MESSAGE_COUNT_CONST),
            ("오늘 블링크빵 전패할 수도 있어양", 5),
            ("보스잡지 말고 사냥이나 하세양 ㅋㅋ", 3),
            ("보스잡지 말고 븜미랑 데이트 어때양?", 1),
            ("오늘 밥값도 안나올 수도 있어양...", 5),
            ("온갖 억까를 당할 수도 있어양", 5),
            ("오늘은 진짜 레알로 보스 안잡는게 좋을것 같아양", 3),
            ("저랑 던파 보스나 잡으러 가양!❤️", 1),
            ("메이플 접고 븜미랑 던파 신혼여행 어때양?✈️", 1),
        ],

        # 캐시 운세 메세지
        "Cash_lv5": [
            (default_message_lv5, DEFAULT_MESSAGE_COUNT_CONST),
            ("지금 자석펫과 마라벨이 기다리고 있어양!", 4),
            ("1등상이 그냥 짜잔하고 나오는 날이에양!", 4),
            ("마스터피스, 루나크리스탈 풀매수 하세양!", 4),
            ("MVP작하고 오히려 돈이 남을수도 있어양!", 4),
            ("오늘 아무거나 사도 좋으니 일단 질러양!", 2),
            ("븜미랑 도박하러 가양! 🎰🎰🎰", 2),
            ("사장님이 미쳤어양", 4),
            ("치킨점.", 1),
        ],
        "Cash_lv4": [
            (default_message_lv4, DEFAULT_MESSAGE_COUNT_CONST),
            ("뽑기에서 좋은 게 나올 거에양!", 4),
            ("뽑기 운이 좋은 날이에양!", 4),
            ("MVP작하면 본전 볼수도 있겠어양!", 4),
            ("🍎 플래티넘애플하기 좋은 날이에양", 2),
            ("🍏 골든애플하기 좋은 날이에양", 2),
            ("👑 로얄스타일하기 좋은 날이에양", 2),
            ("🍓 원더베리하기 좋은 날이에양", 2),
            ("MVP작하기 좋은 날이에양", 2)
        ],
        "Cash_lv3": [
            (default_message_lv3, DEFAULT_MESSAGE_COUNT_CONST),
            ("무난하게 캐시템을 뽑을 수 있을거에양", 4),
            ("오늘은 무난한 날이에양. 캐시템도 무난하게 뽑을거에양.", 4),
            ("원하는 캐시템이 금방 나올거에양", 4),
            ("뽑기 운이 그저그럴 수도 있어양", 4),
            ("신중한 선택이 필요해양", 4),
        ],
        "Cash_lv2": [
            (default_message_lv2, DEFAULT_MESSAGE_COUNT_CONST),
            ("충동적인 도박🎰은 하지마세양!", 4),
            ("지갑이 얇아질 수도 있어양...", 4),
            ("오늘은 뽑기하지 않는게 좋겠어양...", 4),
            ("MVP작하면 손해볼 수도 있어양", 4),
            ("폭망할 수도 있으니 조심해양", 4),
        ],
        "Cash_lv1": [
            (default_message_lv1, DEFAULT_MESSAGE_COUNT_CONST),
            ("지갑이 텅텅 비는 미래가 보였어양!", 2),
            ("돈버리기 페이커가 되고 싶으면 하세양!", 2),
            ("던파나 하러 가세양! ㅋ", 4),
            ("봉자나 까러 가세양! 🔐", 4),
            ("개 폭망하는 미래가 보였어양!💥", 6),
            ("오늘은 진짜 레알로 뽑기하지 않는게 좋겠어양...", 4),
            ("도박하지 말고 저랑 던파나 하러 가양! 🔫", 1),
            ("캐쉬샵 가지 말고 븜미네 집으로 가양!", 1),
        ],

        # 사냥 운세 메세지
        "Hunter_lv5": [
            (default_message_lv5, DEFAULT_MESSAGE_COUNT_CONST),
            ("지금 당장 사냥터로 가세양!", 5),
            ("다조를 모아서 이번달 전기세 마련해양!", 7),
            ("에스페시아 언니의 전설 상자 보러가양!", 7),
            ("엄청나게 많은 다조를 먹어양", 5),
            ("븜미랑 사냥터에서 재획데이트해양!❤️", 3),
            ("다조를 이렇게 뿌리면 임신할거 같아양..", 1),
            ("다조를 너무 많이 먹어서 배탈났어양..", 3),
            ("이 모든 것이 신창섭의 은혜겠지요...", 1),
        ],
        "Hunter_lv4": [
            (default_message_lv4, DEFAULT_MESSAGE_COUNT_CONST),
            ("사냥하다가 좋은 일이 일어날 것 같은 예감..", 5),
            ("오늘은 사냥하기 좋은 날이에양!", 5),
            ("사냥터에 버닝필드가 남아있는 소소한 행복", 2),
            ("다조를 모아서 오늘의 식비를 마련해양!", 5),
            ("다조와 솔에르다가 잘 나올 것 같아양!", 5),
            ("오늘 사냥터에서 귀여운 븜미를 만날 수도 있어양!❤️", 1),
        ],
        "Hunter_lv3": [
            (default_message_lv3, DEFAULT_MESSAGE_COUNT_CONST),
            ("언제나 똑같은 일이 일어날 거에양", 5),
            ("늘 먹던대로 사냥할 것 같아양", 5),
            ("늘 하던 메이플이랑 똑같아양", 5),
            ("메소 모아 하이마운틴 이에양", 5),
            ("다조와 솔 에르다를 열심히 모아봐양", 5),
            ("오늘은 사냥터에서 븜미를 못볼 것 같아양...", 1),
        ],
        "Hunter_lv2": [
            (default_message_lv2, DEFAULT_MESSAGE_COUNT_CONST),
            ("오늘은 간단하게 소재비 하나만 빨아봐양", 5),
            ("오늘은 간단하게 30분만 사냥해봐양", 5),
            ("오늘 운이 안좋아서 폭망할수도 있어양", 5),
            ("평소보다 다조가 적게 들어올 수도 있어양...", 5),
            ("이상한 사람을 만날 수도 있어양", 2),
            ("너무 오래 사냥하면 피로도가 쌓여양...💀", 3),
            ("거짓말 탐지기 때문에 피곤한 하루가 될 수도 있어양...", 4),
            ("오늘 사냥터에서 븜미를 못볼 것 같아양...", 1),
        ],
        "Hunter_lv1": [
            (default_message_lv1, DEFAULT_MESSAGE_COUNT_CONST),
            ("사냥하지 말고 딴거 하러 가세요라에양!", 5),
            ("소재비가 아까워양...💀", 5),
            ("오늘은 진짜 레알로 폭망할 것 같아양!💥", 3),
            ("오늘은 사냥하기 좋은 날이 아니에양...", 2),
            ("오늘은 간단하게 일퀘만 해야할 것 같아양...", 5),
            ("사냥터에서 비올레타를 볼 것 같아양...", 3),
            ("저랑 던파하러 가양! 🔫", 1),
            ("오늘은 메이플하지 말고 븜미랑 던파 데이트하러 가양! ❤️", 1),
            ("사냥터에서 븜미 대신 이상한 사람을 만날 수도 있어양...💔", 1),
        ],
    }
    
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
    def _pick_grade(rng: random.Random) -> int:
        roll = rng.randint(1, 100)
        acc = 0
        for g, w in fortune_grade_weights:
            acc += w
            if roll <= acc:
                return g
        return -1
    
    fortune_result: List[str] = []
    for f_cate, f_name in fortune_category.items():
        # 행운 등급 결정
        random_grade: random.Random = random.Random(_mix_seed(seed, f_cate, "grade"))
        f_grade = _pick_grade(random_grade)

        if f_grade != -1:
            # 행운 메세지 결정
            random_message: random.Random = random.Random(_mix_seed(seed, f_cate, "message"))
            f_result_star, f_result_name = fortune_grade_table[f_grade]
            f_fortune_message_dict: Dict[int, List[str]] = fortune_message.get(f_cate)
            f_fortune_message: str = random_message.choice(f_fortune_message_dict.get(f_grade, []))
            f_text = (
                f"{f_name}\n"
                f"{f_result_star} ({f_result_name}): {f_fortune_message}\n"
            )
        else:
            f_text = f"{f_name}\n오늘의 운세를 알 수 없어양...\n"
        fortune_result.append(f_text)

    return "\n".join(fortune_result)

def get_weekly_xp_history(character_ocid: str) -> Tuple[str, int, str]:
    """메이플 스토리 캐릭터의 1주일 간 경험치 추세 데이터 수집
    
    Args:
        character_ocid (str): 캐릭터 고유 ID

    Returns:
        List[Tuple[str, int, float]]: 날짜, 레벨, 경험치 퍼센트 데이터 (1주일치)
        (예: ("2023-10-01", 250, "75.321%"))

    Raises:
        NexonAPIError: API 호출 오류
    """

    start_date = datetime.now(tz=timezone("Asia/Seoul")).date()
    date_list: List[str] = [(start_date - timedelta(days=2+i)).strftime("%Y-%m-%d") for i in range(7)]
    return_data: List[Tuple[str, int, str]] = []

    for param_date in date_list:
        request_service_url: str = f"/maplestory/v1/character/basic"
        request_url: str = f"{NEXON_API_HOME}{request_service_url}?ocid={character_ocid}&date={param_date}"
        time.sleep(0.34)  # API Rate Limit 방지
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


def get_dnf_weekly_timeline(server_name: str, character_name: str) -> Dict[str, Any]:
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
    # 타임라인 조회 대상
    server_id: str = neople_dnf_server_parse(server_name)
    character_id: str = neople_dnf_get_character_id(server_name, character_name)

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
    base_request_url: str = f"{NEOPLE_API_HOME}/df/servers/{server_id}/characters/{character_id}/timeline"
    request_url: str = f"{base_request_url}?limit=100{timeline_date_query}&apikey={NEOPLE_API_KEY}"
    response_data: dict = general_request_handler_neople(request_url)

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