"""
Document Management API

Endpoints for document ingestion and RAG indexing.
Used by NiFi flows to trigger document processing.
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "1_data"))

router = APIRouter(prefix="/api/documents", tags=["documents"])


# ============================================================================
# Models
# ============================================================================

class DocumentIngest(BaseModel):
    """Request model for ingesting a document from NiFi."""
    ticker: str
    company_name: str
    doc_type: str = "10-K"
    fiscal_year: int
    content: str
    source: str = "nifi"
    filing_date: Optional[str] = None
    accession: Optional[str] = None


class IndexRequest(BaseModel):
    """Request model for triggering document indexing."""
    ticker: Optional[str] = None
    doc_type: Optional[str] = None
    force_reindex: bool = False


class DocumentResponse(BaseModel):
    """Response model for document operations."""
    success: bool
    message: str
    document_id: Optional[str] = None
    chunks_indexed: Optional[int] = None


# ============================================================================
# Helper Functions
# ============================================================================

def get_db_path() -> Path:
    """Get database path."""
    return Path(__file__).parent.parent.parent / "data" / "credit_risk.db"


def get_chroma_path() -> Path:
    """Get ChromaDB path."""
    return Path(__file__).parent.parent.parent / "data" / "chroma_company_docs"


def get_docs_path() -> Path:
    """Get company docs directory."""
    return Path(__file__).parent.parent.parent / "data" / "company_docs"


def get_db_connection():
    """Get database connection."""
    return sqlite3.connect(str(get_db_path()))


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list:
    """Split text into overlapping chunks for better retrieval."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            para_break = text.rfind('\n\n', start, end)
            if para_break > start + chunk_size // 2:
                end = para_break + 2
            else:
                sent_break = text.rfind('. ', start, end)
                if sent_break > start + chunk_size // 2:
                    end = sent_break + 2

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


