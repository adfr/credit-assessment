#!/usr/bin/env python3
"""
Document Indexer for RAG

Indexes company 10-K filings into ChromaDB vector store
for semantic search and retrieval.

Usage:
    python index_documents.py
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "5_backend"))

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    print("[ERROR] chromadb not installed. Run: pip install chromadb")
    exit(1)


def get_db_path() -> Path:
    """Get database path."""
    return Path(__file__).parent.parent / "data" / "credit_risk.db"


def get_chroma_path() -> Path:
    """Get ChromaDB path."""
    return Path(__file__).parent.parent / "data" / "chroma_company_docs"


def get_db_connection():
    """Get database connection."""
    return sqlite3.connect(str(get_db_path()))


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """
    Split text into overlapping chunks for better retrieval.

    Args:
        text: Full document text
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at paragraph or sentence
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind('\n\n', start, end)
            if para_break > start + chunk_size // 2:
                end = para_break + 2
            else:
                # Look for sentence break
                sent_break = text.rfind('. ', start, end)
                if sent_break > start + chunk_size // 2:
                    end = sent_break + 2

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


def index_documents():
    """Index all company documents into ChromaDB."""
    print("\n" + "=" * 60)
    print("Document Indexer for RAG")
    print("=" * 60)

    # Initialize ChromaDB
    chroma_path = get_chroma_path()
    chroma_path.mkdir(parents=True, exist_ok=True)

    print(f"\n[INFO] ChromaDB path: {chroma_path}")

    client = chromadb.PersistentClient(path=str(chroma_path))

    # Use default embedding function (or OpenAI if available)
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    # Delete and recreate collection to clear existing documents
    try:
        existing_collection = client.get_collection("company_filings")
        existing_count = existing_collection.count()
        if existing_count > 0:
            print(f"[INFO] Clearing {existing_count} existing documents...")
            client.delete_collection("company_filings")
    except Exception:
        pass  # Collection doesn't exist yet

    # Create collection
    collection = client.get_or_create_collection(
        name="company_filings",
        embedding_function=embedding_fn,
        metadata={"description": "10-K filings and company documents"}
    )

    # Load documents from database
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ticker, company_name, doc_type, fiscal_year, content
        FROM company_documents
        WHERE content IS NOT NULL
    """)

    docs = cursor.fetchall()
    print(f"\n[INFO] Found {len(docs)} documents to index")

    total_chunks = 0

    for ticker, company_name, doc_type, year, content in docs:
        print(f"\n  Indexing {ticker} ({company_name}) - {doc_type} {year}...")

        # Chunk the document
        chunks = chunk_text(content, chunk_size=1500, overlap=200)
        print(f"    - Split into {len(chunks)} chunks")

        # Prepare data for ChromaDB
        ids = [f"{ticker}_{year}_{doc_type}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "ticker": ticker,
                "company_name": company_name,
                "doc_type": doc_type,
                "fiscal_year": year,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source": "company_filing"
            }
            for i in range(len(chunks))
        ]

        # Add to collection
        collection.add(
            ids=ids,
            documents=chunks,
            metadatas=metadatas
        )

        total_chunks += len(chunks)

        # Update database
        cursor.execute("""
            UPDATE company_documents
            SET indexed_at = ?
            WHERE ticker = ? AND doc_type = ? AND fiscal_year = ?
        """, (datetime.now().isoformat(), ticker, doc_type, year))

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print(f"[DONE] Indexed {len(docs)} documents ({total_chunks} chunks)")
    print("=" * 60)

    # Verify
    final_count = collection.count()
    print(f"\n[INFO] Total documents in collection: {final_count}")

    return 0


def test_search(query: str = "risk factors"):
    """Test the search functionality."""
    print(f"\n[TEST] Searching for: '{query}'")

    chroma_path = get_chroma_path()
    client = chromadb.PersistentClient(path=str(chroma_path))

    collection = client.get_collection(
        name="company_filings",
        embedding_function=embedding_functions.DefaultEmbeddingFunction()
    )

    results = collection.query(
        query_texts=[query],
        n_results=3
    )

    print("\nTop results:")
    for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
        print(f"\n{i+1}. {metadata['company_name']} ({metadata['ticker']}) - {metadata['doc_type']} {metadata['fiscal_year']}")
        print(f"   Chunk {metadata['chunk_index']+1}/{metadata['total_chunks']}")
        print(f"   Preview: {doc[:200]}...")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Index company documents for RAG")
    parser.add_argument("--test", type=str, help="Test search with query")
    args = parser.parse_args()

    if args.test:
        test_search(args.test)
    else:
        exit(index_documents())
