from __future__ import annotations
from exceptions.base import UtilsBaseException

class YFinanceAPIError(UtilsBaseException):
    """YFinance API 사용 중 발생하는 오류"""
    pass

class DataGoAPIError(UtilsBaseException):
    """공공 데이터 포탈 API 사용 중 발생하는 오류"""
    pass

class StockException(YFinanceAPIError):
    """주식 관련 예외 클래스"""
    pass

class CurrencyException(UtilsBaseException):
    """환율 관련 예외 클래스"""
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

class YFI_HISTORY_INVALID_PERIOD(YFinanceAPIError):
    """지원하지 않는 기간으로 주식 히스토리를 요청할 때 발생하는 예외"""
    pass

class YFI_CURRENCY_PARSE_ERROR(CurrencyException):
    """현지 통화 단위를 파싱할 수 없는 예외"""
    pass

class YFI_CURRENCY_NOT_SUPPORT(CurrencyException):
    """지원하지 않는 현지통화 파싱시도"""
    pass

class STK_KRX_SEARCH_ERROR(DataGoAPIError):
    """한국 주식 코드 검색 오류 예외"""
    pass

class STK_KRX_SEARCH_NO_RESULT(DataGoAPIError):
    """한국 주식 코드 검색 결과 없음 예외"""
    pass