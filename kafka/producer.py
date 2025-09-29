import json
import time
import uuid
import asyncio
import traceback

from aiokafka import AIOKafkaProducer


class BotEventProducer:
    def __init__(self, bootstrap_servers: str, client_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.producer : AIOKafkaProducer | None = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,
            acks="all",
            enable_idempotence=True,
            compression_type="zstd",
        )
        await self.producer.start()

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def send(self, topic: str, key: str, value: dict):
        payload = json.dumps(value).encode("utf-8")
        await self.producer.send_and_wait(topic, key=key.encode(), value=payload)

producer = BotEventProducer(bootstrap_servers="localhost:9092", client_id="discord-bot")