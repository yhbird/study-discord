CREATE TABLE IF NOT EXISTS app_service.nexon_api_tokens (
    discord_id   BIGINT NOT NULL,
    key_index    VARCHAR(4) NOT NULL CHECK (key_index IN ('main', 'sub')),
    api_token    TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    latest_at    TIMESTAMPTZ,                -- NULL이면 아직 사용 안 함 (2026-10-05, Opus 5.5)
    call_counts  BIGINT NOT NULL DEFAULT 0,
    rate_limits  INT NOT NULL DEFAULT 0,
    error_counts INT NOT NULL DEFAULT 0,
    PRIMARY KEY (discord_id, key_index)
);

COMMENT ON TABLE app_service.nexon_api_tokens
    IS '사용자별 Nexon Open API 토큰 저장소 (개인화 기능 제공용, 사용자 수집 동의 필요)';
COMMENT ON COLUMN app_service.nexon_api_tokens.discord_id   IS '디스코드 사용자 ID';
COMMENT ON COLUMN app_service.nexon_api_tokens.key_index    IS 'API 키 구분 (main: 본계정, sub: 부계정 또는 main 실패시 예비 키)';
COMMENT ON COLUMN app_service.nexon_api_tokens.api_token    IS '암호화된 Nexon API 토큰 (평문 저장 금지)';
COMMENT ON COLUMN app_service.nexon_api_tokens.created_at   IS 'API 키 등록 일시';
COMMENT ON COLUMN app_service.nexon_api_tokens.latest_at    IS 'API 키 마지막 사용 일시 (NULL이면 아직 사용 안 함)';
COMMENT ON COLUMN app_service.nexon_api_tokens.call_counts  IS 'API 호출 누적 횟수';
COMMENT ON COLUMN app_service.nexon_api_tokens.rate_limits  IS 'API 호출 요청 초과(rate limit)로 실패한 누적 횟수';
COMMENT ON COLUMN app_service.nexon_api_tokens.error_counts IS 'API 호출 중 에러가 발생한 누적 횟수';

-- discord_id 단독 조회는 기본키 인덱스(discord_id, key_index)를 사용 (2026-10-05, Opus 5.5)
CREATE INDEX idx_last_used_token ON app_service.nexon_api_tokens (discord_id, latest_at ASC NULLS FIRST);
