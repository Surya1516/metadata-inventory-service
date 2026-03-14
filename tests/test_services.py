from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.metadata import FetchStatus
from app.services.fetcher import FetchError, fetch_url_metadata
from app.services.metadata_service import collect_and_store, schedule_background_collect
from tests.conftest import FAKE_FETCH_RESULT

pytestmark = pytest.mark.asyncio


def _make_mock_client(return_value=None, side_effect=None):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=return_value, side_effect=side_effect)
    return mock_client


async def test_fetch_url_metadata_success():
    mock_response = MagicMock()
    mock_response.headers = {"content-type": "text/html"}
    mock_response.cookies = {"session": "abc"}
    mock_response.text = "<html></html>"
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.fetcher.httpx.AsyncClient", return_value=_make_mock_client(mock_response)):
        result = await fetch_url_metadata("https://example.com")

    assert result["headers"] == {"content-type": "text/html"}
    assert result["cookies"] == {"session": "abc"}
    assert result["page_source"] == "<html></html>"


async def test_fetch_url_metadata_timeout():
    with patch("app.services.fetcher.httpx.AsyncClient",
               return_value=_make_mock_client(side_effect=httpx.TimeoutException("timed out"))):
        with pytest.raises(FetchError, match="timed out"):
            await fetch_url_metadata("https://slow.example.com")


async def test_fetch_url_metadata_http_error():
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(404, request=request)

    with patch("app.services.fetcher.httpx.AsyncClient",
               return_value=_make_mock_client(
                   side_effect=httpx.HTTPStatusError("Not Found", request=request, response=response)
               )):
        with pytest.raises(FetchError, match="404"):
            await fetch_url_metadata("https://example.com/missing")


async def test_fetch_url_metadata_request_error():
    request = httpx.Request("GET", "https://example.com")

    with patch("app.services.fetcher.httpx.AsyncClient",
               return_value=_make_mock_client(
                   side_effect=httpx.ConnectError("Connection refused", request=request)
               )):
        with pytest.raises(FetchError, match="Connection refused"):
            await fetch_url_metadata("https://unreachable.example.com")


async def test_collect_and_store_success(mock_db):
    with patch(
        "app.services.metadata_service.fetch_url_metadata",
        new=AsyncMock(return_value=FAKE_FETCH_RESULT),
    ):
        record = await collect_and_store(mock_db, "https://example.com")

    assert record.url == "https://example.com"
    assert record.status == FetchStatus.complete
    assert record.headers == FAKE_FETCH_RESULT["headers"]
    assert record.page_source == FAKE_FETCH_RESULT["page_source"]
    assert record.fetched_at is not None


async def test_collect_and_store_propagates_fetch_error(mock_db):
    with patch(
        "app.services.metadata_service.fetch_url_metadata",
        new=AsyncMock(side_effect=FetchError("timeout")),
    ):
        with pytest.raises(FetchError):
            await collect_and_store(mock_db, "https://example.com")


async def test_schedule_background_collect_creates_task(mock_db):
    with patch("app.services.metadata_service.asyncio.create_task") as mock_create_task:
        def _close(coro):
            coro.close()
            return mock_create_task.return_value

        mock_create_task.side_effect = _close
        schedule_background_collect(mock_db, "https://example.com")

    mock_create_task.assert_called_once()
