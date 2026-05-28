"""
Vector Service — Claude-powered semantic search (no local models)
Uses keyword matching + Claude for retrieval on free tier.
"""
from database.supabase_client import get_supabase


async def semantic_search(query: str, top_k: int = 3) -> list[dict]:
    """Keyword-based search fallback when pgvector embeddings not available."""
    supabase = get_supabase()
    result = supabase.table("hr_documents").select(
        "id, title, category, content"
    ).eq("is_active", True).execute()

    docs = result.data or []
    query_lower = query.lower()

    # Score by keyword overlap
    scored = []
    for doc in docs:
        content_lower = doc["content"].lower()
        title_lower = doc["title"].lower()
        score = sum(1 for word in query_lower.split()
                   if len(word) > 3 and (word in content_lower or word in title_lower))
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k] if _ >= 0]


async def get_retrieval_context(query: str) -> tuple[str, list[str]]:
    docs = await semantic_search(query, top_k=3)
    if not docs:
        return "", []
    context_parts = [f"[{doc.get('title','Policy')}]\n{doc.get('content','')}" for doc in docs]
    doc_ids = [doc["id"] for doc in docs if "id" in doc]
    return "\n\n---\n\n".join(context_parts), doc_ids


async def embed_all_documents() -> int:
    """No-op on free tier — returns count of existing documents."""
    supabase = get_supabase()
    result = supabase.table("hr_documents").select("id").eq("is_active", True).execute()
    return len(result.data or [])
