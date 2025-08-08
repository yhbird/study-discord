"""api_exceptions.py

API 관련 예외 처리 모듈

api_command.py / api_utils.py에서 사용되는 예외 클래스 정의

"""
from service.common import (
    BotBaseException, 
    BotCommandError, 
    BotCommandInvalidError, 
    BotCommandResponseError
)

class NexonAPIError(BotBaseException):
    """Nexon API 사용 중 발생하는 오류"""
    pass

class NexonAPIBadRequest(NexonAPIError):
    """Nexon API Bad Request 오류"""
    def __init__(self, message: str = "Nexon API 요청이 잘못 되었어양"):
        super().__init__(message)
        self.message = message

class NexonAPIForbidden(NexonAPIError):
    """Nexon API Forbidden 오류"""
    def __init__(self, message: str = "Nexon API 접근 권한이 없어양"):
        super().__init__(message)
        self.message = message

class NexonAPITooManyRequests(NexonAPIError):
    """Nexon API Too Many Requests 오류"""
    def __init__(self, message: str = "Nexon API 요청이 너무 많아양"):
        super().__init__(message)
        self.message = message

class NexonAPIServiceUnavailable(NexonAPIError):
    """Nexon API Service Unavailable 오류"""
    def __init__(self, message: str = "Nexon API 서비스가 사용 불가능 해양"):
        super().__init__(message)
        self.message = message

class NexonAPIOCIDNotFound(NexonAPIError):
    """Nexon API OCID Not Found 오류"""
    def __init__(self, message: str = "Nexon API에서 OCID를 찾을 수 없어양"):
        super().__init__(message)
        self.message = message
        

class KakaoAPIError(BotBaseException):
    """Kakao API 사용 중 발생하는 오류"""
    pass

class KKO_NO_LOCAL_INFO(KakaoAPIError):
    """카카오 로컬 API 지역정보 검색결과 없음"""
    def __init__(self, message: str = "Kakao API에서 지역 정보를 찾을 수 없어양"):
        super().__init__(message)
        self.message = message

class KKO_LOCAL_API_ERROR(KakaoAPIError):
    """카카오 로컬 API 관련 오류"""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class WeatherAPIError(BotBaseException):
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

class WTH_API_KEY_LIMIT_EXCEEDED(WTH_API_KEY_TEMP_ERROR):
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