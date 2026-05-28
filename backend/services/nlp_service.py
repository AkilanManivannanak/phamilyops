"""
NLP Service — Claude-powered (no local models)
Handles resume entity extraction, skill detection, scoring.
Uses Claude API instead of PyTorch/HuggingFace to stay within free tier memory.
"""
import re
import json
from services.claude_service import claude_complete

PHAMILY_SKILLS = {
    "ai_tools": ["claude", "chatgpt", "gemini", "openai", "anthropic", "gpt"],
    "ml_frameworks": ["pytorch", "tensorflow", "huggingface", "transformers", "sklearn"],
    "languages": ["python", "javascript", "typescript", "sql", "bash"],
    "backend": ["fastapi", "flask", "django", "node", "express", "rest api"],
    "data": ["pandas", "numpy", "spark", "dbt", "airflow"],
    "retrieval": ["vector", "embedding", "semantic search", "retrieval", "knowledge retrieval", "rag"],
    "databases": ["postgresql", "supabase", "mongodb", "redis", "pinecone"],
    "devops": ["docker", "kubernetes", "github actions", "ci/cd", "railway", "vercel"],
    "healthcare": ["healthcare", "hipaa", "ehr", "care management", "clinical"],
    "soft_skills": ["leadership", "collaboration", "communication", "initiative", "ownership"],
}


def extract_skills(resume_text: str) -> list[dict]:
    text_lower = resume_text.lower()
    found = []
    for category, skills in PHAMILY_SKILLS.items():
        for skill in skills:
            if skill in text_lower:
                found.append({
                    "skill": skill.title(),
                    "category": category,
                    "relevant_to_phamily": category in ["ai_tools", "ml_frameworks", "retrieval", "healthcare"]
                })
    return found


def compute_skill_alignment(resume_text: str, role: str) -> float:
    skills = extract_skills(resume_text)
    if not skills:
        return 0.0
    role_weights = {
        "HR, AI Automation Intern": {
            "ai_tools": 3.0, "ml_frameworks": 2.0, "languages": 2.0,
            "backend": 1.5, "healthcare": 2.5, "retrieval": 2.0,
        },
        "AI Native Process Automation Intern": {
            "ai_tools": 3.0, "languages": 2.5, "backend": 2.0,
            "ml_frameworks": 2.0, "devops": 1.5, "healthcare": 2.0,
        }
    }
    weights = role_weights.get(role, role_weights["HR, AI Automation Intern"])
    score = sum(weights.get(s["category"], 0.5) for s in skills)
    max_score = sum(weights.values()) * 3
    return min(100.0, round((score / max_score) * 100, 1))


def extract_entities(resume_text: str) -> dict:
    keywords = ["built", "launched", "shipped", "led", "designed", "improved", "automated"]
    hits = sum(1 for kw in keywords if kw in resume_text.lower())
    return {"builder_signals": hits, "text_length": len(resume_text)}


def assess_culture_fit(resume_text: str) -> str:
    keywords = ["built", "launched", "shipped", "designed", "led", "improved",
                "automated", "initiative", "ownership", "mission", "impact", "healthcare"]
    hits = sum(1 for kw in keywords if kw in resume_text.lower())
    if hits >= 5: return "Strong culture fit"
    elif hits >= 2: return "Moderate culture fit"
    return "Unclear culture fit"


def parse_years_experience(text: str) -> int:
    match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', text, re.IGNORECASE)
    return int(match.group(1)) if match else 0
