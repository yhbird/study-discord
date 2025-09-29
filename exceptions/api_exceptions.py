"""
exceptions/api_exceptions.py

API 관련 예외 처리 모듈

???_command.py / ???_utils.py에서 사용되는 예외 클래스 정의
"""

from exceptions.base import ClientBaseException

class NexonAPIError(ClientBaseException):
    """Nexon API 사용 중 발생하는 오류"""
    pass

class NexonAPIBadRequest(ClientBaseException):
    """Nexon API Bad Request 오류"""
    def __init__(self, message: str = "Nexon API 요청이 잘못 되었어양"):
        super().__init__(message)
        self.message = message

class NexonAPIForbidden(ClientBaseException):
    """Nexon API Forbidden 오류"""
    def __init__(self, message: str = "Nexon API 접근 권한이 없어양"):
        super().__init__(message)
        self.message = message

class NexonAPITooManyRequests(ClientBaseException):
    """Nexon API Too Many Requests 오류"""
    def __init__(self, message: str = "Nexon API 요청이 너무 많아양"):
        super().__init__(message)
        self.message = message

class NexonAPIServiceUnavailable(ClientBaseException):
    """Nexon API Service Unavailable 오류"""
    def __init__(self, message: str = "Nexon API 서비스가 사용 불가능 해양"):
        super().__init__(message)
        self.message = message

class NexonAPIOCIDNotFound(ClientBaseException):
    """Nexon API OCID Not Found 오류"""
    def __init__(self, message: str = "Nexon API에서 OCID를 찾을 수 없어양"):
        super().__init__(message)
        self.message = message


class NeopleAPIError(ClientBaseException):
    """Neople API 사용 중 발생하는 오류"""
    pass

class NeopleAPIKeyMissing(ClientBaseException):
    """Neople API Key 미입력 (API000)"""
    def __init__(self, message: str = "네오플 API 키가 입력되지 않거나 잘못되었어양"):
        super().__init__(message)
        self.message = message

