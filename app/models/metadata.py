from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, HttpUrl


class FetchStatus(str, Enum):
    pending = "pending"
    complete = "complete"
    error = "error"


class MetadataRecord(BaseModel):
    url: str
    status: FetchStatus
    headers: Dict[str, Any] = {}
    cookies: Dict[str, Any] = {}
    page_source: str = ""
    fetched_at: Optional[datetime] = None
    error: Optional[str] = None


class CreateMetadataRequest(BaseModel):
    url: HttpUrl


class AcceptedResponse(BaseModel):
    message: str
    url: str
