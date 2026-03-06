from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    file_id: UUID = Field(alias="id")
    parse_status: str
    file_hash: str
    original_filename: str
    uploaded_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
