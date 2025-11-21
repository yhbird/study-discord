import asyncio
import json

from aiokafka import AIOKafkaConsumer
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from typing import Literal

# Kafka 설정
from config import KAFKA_ACTIVE
from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_NAME, POSTGRES_DSN
KAFKA_GROUP_ID: Literal["discord-command-log-writer"] = "discord-command-log-writer"
target_schema = "app_service"
target_table = "discord_command_logs"

# DB 엔진 생성
def get_engine() -> Engine:
    if POSTGRES_DSN != "":
        return create_engine(POSTGRES_DSN, pool_pre_ping=True)
    else:
        return None
    
async def handle_message(engine: Engine, payload: dict) -> None:
    """Kafka 메세지 1개를 app_service_discord_command_logs에 Insert합니다.

    Args:
        engine (Engine): SQLAlchemy Engine 객체
        payload (dict): Kafka 메세지의 payload
    """
    sql = text(
        f"""
        INSERT INTO {target_schema}.{target_table} (
            guild_id,
            guild_name,
            channel_id,
            channel_name,
            user_id,
            user_name,
            command_name,
            command_name_alt,
            args_json,
            result,
            elapsed_time_ms,
            error_code,
            error_type,
            error_message,
            traceback,
            etc_1
        ) VALUES (
            :guild_id,
            :guild_name,
            :channel_id,
            :channel_name,
            :user_id,
            :user_name,
            :command_name,
            :command_name_alt,
            CAST(:args_json AS jsonb),
            :result,
            :elapsed_time_ms,
            :error_code,
            :error_type,
            :error_message,
            :traceback,
            CAST(:etc_1 AS jsonb)
        )
        """
    )

    args_json = payload.get("args_json", {})
    etc_1 = payload.get("etc_1") or {}

    params = {
        "guild_id": payload.get("guild_id"),
        "guild_name": payload.get("guild_name"),
        "channel_id": payload.get("channel_id"),
        "channel_name": payload.get("channel_name"),
        "user_id": payload.get("user_id"),
        "user_name": payload.get("user_name"),
        "command_name": payload.get("command_name"),
        "command_name_alt": payload.get("command_name_alt"),
        "args_json": json.dumps(args_json, ensure_ascii=False),
        "result": payload.get("result"),
        "elapsed_time_ms": payload.get("elapsed_time_ms"),
        "error_code": payload.get("error_code"),
        "error_type": payload.get("error_type"),
        "error_message": payload.get("error_message"),
        "traceback": payload.get("traceback"),
        "etc_1": json.dumps(etc_1, ensure_ascii=False),
    }

    with engine.begin() as connection:
        connection.execute(sql, params)


async def consume_kafka_logs() -> None:
    """Kafka에서 명령어 로그를 소비하여 DB에 저장합니다."""
    if not KAFKA_ACTIVE:
        return

    if POSTGRES_DSN == "":
        return
    
    engine = get_engine()
    if engine is None:
        return

    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC_NAME,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        enable_auto_commit=True,
        auto_offset_reset="latest",
    )

    await consumer.start()
    try:
        async for msg in consumer:
            payload: dict = msg.value
            try:
                await handle_message(engine, payload)
            except Exception as e:
                print(f"[ERROR] Failed to insert log: {e}")
                print(f"Payload: {payload}")
    finally:
        await consumer.stop()