class NeopleAPIInvalidId(ClientBaseException):
    """Neople API 유효하지 않은 게임아이디 (API001)"""
    def __init__(self, message: str = "유효하지 않은 게임아이디를 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleAPILimitExceed(ClientBaseException):
    """Neople API 요청 제한 초과 (API002)"""
    def __init__(self, message: str = "네오플 API 요청 제한을 초과했어양"):
        super().__init__(message)
        self.message = message

class NeopleAPIInvalidAPIkey(ClientBaseException):
    """Neople API 잘못된 API 키 (API003)"""
    def __init__(self, message: str = "유효하지 않은 API 키를 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleAPIBlockedAPIKey(ClientBaseException):
    """Neople API 차단된 API 키 (API004)"""
    def __init__(self, message: str = "차단된 네오플 API 키를 사용하고 있어양"):
        super().__init__(message)
        self.message = message

class NeopleAPIWrongGameKey(ClientBaseException):
    """Neople API 잘못된 게임 키 (API005)"""
    def __init__(self, message: str = "다른 게임의 네오플 API를 호출했어양"):
        super().__init__(message)
        self.message = message

class NeopleAPIInvalidParams(ClientBaseException):
    """Neople API 잘못된 파라미터 (API006)"""
    def __init__(self, message: str = "잘못된 API 요청 파라미터를 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleAPIClientSocketError(ClientBaseException):
    """Neople API 클라이언트 소켓 오류 (API007)"""
    def __init__(self, message: str = "네오플 API와 통신 중에 오류가 발생했어양"):
        super().__init__(message)
        self.message = message

class NeopleAPIInvalidURL(ClientBaseException):
    """Neople API 잘못된 URL (API900)"""
    def __init__(self, message: str = "잘못된 API 요청 URL을 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleAPIInvalidRequestParams(ClientBaseException):
    """Neople API 잘못된 요청 파라미터 (API901)"""
    def __init__(self, message: str = "잘못된 API 요청 파라미터를 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleAPISystemError(ClientBaseException):
    """Neople API 시스템 오류 (API999)"""
    def __init__(self, message: str = "네오플 API 시스템 오류가 발생했어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFInvalidServerID(ClientBaseException):
    """Neople API 유효하지 않은 서버 ID (DNF000)"""
    def __init__(self, message: str = "잘못된 서버명(ID)를 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFInvalidCharacterInfo(ClientBaseException):
    """Neople API 유효하지 않은 캐릭터 정보 (DNF001)"""
    def __init__(self, message: str = "잘못된 캐릭터 정보를 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFInvalidItemInfo(ClientBaseException):
    """Neople API 유효하지 않은 아이템 정보 (DNF003)"""
    def __init__(self, message: str = "잘못된 아이템 정보를 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFInvalidAuctionInfo(ClientBaseException):
    """Neople API 유효하지 않은 경매장 정보 (DNF004)"""
    def __init__(self, message: str = "잘못된 경매장 정보를 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFInvalidSkillInfo(ClientBaseException):
    """Neople API 유효하지 않은 스킬 정보 (DNF005)"""
    def __init__(self, message: str = "잘못된 스킬 정보를 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFInvalidTimelineParams(ClientBaseException):
    """Neople API 유효하지 않은 타임라인 검색 시간 파라미터 (DNF006)"""
    def __init__(self, message: str = "타임라인을 불러오는데 문제가 발생했어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFSearchAuctionItemOptionException(ClientBaseException):
    """Neople API 경매장 아이템 검색 갯수 제한 (DNF007)"""
    def __init__(self, message: str = "경매장 아이템 검색 갯수 제한에 걸렸어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFSearchAuctionMultipleItemOptionException(ClientBaseException):
    """Neople API 다중 아이템 검색 갯수 제한 (DNF008)"""
    def __init__(self, message: str = "다중 아이템 검색 갯수 제한에 걸렸어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFSearchAvatarMarketOptionException(ClientBaseException):
    """Neople API 아바타 마켓 검색 갯수 제한 (DNF009)"""
    def __init__(self, message: str = "아바타 마켓 검색 갯수 제한에 걸렸어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFInvalidURL(ClientBaseException):
    """Neople API 유효하지 않은 URL (DNF900)"""
    def __init__(self, message: str = "잘못된 API 요청 URL을 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFInvalidRequestParams(ClientBaseException):
    """Neople API 유효하지 않은 요청 파라미터 (DNF901)"""
    def __init__(self, message: str = "잘못된 API 요청 파라미터를 입력했어양"):
        super().__init__(message)
        self.message = message

class NeopleDNFSystemMaintenance(ClientBaseException):
    """Neople API 서비스 점검중 (DNF980)"""
    def __init__(self, message: str = "던파 서비스 점검 중이에양!"):
        super().__init__(message)
        self.message = message

class NeopleDNFSystemError(ClientBaseException):
    """Neople API 시스템 오류 (DNF999)"""
    def __init__(self, message: str = "던파 API 시스템 오류가 발생했어양"):
        super().__init__(message)
        self.message = message

def neople_api_error_handler(error_code: str) -> None:
    """Neople API 오류 처리 함수

    Args:
        error_code (str): Neople API 오류 코드

    Raises:
        NeopleAPIError: Neople API 오류

    Returns:
        No return
    """
    if not isinstance(error_code, str):
        raise NeopleAPIError("Invalid Neople API error code")
    else:
        error_code = error_code.strip().upper()

    # Neople API 오류 로직처리
    if "API000" in error_code:
        raise NeopleAPIKeyMissing(error_code)
    elif "API001" in error_code:
        raise NeopleAPIInvalidId(error_code)
    elif "API002" in error_code:
        raise NeopleAPILimitExceed(error_code)
    elif "API003" in error_code:
        raise NeopleAPIInvalidAPIkey(error_code)
    elif "API004" in error_code:
        raise NeopleAPIBlockedAPIKey(error_code)
    elif "API005" in error_code:
        raise NeopleAPIWrongGameKey(error_code)
    elif "API006" in error_code:
        raise NeopleAPIInvalidParams(error_code)
    elif "API007" in error_code:
        raise NeopleAPIClientSocketError(error_code)
    elif "API900" in error_code:
        raise NeopleAPIInvalidURL(error_code)
    elif "API901" in error_code:
        raise NeopleAPIInvalidRequestParams(error_code)
    elif "API999" in error_code:
        raise NeopleAPISystemError(error_code)
    elif "DNF000" in error_code:
        raise NeopleDNFInvalidServerID(error_code)
    elif "DNF001" in error_code:
        raise NeopleDNFInvalidCharacterInfo(error_code)
    elif "DNF003" in error_code:
        raise NeopleDNFInvalidItemInfo(error_code)
    elif "DNF004" in error_code:
        raise NeopleDNFInvalidAuctionInfo(error_code)
    elif "DNF005" in error_code:
        raise NeopleDNFInvalidSkillInfo(error_code)
    elif "DNF006" in error_code:
        raise NeopleDNFInvalidTimelineParams(error_code)
    elif "DNF007" in error_code:
        raise NeopleDNFSearchAuctionItemOptionException(error_code)
    elif "DNF008" in error_code:
        raise NeopleDNFSearchAuctionMultipleItemOptionException(error_code)
    elif "DNF009" in error_code:
        raise NeopleDNFSearchAvatarMarketOptionException(error_code)
    elif "DNF900" in error_code:
        raise NeopleDNFInvalidURL(error_code)
    elif "DNF901" in error_code:
        raise NeopleDNFInvalidRequestParams(error_code)
    elif "DNF980" in error_code:
        raise NeopleDNFSystemMaintenance(error_code)
    elif "DNF999" in error_code:
        raise NeopleDNFSystemError(error_code)
    else:
        raise NeopleAPIError(f"Unknown Neople API error code: {error_code}")
    

class KakaoAPIError(ClientBaseException):
    """Kakao API 사용 중 발생하는 오류"""
    pass

class KakaoNoLocalInfo(ClientBaseException):
    """카카오 로컬 API 지역정보 검색결과 없음"""
    def __init__(self, message: str = "Kakao API에서 지역 정보를 찾을 수 없어양"):
        super().__init__(message)
        self.message = message

class KKO_LOCAL_API_ERROR(ClientBaseException):
    """카카오 로컬 API 관련 오류"""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class WeatherAPIError(ClientBaseException):
    """날씨 API 사용 중 발생하는 오류"""
    pass

class WTH_API_INTERNAL_ERROR(ClientBaseException):
    """날씨 API 내부 오류"""
    pass

class WTH_API_DATA_ERROR(ClientBaseException):
    """날씨 API 데이터 오류"""
    pass

class WTH_API_DATA_NOT_FOUND(ClientBaseException):
    """날씨 API 데이터 없음"""
    pass

class WTH_API_HTTP_ERROR(ClientBaseException):
    """날씨 API 잘못된 요청"""
    pass

class WTH_API_TIMEOUT(ClientBaseException):
    """날씨 API 타임아웃 오류"""
    pass

class WTH_API_INVALID_PARAMS(ClientBaseException):
    """날씨 API 잘못된 파라미터"""
    pass

class WTH_API_INVALID_REGION(ClientBaseException):
    """날씨 API 잘못된 지역"""
    pass

class WTH_API_DEPRECATED(ClientBaseException):
    """날씨 API 사용 중단"""
    pass

class WTH_API_UNAUTHORIZED(ClientBaseException):
    """날씨 API 서비스 접근 거부"""
    pass

class WTH_API_KEY_TEMP_ERROR(ClientBaseException):
    """날씨 API 키 일시적 오류"""
    pass

class WTH_API_KEY_LIMIT_EXCEEDED(ClientBaseException):
    """날씨 API 키 요청 제한 초과"""
    pass

class WTH_API_KEY_INVALID(ClientBaseException):
    """날씨 API 잘못된 API 키 사용"""
    pass

class WTH_API_KEY_EXPIRED(ClientBaseException):
    """날씨 API API 키 만료"""
    pass

class WTH_API_OTHER_ERROR(ClientBaseException):
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
    def __init__(self, message: str = "주식 관련 오류가 발생했어양"):
        super().__init__(message)
        self.message = message

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