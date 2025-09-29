"""
exceptions/base.py

공통 예외 처리 모듈

각 단계별 예외 클래스를 정의합니다.

"""

# 기본 bot 예외 클래스
class BotBaseException(Exception):
    """Bot 기본 예외 클래스"""
    def __init__(self, message: str = "알수 없는 오류가 발생 했어양"):
        super().__init__(message)
        self.message = message

class BotConfigFailed(BotBaseException):
    """봇 설정 실패"""
    def __init__(self, message: str = "봇 설정을 불러오는 데 실패했어양"):
        super().__init__(message)
        self.message = message

class BotInitializationError(BotBaseException):
    """봇 초기화 실패"""
    def __init__(self, message: str = "봇 초기화에 실패했어양"):
        super().__init__(message)
        self.message = message
        
class BotWarning(Exception):
    """작업을 중단하지 않고 경고 메시지를 표시할 때 사용"""
    pass

# client 단계 예외 클래스
class ClientBaseException(Exception):
    """Client 기본 예외 클래스"""
    def __init__(self, message: str = "알수 없는 API 호출 오류가 발생 했어양"):
        super().__init__(message)
        self.message = message

# mapping 단계 예외 클래스
class MapperBaseException(Exception):
    """Mapper 기본 예외 클래스"""
    def __init__(self, message: str = "알수 없는 데이터 오류가 발생 했어양"):
        super().__init__(message)
        self.message = message

# service 단계 예외 클래스
class ServiceBaseException(Exception):
    """Service 기본 예외 클래스"""
    def __init__(self, message: str = "알수 없는 디스코드 오류가 발생 했어양"):
        super().__init__(message)
        self.message = message

class BotCommandResponseError(BotBaseException):
    """명령어 응답 처리 중 오류 발생"""
    def __init__(self, message: str = "명령어 응답 처리 중 오류가 발생 했어양"):
        super().__init__(message)
        self.message = message