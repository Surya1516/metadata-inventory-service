import asyncio
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None


async def connect_with_retry(max_retries: int = 5, delay: float = 2.0) -> AsyncIOMotorClient:
    for attempt in range(1, max_retries + 1):
        try:
            client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
            await client.admin.command("ping")
            logger.info("Connected to MongoDB (attempt %d)", attempt)
            return client
        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            logger.warning("MongoDB not ready (attempt %d/%d): %s", attempt, max_retries, exc)
            if attempt < max_retries:
                await asyncio.sleep(delay * attempt)
    raise RuntimeError(f"Could not connect to MongoDB after {max_retries} attempts")


async def init_db() -> None:
    global _client
    _client = await connect_with_retry()
    await get_db()["metadata"].create_index("url", unique=True)


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _client[settings.mongodb_db]
