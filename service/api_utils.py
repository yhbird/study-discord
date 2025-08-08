import math
import requests
import io
from urllib.parse import quote
from datetime import datetime, timedelta
from pytz import timezone

from config import NEXON_API_HOME, NEXON_API_KEY # NEXON OPEN API
from config import KKO_LOCAL_API_KEY, KKO_API_HOME # KAKAO Local API
from config import WTH_DATA_API_KEY, WTH_API_HOME # Weather API
from service.api_exception import *

from typing import Optional


def general_request_error_handler(response: requests.Response) -> None:
    """Nexon Open API의 일반적인 요청 오류를 처리하는 함수  
    특수한 오류가 있는 경우를 제외하고, 일반적인 오류에 대한 예외를 발생시킴  
    예외 처리 기준은 아래 Reference 링크를 참고

    Args:
        res (requests.Response): 요청 응답 객체

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14
    """
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


def general_request_handler(request_url: str, headers: Optional[dict] = None) -> dict:
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
    
    response = requests.get(url=request_url, headers=headers)
    
    if response.status_code != 200:
        general_request_error_handler(response)
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
    response_data: dict = general_request_handler(request_url)
    
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
        response_data: dict = general_request_handler(request_url)

        popularity: int = response_data.get('popularity', "몰라양")
        return popularity
    except NexonAPIError:
        return "몰라양"  # 예외 발생 시 기본값으로 "몰라양" 반환


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
    response_data: dict = general_request_handler(request_url)
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
    response_data: dict = general_request_handler(request_url)
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
        error_code: str = response_result.get('resultCode', 'Unknown Error')
        error_text: str = response_result.get('resultMsg', 'Unknown Error')
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
    basedate: str = item.get('baseDate', '알수없음')
    basetime: str = item.get('baseTime', '알수없음')
    base_date_ymd: str = f"{basedate[:4]}년 {basedate[4:6]}월 {basedate[6:]}일"
    base_time_hm: str = f"{basetime[:2]}시 {basetime[2:]}분"

    # 날씨정보 1 - PTY: 강수 형태 코드
    return_data: dict = {}
    return_data["기준시간"] = f"{base_date_ymd} {base_time_hm}"
    result_data["PTY"] = result_data.get("PTY", "0")
    if result_data["PTY"] == "0":
        return_data["강수형태"] = "없음"
    elif result_data["PTY"] == "1":
        return_data["강수형태"] = "비"
    elif result_data["PTY"] == "2":
        return_data["강수형태"] = "비/눈"
    elif result_data["PTY"] == "3":
        return_data["강수형태"] = "눈"
    elif result_data["PTY"] == "5":
        return_data["강수형태"] = "빗방울"
    elif result_data["PTY"] == "6":
        return_data["강수형태"] = "빗방울/눈날림"
    elif result_data["PTY"] == "7":
        return_data["강수형태"] = "눈날림"

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



