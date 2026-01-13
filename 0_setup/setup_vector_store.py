#!/usr/bin/env python3
"""
Vector Store Setup Script
Initializes ChromaDB vector store with collections for policy documents
and customer documents.
"""

import os
import sys
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("[ERROR] ChromaDB not installed. Run: pip install chromadb")
    sys.exit(1)

# Get project root from environment or current working directory
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", os.getcwd()))


def get_chroma_path() -> Path:
    """Get the ChromaDB persistence directory."""
    chroma_path = os.environ.get("CHROMA_PERSIST_DIRECTORY")
    if chroma_path:
        chroma_dir = Path(chroma_path)
    else:
        chroma_dir = PROJECT_ROOT / "data" / "chroma_db"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chroma_dir


def create_client(persist_directory: Path) -> chromadb.PersistentClient:
    """Create a ChromaDB persistent client."""
    print(f"\n[INFO] Initializing ChromaDB at: {persist_directory}")

    client = chromadb.PersistentClient(
        path=str(persist_directory),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )

    return client


def create_collections(client: chromadb.PersistentClient):
    """Create the required collections."""
    print("\n" + "="*60)
    print("Creating ChromaDB Collections")
    print("="*60 + "\n")

    # Collection for credit policy documents
    policy_collection = client.get_or_create_collection(
        name="policy_documents",
        metadata={
            "description": "Credit policy documents for RAG",
            "hnsw:space": "cosine"
        }
    )
    print(f"  [OK] policy_documents collection created (count: {policy_collection.count()})")

    # Collection for customer documents
    customer_collection = client.get_or_create_collection(
        name="customer_documents",
        metadata={
            "description": "Customer-specific documents (financial statements, etc.)",
            "hnsw:space": "cosine"
        }
    )
    print(f"  [OK] customer_documents collection created (count: {customer_collection.count()})")

    # Collection for historical analysis
    analysis_collection = client.get_or_create_collection(
        name="analysis_history",
        metadata={
            "description": "Historical analysis and decision rationales",
            "hnsw:space": "cosine"
        }
    )
    print(f"  [OK] analysis_history collection created (count: {analysis_collection.count()})")

    return {
        "policy_documents": policy_collection,
        "customer_documents": customer_collection,
        "analysis_history": analysis_collection
    }


def verify_collections(client: chromadb.PersistentClient):
    """Verify all collections exist."""
    print("\n" + "="*60)
    print("Verifying Collections")
    print("="*60 + "\n")

    collections = client.list_collections()
    print(f"Total collections: {len(collections)}")

    for collection in collections:
        count = collection.count()
        print(f"  - {collection.name}: {count} documents")


def test_embedding(client: chromadb.PersistentClient):
    """Test that embedding works with a sample document."""
    print("\n" + "="*60)
    print("Testing Embedding Functionality")
    print("="*60 + "\n")

    test_collection = client.get_or_create_collection(name="test_collection")

    # Add a test document
    try:
        test_collection.add(
            documents=["This is a test document for the credit risk platform."],
            ids=["test_doc_1"],
            metadatas=[{"source": "test"}]
        )
        print("  [OK] Successfully added test document")

        # Query the test document
        results = test_collection.query(
            query_texts=["credit risk"],
            n_results=1
        )
        print(f"  [OK] Query returned {len(results['documents'][0])} results")

        # Clean up test collection
        client.delete_collection(name="test_collection")
        print("  [OK] Test collection cleaned up")

        return True

    except Exception as e:
        print(f"  [FAIL] Embedding test failed: {e}")
        return False


def main():
    """Main function to setup the vector store."""
    print("\n" + "="*60)
    print("Credit Risk Platform - Vector Store Setup")
    print("="*60)

    # Get persistence directory
    chroma_path = get_chroma_path()

    # Create client
    client = create_client(chroma_path)

    # Create collections
    collections = create_collections(client)

    # Verify collections
    verify_collections(client)

    # Test embedding
    embedding_ok = test_embedding(client)

    # Summary
    print("\n" + "="*60)
    print("Vector Store Setup Summary")
    print("="*60)

    if embedding_ok:
        print("\n[SUCCESS] Vector store setup completed successfully!")
        print(f"\nChromaDB directory: {chroma_path}")
        print("\nCollections created:")
        for name in collections:
            print(f"  - {name}")
        print("\nNext steps:")
        print("  1. Run 0_setup/load_policy_docs.py to load policy documents")
        print("  2. Run 1_data/generate_synthetic.py to generate sample data")
    else:
        print("\n[WARNING] Vector store created but embedding test failed.")
        print("Check that you have an embedding model available.")

    return 0 if embedding_ok else 1


if __name__ == "__main__":
    main()
