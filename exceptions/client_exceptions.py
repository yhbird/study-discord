"""
exceptions/client_exceptions.py

API 관련 예외 처리 모듈

???_utils.py에서 사용되는 예외 클래스 정의
"""

from __future__ import annotations
from typing import Dict

import httpx
import requests
from exceptions.base import ClientBaseException

class NexonAPIError(ClientBaseException):
    """Nexon API 사용 중 발생하는 오류"""

class NexonAPICharacterNotFound(NexonAPIError):
    """Nexon API 캐릭터 없음 오류"""
        
class NexonAPIBadRequest(NexonAPIError):
    """Nexon API Bad Request 오류"""

class NexonAPIForbidden(NexonAPIError):
    """Nexon API Forbidden 오류"""

class NexonAPITooManyRequests(NexonAPIError):
    """Nexon API Too Many Requests 오류"""

class NexonAPIServiceUnavailable(NexonAPIError):
    """Nexon API Service Unavailable 오류"""

class NexonAPIOCIDNotFound(NexonAPIError):
    """Nexon API OCID Not Found 오류"""

class NexonAPINoticeNotFound(NexonAPIError):
    """Nexon API 공지사항 없음 오류"""

class NexonAPISundayEventNotFound(NexonAPIError):
    """Nexon API 썬데이 이벤트 공지사항 없음 오류"""

def nexon_api_error_handler(response: httpx.Response):
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
    

class NeopleAPIError(ClientBaseException):
    """Neople API 사용 중 발생하는 오류"""
    pass

class DNFServerNotFound(NeopleAPIError):
    """던전앤파이터 서버 조회 실패"""

class DNFCharacterNotFound(NeopleAPIError):
    """던전앤파이터 캐릭터 조회 실패"""

class DNFCIDNotFound(NeopleAPIError):
    """던전앤파이터 캐릭터 고유ID 조회 실패"""

class NeopleAPIKeyMissing(NeopleAPIError):
    """Neople API Key 미입력 (API000)"""

class NeopleAPIInvalidId(NeopleAPIError):
    """Neople API 유효하지 않은 게임아이디 (API001)"""

class NeopleAPILimitExceed(NeopleAPIError):
    """Neople API 요청 제한 초과 (API002)"""

class NeopleAPIInvalidAPIkey(NeopleAPIError):
    """Neople API 잘못된 API 키 (API003)"""

class NeopleAPIBlockedAPIKey(NeopleAPIError):
    """Neople API 차단된 API 키 (API004)"""

class NeopleAPIWrongGameKey(NeopleAPIError):
    """Neople API 잘못된 게임 키 (API005)"""

class NeopleAPIInvalidParams(NeopleAPIError):
    """Neople API 잘못된 파라미터 (API006)"""

class NeopleAPIClientSocketError(NeopleAPIError):
    """Neople API 클라이언트 소켓 오류 (API007)"""

class NeopleAPIInvalidURL(NeopleAPIError):
    """Neople API 잘못된 URL (API900)"""

class NeopleAPIInvalidRequestParams(NeopleAPIError):
    """Neople API 잘못된 요청 파라미터 (API901)"""

class NeopleAPISystemError(NeopleAPIError):
    """Neople API 시스템 오류 (API999)"""

class NeopleDNFInvalidServerID(NeopleAPIError):
    """Neople API 유효하지 않은 서버 ID (DNF000)"""

class NeopleDNFInvalidCharacterInfo(NeopleAPIError):
    """Neople API 유효하지 않은 캐릭터 정보 (DNF001)"""

class NeopleDNFInvalidItemInfo(NeopleAPIError):
    """Neople API 유효하지 않은 아이템 정보 (DNF003)"""

class NeopleDNFInvalidAuctionInfo(NeopleAPIError):
    """Neople API 유효하지 않은 경매장 정보 (DNF004)"""

