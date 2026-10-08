/*
 app_service 스키마와 명령어 사용 로그 테이블 생성 (2026-10-05, Opus 5.5)
 - db/init/002_app_schema.sql, db/init/003_app_command_log.sql에서 이동
   (init은 빈 DB에서 한 번만 실행되어 변경 이력을 남길 수 없음, init에는 계정 생성만 유지)
 - 운영 DB에는 이미 있는 스키마, 테이블이라 IF NOT EXISTS로 작성
 - 주의: ALTER DEFAULT PRIVILEGES는 이 파일을 실행한 계정이 이후에 만드는 객체에만 적용되므로
   모든 마이그레이션은 같은 계정(postgres)으로 실행
 */

/*
 1. app_service 스키마 생성
 */

-- 스키마 소유자는 실행 계정(postgres), 봇(app)은 권한만 부여
CREATE SCHEMA IF NOT EXISTS app_service;

COMMENT ON SCHEMA app_service IS '디스코드 봇 서비스 데이터 (명령어 로그, 서버 설정, 사용자 토큰, 개인정보 동의 기록)';

/*
 2. app_service 권한 부여 (테이블 생성 전에 기본 권한을 먼저 설정)
 */

-- 봇(app), airflow: 데이터 읽기, 쓰기
GRANT USAGE, CREATE ON SCHEMA app_service TO app, airflow;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_service GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app, airflow;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_service GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO app, airflow;

-- maintenance_user, discord_dev: 모든 권한
GRANT ALL PRIVILEGES ON SCHEMA app_service TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_service GRANT ALL ON TABLES TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_service GRANT ALL ON SEQUENCES TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_service GRANT ALL ON FUNCTIONS TO maintenance_user, discord_dev;

/*
 3. discord_command_logs 테이블 생성
 - Kafka consumer(kafka/consumer.py)가 discord.command.logs 토픽 메세지를 받아서 INSERT
 - consumer는 enable_auto_commit=True라서 INSERT 실패시 로그가 사라지므로, 봇 시작 전에 이 테이블이 있어야 함
 */

CREATE TABLE IF NOT EXISTS app_service.discord_command_logs (
    id               BIGSERIAL PRIMARY KEY,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 명령어 메타 데이터
    guild_id         BIGINT NOT NULL,
    guild_name       TEXT,
    channel_id       BIGINT NOT NULL,
    channel_name     TEXT,
    user_id          BIGINT NOT NULL,
    user_name        TEXT,
    command_name     TEXT NOT NULL,
    command_name_alt TEXT,
    args_json        JSONB,

    -- 명령어 실행 결과
    command_result   TEXT,
    elapsed_time_ms  INT,
    error_code       TEXT,
    error_type       TEXT,
    error_message    TEXT,
    traceback        TEXT,

    -- 기타 주석 데이터
    etc_1            JSONB
);

COMMENT ON TABLE app_service.discord_command_logs
    IS '디스코드 봇 명령어 사용 로그 (Kafka consumer가 적재, 이용 통계와 문제 시점 추적용)';
COMMENT ON COLUMN app_service.discord_command_logs.id               IS '로그 고유 ID';
COMMENT ON COLUMN app_service.discord_command_logs.created_at       IS '로그 생성 일시 (KST)';
COMMENT ON COLUMN app_service.discord_command_logs.guild_id         IS '디스코드 서버(guild) ID';
COMMENT ON COLUMN app_service.discord_command_logs.guild_name       IS '디스코드 서버(guild) 이름';
COMMENT ON COLUMN app_service.discord_command_logs.channel_id       IS '명령어를 사용한 채널 ID';
COMMENT ON COLUMN app_service.discord_command_logs.channel_name     IS '명령어를 사용한 채널 이름';
COMMENT ON COLUMN app_service.discord_command_logs.user_id          IS '명령어를 사용한 디스코드 사용자 ID';
COMMENT ON COLUMN app_service.discord_command_logs.user_name        IS '명령어를 사용한 디스코드 사용자 이름';
COMMENT ON COLUMN app_service.discord_command_logs.command_name     IS '실행된 명령어 함수 이름';
COMMENT ON COLUMN app_service.discord_command_logs.command_name_alt IS '명령어 표시 이름 (예: 븜 이미지, 없으면 함수 이름)';
COMMENT ON COLUMN app_service.discord_command_logs.args_json        IS '명령어 인자';
COMMENT ON COLUMN app_service.discord_command_logs.command_result   IS '명령어 실행 결과 (success, error, warning)';
COMMENT ON COLUMN app_service.discord_command_logs.elapsed_time_ms  IS '명령어 실행에 걸린 시간 (밀리초)';
COMMENT ON COLUMN app_service.discord_command_logs.error_code       IS '커스텀 에러 코드';
COMMENT ON COLUMN app_service.discord_command_logs.error_type       IS '에러 타입 (예외 클래스 이름)';
COMMENT ON COLUMN app_service.discord_command_logs.error_message    IS '에러 메세지';
COMMENT ON COLUMN app_service.discord_command_logs.traceback        IS '에러 traceback';
COMMENT ON COLUMN app_service.discord_command_logs.etc_1            IS '기타 부가 데이터';

/*
 4. discord_command_logs 인덱스 생성
 */

CREATE INDEX IF NOT EXISTS idx_discord_command_logs_guild_id   ON app_service.discord_command_logs (guild_id);
CREATE INDEX IF NOT EXISTS idx_discord_command_logs_user_id    ON app_service.discord_command_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_discord_command_logs_created_at ON app_service.discord_command_logs (created_at);
