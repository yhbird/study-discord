"""
exceptions/base.py

공통 예외 처리 모듈

각 단계별 예외 클래스를 정의합니다.

"""

# 기본 bot 예외 클래스
class BotBaseException(Exception):
    """Bot 기본 예외 클래스"""

class BotConfigFailed(BotBaseException):
    """봇 설정 실패"""

class BotInitializationError(BotBaseException):
    """봇 초기화 실패"""
        
class BotWarning(Exception):
    """작업을 중단하지 않고 경고 메시지를 표시할 때 사용"""
    pass

# utils 단계 예외 클래스
class UtilsBaseException(Exception):
    """Utils 기본 예외 클래스 common.py에서 사용됨"""

# command 단계 예외 클래스
class CommandBaseException(Exception):
    """Command 기본 예외 클래스 command.py에서 사용됨"""