class NeopleDNFInvalidSkillInfo(NeopleAPIError):
    """Neople API 유효하지 않은 스킬 정보 (DNF005)"""

class NeopleDNFInvalidTimelineParams(NeopleAPIError):
    """Neople API 유효하지 않은 타임라인 검색 시간 파라미터 (DNF006)"""

class NeopleDNFSearchAuctionItemOptionException(NeopleAPIError):
    """Neople API 경매장 아이템 검색 갯수 제한 (DNF007)"""

class NeopleDNFSearchAuctionMultipleItemOptionException(NeopleAPIError):
    """Neople API 다중 아이템 검색 갯수 제한 (DNF008)"""

class NeopleDNFSearchAvatarMarketOptionException(NeopleAPIError):
    """Neople API 아바타 마켓 검색 갯수 제한 (DNF009)"""

class NeopleDNFInvalidURL(NeopleAPIError):
    """Neople API 유효하지 않은 URL (DNF900)"""

class NeopleDNFInvalidRequestParams(NeopleAPIError):
    """Neople API 유효하지 않은 요청 파라미터 (DNF901)"""

class NeopleDNFSystemMaintenance(NeopleAPIError):
    """Neople API 서비스 점검중 (DNF980)"""

class NeopleDNFSystemError(NeopleAPIError):
    """Neople API 시스템 오류 (DNF999)"""

def neople_api_error_handler(response: httpx.Response | requests.Response) -> None:
    """Neople API 오류 처리 함수

    Args:
        error_code (str): Neople API 오류 코드

    Raises:
        NeopleAPIError: Neople API 오류

    Returns:
        No return
    """
    if not isinstance(response, (httpx.Response, requests.Response)):
        raise NeopleAPIError("Invalid Neople API error response")

    status = response.status_code
    msg = None
    try:
        payload: dict = response.json()
        print(payload)
        error: Dict[str, str] = payload.get("error") if isinstance(payload, dict) else None
        error_status = error.get("status", status)
        error_code = error.get("code") or "Unknown"
        msg = error.get("message")
    except Exception:
        msg = response.text.strip()

    prefix = f"Neople API Error {error_status or status} : "
    if "API000" in error_code:
        raise NeopleAPIKeyMissing(f"{prefix}{msg or 'API Key is missing.'}")
    elif "API001" in error_code:
        raise NeopleAPIInvalidId(f"{prefix}{msg or 'Invalid ID.'}")
    elif "API002" in error_code:
        raise NeopleAPILimitExceed(f"{prefix}{msg or 'API limit exceeded.'}")
    elif "API003" in error_code:
        raise NeopleAPIInvalidAPIkey(f"{prefix}{msg or 'Invalid API key.'}")
    elif "API004" in error_code:
        raise NeopleAPIBlockedAPIKey(f"{prefix}{msg or 'Blocked API key.'}")
    elif "API005" in error_code:
        raise NeopleAPIWrongGameKey(f"{prefix}{msg or 'Wrong game key for the API.'}")
    elif "API006" in error_code:
        raise NeopleAPIInvalidParams(f"{prefix}{msg or 'Invalid parameters.'}")
    elif "API007" in error_code:
        raise NeopleAPIClientSocketError(f"{prefix}{msg or 'Client socket error.'}")
    elif "API900" in error_code:
        raise NeopleAPIInvalidURL(f"{prefix}{msg or 'Invalid URL.'}")
    elif "API901" in error_code:
        raise NeopleAPIInvalidRequestParams(f"{prefix}{msg or 'Invalid request parameters.'}")
    elif "API999" in error_code:
        raise NeopleAPISystemError(f"{prefix}{msg or 'api system error.'}")
    elif "DNF000" in error_code:
        raise NeopleDNFInvalidServerID(f"{prefix}{msg or 'Invalid server ID.'}")
    elif "DNF003" in error_code:
        raise NeopleDNFInvalidCharacterInfo(f"{prefix}{msg or 'Invalid character information.'}")
    elif "DNF004" in error_code:
        raise NeopleDNFInvalidAuctionInfo(f"{prefix}{msg or 'Invalid auction information.'}")
    elif "DNF005" in error_code:
        raise NeopleDNFInvalidSkillInfo(f"{prefix}{msg or 'Invalid skill information.'}")
    elif "DNF006" in error_code:
        raise NeopleDNFInvalidTimelineParams(f"{prefix}{msg or 'Invalid timeline parameters.'}")
    elif "DNF007" in error_code:
        raise NeopleDNFSearchAuctionItemOptionException(f"{prefix}{msg or 'Search auction item option exception.'}")
    elif "DNF008" in error_code:
        raise NeopleDNFSearchAuctionMultipleItemOptionException(f"{prefix}{msg or 'Search auction multiple item option exception.'}")
    elif "DNF009" in error_code:
        raise NeopleDNFSearchAvatarMarketOptionException(f"{prefix}{msg or 'Search avatar market option exception.'}")
    elif "DNF900" in error_code:
        raise NeopleDNFInvalidURL(f"{prefix}{msg or 'Invalid URL.'}")
    elif "DNF901" in error_code:
        raise NeopleDNFInvalidRequestParams(f"{prefix}{msg or 'Invalid request parameters.'}")
    elif "DNF980" in error_code:
        raise NeopleDNFSystemMaintenance(f"{prefix}{msg or 'System maintenance in progress.'}")
    elif "DNF999" in error_code:
        raise NeopleDNFSystemError(f"{prefix}{msg or 'System error.'}")
    else:
        raise NeopleAPIError(f"{prefix}{msg or 'Unknown error.'}")

    
