from unittest.mock import AsyncMock, patch

import pytest

from app.models.metadata import FetchStatus
from tests.conftest import FAKE_FETCH_RESULT, FAKE_RECORD

pytestmark = pytest.mark.asyncio


async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_post_metadata_success(client):
    with patch(
        "app.services.metadata_service.fetch_url_metadata",
        new=AsyncMock(return_value=FAKE_FETCH_RESULT),
    ):
        response = await client.post("/metadata", json={"url": "https://example.com"})

    assert response.status_code == 201
    body = response.json()
    assert body["url"].rstrip("/") == "https://example.com"
    assert body["status"] == FetchStatus.complete
    assert body["headers"] == FAKE_FETCH_RESULT["headers"]
    assert body["cookies"] == FAKE_FETCH_RESULT["cookies"]
    assert body["page_source"] == FAKE_FETCH_RESULT["page_source"]


async def test_post_metadata_invalid_url(client):
    response = await client.post("/metadata", json={"url": "not-a-url"})
    assert response.status_code == 422


async def test_post_metadata_fetch_error(client):
    from app.services.fetcher import FetchError

    with patch(
        "app.services.metadata_service.fetch_url_metadata",
        new=AsyncMock(side_effect=FetchError("Connection refused")),
    ):
        response = await client.post("/metadata", json={"url": "https://unreachable.example"})

    assert response.status_code == 422
    assert "Connection refused" in response.json()["detail"]


async def test_get_metadata_cache_hit(client, mock_db):
    await mock_db["metadata"].insert_one({**FAKE_RECORD, "url": "https://example.com"})

    response = await client.get("/metadata", params={"url": "https://example.com"})

    assert response.status_code == 200
    body = response.json()
    assert body["url"] == "https://example.com"
    assert body["status"] == FetchStatus.complete


async def test_get_metadata_cache_miss_returns_202(client):
    with patch("app.api.routes.metadata_service.schedule_background_collect") as mock_schedule:
        response = await client.get("/metadata", params={"url": "https://new-url.example.com"})

    assert response.status_code == 202
    body = response.json()
    assert "scheduled" in body["message"].lower()
    assert body["url"] == "https://new-url.example.com"
    mock_schedule.assert_called_once()


async def test_get_metadata_pending_record_no_duplicate_task(client, mock_db):
    await mock_db["metadata"].insert_one(
        {
            "url": "https://pending.example.com",
            "status": FetchStatus.pending,
            "headers": {},
            "cookies": {},
            "page_source": "",
            "fetched_at": None,
            "error": None,
        }
    )

    with patch("app.api.routes.metadata_service.schedule_background_collect") as mock_schedule:
        response = await client.get("/metadata", params={"url": "https://pending.example.com"})

    assert response.status_code == 200
    mock_schedule.assert_not_called()


async def test_get_metadata_missing_url_param(client):
    response = await client.get("/metadata")
    assert response.status_code == 422
