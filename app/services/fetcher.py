import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class FetchError(Exception):
    pass


async def fetch_url_metadata(url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=settings.fetch_timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

        logger.info("Fetched %s (%d bytes)", url, len(response.text))
        return {
            "headers": dict(response.headers),
            "cookies": dict(response.cookies),
            "page_source": response.text,
        }

    except httpx.TimeoutException as exc:
        raise FetchError(f"Request timed out for {url}: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise FetchError(f"HTTP error {exc.response.status_code} for {url}") from exc
    except httpx.RequestError as exc:
        raise FetchError(f"Request error for {url}: {exc}") from exc
