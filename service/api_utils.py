import math
import requests
import io
import re
from urllib.parse import quote
from datetime import datetime, timedelta
from pytz import timezone

from config import NEXON_API_HOME, NEXON_API_KEY # NEXON OPEN API
from config import KKO_LOCAL_API_KEY, KKO_API_HOME # KAKAO Local API
from config import WTH_DATA_API_KEY, WTH_API_HOME # Weather API
from config import NEOPLE_API_KEY, NEOPLE_API_HOME # Neople Developers API
from service.api_exception import *

from typing import Optional, Dict, List


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
        ability_grade_symbol: str = convert_grade_text(ability_grade)
        result_ability_text += f"{ability_grade_symbol} {ability_text}\n"

    return result_ability_text.strip() if result_ability_text else "몰라양"


def convert_grade_text(grade_text: str) -> str:
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
        

def get_weather_info(local_x: str, local_y: str) -> dict:
    """기상청 API를 통해 지역의 날씨 정보 조회

    Args:
        local_x (str): 지역의 x 좌표 (경도)
        local_y (str): 지역의 y 좌표 (위도)

    Returns:
        dict: 지역의 날씨 정보

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://www.data.go.kr/data/15084084/openapi.do
    """
    local_x: float = round(float(local_x), 6)
    local_y: float = round(float(local_y), 6)
    nx, ny = convert_grid(lat=local_y, lon=local_x)

    query_date: datetime = datetime.now(timezone('Asia/Seoul')) - timedelta(minutes=30)
    base_date: str = query_date.strftime('%Y%m%d')
    base_time: str = query_date.strftime('%H%M')
    request_url = f"{WTH_API_HOME}/getUltraSrtNcst"
    request_params = {
        'ServiceKey': WTH_DATA_API_KEY,
        'numOfRows': 1000,
        'pageNo': 1,
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': nx,
        'ny': ny
    }
    
    response = requests.get(request_url, params=request_params)
    # 에러가 발생한 경우 (기상청은 에러가 발생해도 200을 반환함)
    response_json: dict = response.json()
    response_content: dict = response_json.get('response')
    response_result: dict = response_content.get('header')
    if response_result.get('resultCode') != '00':
        error_code: str = (
            str(response_result.get('resultCode').strip())
            if response_result.get('resultCode') is not None
            else 'Unknown Error'
        )
        error_text: str = (
            str(response_result.get('resultMsg').strip())
            if response_result.get('resultMsg') is not None
            else 'Unknown Error'
        )
        weather_exception_handler(error_code, error_text)
    else:
        # 정상적으로 응답이 온 경우
        response_data: dict = response_content.get("body")
        weather_data: dict = response_data.get("items", {})
        if weather_data:
            return weather_data
        else:
            raise WeatherAPIError("WTH_NO_WEATHER_DATA")
        

