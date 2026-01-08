"""
RAG tools for policy queries and context retrieval
"""

from typing import Any, Optional
from pathlib import Path


def get_chroma_client():
    """Get ChromaDB client"""
    try:
        import chromadb
        persist_dir = Path(__file__).parent.parent.parent.parent / "data" / "chroma_db"
        client = chromadb.PersistentClient(path=str(persist_dir))
        return client
    except Exception as e:
        return None


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
