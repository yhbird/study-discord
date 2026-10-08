"""
`븜 넥슨토큰` 기능에서 사용하는 상수 모음 (2026-10-05, Opus 5.5)
"""
from typing import Literal


class NexonTokenVars:
    # 개인정보 수집 동의 기록 구분 (personal_information_usage_agreement.service_code)
    SERVICE_CODE: Literal["nexon_api_token"] = "nexon_api_token"

    # 수집 동의 안내문 버전, 안내문 내용을 바꾸면 날짜를 갱신
    POLICY_VERSION: Literal["2026-10-05"] = "2026-10-05"

    # 토큰 관리 쓰레드 유지 시간 (초), 지나면 쓰레드를 삭제
    SESSION_TIMEOUT_SEC: int = 30 * 60

    # 쓰레드 자동 보관 시간 (분), 디스코드 최소값 60분 (봇 재시작으로 삭제 작업이 사라졌을 때 대비)
    THREAD_AUTO_ARCHIVE_MIN: Literal[60] = 60

    # 토큰 목록에 보여줄 앞자리 글자 수
    TOKEN_PREVIEW_LEN: int = 10

    # 토큰 입력값 길이 제한
    TOKEN_MIN_LEN: int = 16
    TOKEN_MAX_LEN: int = 200

    # 저장 가능한 토큰 구분 (main: 본계정, sub: 부계정 또는 예비 키)
    KEY_INDEXES: tuple[str, str] = ("main", "sub")
    KEY_INDEX_LABEL: dict[str, str] = {
        "main": "메인",
        "sub": "서브",
    }


class NexonTokenUrls:
    # 토큰 유효성 검사용 API (계정 본인의 API 키로만 조회 가능한 스타포스 강화 기록)
    TOKEN_VALIDATION = "/maplestory/v1/history/starforce"
