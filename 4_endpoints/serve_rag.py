#!/usr/bin/env python3
"""
RAG (Retrieval Augmented Generation) Service Endpoint
Answers questions using policy documents and customer context.
"""

import os
from pathlib import Path
from typing import Optional

# Try to import required libraries
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# Global clients
_chroma_client = None
_anthropic_client = None


def get_chroma_client():
    """Get or create ChromaDB client."""
    global _chroma_client

    if _chroma_client is not None:
        return _chroma_client

    if not CHROMA_AVAILABLE:
        return None

    possible_paths = [
        Path(__file__).parent.parent / "data" / "chroma_db",
        Path("/home/cdsw/data/chroma_db"),
        Path("./data/chroma_db"),
    ]

    chroma_path = None
    for path in possible_paths:
        if path.exists():
            chroma_path = path
            break

    if chroma_path is None:
        return None

    _chroma_client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False)
    )

    return _chroma_client


def get_anthropic_client():
    """Get or create Anthropic client."""
    global _anthropic_client

    if _anthropic_client is not None:
        return _anthropic_client

    if not ANTHROPIC_AVAILABLE:
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    _anthropic_client = Anthropic(api_key=api_key)
    return _anthropic_client


def retrieve_policy_documents(question: str, n_results: int = 5) -> list:
    """Retrieve relevant policy documents."""
    client = get_chroma_client()
    if client is None:
        return []

    try:
        collection = client.get_collection("policy_documents")
        results = collection.query(
            query_texts=[question],
            n_results=n_results
        )

        documents = []
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i]
            documents.append({
                "content": doc,
                "title": metadata.get("title", "Unknown"),
                "category": metadata.get("category", "Unknown"),
                "chunk_index": metadata.get("chunk_index", 0),
            })

        return documents

    except Exception as e:
        print(f"[ERROR] Document retrieval failed: {e}")
        return []


def retrieve_customer_documents(customer_id: str, question: str, n_results: int = 3) -> list:
    """Retrieve relevant customer-specific documents."""
    client = get_chroma_client()
    if client is None:
        return []

    try:
        collection = client.get_collection("customer_documents")
        results = collection.query(
            query_texts=[question],
            n_results=n_results,
            where={"customer_id": customer_id} if customer_id else None
        )

        documents = []
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i]
            documents.append({
                "content": doc,
                "type": metadata.get("document_type", "Unknown"),
                "date": metadata.get("date", "Unknown"),
            })

        return documents

    except Exception:
        return []


def generate_response(question: str, context: str, risk_context: dict = None) -> str:
    """Generate response using Claude API."""
    client = get_anthropic_client()

    if client is None:
        # Fallback response without LLM
        return generate_fallback_response(question, context)

    # Build system prompt
    system_prompt = """You are an AI credit risk analyst assistant. Your role is to help analysts
make informed decisions by providing accurate information from credit policies and customer data.

Guidelines:
- Be precise and cite sources when referring to policies
- Provide clear, actionable guidance
- Flag any concerns or risk factors
- If information is not available, say so clearly
- Be concise but thorough"""

    # Build user message
    user_message = f"""Question: {question}

Policy Context:
{context}"""

    if risk_context:
        user_message += f"""

Risk Metrics:
- PD Score: {risk_context.get('pd_score', 'N/A')}
- LGD Score: {risk_context.get('lgd_score', 'N/A')}
- Risk Grade: {risk_context.get('risk_grade', 'N/A')}
- Loan Amount: ${risk_context.get('loan_amount', 'N/A'):,.0f}"""

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Use Haiku for speed
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        return response.content[0].text

    except Exception as e:
        print(f"[ERROR] LLM response failed: {e}")
        return generate_fallback_response(question, context)


def generate_fallback_response(question: str, context: str) -> str:
    """Generate a simple response without LLM."""
    # Extract key sentences from context that might answer the question
    question_lower = question.lower()

    # Keywords to look for
    keywords = question_lower.split()

    relevant_sentences = []
    for sentence in context.split(". "):
        sentence_lower = sentence.lower()
        if any(kw in sentence_lower for kw in keywords if len(kw) > 3):
            relevant_sentences.append(sentence.strip())

    if relevant_sentences:
        return "Based on the available policy documents:\n\n" + "\n".join(
            f"- {s}" for s in relevant_sentences[:5]
        )
    else:
        return "I found relevant policy documents but couldn't extract a specific answer. Please review the source documents or rephrase your question."


def query(args: dict) -> dict:
    """
    Main query function for RAG endpoint.

    Args:
        args: Dictionary containing:
            - question: str (the user's question)
            - customer_id: str (optional, for customer-specific context)
            - risk_context: dict (optional, risk metrics for context)
            - n_results: int (number of documents to retrieve)

    Returns:
        Dictionary with answer and sources
    """
    try:
        question = args.get("question", "")
        if not question:
            return {
                "status": "error",
                "error": "No question provided",
            }

        customer_id = args.get("customer_id")
        risk_context = args.get("risk_context")
        n_results = args.get("n_results", 5)

        # Retrieve relevant documents
        policy_docs = retrieve_policy_documents(question, n_results)
        customer_docs = []

        if customer_id:
            customer_docs = retrieve_customer_documents(customer_id, question)

        # Build context
        context_parts = []

        if policy_docs:
            context_parts.append("=== Policy Documents ===")
            for doc in policy_docs:
                context_parts.append(f"\n[{doc['title']}]\n{doc['content']}")

        if customer_docs:
            context_parts.append("\n=== Customer Documents ===")
            for doc in customer_docs:
                context_parts.append(f"\n[{doc['type']}]\n{doc['content']}")

        context = "\n".join(context_parts)

        # Generate response
        answer = generate_response(question, context, risk_context)

        # Format sources
        sources = []
        for doc in policy_docs:
            sources.append({
                "title": doc["title"],
                "category": doc["category"],
                "type": "policy",
            })
        for doc in customer_docs:
            sources.append({
                "title": doc["type"],
                "type": "customer",
            })

        return {
            "status": "success",
            "question": question,
            "answer": answer,
            "sources": sources,
            "documents_retrieved": len(policy_docs) + len(customer_docs),
            "has_customer_context": bool(customer_id and customer_docs),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("RAG Service Endpoint - Test")
    print("=" * 50)

    # Test query
    result = query({
        "question": "What is the minimum RORAC requirement for BBB grade loans?",
        "n_results": 3,
    })

    print(f"\nQuery Results:")
    print(f"  Status: {result['status']}")
    print(f"  Documents Retrieved: {result.get('documents_retrieved', 0)}")
    print(f"\nAnswer:")
    print(result.get('answer', 'No answer generated'))

    if result.get('sources'):
        print(f"\nSources:")
        for source in result['sources']:
            print(f"  - {source['title']} ({source['type']})")
