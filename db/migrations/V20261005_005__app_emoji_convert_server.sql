/*
 이모지 변환 서버 설정 테이블 (2026-10-05, Opus 5.5)
 - 운영 DB에만 있고 SQL 파일이 없던 테이블을 pg_dump 구조 기준으로 작성
 - 새 설치: timestamptz로 바로 생성
 - 운영 DB: 이미 있는 테이블은 건너뛰고, timestamp 컬럼만 KST 기준으로 timestamptz로 변환
 - id는 운영 DB와 같게 SERIAL(integer) 유지
 */
CREATE TABLE IF NOT EXISTS app_service.emoji_convert_server (
    id            SERIAL PRIMARY KEY,
    guild_id      BIGINT NOT NULL UNIQUE,
    guild_name    TEXT,
    emoji_convert BOOLEAN DEFAULT false,
    create_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    update_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 운영 DB의 timestamp(시간대 없음) 컬럼 변환, 기존 값은 Asia/Seoul 기준으로 저장되어 있음
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'app_service'
          AND table_name = 'emoji_convert_server'
          AND column_name = 'create_at'
          AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE app_service.emoji_convert_server
            ALTER COLUMN create_at TYPE TIMESTAMPTZ USING create_at AT TIME ZONE 'Asia/Seoul',
            ALTER COLUMN update_at TYPE TIMESTAMPTZ USING update_at AT TIME ZONE 'Asia/Seoul';
    END IF;
END
$$;

COMMENT ON TABLE app_service.emoji_convert_server
    IS 'Discord앱 사용자가 이모지만 있는 메세지를 입력한 경우 큰 이미지의 이모지로 변경하는 기능을 사용할 수 있는 서버 목록
봇을 처음 도입한 서버의 경우 최초 1회 안내 메세지 출력 + OFF 상태로 자동 등록';
COMMENT ON COLUMN app_service.emoji_convert_server.id            IS '서버 등록 고유 ID';
COMMENT ON COLUMN app_service.emoji_convert_server.guild_id      IS '디스코드 서버(guild) ID';
COMMENT ON COLUMN app_service.emoji_convert_server.guild_name    IS '디스코드 서버(guild) 이름 (설정 변경시 갱신)';
COMMENT ON COLUMN app_service.emoji_convert_server.emoji_convert IS '이모지 큰 이미지 변환 사용 여부 (true: ON, false: OFF)';
COMMENT ON COLUMN app_service.emoji_convert_server.create_at     IS '서버 등록 일시';
COMMENT ON COLUMN app_service.emoji_convert_server.update_at     IS '설정 마지막 변경 일시';
