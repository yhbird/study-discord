import requests
import math

from datetime import datetime, timedelta
from pytz import timezone

from typing import List
from config import WTH_API_HOME, WTH_DATA_API_KEY # Weather API
from config import KKO_API_HOME, KKO_LOCAL_API_KEY # Kakao Local API
from exceptions.api_exceptions import *

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
            raise KakaoNoLocalInfo("해당 지역 정보를 찾을 수 없어양")
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