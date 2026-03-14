import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import close_db, init_db

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="HTTP Metadata Inventory Service",
    description="Collect and query HTTP metadata (headers, cookies, page source) for URLs.",
    version="1.0.0",
    lifespan=lifespan,
)

from app.api.routes import router 

app.include_router(router)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}
