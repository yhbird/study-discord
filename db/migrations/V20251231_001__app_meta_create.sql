BEGIN;

/*
 1. app_meta 스키마 생성
 */

CREATE SCHEMA IF NOT EXISTS app_meta;

COMMENT ON SCHEMA app_meta IS '게임 고정 확률 아이템, 정보 메타데이터 저장소';

/*
 1-1. app_meta 권한 부여 (2026-10-05, Opus 5.5)
 - 테이블 생성 전에 기본 권한을 먼저 설정 (이후에 만드는 객체에만 적용)
 - 봇(app)은 메타데이터 조회만, airflow는 메타데이터 수집(적재, 갱신)
 */

GRANT USAGE ON SCHEMA app_meta TO app, airflow;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_meta GRANT SELECT ON TABLES TO app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_meta GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO airflow;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_meta GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO airflow;

GRANT ALL PRIVILEGES ON SCHEMA app_meta TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_meta GRANT ALL ON TABLES TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_meta GRANT ALL ON SEQUENCES TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA app_meta GRANT ALL ON FUNCTIONS TO maintenance_user, discord_dev;

/*
 2. maple_potential_options 테이블 생성
 */

CREATE TABLE IF NOT EXISTS app_meta.maple_potential_options (
    id             BIGSERIAL PRIMARY KEY,

    -- 검색 조건 칼럼
    option_grade   VARCHAR(4)  NOT NULL,   -- 잠재등급 (R, E, U, L)
    option_type    VARCHAR(10) NOT NULL,   -- 윗잠 아랫잠 구분
    option_id      VARCHAR(50) NOT NULL,   -- STR, STR_P 등
    option_tier    VARCHAR(10),            -- 유효옵션 여부 (Prime, Selective, Semi-Prime, Semi-Selective, None)

    -- 아이템 조건
    item_lev_tier  INT NOT NULL,    -- 잠재등급 적용 레벨 구간
    item_lev_min   INT DEFAULT 0,   -- 착용 레벨 하한 (71)
    item_lev_max   INT DEFAULT 250, -- 착용 레벨 상한 (250)
    allowed_slots  JSONB,           -- 등장 가능 부위
                                    -- 예: ["hat", "top"]

    -- 수치 데이터
    option_value_1 DECIMAL(10, 2),  -- 메인 수치 (예: 12, 9)
    option_value_2 DECIMAL(10, 2),  -- 서브 수치 (확률, 지속시간)
    option_etc     VARCHAR(50),     -- 기타 옵션 (문장형 옵션 대비)

    -- 옵션 출력 예시
    display_option TEXT, -- 예: "공격시 {val2}% 확률로 MP {val1} 회복"

    -- 데이터 관리용 칼럼
    data_source    VARCHAR(10), -- 데이터 수집방식 (airflow, manual)
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE app_meta.maple_potential_options
    IS '메이플스토리 큐브, 잠재능력 재설정 옵션 목록 메타데이터 버전: 2025년 12월 31일';
COMMENT ON COLUMN app_meta.maple_potential_options.id             IS '옵션 고유 ID';
COMMENT ON COLUMN app_meta.maple_potential_options.option_grade   IS '잠재등급 (R, E, U, L)';
COMMENT ON COLUMN app_meta.maple_potential_options.option_type    IS '잠재능력, 에디셔널 잠재능력 구분';
COMMENT ON COLUMN app_meta.maple_potential_options.option_id      IS '잠재능력 구분ID (STR, STR_P)';
COMMENT ON COLUMN app_meta.maple_potential_options.option_tier    IS '유효옵션 여부 (Prime, Selective, Semi-Prime, Semi-Selective, None)';
COMMENT ON COLUMN app_meta.maple_potential_options.item_lev_tier  IS '잠재등급 적용 레벨 구간';
COMMENT ON COLUMN app_meta.maple_potential_options.item_lev_min   IS '착용 레벨 하한 (예: 71)';
COMMENT ON COLUMN app_meta.maple_potential_options.item_lev_max   IS '착용 레벨 상한 (예: 250)';
COMMENT ON COLUMN app_meta.maple_potential_options.allowed_slots  IS '등장 가능 부위 (예: ["hat", "top"])';
COMMENT ON COLUMN app_meta.maple_potential_options.option_value_1 IS '메인 수치 (예: 12, 9)';
COMMENT ON COLUMN app_meta.maple_potential_options.option_value_2 IS '서브 수치 (확률, 지속시간)';
COMMENT ON COLUMN app_meta.maple_potential_options.option_etc     IS '기타 옵션 (문장형 옵션 대비)';
COMMENT ON COLUMN app_meta.maple_potential_options.display_option IS '옵션 출력 형식 (예: 공격시 {val2}% 확률로 MP {val1} 회복)';
COMMENT ON COLUMN app_meta.maple_potential_options.data_source    IS '데이터 수집방식 (airflow, manual)';
COMMENT ON COLUMN app_meta.maple_potential_options.created_at     IS '데이터 등록 일시';
COMMENT ON COLUMN app_meta.maple_potential_options.updated_at     IS '데이터 수정 일시';

/*
 3. maple_potential_options 인덱스 생성
 */

 -- 봇이나 시뮬레이터가 주로 조회하는 패턴: 등급 + 레벨 + 부위
CREATE INDEX idx_maple_pot_search
ON app_meta.maple_potential_options (option_grade, item_lev_tier, item_lev_min, item_lev_max);

-- 옵션 타입으로 특정 옵션만 찾을 때
CREATE INDEX idx_maple_pot_type
ON app_meta.maple_potential_options (option_type);

-- JSONB 인덱스 (특정 부위에서 뜨는 옵션만 조회할 때 매우 빠름)
-- 예: WHERE allowed_slots ? 'hat'
CREATE INDEX idx_maple_pot_slots
ON app_meta.maple_potential_options USING GIN (allowed_slots);

COMMIT;