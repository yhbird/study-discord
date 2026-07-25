from __future__ import annotations
from common_exceptions.client_exceptions import NexonAPIError


class NexonMapleStoryError(NexonAPIError):
    """넥슨 메이플스토리 오픈 API 관련 예외 클래스"""
    pass

class APICharacterNotFound(NexonMapleStoryError):
    """넥슨 메이플스토리 오픈 API 캐릭터 조회 실패 예외 클래스"""
    pass

class MapleSchedulerNotFound(NexonMapleStoryError):
    """넥슨 메이플스토리 오픈 API 스케줄 조회 실패 예외 클래스"""

class MapleSchedulerNotRegistered(NexonMapleStoryError):
    """넥슨 메이플스토리 오픈 API 스케줄 조회 결과 예외 클래스"""

class MapleErrorMessage:
    """넥슨 메이플스토리 오픈 API 에러 메시지 상수 클래스"""

    # NexonAPICharacterNotFound 예외 발생 시 메시지
    CHARACTER_NOT_FOUND = "캐릭터 \'{character_name}\'이(가) 존재하지 않거나 찾을 수 없어양!"
    CHARACTER_OCID_NOT_FOUND = "캐릭터 \'{character_name}\' 정보를 찾을 수 없어양!"
    CHARACTER_SCHEDULER_NOT_FOUND = "캐릭터 \'{character_name}\'의 스케줄 정보를 조회 중에 에러가 발생했어양!"