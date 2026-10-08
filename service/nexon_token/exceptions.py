"""
`븜 넥슨토큰` 기능의 utils 단계 예외 모음 (2026-10-05, Opus 5.5)
"""
from __future__ import annotations
from common_exceptions.base import UtilsBaseException
from common_exceptions.error_message import ErrorMessageMap


class NexonTokenError(UtilsBaseException):
    """넥슨 토큰 관리 기능 기본 예외 클래스"""


class TokenEncryptionUnavailable(NexonTokenError):
    """암호화 키(NEXON_TOKEN_ENC_KEY)가 없거나 잘못된 경우"""


class TokenAgreementRequired(NexonTokenError):
    """개인정보 수집 동의를 하지 않은 사용자가 저장, 삭제 기능을 사용한 경우"""


class TokenFormatInvalid(NexonTokenError):
    """입력한 토큰의 형식이 올바르지 않은 경우"""


class TokenLimitExceeded(NexonTokenError):
    """저장 가능한 토큰 개수(main, sub)를 넘은 경우"""


class TokenDuplicated(NexonTokenError):
    """이미 등록한 토큰을 다시 등록한 경우"""


class TokenInvalid(NexonTokenError):
    """Nexon Open API가 토큰을 거부한 경우 (잘못된 키, 만료된 키)"""


class TokenValidationFailed(NexonTokenError):
    """Nexon Open API 오류로 토큰 유효성 검사를 하지 못한 경우"""


class TokenNotFound(NexonTokenError):
    """삭제할 토큰이 없는 경우"""


class TokenThreadUnavailable(NexonTokenError):
    """비공개 쓰레드를 만들 수 없는 채널이거나 권한이 없는 경우"""


# utils 예외 → 사용자 안내 메시지 (command.py에서 옮김, 2026-10-08, Opus 5.5)
TOKEN_ERROR_MESSAGES: ErrorMessageMap = {
    TokenAgreementRequired:
        "개인정보 수집 및 이용에 동의해야 사용할 수 있어양!",
    TokenFormatInvalid: (
        "토큰 형식이 올바르지 않아양! "
        "넥슨 Open API 사이트에서 복사한 키를 그대로 붙여넣어 주세양"),
    TokenLimitExceeded: (
        "토큰은 최대 2개(메인, 서브)까지 저장할 수 있어양! "
        "기존 토큰을 삭제하고 다시 시도해주세양"),
    TokenDuplicated: "이미 저장한 토큰이에양!",
    TokenInvalid: (
        "넥슨 Open API에서 사용할 수 없는 토큰이라고 응답했어양! "
        "키를 다시 확인해주세양"),
    TokenValidationFailed: (
        "넥슨 Open API 서버 문제로 토큰을 확인하지 못했어양... "
        "잠시 후 다시 시도해주세양"),
    TokenNotFound: "이미 삭제된 토큰이에양!",
}
