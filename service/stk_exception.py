from service.common import (
    BotBaseException, 
    BotWarning
)

class STKException(BotBaseException):
    """주식 관련 예외 클래스"""
    def __init__(self, message: str = "주식 관련 오류가 발생했어양"):
        super().__init__(message)
        self.message = message

class STK_ERROR_NO_RATE(BotWarning):
    """환율 정보를 찾을 수 없는 예외
    
    경고 메시지로 처리되며, 명령어 실행을 중단하지 않음
    """
    pass

class STK_ERROR_FETCH_RATE(BotWarning):
    """환율 정보를 가져오는 데 실패한 예외
    
    경고 메시지로 처리되며, 명령어 실행을 중단하지 않음
    """
    pass

class STK_ERROR_NO_TICKER(STKException):
    """티커 정보를 찾을 수 없는 예외"""
    pass