class KakaoAPIError(ClientBaseException):
    """Kakao API 사용 중 발생하는 오류"""

class KakaoNoLocalInfo(KakaoAPIError):
    """카카오 로컬 API 지역정보 검색결과 없음"""

class KKO_LOCAL_API_ERROR(KakaoAPIError):
    """카카오 로컬 API 관련 오류"""

class WeatherAPIError(ClientBaseException):
    """날씨 API 사용 중 발생하는 오류"""
    pass

class WTH_API_INTERNAL_ERROR(WeatherAPIError):
    """날씨 API 내부 오류"""
    pass

class WTH_API_DATA_ERROR(WeatherAPIError):
    """날씨 API 데이터 오류"""
    pass

class WTH_API_DATA_NOT_FOUND(WeatherAPIError):
    """날씨 API 데이터 없음"""
    pass

class WTH_API_HTTP_ERROR(WeatherAPIError):
    """날씨 API 잘못된 요청"""
    pass

class WTH_API_TIMEOUT(WeatherAPIError):
    """날씨 API 타임아웃 오류"""
    pass

class WTH_API_INVALID_PARAMS(WeatherAPIError):
    """날씨 API 잘못된 파라미터"""
    pass

class WTH_API_INVALID_REGION(WeatherAPIError):
    """날씨 API 잘못된 지역"""
    pass

class WTH_API_DEPRECATED(WeatherAPIError):
    """날씨 API 사용 중단"""
    pass

class WTH_API_UNAUTHORIZED(WeatherAPIError):
    """날씨 API 서비스 접근 거부"""
    pass

class WTH_API_KEY_TEMP_ERROR(WeatherAPIError):
    """날씨 API 키 일시적 오류"""
    pass

class WTH_API_KEY_LIMIT_EXCEEDED(WeatherAPIError):
    """날씨 API 키 요청 제한 초과"""
    pass

class WTH_API_KEY_INVALID(WeatherAPIError):
    """날씨 API 잘못된 API 키 사용"""
    pass

class WTH_API_KEY_EXPIRED(WeatherAPIError):
    """날씨 API API 키 만료"""
    pass

class WTH_API_OTHER_ERROR(WeatherAPIError):
    """날씨 API 기타 오류"""
    pass

