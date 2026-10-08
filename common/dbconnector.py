import asyncpg


class AsyncDBConnector:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None
        self._is_connected = False  # 상태 플래그 추가

    async def connect(self):
        """pool이 유효한 경우 재생성하지 않음"""
        if self.pool is not None and not self.pool._closed:
            self._is_connected = True
            return
        try:
            self.pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=1,
                max_size=5,
                max_inactive_connection_lifetime=300.0,
                command_timeout=30.0,
            )
            self._is_connected = True
            print("AsyncDBConnector: pool created.")
        except Exception as e:
            self._is_connected = False
            self.pool = None
            print(f"AsyncDBConnector: pool creation failed. {e}")
            raise e

    async def close(self):
        """pool이 열려있을 때만 닫기"""
        if self.pool is None or self.pool._closed:
            self._is_connected = False
            return
        try:
            await self.pool.close()
            print("AsyncDBConnector: pool closed.")
        except Exception as e:
            print(f"AsyncDBConnector: pool close failed. {e}")
        finally:
            self._is_connected = False
            self.pool = None

    def is_available(self) -> bool:
        """pool이 실제로 사용 가능한 상태인지 확인"""
        return (
            self._is_connected
            and self.pool is not None
            and not self.pool._closed
        )

    async def get_emoji_convert_server(self, guild_id: int) -> asyncpg.Record | None:
        """
        서버(guild)별 이모지 변환 설정 정보를 가져오는 함수
        
        Args:
            guild_id (int): 서버(guild) ID

        Returns:
            asyncpg.Record | None: 이모지 변환 설정 정보 (없으면 None)

        Note:
            - "븜 이모지출력" 명령어를 사용했는데 결과가 없으면 -> INSERT쿼리 실행 + ON설정
            - "븜 이모지출력" 명령어를 사용했는데 결과가 있으면 -> UPDATE쿼리 실행 + ON/OFF 설정
            - 서버 내 사용자가 최초로 이모지만 있는 메세지를 보냄 -> 안내메세지 출력 + INSERT쿼리 실행 + OFF 설정

        """
        async with self.pool.acquire() as connection:
            conn: asyncpg.Connection = connection
            query = (
                """
                    select emoji_convert
                    from app_service.emoji_convert_server
                    where guild_id = $1
                """
            )
            return await conn.fetchrow(query, guild_id) or None

    
    async def register_server_default_off(self, guild_id: int, guild_name: str):
        """
        서버(guild)별 이모지 변환 설정 정보를 기본값(OFF)으로 등록하는 함수

        "븜 이모지출력" 기능이 있다고 최초 안내 이후, 테이블에 OFF 상태로 등록하는 용도로 사용

        Args:
            guild_id   (int): 서버(guild) ID
            guild_name (str): 서버(guild) 이름
        """
        async with self.pool.acquire() as connection:
            conn: asyncpg.Connection = connection
            query = (
                """
                    insert into app_service.emoji_convert_server 
                    (guild_id, guild_name, emoji_convert, create_at, update_at)
                    values ($1, $2, false, now(), now())
                    on conflict (guild_id) do nothing
                """
            )
            await conn.execute(query, guild_id, guild_name)

    
    async def toggle_emoji_convert(self, guild_id: int, guild_name: str) -> bool:
        """
        서버(guild)별 이모지 변환 설정을 토글하는 함수

        "븜 이모지출력" 명령어 사용 시, ON/OFF 상태를 토글하는 용도로 사용

        만약 테이블에 존재하지 않는 서버(guild_id)라면, 새로 등록하면서 ON 상태로 설정

        Args:
            guild_id   (int): 서버(guild) ID
            guild_name (str): 서버(guild) 이름

        Returns:
            bool: 토글 이후의 이모지 변환 설정 상태 (ON: True, OFF: False)
        """
        async with self.pool.acquire() as connection:
            conn: asyncpg.Connection = connection
            async with conn.transaction():
                row = await conn.fetchrow(
                    "select emoji_convert from app_service.emoji_convert_server"
                    " where guild_id = $1", guild_id
                )

                if row is None:
                    # 서버(guild)가 테이블에 없으면 새로 등록하면서 ON 상태로 설정
                    query = (
                        """
                            insert into app_service.emoji_convert_server 
                            (guild_id, guild_name, emoji_convert, create_at, update_at)
                            values ($1, $2, true, now(), now())
                        """
                    )
                    await conn.execute(query, guild_id, guild_name)
                    return True  # 새로 등록하면서 ON 상태
                else:
                    # 서버(guild)가 테이블에 있으면 현재 상태를 토글
                    update_status = not row["emoji_convert"]
                    query = (
                        """
                            update app_service.emoji_convert_server
                            set emoji_convert = $1, guild_name = $2, update_at = now()
                            where guild_id = $3
                        """
                    )
                    await conn.execute(query, update_status, guild_name, guild_id)
                    return update_status


    async def get_active_agreement(self, discord_id: int, service_code: str) -> asyncpg.Record | None:
        """
        사용자의 유효한(철회하지 않은) 개인정보 수집 동의 기록을 가져오는 함수 (2026-10-05, Opus 5.5)

        Args:
            discord_id   (int): 디스코드 사용자 ID
            service_code (str): 동의 대상 서비스 구분 (예: nexon_api_token)

        Returns:
            asyncpg.Record | None: 동의 기록 (동의하지 않았거나 철회했으면 None)
        """
        async with self.pool.acquire() as connection:
            conn: asyncpg.Connection = connection
            query = (
                """
                    select agreement_id, policy_version, agreed_at
                    from app_service.personal_information_usage_agreement
                    where discord_id = $1
                      and service_code = $2
                      and withdrawn_at is null
                """
            )
            return await conn.fetchrow(query, discord_id, service_code) or None


    async def insert_agreement(self, discord_id: int, service_code: str, policy_version: str) -> None:
        """
        개인정보 수집 동의 기록을 등록하는 함수 (2026-10-05, Opus 5.5)

        이미 유효한 동의 기록이 있으면 아무것도 하지 않음 (uq_agreement_active 인덱스)

        Args:
            discord_id     (int): 디스코드 사용자 ID
            service_code   (str): 동의 대상 서비스 구분
            policy_version (str): 사용자가 동의한 안내문 버전
        """
        async with self.pool.acquire() as connection:
            conn: asyncpg.Connection = connection
            query = (
                """
                    insert into app_service.personal_information_usage_agreement
                    (discord_id, service_code, policy_version, agreed_at)
                    values ($1, $2, $3, now())
                    on conflict (discord_id, service_code) where withdrawn_at is null
                    do nothing
                """
            )
            await conn.execute(query, discord_id, service_code, policy_version)


    async def get_nexon_api_tokens(self, discord_id: int) -> list[asyncpg.Record]:
        """
        사용자가 등록한 Nexon API 토큰 목록을 가져오는 함수 (main, sub 순서) (2026-10-05, Opus 5.5)

        Args:
            discord_id (int): 디스코드 사용자 ID

        Returns:
            list[asyncpg.Record]: 토큰 목록 (api_token은 암호화된 값)
        """
        async with self.pool.acquire() as connection:
            conn: asyncpg.Connection = connection
            query = (
                """
                    select key_index, api_token, created_at, latest_at, call_counts
                    from app_service.nexon_api_tokens
                    where discord_id = $1
                    order by case key_index when 'main' then 0 else 1 end
                """
            )
            return await conn.fetch(query, discord_id)


    async def insert_nexon_api_token(self, discord_id: int, encrypted_token: str) -> str | None:
        """
        Nexon API 토큰을 비어있는 key_index(main → sub 순서)에 등록하는 함수 (2026-10-05, Opus 5.5)

        Args:
            discord_id      (int): 디스코드 사용자 ID
            encrypted_token (str): 암호화된 API 토큰

        Returns:
            str | None: 등록된 key_index (빈 자리가 없거나 동시 등록으로 충돌하면 None)
        """
        async with self.pool.acquire() as connection:
            conn: asyncpg.Connection = connection
            async with conn.transaction():
                rows = await conn.fetch(
                    "select key_index from app_service.nexon_api_tokens"
                    " where discord_id = $1 for update", discord_id
                )
                used_indexes = {row["key_index"] for row in rows}
                key_index = next((k for k in ("main", "sub") if k not in used_indexes), None)
                if key_index is None:
                    return None

                query = (
                    """
                        insert into app_service.nexon_api_tokens
                        (discord_id, key_index, api_token, created_at, latest_at)
                        values ($1, $2, $3, now(), null)
                        on conflict (discord_id, key_index) do nothing
                        returning key_index
                    """
                )
                return await conn.fetchval(query, discord_id, key_index, encrypted_token)


    async def delete_nexon_api_token(self, discord_id: int, key_index: str) -> bool:
        """
        Nexon API 토큰을 삭제하는 함수 (2026-10-05, Opus 5.5)

        main 토큰을 삭제했을 때 sub 토큰이 남아 있으면 sub를 main으로 변경

        Args:
            discord_id (int): 디스코드 사용자 ID
            key_index  (str): 삭제할 토큰 구분 (main, sub)

        Returns:
            bool: 삭제 성공 여부 (삭제할 토큰이 없으면 False)
        """
        async with self.pool.acquire() as connection:
            conn: asyncpg.Connection = connection
            async with conn.transaction():
                result: str = await conn.execute(
                    "delete from app_service.nexon_api_tokens"
                    " where discord_id = $1 and key_index = $2", discord_id, key_index
                )
                if result == "DELETE 0":
                    return False

                if key_index == "main":
                    await conn.execute(
                        "update app_service.nexon_api_tokens set key_index = 'main'"
                        " where discord_id = $1 and key_index = 'sub'", discord_id
                    )
                return True


    async def withdraw_nexon_token_agreement(self, discord_id: int, service_code: str) -> int:
        """
        Nexon API 토큰 수집 동의를 철회하고 등록된 토큰을 모두 삭제하는 함수 (2026-10-05, Opus 5.5)

        동의 기록은 증빙을 위해 삭제하지 않고 withdrawn_at만 기록

        Args:
            discord_id   (int): 디스코드 사용자 ID
            service_code (str): 동의 대상 서비스 구분

        Returns:
            int: 삭제된 토큰 개수
        """
        async with self.pool.acquire() as connection:
            conn: asyncpg.Connection = connection
            async with conn.transaction():
                result: str = await conn.execute(
                    "delete from app_service.nexon_api_tokens where discord_id = $1", discord_id
                )
                await conn.execute(
                    """
                        update app_service.personal_information_usage_agreement
                        set withdrawn_at = now()
                        where discord_id = $1
                          and service_code = $2
                          and withdrawn_at is null
                    """, discord_id, service_code
                )
                return int(result.split()[-1])