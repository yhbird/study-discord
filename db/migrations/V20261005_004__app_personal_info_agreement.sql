/*
 개인정보 수집 및 이용 동의 기록 테이블 (2026-10-05, Opus 5.5)
 - 여러 서비스의 수집 동의 기록을 한 테이블에서 관리 (service_code로 구분)
 - 동의 철회시 행을 지우지 않고 withdrawn_at을 기록, 재동의시 새 행을 추가
 - 연 1회 이용내역 통지(DM) 스케줄링은 notified_at 기준으로 대상 조회
 */
CREATE TABLE IF NOT EXISTS app_service.personal_information_usage_agreement (
    agreement_id   BIGSERIAL PRIMARY KEY,
    discord_id     BIGINT NOT NULL,
    service_code   VARCHAR(30) NOT NULL,
    policy_version VARCHAR(20) NOT NULL,
    agreed_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    withdrawn_at   TIMESTAMPTZ,
    notified_at    TIMESTAMPTZ
);

COMMENT ON TABLE app_service.personal_information_usage_agreement
    IS '서비스별 개인정보 수집 및 이용 동의 기록 (동의 사실 증빙, 연 1회 이용내역 통지용)';
COMMENT ON COLUMN app_service.personal_information_usage_agreement.agreement_id   IS '동의 기록 고유 ID';
COMMENT ON COLUMN app_service.personal_information_usage_agreement.discord_id     IS '디스코드 사용자 ID';
COMMENT ON COLUMN app_service.personal_information_usage_agreement.service_code   IS '동의 대상 서비스 구분 (예: nexon_api_token)';
COMMENT ON COLUMN app_service.personal_information_usage_agreement.policy_version IS '사용자가 동의한 안내문 버전 (예: 2026-10-05)';
COMMENT ON COLUMN app_service.personal_information_usage_agreement.agreed_at      IS '수집 및 이용 동의 일시';
COMMENT ON COLUMN app_service.personal_information_usage_agreement.withdrawn_at   IS '동의 철회 일시 (NULL이면 동의 유지중)';
COMMENT ON COLUMN app_service.personal_information_usage_agreement.notified_at    IS '마지막 이용내역 통지(DM) 일시';

-- 사용자별, 서비스별 유효한 동의는 하나만 존재
CREATE UNIQUE INDEX uq_agreement_active
    ON app_service.personal_information_usage_agreement (discord_id, service_code)
    WHERE withdrawn_at IS NULL;

-- 연 1회 이용내역 통지 대상 조회
CREATE INDEX idx_agreement_notify
    ON app_service.personal_information_usage_agreement (service_code, notified_at)
    WHERE withdrawn_at IS NULL;
