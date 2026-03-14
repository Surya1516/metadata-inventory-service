import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.models.metadata import FetchStatus, MetadataRecord

logger = logging.getLogger(__name__)

COLLECTION = "metadata"


def _doc_to_record(doc: Dict[str, Any]) -> MetadataRecord:
    doc.pop("_id", None)
    return MetadataRecord(**doc)


async def find_by_url(db: AsyncIOMotorDatabase, url: str) -> Optional[MetadataRecord]:
    doc = await db[COLLECTION].find_one({"url": url}, {"_id": 0})
    return _doc_to_record(doc) if doc is not None else None


async def upsert_record(db: AsyncIOMotorDatabase, data: Dict[str, Any]) -> MetadataRecord:
    doc = await db[COLLECTION].find_one_and_update(
        {"url": data["url"]},
        {"$set": data},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return _doc_to_record(doc)


async def insert_pending(db: AsyncIOMotorDatabase, url: str) -> bool:
    """Insert a pending placeholder. Returns False if the URL already exists."""
    try:
        await db[COLLECTION].insert_one(
            {
                "url": url,
                "status": FetchStatus.pending,
                "headers": {},
                "cookies": {},
                "page_source": "",
                "fetched_at": None,
                "error": None,
            }
        )
        return True
    except DuplicateKeyError:
        return False


async def mark_error(db: AsyncIOMotorDatabase, url: str, error: str) -> None:
    await db[COLLECTION].update_one(
        {"url": url},
        {
            "$set": {
                "status": FetchStatus.error,
                "error": error,
                "fetched_at": datetime.now(tz=timezone.utc),
            }
        },
    )
