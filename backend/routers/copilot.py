"""
HR Copilot Router
Pipeline: User query → semantic search (pgvector) →
          context injection → Claude streaming → RAGAS eval → Supabase log
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.claude_service import claude_stream, claude_complete, COPILOT_SYSTEM
from services.vector_service import get_retrieval_context, embed_all_documents
from services.ragas_service import evaluate_response, get_average_scores
from services.safety_service import sanitize_input
from database.supabase_client import get_supabase
import json, uuid, time

router = APIRouter(prefix="/copilot", tags=["copilot"])


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    history: list = []


class EmbedRequest(BaseModel):
    confirm: bool = False


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Streaming chat endpoint.
    Full pipeline: retrieve context → stream Claude response → async eval.
    """
    session_id = req.session_id or str(uuid.uuid4())
    clean_msg = sanitize_input(req.message)

    # 1. Retrieve relevant policy context via semantic search
    context, doc_ids = await get_retrieval_context(clean_msg)

    # 2. Build system prompt with injected context
    system_with_context = COPILOT_SYSTEM
    if context:
        system_with_context += f"\n\n=== RELEVANT PHAMILY POLICY CONTEXT ===\n{context}\n=== END CONTEXT ==="

    # 3. Build message history for multi-turn conversation
    messages = []
    for turn in req.history[-6:]:  # last 3 turns max
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": clean_msg})

    # 4. Log user message to Supabase
    supabase = get_supabase()
    try:
        supabase.table("chat_history").insert({
            "session_id": session_id,
            "role": "user",
            "message": clean_msg,
            "retrieved_doc_ids": doc_ids,
        }).execute()
    except Exception:
        pass

    # 5. Stream response and collect full text for logging
    full_response = []
    start_time = time.time()

    async def generate():
        async for chunk in claude_stream(system_with_context, messages):
            full_response.append(chunk)
            yield f"data: {json.dumps({'text': chunk, 'session_id': session_id})}\n\n"

        # After streaming completes — log + evaluate async
        response_text = "".join(full_response)
        elapsed_ms = int((time.time() - start_time) * 1000)

        try:
            supabase.table("chat_history").insert({
                "session_id": session_id,
                "role": "assistant",
                "message": response_text,
                "retrieved_doc_ids": doc_ids,
                "response_time_ms": elapsed_ms,
            }).execute()
        except Exception:
            pass

        # Async RAGAS evaluation (non-blocking)
        try:
            await evaluate_response(clean_msg, response_text, context, session_id)
        except Exception:
            pass

        yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/chat/sync")
async def chat_sync(req: ChatRequest):
    """Non-streaming chat for simple integrations."""
    session_id = req.session_id or str(uuid.uuid4())
    clean_msg = sanitize_input(req.message)
    context, doc_ids = await get_retrieval_context(clean_msg)

    system_with_context = COPILOT_SYSTEM
    if context:
        system_with_context += f"\n\n=== RELEVANT PHAMILY POLICY CONTEXT ===\n{context}\n=== END CONTEXT ==="

    messages = [{"role": "user", "content": clean_msg}]
    response = await claude_complete(system_with_context, clean_msg, max_tokens=1000)

    supabase = get_supabase()
    try:
        supabase.table("chat_history").insert({
            "session_id": session_id, "role": "user", "message": clean_msg,
            "retrieved_doc_ids": doc_ids,
        }).execute()
        supabase.table("chat_history").insert({
            "session_id": session_id, "role": "assistant", "message": response,
            "retrieved_doc_ids": doc_ids,
        }).execute()
    except Exception:
        pass

    return {"response": response, "session_id": session_id, "context_used": bool(context)}


@router.post("/embed-documents")
async def embed_documents(req: EmbedRequest):
    """
    One-time setup: generate embeddings for all HR policy documents.
    Call this once after running schema.sql.
    """
    if not req.confirm:
        return {"message": "Pass confirm=true to run embedding"}
    count = await embed_all_documents()
    return {"embedded": count, "message": f"Successfully embedded {count} HR policy documents"}


@router.get("/quality-metrics")
async def quality_metrics():
    """Return average RAGAS scores for dashboard."""
    return await get_average_scores()


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    supabase = get_supabase()
    result = supabase.table("chat_history").select("*").eq(
        "session_id", session_id
    ).order("created_at").execute()
    return {"history": result.data or []}
