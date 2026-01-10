"""
RAG tools for policy queries and context retrieval
"""

from typing import Any, Optional
from pathlib import Path


def get_chroma_client(collection_type: str = "policies"):
    """Get ChromaDB client for specified collection type."""
    try:
        import chromadb
        if collection_type == "company_docs":
            persist_dir = Path(__file__).parent.parent.parent.parent / "data" / "chroma_company_docs"
        else:
            persist_dir = Path(__file__).parent.parent.parent.parent / "data" / "chroma_db"
        client = chromadb.PersistentClient(path=str(persist_dir))
        return client
    except Exception as e:
        return None


def query_company_documents(
    query: str,
    ticker: Optional[str] = None,
    n_results: int = 5
) -> dict[str, Any]:
    """
    Query company 10-K filings and financial documents.

    Args:
        query: Search query (e.g., "risk factors", "revenue growth")
        ticker: Optional ticker to filter by specific company
        n_results: Number of results to return

    Returns:
        dict with relevant document chunks and metadata
    """
    client = get_chroma_client("company_docs")

    if client is None:
        return {
            "documents": [],
            "error": "Company document vector store not available. Run: python 1_data/index_documents.py",
        }

    try:
        from chromadb.utils import embedding_functions
        embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        collection = client.get_collection(
            name="company_filings",
            embedding_function=embedding_fn
        )

        # Build where filter for ticker
        where_filter = None
        if ticker:
            where_filter = {"ticker": ticker.upper()}

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        documents = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else None
                documents.append({
                    "content": doc[:1000] + "..." if len(doc) > 1000 else doc,
                    "ticker": metadata.get("ticker", "Unknown"),
                    "company_name": metadata.get("company_name", "Unknown"),
                    "doc_type": metadata.get("doc_type", "10-K"),
                    "fiscal_year": metadata.get("fiscal_year"),
                    "relevance_score": round(1 - distance, 3) if distance else None,
                })

        return {
            "query": query,
            "ticker_filter": ticker,
            "documents": documents,
            "count": len(documents),
        }
    except Exception as e:
        return {
            "documents": [],
            "error": str(e),
        }


def query_policies(
    query: str,
    n_results: int = 5,
    category: Optional[str] = None
) -> dict[str, Any]:
    """
    Query policy documents using RAG

    Args:
        query: User query
        n_results: Number of results to return
        category: Optional category filter

    Returns:
        dict with relevant documents and metadata
    """
    client = get_chroma_client()

    if client is None:
        return {
            "documents": [],
            "error": "Vector store not available",
        }

    try:
        collection = client.get_collection("credit_policies")

        # Build where filter
        where_filter = None
        if category:
            where_filter = {"category": category}

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        documents = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else None
                documents.append({
                    "content": doc,
                    "metadata": metadata,
                    "relevance_score": 1 - distance if distance else None,
                    "title": metadata.get("title", "Unknown"),
                    "category": metadata.get("category", "policy"),
                })

        return {
            "query": query,
            "documents": documents,
            "count": len(documents),
        }
    except Exception as e:
        return {
            "documents": [],
            "error": str(e),
        }


def get_relevant_context(
    query: str,
    include_portfolio: bool = True,
    include_policies: bool = True
) -> dict[str, Any]:
    """
    Get all relevant context for a query

    Args:
        query: User query
        include_portfolio: Include portfolio context
        include_policies: Include policy documents

    Returns:
        dict with combined context
    """
    context = {
        "query": query,
        "portfolio": None,
        "policies": [],
        "entities": [],
    }

    # Extract entities from query
    entities = _extract_entities(query)
    context["entities"] = entities

    # Get portfolio context if needed
    if include_portfolio:
        from .portfolio_tools import get_portfolio_summary
        context["portfolio"] = get_portfolio_summary()

    # Get policy documents if needed
    if include_policies:
        policy_result = query_policies(query)
        context["policies"] = policy_result.get("documents", [])

    return context


def _extract_entities(query: str) -> list[dict]:
    """
    Extract entities from query (simplified)

    In production, this would use NER model
    """
    entities = []

    # Simple keyword extraction
    keywords = {
        "pd": "probability_of_default",
        "lgd": "loss_given_default",
        "var": "value_at_risk",
        "capital": "capital_requirement",
        "concentration": "concentration_risk",
        "exposure": "exposure",
        "default": "default_risk",
        "rating": "risk_rating",
        "industry": "industry_concentration",
        "region": "geographic_concentration",
    }

    query_lower = query.lower()
    for keyword, entity_type in keywords.items():
        if keyword in query_lower:
            entities.append({
                "text": keyword,
                "type": entity_type,
            })

    # Look for loan IDs (pattern: LOAN-XXXXX)
    import re
    loan_ids = re.findall(r'LOAN-\w+', query, re.IGNORECASE)
    for loan_id in loan_ids:
        entities.append({
            "text": loan_id,
            "type": "loan_id",
        })

    return entities
