"""
`븜` 메이플스토리 기능의 예외와 사용자 안내 메시지 모음

- 안내 메시지 맵 추가, 사용하지 않는 예외 클래스 삭제 (2026-10-08, Opus 5.5)
"""
from __future__ import annotations
from common_exceptions.client_exceptions import (
    NexonAPIError, NexonAPIBadRequest, NexonAPICharacterNotFound,
    NexonAPIForbidden, NexonAPIOCIDNotFound, NexonAPIServiceUnavailable,
    NexonAPISundayEventNotFound, NexonAPITooManyRequests)
from common_exceptions.error_message import ErrorMessageMap


class NexonMapleStoryError(NexonAPIError):
    """넥슨 메이플스토리 오픈 API 관련 예외 클래스"""
    pass


class MapleSchedulerNotRegistered(NexonMapleStoryError):
    """넥슨 메이플스토리 오픈 API 스케줄 조회 결과 예외 클래스"""


# Nexon API 예외 → 사용자 안내 메시지 (2026-10-08, Opus 5.5)
# 명령어마다 다른 메시지는 handle_command_error의 default로 넘긴다
NEXON_API_ERROR_MESSAGES: ErrorMessageMap = {
    NexonAPICharacterNotFound:
        "캐릭터 '{character_name}'을(를) 찾을 수 없어양!",
    NexonAPIOCIDNotFound:
        "캐릭터 '{character_name}'의 OCID를 찾을 수 없어양!",
    NexonAPIForbidden:
        "Nexon Open API 접근 권한이 없어양!",
    NexonAPITooManyRequests:
        "API 요청이 너무 많아양! 잠시 후 다시 시도해보세양",
    NexonAPIServiceUnavailable:
        "Nexon Open API 서버에 오류가 발생했거나 점검중이에양",
}

SUNDAY_NOTICE_ERROR_MESSAGES: ErrorMessageMap = {
    **NEXON_API_ERROR_MESSAGES,
    NexonAPISundayEventNotFound: (
        "썬데이 이벤트 공지사항이 아직 없어양!!\n"
        "매주 금요일 오전 10시에 업데이트 되니 참고해양!!"),
}

SCHEDULER_ERROR_MESSAGES: ErrorMessageMap = {
    **NEXON_API_ERROR_MESSAGES,
    MapleSchedulerNotRegistered:
        "캐릭터 '{character_name}'의 등록된 스케줄이 하나도 없어양!",
    NexonAPIBadRequest: (
        "캐릭터 '{character_name}'의 스케줄 조회에 실패했어양!\n"
        "지금 일부 캐릭터가 조회가 안되는 버그가 있어양 ㅠ"),
}


class MapleErrorMessage:
    """명령어별 기본 안내 메시지

    NEXON_API_ERROR_MESSAGES에 없는 예외일 때 사용 (2026-10-08, Opus 5.5)
    """

    BASIC_INFO_NOT_FOUND = "캐릭터 '{character_name}'의 기본 정보를 찾을 수 없어양!"
    CHARACTER_INFO_NOT_FOUND = "캐릭터 '{character_name}'의 정보를 찾을 수 없어양!"
    CHARACTER_NOT_FOUND = "캐릭터 '{character_name}'을(를) 찾을 수 없어양!"
    ABILITY_NOT_FOUND = (
        "캐릭터 '{character_name}'의 어빌리티 정보를 찾을 수 없어양!")
    CASH_EQUIPMENT_NOT_FOUND = (
        "캐릭터 '{character_name}'의 코디 정보를 찾을 수 없어양!")
    ITEM_EQUIPMENT_NOT_FOUND = (
        "캐릭터 '{character_name}'의 장비 정보를 찾을 수 없어양!")
    SCHEDULER_NOT_FOUND = "캐릭터 '{character_name}'의 스케줄 조회에 실패했어양!"
    PCBANG_NOTICE_NOT_FOUND = "PC방 이벤트 공지사항을 찾을 수 없어양!"
    SUNDAY_NOTICE_NOT_FOUND = "썬데이 이벤트 공지사항을 찾을 수 없어양!"
