DO
$$
begin
    -- admin 계정 생성
    if not exists (select from pg_catalog.pg_roles where rolname = 'maintenance_user') then
        create role maintenance_user login password 'maintenance_password';
    end if;

    -- bot 연결 계정 생성
    if not exists (select from pg_catalog.pg_roles where rolname = 'app') then
        create role app login password 'app_password';
    end if;

    -- airflow 연결 계정 생성
    if not exists (select from pg_catalog.pg_roles where rolname = 'airflow') then
        create role airflow login password 'airflow_password';
    end if;

    -- dbms 연결 계정 생성
    if not exists (select from pg_catalog.pg_roles where rolname = 'discord_dev') then
        create role discord_dev login password 'dev_password';
    end if;
end
$$;

grant connect on database discord_bot to app, airflow, discord_dev, maintenance_user;

\connect discord_bot

-- public schema 권한 부여
grant usage on schema public to app, airflow, discord_dev;
grant create on schema public to app, airflow, discord_dev;
alter default privileges in schema public grant select, insert, update on tables to app, airflow;
alter default privileges in schema public grant usage, select, update on sequences to app, airflow;
    
-- maintenance_user, discord_dev 에게 모든 권한 부여
grant all privileges on database discord_bot to maintenance_user, discord_dev;
grant all privileges on schema public to maintenance_user, discord_dev;
alter default privileges in schema public grant all on tables to maintenance_user, discord_dev;
alter default privileges in schema public grant all on sequences to maintenance_user, discord_dev;
alter default privileges in schema public grant all on functions to maintenance_user, discord_dev;

commit;