def get_wind_direction(wind_degree: float) -> str:
    """기상청 API로부터 얻은 풍향 데이터 변환

    Args:
        wind_degree (float): 풍향 (도, deg)

    Returns:
        str: 풍향 (북, 북동, 동, 남동, 남, 남서, 서, 북서)
    """
    wind_directions = [
        "북", "북동", "동", "남동",
        "남", "남서", "서", "북서"
    ]
    idx = int((wind_degree + 22.5) % 360 // 45)
    return wind_directions[idx]

def process_weather_data(weather_data: dict) -> dict:
    """기상청 API로부터 받은 날씨 데이터를 전처리하는 함수

    Args:
        weather_data (dict): 기상청 API로부터 받은 날씨 데이터

    Returns:
        dict: 전처리된 날씨 데이터  
        {  
            "PTY" -> 강수 형태 코드 (0: 없음, 1: 비, 2: 비/눈, 3: 눈, 5: 빗방울, 6: 빗방울/눈날림, 7: 눈날림)  
            "REH" -> 습도 (%)  
            "RN1" -> 1시간 강수량 (mm)  
            "T1H" -> 기온 (℃)  
            "UUU" -> 동서풍속 (m/s)  
            "VVV" -> 남북풍속 (m/s)  
            "VEC" -> 풍향 (도, deg)  
            "WSD" -> 풍속 (m/s)  
        }  

    Reference:
        https://www.data.go.kr/data/15084084/openapi.do
    """
    local_weather_data: list[dict] = weather_data.get('item', [])
    result_data: dict = {}
    for item in local_weather_data:
        category: str = item.get('category')
        value: str = item.get('obsrValue')
        result_data[category] = value
    basedate: str = (
        str(item.get('baseDate'))
        if item.get('baseDate') is not None
        else '알수없음'
    )
    basetime: str = (
        str(item.get('baseTime'))
        if item.get('baseTime') is not None
        else '알수없음'
    )
    base_date_ymd: str = f"{basedate[:4]}년 {basedate[4:6]}월 {basedate[6:]}일"
    base_time_hm: str = f"{basetime[:2]}시 {basetime[2:]}분"

    # 날씨정보 1 - PTY: 강수 형태 코드
    return_data: dict = {}
    return_data["기준시간"] = f"{base_date_ymd} {base_time_hm}"
    rainsnow_flag = result_data.get("PTY", "몰라양")
    return_data["강수형태"] = rainsnow_flag
    if rainsnow_flag == "0":
        return_data["강수형태"] = "없음"
    elif rainsnow_flag == "1":
        return_data["강수형태"] = "비"
    elif rainsnow_flag == "2":
        return_data["강수형태"] = "비/눈"
    elif rainsnow_flag == "3":
        return_data["강수형태"] = "눈"
    elif rainsnow_flag == "5":
        return_data["강수형태"] = "빗방울"
    elif rainsnow_flag == "6":
        return_data["강수형태"] = "빗방울/눈날림"
    elif rainsnow_flag == "7":
        return_data["강수형태"] = "눈날림"
    else:
        return_data["강수형태"] = "몰라양"

    # 날씨정보 2 - REH: 습도 (%)
    return_data["습도"] = f"{result_data.get('REH', '알수없음')}%"

    # 날씨정보 3 - RN1: 1시간 강수량 (mm)
    r1n = result_data.get('RN1', '알수없음')
    return_data["1시간강수량_수치"] = r1n
    
    if r1n == "0":
        return_data["1시간강수량_표시"] = "없음"
        return_data["1시간강수량_정성"] = "없음"
    else:
        r1n_float: float = float(r1n)
        if r1n_float < 3.0:
            return_data["1시간강수량_정성"] = "약한 비"
        elif r1n_float < 15.0:
            return_data["1시간강수량_정성"] = "보통 비"
        elif r1n_float < 30.0:
            return_data["1시간강수량_정성"] = "강한 비"
        elif r1n_float < 50.0:
            return_data["1시간강수량_정성"] = "매우 강한 비"
        else:
            return_data["1시간강수량_정성"] = "⚠️ 폭우 ⚠️"

        if r1n_float < 1.0:
            return_data["1시간강수량_표시"] = "1mm 미만"
        elif r1n_float < 30.0:
            return_data["1시간강수량_표시"] = f"{r1n}mm"
        elif r1n_float < 50.0:
            return_data["1시간강수량_표시"] = f"30.0mm ~ 50.0mm ({r1n}mm)"
        else:
            return_data["1시간강수량_표시"] = f"50.0mm 이상 ({r1n}mm)"


    # 날씨정보 4 - 기온 (℃)
    return_data["기온"] = f"{result_data.get('T1H', '알수없음')}℃"

    # 날씨정보 5 - 풍속 (m/s)
    vec = result_data.get('VEC', '몰라양')
    wsd = result_data.get('WSD', '몰라양')
    if vec == "999":
        return_data["풍향"] = "몰라양"
    else:
        return_data["풍향"] = get_wind_direction(wind_degree=float(vec))

    if wsd ==  "-998.9":
        return_data["풍속"] = "몰라양"
    else:
        return_data["풍속"] = f"{wsd} m/s"

    return return_data


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
    character_name = quote(character_name.strip())
    request_url = f"{NEOPLE_API_HOME}/df/servers/{server_id}/characters?characterName={character_name}&apikey={NEOPLE_API_KEY}"
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
        raise NeopleAPIError(f"{server_name}서버 {character_name}모험가 정보를 찾을 수 없어양")