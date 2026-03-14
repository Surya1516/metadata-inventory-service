import asyncio
import logging
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.metadata import FetchStatus, MetadataRecord
from app.repositories import metadata_repo
from app.services.fetcher import FetchError, fetch_url_metadata

logger = logging.getLogger(__name__)


async def collect_and_store(db: AsyncIOMotorDatabase, url: str) -> MetadataRecord:
    fetch_result = await fetch_url_metadata(url)
    return await metadata_repo.upsert_record(db, {
        "url": url,
        "status": FetchStatus.complete,
        "headers": fetch_result["headers"],
        "cookies": fetch_result["cookies"],
        "page_source": fetch_result["page_source"],
        "fetched_at": datetime.now(tz=timezone.utc),
        "error": None,
    })


async def _background_collect(db: AsyncIOMotorDatabase, url: str) -> None:
    try:
        await collect_and_store(db, url)
        logger.info("Background fetch done for %s", url)
    except FetchError as exc:
        logger.warning("Background fetch failed for %s: %s", url, exc)
        await metadata_repo.mark_error(db, url, str(exc))
    except Exception as exc:
        logger.exception("Unexpected error fetching %s", url)
        await metadata_repo.mark_error(db, url, str(exc))


def schedule_background_collect(db: AsyncIOMotorDatabase, url: str) -> None:
    asyncio.create_task(_background_collect(db, url))
