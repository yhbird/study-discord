-- schema 생성 권한 부여
create schema if not exists app_service authorization app;
grant usage on schema app_service to app, airflow;
grant create on schema app_service to app, airflow;
alter default privileges in schema app_service grant select, insert, update, delete on tables to app, airflow;
alter default privileges in schema app_service grant usage, select, update on sequences to app, airflow;

-- maintenance_user 에게 모든 권한 부여
grant all privileges on schema app_service to maintenance_user, discord_dev;
grant all privileges on all tables in schema app_service to maintenance_user, discord_dev;
grant all privileges on all sequences in schema app_service to maintenance_user, discord_dev;
grant all privileges on all functions in schema app_service to maintenance_user, discord_dev;
alter default privileges in schema app_service grant all on tables to maintenance_user, discord_dev;
alter default privileges in schema app_service grant all on sequences to maintenance_user, discord_dev;
alter default privileges in schema app_service grant all on functions to maintenance_user, discord_dev;
-- 파일 마지막에 항상 commit; 추가
commit;