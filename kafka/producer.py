import asyncio
import json
import time
import traceback
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaProducer

from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_NAME

producer: Optional[AIOKafkaProducer] = None


async def init_kafka_producer() -> None:
    global producer
    if producer is None:
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8")
        )
        try:
            await producer.start()
        except Exception as e:
            print(f"[ERROR] Failed to start Kafka producer: {e}")
            traceback.print_exc()
            producer = None


async def close_kafka_producer() -> None:
    global producer
    if producer is not None:
        await producer.stop()
        producer = None


async def send_log_to_kafka(payload: Dict[str, Any]) -> None:
    global producer
    if producer is None:
        return
    
    try:
        await producer.send_and_wait(KAFKA_TOPIC_NAME, payload)

    except Exception as e:
        print(f"[ERROR] Failed to send log to Kafka: {e}")
        traceback.print_exc()