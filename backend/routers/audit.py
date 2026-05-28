"""
Workflow Audit Router
Pipeline: Process data → scoring algorithm → Claude roadmap generation → Supabase storage
"""
from fastapi import APIRouter
from pydantic import BaseModel
from services.claude_service import claude_complete, AUDIT_SYSTEM
from database.supabase_client import get_supabase
import json

router = APIRouter(prefix="/audit", tags=["audit"])


class ProcessInput(BaseModel):
    name: str
    frequency_per_week: int
    avg_hours: float
    error_rate_pct: int


class AuditRequest(BaseModel):
    processes: list[ProcessInput]
    department: str = "HR"


def compute_automation_score(freq: int, hours: float, error_rate: int) -> int:
    """
    Score a process on automation potential (0-99).
    Formula weights: frequency (30%), time cost (35%), error rate (25%), base (10%)
    """
    freq_score = (freq / 5) * 30
    time_score = (min(hours, 10) / 10) * 35
    error_score = (error_rate / 50) * 25
    base = 10
    return min(99, int(freq_score + time_score + error_score + base))


def compute_roi(freq: int, hours: float, hourly_rate: float = 30.0) -> float:
    """Annual ROI estimate in dollars."""
    return round(freq * hours * 52 * hourly_rate, 2)


@router.post("/analyze")
async def analyze_workflows(req: AuditRequest):
    # 1. Score each process
    scored = []
    for p in req.processes:
        score = compute_automation_score(p.frequency_per_week, p.avg_hours, p.error_rate_pct)
        roi = compute_roi(p.frequency_per_week, p.avg_hours)
        scored.append({
            "name": p.name,
            "frequency_per_week": p.frequency_per_week,
            "avg_hours": p.avg_hours,
            "error_rate_pct": p.error_rate_pct,
            "automation_score": score,
            "roi_annual": roi,
        })

    # 2. Sort by score descending
    ranked = sorted(scored, key=lambda x: x["automation_score"], reverse=True)
    for i, item in enumerate(ranked):
        item["priority_rank"] = i + 1

    # 3. Claude generates implementation roadmap
    user_prompt = f"""
    Department: {req.department}
    
    Analyzed processes (ranked by automation potential):
    {json.dumps(ranked[:10], indent=2)}
    
    Generate a practical implementation roadmap for Phamily.
    Return JSON:
    {{
      "executive_summary": "<2-3 sentence summary for leadership>",
      "total_annual_roi": <sum of ROI>,
      "total_hours_saved_monthly": <estimated monthly hours>,
      "quick_wins": ["<process name>: <one-line implementation approach>"],
      "recommendations": [
        {{
          "rank": 1,
          "process": "<name>",
          "approach": "<specific tool/method to automate it>",
          "timeline_weeks": <number>,
          "difficulty": "low|medium|high"
        }}
      ]
    }}
    """
    try:
        raw = await claude_complete(AUDIT_SYSTEM, user_prompt, max_tokens=1000)
        roadmap = json.loads(raw)
    except Exception as e:
        roadmap = {
            "executive_summary": f"Analyzed {len(ranked)} processes. Top automation opportunity: {ranked[0]['name']} with ${ranked[0]['roi_annual']:,.0f} annual ROI.",
            "total_annual_roi": sum(r["roi_annual"] for r in ranked),
            "total_hours_saved_monthly": sum(r["avg_hours"] * r["frequency_per_week"] * 4 for r in ranked),
            "quick_wins": [f"{r['name']}: Automate with AI workflow builder" for r in ranked[:3]],
            "recommendations": [{"rank": r["priority_rank"], "process": r["name"],
                                  "approach": "AI automation", "timeline_weeks": 2, "difficulty": "medium"} for r in ranked[:5]]
        }

    # 4. Store in Supabase
    supabase = get_supabase()
    for item in ranked:
        supabase.table("workflow_audits").insert({
            "process_name": item["name"],
            "frequency_per_week": item["frequency_per_week"],
            "avg_hours": item["avg_hours"],
            "error_rate_pct": item["error_rate_pct"],
            "automation_score": item["automation_score"],
            "roi_annual": item["roi_annual"],
            "priority_rank": item["priority_rank"],
        }).execute()

    return {
        "ranked_processes": ranked,
        "roadmap": roadmap,
        "total_processes_analyzed": len(ranked),
    }


@router.get("/history")
async def get_audit_history():
    supabase = get_supabase()
    result = supabase.table("workflow_audits").select("*").order(
        "created_at", desc=True
    ).limit(50).execute()
    return {"audits": result.data or []}
