from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.database import get_db
from app.main import app
from app.models.metadata import FetchStatus


@pytest.fixture()
def mock_db():
    return AsyncMongoMockClient()["test_db"]


FAKE_FETCH_RESULT = {
    "headers": {"content-type": "text/html"},
    "cookies": {"session": "abc123"},
    "page_source": "<html><body>Hello</body></html>",
}

FAKE_RECORD = {
    "url": "https://example.com",
    "status": FetchStatus.complete,
    "headers": FAKE_FETCH_RESULT["headers"],
    "cookies": FAKE_FETCH_RESULT["cookies"],
    "page_source": FAKE_FETCH_RESULT["page_source"],
    "fetched_at": datetime.now(tz=timezone.utc),
    "error": None,
}


@pytest_asyncio.fixture()
async def client(mock_db) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
