import json
import requests
import hashlib
import random
import math
import time
import re

from urllib.parse import quote
from datetime import datetime, timedelta
from pytz import timezone

from config import NEXON_API_KEY, NEXON_API_HOME # Nexon Open API
from utils.time import kst_format_now_v2
from data.json.fortune_message_table import fortune_message_table_raw

from typing import Literal, Optional, Dict, List, Tuple, Any
from exceptions.api_exceptions import *

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


def get_weekly_xp_history(character_ocid: str, time_delta: int = 2) -> Tuple[str, int, str]:
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

    start_date = datetime.now(tz=timezone("Asia/Seoul")).date()
    date_list: List[str] = [
        (start_date - timedelta(days=time_delta + i)).strftime("%Y-%m-%d") for i in range(7)
    ]
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


def process_maple_basic_info(raw_data: dict) -> dict:
    """메이플스토리 캐릭터 기본 정보 데이터를 가공하는 함수

    Args:
        raw_data (dict): 원본 캐릭터 기본 정보 데이터

    Returns:
        dict: 가공된 캐릭터 기본 정보 데이터
    """
    if isinstance(raw_data, dict):
        input_data: dict = raw_data.copy()
        return_data: dict = {}

        # basic info 1. 캐릭터 이름
        character_name: str | bool = input_data.get('character_name')
        if character_name is None:
            return False
        else:
            return_data['character_name'] = character_name
        
        # basic info 2. 캐릭터 레벨
        character_level: int = (
            int(input_data.get('character_level'))
            if input_data.get('character_level') is not None
            else -1
        )
        return_data['character_level'] = character_level if character_level != -1 else "몰라양"

        # basic info 3. 캐릭터 소속월드
        character_world: str | Literal["알수없음"] = (
            str(input_data.get('world_name')).strip()
            if input_data.get('world_name') is not None
            else "알수없음"
        )
        return_data['character_world'] = character_world

        # basic info 4. 캐릭터 성별
        character_gender: str | Literal["제로"] = (
            str(input_data.get('character_gender')).strip()
            if input_data.get('character_gender') is not None
            else "제로"
        )
        return_data['character_gender'] = character_gender

        # basic info 5. 캐릭터 직업 & 직업차수
        character_class: str | Literal["알수없음"] = (
            str(input_data.get('character_class')).strip()
            if input_data.get('character_class') is not None
            else "알수없음"
        )
        character_class_level: str | Literal["알수없음"] = (
            str(input_data.get('character_class_level')).strip()
            if input_data.get('character_class_level') is not None
            else "알수없음"
        )
        return_data['character_job'] = f"{character_class} ({character_class_level}차 전직)"
        return_data['character_class'] = character_class
        return_data['character_class_level'] = character_class_level

        # basic info 6. 캐릭터 경험치 & 퍼센트
        character_exp: int = (
            int(input_data.get('character_exp'))
            if input_data.get('character_exp') is not None
            else -1
        )
        character_exp_rate: str | Literal["0.000%"] = (
            str(input_data.get('character_exp_rate')).strip()
            if input_data.get('character_exp_rate') is not None
            else "0.000%"
        )
        return_data['character_exp'] = character_exp
        return_data['character_exp_rate'] = character_exp_rate

        # basic info 7. 캐릭터 소속 길드
        character_guild_name_json = input_data.get('character_guild_name')
        if character_guild_name_json is None:
            character_guild_name = "길드가 없어양!"
        else:
            character_guild_name = str(character_guild_name_json).strip()
        return_data['character_guild_name'] = character_guild_name

        # basic info 8. 캐릭터 외형 이미지 URL
        character_image: str | Literal[""] = (
            str(input_data.get('character_image')).strip()
            if input_data.get('character_image') is not None
            else ""
        )
        return_data['character_image'] = character_image

        # basic info 9. 캐릭터 생성일
        character_date_create: str | Literal["알수없음"] = (
            str(input_data.get('character_date_create')).strip()
            if input_data.get('character_date_create') is not None
            else "알수없음"
        )
        return_data['character_date_create'] = character_date_create

        # basic info 10. 캐릭터 최근 7일 이내 접속 여부 (flag)
        character_access_flag: bool | Literal["알수없음"]  = (
            str(input_data.get('character_access_flag')).strip()
            if input_data.get('character_access_flag') is not None
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
            str(input_data.get('liberation_quest_clear')).strip()
            if input_data.get('liberation_quest_clear') is not None
            else "알수없음"
        )
        return_data['liberation_quest_clear'] = character_liberation_quest_clear

    return return_data