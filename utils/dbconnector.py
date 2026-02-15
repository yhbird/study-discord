import asyncpg


class AsyncDBConnector:
    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None


    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10)
            print(f"[Bot] Database Connection Pool Created {self.dsn}")


    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            print("[Bot] Database Connection Pool Closed")


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