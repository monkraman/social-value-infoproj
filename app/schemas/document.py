import uuid
from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class DocumentBase(BaseModel):
    filename: str
    document_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentResponse(DocumentBase):
    id: uuid.UUID
    created_at: datetime
    chunks_count: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class DocumentIngestResponse(BaseModel):
    document_id: str
    filename: str
    document_type: str
    chunks_created: int
    message: str = "Document successfully ingested and indexed"


class DocumentChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
