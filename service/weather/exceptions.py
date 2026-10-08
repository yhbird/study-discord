"""
`븜 날씨` 기능의 예외 → 사용자 안내 메시지 모음 (2026-10-08, Opus 5.5)

예외 클래스는 common_exceptions.client_exceptions에 있다.
날씨 API 예외는 weather_exception_handler에서 발생시킨다.
"""
from __future__ import annotations
from common_exceptions.client_exceptions import (
    KakaoAPIError, KakaoNoLocalInfo, WeatherAPIError, WTH_API_DATA_ERROR,
    WTH_API_DATA_NOT_FOUND, WTH_API_DEPRECATED, WTH_API_HTTP_ERROR,
    WTH_API_INTERNAL_ERROR, WTH_API_INVALID_PARAMS, WTH_API_INVALID_REGION,
    WTH_API_KEY_EXPIRED, WTH_API_KEY_INVALID, WTH_API_KEY_LIMIT_EXCEEDED,
    WTH_API_KEY_TEMP_ERROR, WTH_API_TIMEOUT, WTH_API_UNAUTHORIZED)
from common_exceptions.error_message import ErrorMessageMap


# Kakao 지역 검색 API 예외 → 사용자 안내 메시지
# KKO_LOCAL_API_ERROR는 KakaoAPIError 메시지를 사용
KAKAO_LOCAL_ERROR_MESSAGES: ErrorMessageMap = {
    KakaoAPIError: "해당 지역의 정보를 검색하는 중에 오류가 발생했어양!",
    KakaoNoLocalInfo: "해당 지역의 정보를 찾을 수 없어양!",
}

# 기상청 날씨 API 예외 → 사용자 안내 메시지
WEATHER_API_ERROR_MESSAGES: ErrorMessageMap = {
    WTH_API_INTERNAL_ERROR: "날씨 정보를 가져오는 중에 오류가 발생했어양!",
    WTH_API_DATA_ERROR: "날씨 API 데이터에 문제가 발생했어양!",
    WTH_API_DATA_NOT_FOUND: "해당 지역의 날씨 정보를 찾을 수 없어양!",
    WTH_API_HTTP_ERROR: "날씨 API 요청 중에 오류가 발생했어양!",
    WTH_API_TIMEOUT: "날씨 데이터 가져오는데 시간이 초과되었어양!",
    WTH_API_INVALID_PARAMS: "날씨 API 요청 파라미터가 잘못되었어양!",
    WTH_API_INVALID_REGION: "해당 지역은 날씨 API에서 지원하지 않아양!",
    WTH_API_DEPRECATED: "더 이상 지원되지 않는 기능이에양!",
    WTH_API_UNAUTHORIZED: "날씨 API 서비스 접근 권한이 없어양!",
    WTH_API_KEY_TEMP_ERROR: "날씨 API 키가 임시로 제한되었어양!",
    WTH_API_KEY_LIMIT_EXCEEDED: "날씨 API 키의 요청 한도를 초과했어양!",
    WTH_API_KEY_INVALID: "날씨 API 키가 유효하지 않아양!",
    WTH_API_KEY_EXPIRED: "날씨 API 키가 만료되었어양!",
    WeatherAPIError: "날씨 API 요청 중에 오류가 발생했어양!",
}
WEATHER_UNKNOWN_ERROR_MESSAGE = (
    "날씨 정보를 가져오는 중에 알 수 없는 오류가 발생했어양!")
