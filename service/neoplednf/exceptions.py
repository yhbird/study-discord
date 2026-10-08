"""
`븜 던파` 기능의 예외 → 사용자 안내 메시지 모음 (2026-10-08, Opus 5.5)

예외 클래스는 common_exceptions.client_exceptions의 neople_api_error_handler에서 발생시킨다.
"""
from __future__ import annotations
from common_exceptions.client_exceptions import (
    DNFCharacterNotFound, DNFCIDNotFound, NeopleAPIError, NeopleAPIInvalidId,
    NeopleAPIInvalidParams, NeopleAPILimitExceed,
    NeopleDNFInvalidCharacterInfo, NeopleDNFInvalidRequestParams,
    NeopleDNFInvalidServerID, NeopleDNFSystemError,
    NeopleDNFSystemMaintenance)
from common_exceptions.error_message import ErrorMessageMap


# Neople API 예외 → 사용자 안내 메시지
NEOPLE_API_ERROR_MESSAGES: ErrorMessageMap = {
    NeopleAPIInvalidId: "네오플 API 요청에 오류가 발생했어양!!!",
    NeopleAPILimitExceed: "네오플 API 요청 제한에 걸렸어양...",
    NeopleAPIInvalidParams: "네오플 API 요청 파라미터가 잘못되었어양...",
    NeopleDNFInvalidServerID: "서버명이 잘못 입력 되었어양...",
    NeopleDNFInvalidCharacterInfo:
        "캐릭터 '{character_name}'을(를) 찾을 수 없어양...",
    NeopleDNFInvalidRequestParams:
        "네오플 API 요청 파라미터에 오류가 발생했어양!!!",
    NeopleDNFSystemMaintenance: "현재 던전앤파이터 서비스 점검 중이에양!",
    NeopleDNFSystemError: "던전앤파이터 API에서 오류가 발생했어양!",
    DNFCIDNotFound:
        "{server_name}서버 '{character_name}'의 고유ID를 찾을 수 없어양...",
    DNFCharacterNotFound:
        "{server_name}서버 '{character_name}'을(를) 찾을 수 없어양...",
    NeopleAPIError: "네오플 API 요청에 오류가 발생했어양!!!",
}
DNF_UNKNOWN_ERROR_MESSAGE = "던전앤파이터 API 통신 중 알 수 없는 오류가 발생했어양!"
