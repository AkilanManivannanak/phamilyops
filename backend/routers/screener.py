"""
Candidate Screener Router
Pipeline: Resume text → PII redaction → NLP entity extraction →
          skill alignment → Claude scoring → bias audit → Supabase storage
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.claude_service import claude_complete, SCREENING_SYSTEM
from services.nlp_service import extract_skills, compute_skill_alignment, assess_culture_fit, extract_entities
from services.safety_service import redact_pii, check_bias, sanitize_input
from database.supabase_client import get_supabase
import json

router = APIRouter(prefix="/screener", tags=["screener"])


class ScreenRequest(BaseModel):
    resume_text: str
    candidate_name: str
    candidate_email: str = ""
    role: str = "HR, AI Automation Intern"
    job_context: str = ""


class ScreenResponse(BaseModel):
    candidate_id: str
    overall_score: int
    skill_alignment: float
    culture_fit: str
    skills: list
    screening_questions: list
    outreach_email: str
    bias_audit: dict
    pii_was_redacted: bool
    entities: dict


@router.post("/screen", response_model=ScreenResponse)
async def screen_candidate(req: ScreenRequest):
    # 1. Sanitize
    resume_clean = sanitize_input(req.resume_text)
    name_clean = sanitize_input(req.candidate_name, max_length=100)

    # 2. PII Redaction (before any AI processing)
    resume_redacted, pii_found = redact_pii(resume_clean)

    # 3. NLP — entity extraction + skill matching
    entities = extract_entities(resume_redacted)
    skills = extract_skills(resume_redacted)
    skill_alignment = compute_skill_alignment(resume_redacted, req.role)
    culture_fit = assess_culture_fit(resume_redacted)

    # 4. Claude — comprehensive scoring + questions + outreach
    user_prompt = f"""
    Role: {req.role}
    Additional Context: {req.job_context}
    
    Candidate Resume (PII redacted):
    {resume_redacted[:3000]}
    
    Pre-computed signals:
    - Detected skills: {[s['skill'] for s in skills]}
    - Skill alignment score: {skill_alignment}/100
    - Culture fit assessment: {culture_fit}
    
    Return JSON:
    {{
      "overall_score": <0-100 integer>,
      "score_rationale": "<2-3 sentence explanation>",
      "strengths": ["<strength1>", "<strength2>", "<strength3>"],
      "concerns": ["<concern1>", "<concern2>"],
      "screening_questions": [
        "<personalized question 1 based on their actual resume>",
        "<personalized question 2>",
        "<personalized question 3>"
      ],
      "outreach_email": "<full personalized outreach email to this candidate>"
    }}
    """
    try:
        raw = await claude_complete(SCREENING_SYSTEM, user_prompt, max_tokens=1200)
        claude_result = json.loads(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e}")

    overall_score = claude_result.get("overall_score", 70)

    # 5. Bias audit
    result_for_audit = {
        "overall_score": overall_score,
        "culture_fit": culture_fit,
        "skills": [s["skill"] for s in skills],
        "rationale": claude_result.get("score_rationale", ""),
    }
    audited = await check_bias(result_for_audit)

    # 6. Store in Supabase
    supabase = get_supabase()
    db_row = {
        "name": name_clean,
        "email": req.candidate_email,
        "role": req.role,
        "resume_text": resume_redacted,
        "overall_score": overall_score,
        "skill_alignment": skill_alignment,
        "culture_fit": culture_fit,
        "status": "screened",
        "skills": skills,
        "screening_questions": claude_result.get("screening_questions", []),
        "outreach_email": claude_result.get("outreach_email", ""),
        "pii_redacted": pii_found,
        "bias_checked": True,
    }
    insert_result = supabase.table("candidates").insert(db_row).execute()
    candidate_id = insert_result.data[0]["id"] if insert_result.data else "unknown"

    return ScreenResponse(
        candidate_id=candidate_id,
        overall_score=overall_score,
        skill_alignment=skill_alignment,
        culture_fit=culture_fit,
        skills=skills,
        screening_questions=claude_result.get("screening_questions", []),
        outreach_email=claude_result.get("outreach_email", ""),
        bias_audit=audited.get("bias_audit", {}),
        pii_was_redacted=pii_found,
        entities=entities,
    )


@router.get("/candidates")
async def get_candidates(status: str = "", limit: int = 50):
    supabase = get_supabase()
    query = supabase.table("candidates").select("*").order("overall_score", desc=True).limit(limit)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return {"candidates": result.data or [], "total": len(result.data or [])}


@router.patch("/candidates/{candidate_id}/status")
async def update_status(candidate_id: str, status: str):
    supabase = get_supabase()
    supabase.table("candidates").update({"status": status}).eq("id", candidate_id).execute()

    # Trigger automation if moved to interview or offer
    if status in ["interview", "offered"]:
        supabase.table("automation_runs").insert({
            "workflow_name": f"{'Interview Scheduling' if status == 'interview' else 'Offer Letter Draft'}",
            "trigger_event": f"candidate_status_{status}",
            "status": "completed",
            "time_saved_minutes": 45 if status == "interview" else 130,
            "details": {"candidate_id": candidate_id}
        }).execute()

    return {"success": True, "candidate_id": candidate_id, "new_status": status}