def index_single_document(ticker: str, company_name: str, doc_type: str,
                          year: int, content: str) -> int:
    """Index a single document into ChromaDB. Returns number of chunks indexed."""
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        raise HTTPException(status_code=500, detail="ChromaDB not installed")

    chroma_path = get_chroma_path()
    chroma_path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(chroma_path))
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    collection = client.get_or_create_collection(
        name="company_filings",
        embedding_function=embedding_fn,
        metadata={"description": "10-K filings and company documents"}
    )

    # Delete existing chunks for this document
    existing_ids = collection.get(
        where={"ticker": ticker, "doc_type": doc_type, "fiscal_year": year}
    )
    if existing_ids and existing_ids.get("ids"):
        collection.delete(ids=existing_ids["ids"])

    # Chunk and index
    chunks = chunk_text(content, chunk_size=1500, overlap=200)

    ids = [f"{ticker}_{year}_{doc_type}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "ticker": ticker,
            "company_name": company_name,
            "doc_type": doc_type,
            "fiscal_year": year,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "source": "company_filing",
            "indexed_at": datetime.now().isoformat()
        }
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas
    )

    return len(chunks)


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/ingest", response_model=DocumentResponse)
async def ingest_document(doc: DocumentIngest, background_tasks: BackgroundTasks):
    """
    Ingest a document from NiFi and store it.

    This endpoint receives documents pushed from NiFi flows,
    stores them in the database and file system, then triggers indexing.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Store in database
        cursor.execute("""
            INSERT OR REPLACE INTO company_documents
            (ticker, company_name, doc_type, fiscal_year, content, summary, source, downloaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc.ticker,
            doc.company_name,
            doc.doc_type,
            doc.fiscal_year,
            doc.content,
            f"{doc.doc_type} Annual Report for fiscal year {doc.fiscal_year}",
            doc.source,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        # Save to file
        docs_path = get_docs_path()
        docs_path.mkdir(parents=True, exist_ok=True)
        file_path = docs_path / f"{doc.ticker}_{doc.fiscal_year}_{doc.doc_type}.txt"
        file_path.write_text(doc.content)

        # Index in background
        background_tasks.add_task(
            index_single_document,
            doc.ticker,
            doc.company_name,
            doc.doc_type,
            doc.fiscal_year,
            doc.content
        )

        return DocumentResponse(
            success=True,
            message=f"Document ingested for {doc.ticker} {doc.doc_type} {doc.fiscal_year}",
            document_id=f"{doc.ticker}_{doc.fiscal_year}_{doc.doc_type}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index", response_model=DocumentResponse)
async def trigger_indexing(request: IndexRequest):
    """
    Trigger RAG indexing for documents.

    Can index all documents or filter by ticker/doc_type.
    Called by NiFi after document ingestion.
    """
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        raise HTTPException(status_code=500, detail="ChromaDB not installed")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Build query based on filters
    query = """
        SELECT ticker, company_name, doc_type, fiscal_year, content
        FROM company_documents
        WHERE content IS NOT NULL
    """
    params = []

    if request.ticker:
        query += " AND ticker = ?"
        params.append(request.ticker)

    if request.doc_type:
        query += " AND doc_type = ?"
        params.append(request.doc_type)

    if not request.force_reindex:
        query += " AND indexed_at IS NULL"

    cursor.execute(query, params)
    docs = cursor.fetchall()

    if not docs:
        return DocumentResponse(
            success=True,
            message="No documents to index",
            chunks_indexed=0
        )

    total_chunks = 0

    for ticker, company_name, doc_type, year, content in docs:
        chunks = index_single_document(ticker, company_name, doc_type, year, content)
        total_chunks += chunks

        # Update indexed_at
        cursor.execute("""
            UPDATE company_documents
            SET indexed_at = ?
            WHERE ticker = ? AND doc_type = ? AND fiscal_year = ?
        """, (datetime.now().isoformat(), ticker, doc_type, year))

    conn.commit()
    conn.close()

    return DocumentResponse(
        success=True,
        message=f"Indexed {len(docs)} documents",
        chunks_indexed=total_chunks
    )


@router.get("/")
async def list_documents(
    ticker: Optional[str] = None,
    doc_type: Optional[str] = None,
    indexed_only: bool = False
):
    """List all documents in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT ticker, company_name, doc_type, fiscal_year,
               source, downloaded_at, indexed_at,
               LENGTH(content) as content_length
        FROM company_documents
        WHERE 1=1
    """
    params = []

    if ticker:
        query += " AND ticker = ?"
        params.append(ticker)

    if doc_type:
        query += " AND doc_type = ?"
        params.append(doc_type)

    if indexed_only:
        query += " AND indexed_at IS NOT NULL"

    query += " ORDER BY downloaded_at DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    documents = []
    for row in rows:
        documents.append({
            "ticker": row[0],
            "company_name": row[1],
            "doc_type": row[2],
            "fiscal_year": row[3],
            "source": row[4],
            "downloaded_at": row[5],
            "indexed_at": row[6],
            "content_length": row[7],
        })

    return {
        "count": len(documents),
        "documents": documents
    }


@router.get("/search")
async def search_documents(
    query: str,
    n_results: int = 5,
    ticker: Optional[str] = None
):
    """
    Search documents using semantic similarity.

    Returns relevant chunks from indexed documents.
    """
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        raise HTTPException(status_code=500, detail="ChromaDB not installed")

    chroma_path = get_chroma_path()
    if not chroma_path.exists():
        raise HTTPException(status_code=404, detail="No documents indexed yet")

    client = chromadb.PersistentClient(path=str(chroma_path))
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    try:
        collection = client.get_collection(
            name="company_filings",
            embedding_function=embedding_fn
        )
    except Exception:
        raise HTTPException(status_code=404, detail="No documents indexed yet")

    # Build where filter
    where_filter = None
    if ticker:
        where_filter = {"ticker": ticker}

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter
    )

    search_results = []
    if results and results.get("documents"):
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results.get('distances', [[]])[0] or [None] * len(results['documents'][0])
        )):
            search_results.append({
                "rank": i + 1,
                "ticker": metadata.get("ticker"),
                "company_name": metadata.get("company_name"),
                "doc_type": metadata.get("doc_type"),
                "fiscal_year": metadata.get("fiscal_year"),
                "chunk_index": metadata.get("chunk_index"),
                "total_chunks": metadata.get("total_chunks"),
                "content": doc,
                "similarity_score": 1 - distance if distance else None
            })

    return {
        "query": query,
        "count": len(search_results),
        "results": search_results
    }


@router.get("/stats")
async def get_document_stats():
    """Get statistics about indexed documents."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Count by source
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM company_documents
        GROUP BY source
    """)
    by_source = {row[0]: row[1] for row in cursor.fetchall()}

    # Count by doc_type
    cursor.execute("""
        SELECT doc_type, COUNT(*) as count
        FROM company_documents
        GROUP BY doc_type
    """)
    by_type = {row[0]: row[1] for row in cursor.fetchall()}

    # Count indexed vs not indexed
    cursor.execute("""
        SELECT
            SUM(CASE WHEN indexed_at IS NOT NULL THEN 1 ELSE 0 END) as indexed,
            SUM(CASE WHEN indexed_at IS NULL THEN 1 ELSE 0 END) as not_indexed
        FROM company_documents
    """)
    row = cursor.fetchone()
    indexed_count = row[0] or 0
    not_indexed_count = row[1] or 0

    conn.close()

    # Get ChromaDB stats
    chunks_count = 0
    try:
        import chromadb
        from chromadb.utils import embedding_functions

        chroma_path = get_chroma_path()
        if chroma_path.exists():
            client = chromadb.PersistentClient(path=str(chroma_path))
            collection = client.get_collection(
                name="company_filings",
                embedding_function=embedding_functions.DefaultEmbeddingFunction()
            )
            chunks_count = collection.count()
    except Exception:
        pass

    return {
        "total_documents": indexed_count + not_indexed_count,
        "indexed_documents": indexed_count,
        "pending_indexing": not_indexed_count,
        "total_chunks": chunks_count,
        "by_source": by_source,
        "by_type": by_type
    }
