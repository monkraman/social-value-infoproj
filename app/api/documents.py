import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.schemas.document import DocumentResponse, DocumentIngestResponse
from app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/ingest", response_model=DocumentIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    file: UploadFile = File(..., description="Document file to ingest (PDF, DOCX, XLSX, TXT)"),
    db: Session = Depends(get_db)
):
    """
    Milestone 5: Document Ingestion Pipeline.
    Extracts text/tables, normalizes, chunks, generates pgvector embeddings,
    and indexes the document in PostgreSQL.
    """
    allowed_extensions = ["pdf", "docx", "doc", "xlsx", "xls", "txt", "md"]
    filename = file.filename or "unknown"
    ext = filename.lower().split(".")[-1]

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty"
            )

        doc = document_service.ingest_document(
            db=db,
            file_bytes=file_bytes,
            filename=filename,
            custom_metadata={"content_type": file.content_type}
        )

        chunks_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()

        return DocumentIngestResponse(
            document_id=str(doc.id),
            filename=doc.filename,
            document_type=doc.document_type,
            chunks_created=chunks_count,
            message="Document successfully ingested and indexed with pgvector"
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ingestion failed: {str(e)}")


@router.get("", response_model=List[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    """Lists all ingested documents with chunk counts."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    results = []
    for d in docs:
        count = db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).count()
        results.append(
            DocumentResponse(
                id=d.id,
                filename=d.filename,
                document_type=d.document_type,
                metadata=d.doc_metadata or {},
                created_at=d.created_at,
                chunks_count=count
            )
        )
    return results


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Deletes an ingested document and its associated chunks."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format")

    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    db.delete(doc)
    db.commit()
    return {"message": f"Document '{doc.filename}' and its chunks deleted successfully"}