def weather_exception_handler(error_code: str, exception_msg: str) -> None:
    """기상청 API 요청 오류를 처리하는 함수

    Args:
        error_code (str): 오류 코드

    Raises:
        WeatherAPIError: 날씨 API 오류

    Reference:
        기상청 Open API 문서 (dada.go.kr)
        - "01" : 내부 서버 오류
        - "02" : 데이터 오류
        - "03" : 데이터 없음
        - "04" : HTTP 통신 오류
        - "05" : 타임아웃 오류
        - "10" : 잘못된 파라미터
        - "11" : 잘못된 지역
        - "12" : 사용 중단된 API
        - "20" : 서비스 접근 거부
        - "21" : API 키 일시적 오류
        - "22" : API 키 요청 제한 초과
        - "30" : 잘못된 API 키 사용
        - "31" : API 키 만료
        - "99" : 기타 오류
    """
    if "01" in error_code:
        raise WTH_API_INTERNAL_ERROR(exception_msg)
    elif "02" in error_code:
        raise WTH_API_DATA_ERROR(exception_msg)
    elif "03" in error_code:
        raise WTH_API_DATA_NOT_FOUND(exception_msg)
    elif "04" in error_code:
        raise WTH_API_HTTP_ERROR(exception_msg)
    elif "05" in error_code:
        raise WTH_API_TIMEOUT(exception_msg)
    elif "10" in error_code:
        raise WTH_API_INVALID_PARAMS(exception_msg)
    elif "11" in error_code:
        raise WTH_API_INVALID_REGION(exception_msg)
    elif "12" in error_code:
        raise WTH_API_DEPRECATED(exception_msg)
    elif "20" in error_code:
        raise WTH_API_UNAUTHORIZED(exception_msg)
    elif "21" in error_code:
        raise WTH_API_KEY_TEMP_ERROR(exception_msg)
    elif "22" in error_code:
        raise WTH_API_KEY_LIMIT_EXCEEDED(exception_msg)
    elif "30" in error_code:
        raise WTH_API_KEY_INVALID(exception_msg)
    elif "31" in error_code:
        raise WTH_API_KEY_EXPIRED(exception_msg)
    elif "99" in error_code:
        raise WTH_API_OTHER_ERROR(exception_msg)
    else:
        raise WeatherAPIError(f"Unknown error code: {error_code}, message: {exception_msg}")
    
class YFinanceAPIError(ClientBaseException):
    """YFinance API 사용 중 발생하는 오류"""
    pass

class STKException(YFinanceAPIError):
    """주식 관련 예외 클래스"""
    pass

class YFI_NO_RATE_WARNING(YFinanceAPIError):
    """환율 정보를 찾을 수 없는 예외
    
    경고 메시지로 처리되며, 명령어 실행을 중단하지 않음
    """
    pass

class YFI_STOCK_FETCH_RATE(YFinanceAPIError):
    """환율 정보를 가져오는 데 실패한 예외
    
    경고 메시지로 처리되며, 명령어 실행을 중단하지 않음
    """
    pass

class YFI_NO_TICKER(YFinanceAPIError):
    """티커 정보를 찾을 수 없는 예외"""
    pass

class STK_KRX_SEARCH_ERROR(STKException):
    """한국 주식 코드 검색 오류 예외"""
    pass

class STK_KRX_SEARCH_NO_RESULT(STKException):
    """한국 주식 코드 검색 결과 없음 예외"""
    pass

class DB_CONNECTION_ERROR(ClientBaseException):
    """데이터베이스 연결 오류 예외"""
    pass

class DB_QUERY_ERROR(ClientBaseException):
    """데이터베이스 쿼리 오류 예외"""
    pass

class DB_DATA_NOT_FOUND(ClientBaseException):
    """데이터베이스 데이터 없음 예외"""
    pass

class RCON_CLIENT_ERROR(ClientBaseException):
    """RCON 클라이언트 오류 예외"""
    pass