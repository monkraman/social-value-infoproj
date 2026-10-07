from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., description="Query to search within knowledge base chunks", examples=["digital inclusion initiatives for Birmingham"])
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to retrieve")
    document_id: Optional[str] = Field(default=None, description="Optional document ID to restrict search")


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    content: str
    similarity: float
    chunk_index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]
