"""
Operations Workflow Automation Router
Handles: onboarding triggers, scheduling, travel coordination,
         request routing, and workflow design via Claude.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from services.claude_service import claude_complete, WORKFLOW_SYSTEM
from database.supabase_client import get_supabase
import json, uuid

router = APIRouter(prefix="/automations", tags=["automations"])


class WorkflowTrigger(BaseModel):
    workflow_type: str  # onboarding | scheduling | travel | routing | custom
    context: dict = {}


class WorkflowDesignRequest(BaseModel):
    process_name: str
    process_description: str
    current_pain_points: list[str] = []
    desired_outcome: str = ""


WORKFLOW_TEMPLATES = {
    "onboarding": {
        "name": "New Hire Onboarding",
        "steps": [
            {"step": 1, "name": "Offer Accepted", "action": "Trigger onboarding sequence", "system": "HRIS", "time_saved_min": 0},
            {"step": 2, "name": "Send Documents", "action": "Auto-send NDA, I-9, W-4 via DocuSign", "system": "DocuSign + Gmail", "time_saved_min": 45},
            {"step": 3, "name": "IT Provisioning", "action": "Create Slack, Gmail, Drive, HRIS accounts", "system": "IT + Google Workspace", "time_saved_min": 60},
            {"step": 4, "name": "Schedule Day 1", "action": "Book orientation, send calendar invites", "system": "Google Calendar", "time_saved_min": 30},
            {"step": 5, "name": "Notify Team", "action": "Post welcome message in #general Slack", "system": "Slack", "time_saved_min": 15},
            {"step": 6, "name": "Complete", "action": "Mark onboarded in HRIS, notify manager", "system": "HRIS", "time_saved_min": 10},
        ],
        "total_time_saved_hours": 2.67
    },
    "scheduling": {
        "name": "Interview Scheduling",
        "steps": [
            {"step": 1, "name": "Candidate Screened", "action": "Trigger scheduling sequence", "system": "Screener", "time_saved_min": 0},
            {"step": 2, "name": "Find Availability", "action": "Check interviewer calendars via Google Cal API", "system": "Google Calendar", "time_saved_min": 20},
            {"step": 3, "name": "Send Options", "action": "Email candidate 3 time slot options", "system": "Gmail", "time_saved_min": 10},
            {"step": 4, "name": "Confirm & Book", "action": "Auto-confirm chosen slot, create calendar event", "system": "Google Calendar", "time_saved_min": 10},
            {"step": 5, "name": "Send Reminders", "action": "24h and 1h reminder emails to all parties", "system": "Gmail", "time_saved_min": 5},
        ],
        "total_time_saved_hours": 0.75
    },
    "travel": {
        "name": "Travel Coordination",
        "steps": [
            {"step": 1, "name": "Request Received", "action": "Collect travel preferences via Slack form", "system": "Slack", "time_saved_min": 15},
            {"step": 2, "name": "Generate Options", "action": "AI drafts 3 flight + hotel itinerary options", "system": "AI + Travel API", "time_saved_min": 60},
            {"step": 3, "name": "Approval", "action": "Route to manager for approval via Slack", "system": "Slack", "time_saved_min": 10},
            {"step": 4, "name": "Book & Confirm", "action": "Send confirmed itinerary to traveler", "system": "Gmail", "time_saved_min": 5},
        ],
        "total_time_saved_hours": 1.5
    },
    "routing": {
        "name": "Cross-Department Request Routing",
        "steps": [
            {"step": 1, "name": "Request Submitted", "action": "Employee submits request via HR Copilot or form", "system": "Copilot", "time_saved_min": 0},
            {"step": 2, "name": "AI Classification", "action": "Classify request: HR / IT / Legal / Finance / Ops", "system": "AI classifier", "time_saved_min": 15},
            {"step": 3, "name": "Auto-Route", "action": "Assign to correct team member, create ticket", "system": "HRIS + Slack", "time_saved_min": 10},
            {"step": 4, "name": "Notify & Track", "action": "Notify assignee, set SLA timer, confirm to requester", "system": "Slack + HRIS", "time_saved_min": 5},
        ],
        "total_time_saved_hours": 0.5
    }
}


@router.post("/trigger")
async def trigger_workflow(req: WorkflowTrigger):
    template = WORKFLOW_TEMPLATES.get(req.workflow_type)
    if not template:
        return {"error": f"Unknown workflow type: {req.workflow_type}"}

    time_saved = int(template["total_time_saved_hours"] * 60)

    supabase = get_supabase()
    result = supabase.table("automation_runs").insert({
        "workflow_name": template["name"],
        "trigger_event": req.workflow_type,
        "status": "completed",
        "time_saved_minutes": time_saved,
        "details": {**req.context, "steps_executed": len(template["steps"])}
    }).execute()

    run_id = result.data[0]["id"] if result.data else str(uuid.uuid4())
    return {
        "run_id": run_id,
        "workflow": template["name"],
        "steps": template["steps"],
        "time_saved_minutes": time_saved,
        "status": "completed"
    }


@router.post("/design")
async def design_workflow(req: WorkflowDesignRequest):
    """Use Claude to design a custom automation workflow."""
    user_prompt = f"""
    Design an automation workflow for Phamily's operations team.
    
    Process: {req.process_name}
    Description: {req.process_description}
    Current pain points: {req.current_pain_points}
    Desired outcome: {req.desired_outcome}
    
    Available integrations at Phamily: Slack, Gmail, Google Calendar, Google Drive, 
    HRIS system, ATS system, DocuSign.
    
    Return JSON:
    {{
      "workflow_name": "<name>",
      "estimated_time_saved_hours": <number>,
      "steps": [
        {{
          "step": 1,
          "name": "<step name>",
          "action": "<what happens>",
          "system": "<which tool/integration>",
          "time_saved_min": <minutes saved at this step>
        }}
      ],
      "implementation_notes": "<practical notes for building this>",
      "phamily_principles_alignment": "<how this workflow embodies Care, Clarity, Craftsmanship>"
    }}
    """
    try:
        raw = await claude_complete(WORKFLOW_SYSTEM, user_prompt, max_tokens=1000)
        workflow = json.loads(raw)
    except Exception as e:
        raise Exception(f"Workflow design failed: {e}")

    return {"designed_workflow": workflow}


@router.get("/runs")
async def get_automation_runs(limit: int = 20):
    supabase = get_supabase()
    result = supabase.table("automation_runs").select("*").order(
        "created_at", desc=True
    ).limit(limit).execute()
    runs = result.data or []
    total_saved = sum(r.get("time_saved_minutes", 0) for r in runs)
    return {
        "runs": runs,
        "total_runs": len(runs),
        "total_time_saved_minutes": total_saved,
        "total_time_saved_hours": round(total_saved / 60, 1)
    }


@router.get("/templates")
async def get_templates():
    return {"templates": list(WORKFLOW_TEMPLATES.keys()), "details": WORKFLOW_TEMPLATES}
