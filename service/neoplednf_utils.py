import requests
from urllib.parse import quote
from datetime import datetime, timedelta
from pytz import timezone

from typing import Optional, Dict, List, Any
from config import NEOPLE_API_HOME, NEOPLE_API_KEY
from exceptions.client_exceptions import *


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