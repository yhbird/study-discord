# DISCORD-BOT 개발 노트
<!-- 작성 방법: .claude/README.md "DISCORD-BOT.md 작성 요령" 참고 -->

## Category별 DISCORD-BOT 개발 및 변경사항

### A: 기능추가

### B: 버그 발생 및 해결
- [B001] `ADMIN_CMD_4`가 `app.env`에 없어 `deb_log` 명령어 값이 `None` → 미해결 (2026-10-04)
- [B002] `븜 이미지` 결과 없음 반복 → 덕덕고 `i.js`가 403 차단, ddgs 9.2.3이 숨기고 빈 결과 반환 → ddgs 9.16.0 업그레이드로 해결 (2026-10-04)
- [B003] 던파 명령어에서 `DNFCIDNotFound`·`DNFCharacterNotFound` 안내가 안 나감 → `except NeopleAPIError`가 먼저 잡음 → MRO 기반 메시지 맵으로 해결 (2026-10-08)

### C: 에러 대처 메뉴얼
- [C001] 시작 시 `Failed loading environment file` → `env/app.env` 없음 → `app.env.example` 복사 후 값 입력 (2026-10-04)
- [C002] 시작 시 `BOT_TOKEN_DEV` 관련 `AssertionError` → `app.env`에 옛 소문자 키가 남음 → 대문자로 변경 (2026-10-04)
- [C003] `븜 이미지` 결과 없음이 자주 뜸 → `python tests/test_image_search.py` 실행해 엔진별 실패 여부 확인 (2026-10-04)

### D: 봇의 특징과 정책 변경
- [D001] `븜 이미지`는 bing 엔진으로 검색되어 safesearch가 무시됨, 일반 채널은 `check_ban` 금칙어 필터에 의존 (2026-10-04)

### E: 기능 수정, 코드 수정
- [E001] env 파일 6개를 `env/app.env`로 통합, `config.py`·`basic_utils.py` 수정, 기존 파일은 `env/_old/` 백업 (2026-10-04)
- [E002] env 변수명 대문자 변경 `bot_token_*`→`BOT_TOKEN_*`, `kko_*`·`wth_*`·`stk_*`도 동일, 토큰 조회에 `.upper()` 사용 (2026-10-04)
- [E003] `ddgs` 9.2.3→9.16.0, `primp` 0.15.0→2.0.1 교체, `num_results`→`max_results`, `"No results found."` 예외 처리 추가 (2026-10-04)
- [E004] `븜 이미지`의 `time.sleep`·동기 DDGS 호출을 `asyncio.sleep`·`asyncio.to_thread`로 변경 (2026-10-04)
- [E005] 메이플·던파·날씨·넥슨토큰의 except 블록을 `common_exceptions/error_message.py`의 `handle_command_error`로 통합, 실패 시 `CommandFailure` 발생 (2026-10-08)
- [E006] `client_exceptions.py`의 미사용 YFinance·STK 중복 예외 삭제, finance는 `service/finance/exceptions.py` 사용 (2026-10-08)

### F: 개발 및 설정 규칙
- [F001] 환경변수는 `env/app.env` 한 파일로 관리하고, 추가할 때 `app.env.example`도 같이 수정 (2026-10-04)
- [F002] 환경변수명은 대문자만 쓰고 값은 항상 `""`로 감싼다 (2026-10-04)
- [F003] 환경변수는 Python에서 `str`로 받고 필요할 때만 형변환 `int(os.getenv('X', '0'))` (2026-10-04)
- [F004] 변수명은 서비스 접두어를 붙이고(`BOT_TOKEN_*`, `DB_*`, `NEXON_*`, `KKO_*` 등) 추가 전 중복 확인 (2026-10-04)
- [F005] `load_dotenv`는 `config.py`에서 한 번만 호출, 다른 모듈은 `config.py` 상수를 import (2026-10-04)
- [F006] F001 예외: DB 컨테이너 비밀번호는 `env/db.env`로 분리, 값은 작은따옴표로 감싼다 (compose가 큰따옴표 안 `$`를 변수로 해석) (2026-10-05)
- [F007] 명령어 안내 메시지는 서비스 `exceptions.py`에 `{예외: 메시지}` 맵으로 정의, `command.py`는 `handle_command_error`로 처리 (2026-10-08)

### 기타: 문서 작성 요령 및 규칙 변경
- [001] DISCORD-BOT 이력 작성 규칙, 범주화 및 index 추가, 범주별 줄바꿈을 통해 가독성 확보