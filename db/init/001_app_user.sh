#!/bin/bash
# DB 계정 생성과 기본 권한 부여 (2026-10-05, Opus 5.5)
# - postgres 컨테이너가 빈 데이터 폴더로 처음 시작할 때 한 번만 실행
# - 비밀번호는 env/db.env 환경변수에서 읽음 (파일에 비밀번호를 쓰지 않음)
# - \getenv로 읽어서 비밀번호가 psql 명령줄 인자(프로세스 목록)에 노출되지 않음
set -euo pipefail

: "${DB_PASSWORD_MAINTENANCE:?env/db.env에 DB_PASSWORD_MAINTENANCE가 없습니다}"
: "${DB_PASSWORD_APP:?env/db.env에 DB_PASSWORD_APP가 없습니다}"
: "${DB_PASSWORD_AIRFLOW:?env/db.env에 DB_PASSWORD_AIRFLOW가 없습니다}"
: "${DB_PASSWORD_DEV:?env/db.env에 DB_PASSWORD_DEV가 없습니다}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
\getenv pw_maintenance DB_PASSWORD_MAINTENANCE
\getenv pw_app DB_PASSWORD_APP
\getenv pw_airflow DB_PASSWORD_AIRFLOW
\getenv pw_dev DB_PASSWORD_DEV
\getenv db_name POSTGRES_DB

-- 계정 생성 (이미 있으면 건너뜀)
-- maintenance_user: 관리자, app: 봇 연결, airflow: 데이터 수집, discord_dev: DB 도구 연결
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', r.rolname, r.pw)
FROM (VALUES
    ('maintenance_user', :'pw_maintenance'),
    ('app',              :'pw_app'),
    ('airflow',          :'pw_airflow'),
    ('discord_dev',      :'pw_dev')
) AS r(rolname, pw)
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = r.rolname)
\gexec

GRANT CONNECT ON DATABASE :"db_name" TO app, airflow, discord_dev, maintenance_user;

-- public schema 권한 부여
GRANT USAGE ON SCHEMA public TO app, airflow, discord_dev;
GRANT CREATE ON SCHEMA public TO app, airflow, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO app, airflow;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO app, airflow;

-- maintenance_user, discord_dev 에게 모든 권한 부여
GRANT ALL PRIVILEGES ON DATABASE :"db_name" TO maintenance_user, discord_dev;
GRANT ALL PRIVILEGES ON SCHEMA public TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO maintenance_user, discord_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO maintenance_user, discord_dev;
EOSQL
