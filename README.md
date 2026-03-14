# HTTP Metadata Inventory Service

A FastAPI + MongoDB service that collects and stores HTTP metadata (headers, cookies, page source) for given URLs, with asynchronous background fetching on cache misses.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Framework | FastAPI |
| Database | MongoDB (via Motor async driver) |
| Orchestration | Docker Compose |
| Testing | Pytest + mongomock-motor |

---

## Running with Docker Compose

```bash
docker-compose up
```

This starts both the API (`localhost:8000`) and MongoDB (`localhost:27017`).
The API waits for MongoDB to pass its healthcheck before starting.

---

## API Reference

Interactive docs are available at **http://localhost:8000/docs** once the service is running.

### `POST /metadata`

Synchronously fetch and store metadata for a URL.

```bash
curl -X POST http://localhost:8000/metadata \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**Response 201:**
```json
{
  "url": "https://example.com",
  "status": "complete",
  "headers": { "content-type": "text/html", ... },
  "cookies": {},
  "page_source": "<!doctype html>...",
  "fetched_at": "2024-01-01T00:00:00Z",
  "error": null
}
```

---

### `GET /metadata?url=<url>`

Retrieve cached metadata for a URL.

```bash
curl "http://localhost:8000/metadata?url=https://example.com"
```

**Response 200** — record found:
```json
{
  "url": "https://example.com",
  "status": "complete",
  ...
}
```

**Response 202** — not yet cached, background collection scheduled:
```json
{
  "message": "Metadata not yet available. Collection has been scheduled.",
  "url": "https://example.com"
}
```

---

## Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and edit environment
cp .env.example .env

# Start a local MongoDB instance, then run:
uvicorn app.main:app --reload
```

---

## Running Tests

```bash
pip install -r requirements.txt
pytest
```

Tests use `mongomock-motor` for an in-memory MongoDB — no running database required.

---

## Architecture

```
app/
├── config.py          # pydantic-settings (env vars)
├── database.py        # MongoDB client + retry-on-startup
├── models/
│   └── metadata.py    # Pydantic models & enums
├── repositories/
│   └── metadata_repo.py  # All DB operations
├── services/
│   ├── fetcher.py        # httpx fetch logic
│   └── metadata_service.py  # Business logic + asyncio background tasks
└── api/
    └── routes.py         # FastAPI route handlers
```

### Background Collection

When a `GET /metadata` request results in a cache miss, the service:

1. Inserts a `pending` placeholder in MongoDB (prevents duplicate tasks)
2. Schedules a background coroutine via `asyncio.create_task()` (no self-HTTP calls)
3. Returns **202 Accepted** immediately
4. The background task fetches the URL, updates the record to `complete` (or `error`)

Subsequent `GET` requests for the same URL will find the `complete` record and return it with **200**.
