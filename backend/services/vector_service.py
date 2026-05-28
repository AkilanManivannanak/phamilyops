"""
Vector Service — sentence-transformers + pgvector
Handles embedding generation and semantic similarity search
for the HR Copilot knowledge base retrieval.
Model: all-MiniLM-L6-v2 (384 dims, fast, CPU-friendly, free)
"""
from __future__ import annotations
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from database.supabase_client import get_supabase


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load embedding model once and cache it."""
    return SentenceTransformer("all-MiniLM-L6-v2")


def embed(text: str) -> list[float]:
    """Generate 384-dimensional embedding for text."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


async def embed_and_store_document(doc_id: str, content: str) -> bool:
    """
    Generate embedding for an HR policy document and store in pgvector.
    Called when new policy documents are added.
    """
    try:
        embedding = embed(content)
        supabase = get_supabase()
        supabase.table("hr_documents").update(
            {"embedding": embedding}
        ).eq("id", doc_id).execute()
        return True
    except Exception as e:
        print(f"Embedding storage error: {e}")
        return False


async def embed_all_documents() -> int:
    """
    Bulk embed all HR documents that don't have embeddings yet.
    Run this once after schema setup.
    """
    supabase = get_supabase()
    docs = supabase.table("hr_documents").select("id, content").eq("is_active", True).execute()
    count = 0
    for doc in docs.data:
        embedding = embed(doc["content"])
        supabase.table("hr_documents").update(
            {"embedding": embedding}
        ).eq("id", doc["id"]).execute()
        count += 1
    return count


async def semantic_search(query: str, top_k: int = 3) -> list[dict]:
    """
    Find most relevant HR policy chunks for a given query.
    Uses cosine similarity via pgvector.
    Returns top_k most relevant documents with their content.
    """
    query_embedding = embed(query)
    supabase = get_supabase()

    # pgvector cosine similarity search using RPC
    result = supabase.rpc(
        "match_hr_documents",
        {
            "query_embedding": query_embedding,
            "match_threshold": 0.3,
            "match_count": top_k
        }
    ).execute()

    if result.data:
        return result.data

    # Fallback: keyword search if vector search returns nothing
    result = supabase.table("hr_documents").select(
        "id, title, category, content"
    ).eq("is_active", True).limit(top_k).execute()
    return result.data or []


async def get_retrieval_context(query: str) -> tuple[str, list[str]]:
    """
    Retrieve relevant policy context for the copilot.
    Returns (formatted_context_string, list_of_doc_ids)
    """
    docs = await semantic_search(query, top_k=3)
    if not docs:
        return "", []
    context_parts = []
    doc_ids = []
    for doc in docs:
        context_parts.append(f"[{doc.get('title', 'Policy')}]\n{doc.get('content', '')}")
        if "id" in doc:
            doc_ids.append(doc["id"])
    context = "\n\n---\n\n".join(context_parts)
    return context, doc_ids
