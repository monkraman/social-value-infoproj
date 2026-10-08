import io
import uuid
import re
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
try:
    import pymupdf
except Exception:
    pymupdf = None

import docx
import openpyxl
import pypdf

from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embedding_service


class DocumentService:
    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
        """Extracts text per page from PDF using PyMuPDF or pypdf."""
        pages = []
        if pymupdf is not None:
            try:
                with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        text = page.get_text("text").strip()
                        if text:
                            pages.append({
                                "page_number": page_num + 1,
                                "text": text
                            })
                if pages:
                    return pages
            except Exception:
                pass

        # Fallback to pure-Python pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        for page_num, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append({
                    "page_number": page_num + 1,
                    "text": text
                })
        return pages

    @staticmethod
    def extract_text_from_docx(file_bytes: bytes) -> List[Dict[str, Any]]:
        """Extracts paragraphs and tables from DOCX using python-docx."""
        sections = []
        doc = docx.Document(io.BytesIO(file_bytes))

        # Paragraphs
        current_section = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                current_section.append(text)

        if current_section:
            sections.append({
                "type": "paragraphs",
                "text": "\n\n".join(current_section)
            })

        # Tables
        for table_idx, table in enumerate(doc.tables):
            table_lines = []
            for row in table.rows:
                row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                if any(row_cells):
                    table_lines.append(" | ".join(row_cells))
            if table_lines:
                sections.append({
                    "type": "table",
                    "table_index": table_idx + 1,
                    "text": f"Table {table_idx + 1}:\n" + "\n".join(table_lines)
                })

        return sections

    @staticmethod
    def extract_text_from_xlsx(file_bytes: bytes) -> List[Dict[str, Any]]:
        """Extracts sheets and structured table rows from XLSX using openpyxl."""
        sections = []
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)

        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            sheet_lines = []
            for row in sheet.iter_rows(values_only=True):
                # Filter out completely empty rows
                non_empty = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                if non_empty:
                    sheet_lines.append(" | ".join(non_empty))
            if sheet_lines:
                sections.append({
                    "sheet_name": sheet_name,
                    "text": f"Sheet [{sheet_name}]:\n" + "\n".join(sheet_lines)
                })

        return sections

    @staticmethod
    def normalize_text(text: str) -> str:
        """Cleans excess whitespace and non-standard characters."""
        # Replace non-breaking spaces and redundant whitespaces
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        return text.strip()

    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
        """
        Splits text into chunks respecting paragraph and sentence boundaries.
        """
        text = self.normalize_text(text)
        if not text:
            return []

        if len(text) <= chunk_size:
            return [text]

        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If single paragraph is longer than chunk_size, split by sentences/lines
            if len(para) > chunk_size:
                lines = para.split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if len(current_chunk) + len(line) + 1 <= chunk_size:
                        current_chunk = f"{current_chunk}\n{line}".strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = line
            else:
                if len(current_chunk) + len(para) + 2 <= chunk_size:
                    current_chunk = f"{current_chunk}\n\n{para}".strip()
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def process_and_chunk_document(self, file_bytes: bytes, filename: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Detects file type, extracts sections, and splits into structured chunks with metadata.
        """
        ext = filename.lower().split(".")[-1]
        raw_chunks: List[Dict[str, Any]] = []

        if ext == "pdf":
            pages = self.extract_text_from_pdf(file_bytes)
            for page in pages:
                sub_chunks = self.chunk_text(page["text"])
                for sub in sub_chunks:
                    raw_chunks.append({
                        "content": sub,
                        "metadata": {"page": page["page_number"], "source_type": "pdf"}
                    })
        elif ext in ["docx", "doc"]:
            sections = self.extract_text_from_docx(file_bytes)
            for sec in sections:
                sub_chunks = self.chunk_text(sec["text"])
                for sub in sub_chunks:
                    raw_chunks.append({
                        "content": sub,
                        "metadata": {"section_type": sec.get("type", "paragraph"), "source_type": "docx"}
                    })
        elif ext in ["xlsx", "xls"]:
            sheets = self.extract_text_from_xlsx(file_bytes)
            for sheet in sheets:
                sub_chunks = self.chunk_text(sheet["text"])
                for sub in sub_chunks:
                    raw_chunks.append({
                        "content": sub,
                        "metadata": {"sheet": sheet["sheet_name"], "source_type": "xlsx"}
                    })
        elif ext in ["txt", "md"]:
            text = file_bytes.decode("utf-8", errors="ignore")
            sub_chunks = self.chunk_text(text)
            for sub in sub_chunks:
                raw_chunks.append({
                    "content": sub,
                    "metadata": {"source_type": ext}
                })
        else:
            raise ValueError(f"Unsupported document format: .{ext}. Supported formats: PDF, DOCX, XLSX, TXT, MD.")

        return ext, raw_chunks

    def ingest_document(
        self,
        db: Session,
        file_bytes: bytes,
        filename: str,
        custom_metadata: Dict[str, Any] = None
    ) -> Document:
        """
        Full ingestion pipeline:
        Extract -> Chunk -> Embed -> PostgreSQL pgvector storage.
        """
        doc_type, raw_chunks = self.process_and_chunk_document(file_bytes, filename)

        if not raw_chunks:
            raise ValueError(f"Could not extract any readable text from {filename}")

        # Create Document record
        doc_id = uuid.uuid4()
        meta = custom_metadata or {}
        meta.update({
            "filename": filename,
            "size_bytes": len(file_bytes),
            "chunks_count": len(raw_chunks)
        })

        db_doc = Document(
            id=doc_id,
            filename=filename,
            document_type=doc_type,
            doc_metadata=meta
        )
        db.add(db_doc)
        db.flush()

        # Generate embeddings in batch
        texts_to_embed = [chunk["content"] for chunk in raw_chunks]
        embeddings = embedding_service.get_embeddings(texts_to_embed)

        # Create DocumentChunk records
        for idx, (chunk_data, embedding) in enumerate(zip(raw_chunks, embeddings)):
            chunk_record = DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_id,
                chunk_index=idx,
                content=chunk_data["content"],
                chunk_metadata=chunk_data["metadata"],
                embedding=embedding
            )
            db.add(chunk_record)

        db.commit()
        db.refresh(db_doc)
        return db_doc


document_service = DocumentService()
