BEGIN;

/*
 1. app_meta 스키마 생성
 */

CREATE SCHEMA IF NOT EXISTS app_meta;

COMMENT ON SCHEMA app_meta IS '게임 고정 확률 아이템, 정보 메타데이터 저장소';

/*
 2. maple_potential_options 테이블 생성
 */

CREATE TABLE IF NOT EXISTS app_meta.maple_potential_options (
    id             BIGSERIAL PRIMARY KEY,

    -- 검색 조건 칼럼
    option_grade   VARCHAR(4)  NOT NULL, -- 잠재등급 (R, E, U, L)
    option_type    VARCHAR(10) NOT NULL, -- 윗잠 아랫잠 구분
    option_id      VARCHAR(50) NOT NULL, -- STR, STR_P 등
    option_prime   VARCHAR(4) DEFAULT 'N', -- 유효옵션 여부 (Y, N)

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