create table if not exists app_service.discord_command_logs(
    id bigserial primary key,
    created_at timestamptz not null default now(), -- log 생성 시간 (KST), 식별자

    -- 명령어 메타 데이터
    guild_id bigint not null,
    guild_name text,
    channel_id bigint not null,
    channel_name text,
    user_id bigint not null,
    user_name text,
    command_name text not null,
    command_name_alt text,
    args_json jsonb,

    -- 명령어 실행 결과
    command_result text, -- "success", "error", "warning"
    elapsed_time_ms int, -- 명령어 실행에 걸린 시간 (밀리초 단위)
    error_code text, -- 커스텀 에러 코드
    error_type text, -- 에러 타입
    error_message text,
    traceback text,
    
    -- 기타 주석 데이터
    etc_1 jsonb
);

-- 인덱스 생성
create index if not exists idx_discord_command_logs_guild_id on app_service.discord_command_logs(guild_id);
create index if not exists idx_discord_command_logs_user_id on app_service.discord_command_logs(user_id);
create index if not exists idx_discord_command_logs_created_at on app_service.discord_command_logs(created_at);

-- 파일 마지막에 항상 commit; 추가
commit;