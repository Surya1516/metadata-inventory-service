import logging
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.metadata import AcceptedResponse, CreateMetadataRequest, MetadataRecord
from app.repositories import metadata_repo
from app.services import metadata_service
from app.services.fetcher import FetchError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.post("", response_model=MetadataRecord, status_code=status.HTTP_201_CREATED)
async def create_metadata(
    body: CreateMetadataRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> MetadataRecord:
    url = str(body.url)
    try:
        return await metadata_service.collect_and_store(db, url)
    except FetchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("", responses={200: {"model": MetadataRecord}, 202: {"model": AcceptedResponse}})
async def get_metadata(
    url: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Union[MetadataRecord, AcceptedResponse]:
    record = await metadata_repo.find_by_url(db, url)
    if record is not None:
        return record

    inserted = await metadata_repo.insert_pending(db, url)
    if inserted:
        metadata_service.schedule_background_collect(db, url)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=AcceptedResponse(
            message="Metadata not yet available. Collection has been scheduled.",
            url=url,
        ).model_dump(),
    )
