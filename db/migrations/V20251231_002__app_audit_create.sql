BEGIN;

/*
 1. app_audit 스키마 생성
 */

CREATE SCHEMA IF NOT EXISTS app_audit;

COMMENT ON SCHEMA app_audit IS '서버 인프라 리소스 모니터링';

/*
 2-1. migration_history 테이블 생성
 */

CREATE TABLE IF NOT EXISTS app_audit.migration_history (
    id           BIGSERIAL PRIMARY KEY,
    version_info VARCHAR(100) NOT NULL,
    description  TEXT,
    apply_at     TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE app_audit.migration_history IS '데이터베이스 마이그레이션 기록';

/*
 2-2. migration_history 인덱스 추가
 */

CREATE INDEX IF NOT EXISTS idx_migration_history_ver ON app_audit.migration_history(version_info);

/*
 3-1. discord_bot_transactions 테이블 생성
 */

CREATE TABLE IF NOT EXISTS app_audit.discord_bot_transactions (
    id           BIGSERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 트랜잭션 기록
    db_user      VARCHAR(30)  NOT NULL,
    bot_name     VARCHAR(100) NOT NULL,
    bot_version  VARCHAR(10)  NOT NULL,
    target_table VARCHAR(100) NOT NULL,
    bot_action   VARCHAR(300) NOT NULL,
    description  TEXT,

    -- 트랜잭션 실행 사용자 기록
    guild_id     BIGINT NOT NULL,
    guild_name   TEXT,
    channel_id   BIGINT NOT NULL,
    channel_name TEXT,
    user_id      BIGINT NOT NULL,
    user_name    TEXT,

    -- 기타 주석 데이터
    etc_detail   TEXT
);

COMMENT ON TABLE app_audit.discord_bot_transactions IS '디스코드 봇 트랜잭션 기록';

/*
 3-2. discord_bot_transactions 인덱스 추가
 */

CREATE INDEX IF NOT EXISTS idx_discord_bot_transactions_guild   ON app_audit.discord_bot_transactions(guild_id);
CREATE INDEX IF NOT EXISTS idx_discord_bot_transactions_user    ON app_audit.discord_bot_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_discord_bot_transactions_created ON app_audit.discord_bot_transactions(created_at);

/*
 4. migration history 작성
 */

INSERT INTO app_audit.migration_history (version_info, description)
VALUES
    (
    'create_app_audit_v1_20251231',
    '스키마 app_audit 생성, 데이터베이스 통합 기록과 디스코드 봇 트랜잭션 기록 추가'
    )
ON CONFLICT (version_info) DO NOTHING;

COMMIT;