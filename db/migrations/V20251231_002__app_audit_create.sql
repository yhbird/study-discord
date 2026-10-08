BEGIN;

/*
 1. app_audit 스키마 생성
 */

CREATE SCHEMA IF NOT EXISTS app_audit;

COMMENT ON SCHEMA app_audit IS '서버 인프라 리소스 모니터링';

/*
 1-1. app_audit 권한 부여 (2026-10-05, Opus 5.5)
 - 테이블 생성 전에 기본 권한을 먼저 설정 (이후에 만드는 객체에만 적용)
 - 감사 기록은 수정, 삭제하지 않음: 봇(app)은 조회와 추가만, airflow는 조회만
 */

GRANT USAGE ON SCHEMA app_audit TO app, airflow;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_audit GRANT SELECT, INSERT ON TABLES TO app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_audit GRANT USAGE ON SEQUENCES TO app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_audit GRANT SELECT ON TABLES TO airflow;

GRANT ALL PRIVILEGES ON SCHEMA app_audit TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_audit GRANT ALL ON TABLES TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_audit GRANT ALL ON SEQUENCES TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_audit GRANT ALL ON FUNCTIONS TO maintenance_user, discord_dev;

/*
 2-1. migration_history 테이블 생성
 - version_info에 UNIQUE 제약 추가: 아래 INSERT의 ON CONFLICT (version_info)에 필요 (2026-10-05, Opus 5.5)
 */

CREATE TABLE IF NOT EXISTS app_audit.migration_history (
    id           BIGSERIAL PRIMARY KEY,
    version_info VARCHAR(100) NOT NULL UNIQUE,
    description  TEXT,
    apply_at     TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE app_audit.migration_history IS '데이터베이스 마이그레이션 기록';

/*
 2-2. migration_history 인덱스
 - UNIQUE 제약이 인덱스(migration_history_version_info_key)를 만들어서 별도 인덱스는 만들지 않음 (2026-10-05, Opus 5.5)
 */

/*
 3-1. discord_bot_transactions 테이블 생성
 */

CREATE TABLE IF NOT EXISTS app_audit.discord_bot_transactions (
    id           BIGSERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 트랜잭션 기록
    db_user      VARCHAR(30)  NOT NULL,
    bot_name     VARCHAR(100) NOT NULL,
    bot_version  VARCHAR(50)  NOT NULL,  -- 예: v1.2.3@prd (2026-10-05, Opus 5.5)
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