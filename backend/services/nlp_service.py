"""
NLP Service — HuggingFace Transformers
Handles resume entity extraction, skill detection, and text processing.
Model: dslim/bert-base-NER (lightweight, runs on CPU, free)
"""
from __future__ import annotations
import re
from functools import lru_cache
from transformers import pipeline

# Known skill taxonomy for Phamily roles
PHAMILY_SKILLS = {
    "ai_tools": ["claude", "chatgpt", "gemini", "openai", "anthropic", "gpt-4"],
    "ml_frameworks": ["pytorch", "tensorflow", "huggingface", "transformers", "sklearn", "scikit-learn"],
    "languages": ["python", "javascript", "typescript", "sql", "bash", "r"],
    "backend": ["fastapi", "flask", "django", "node", "express", "rest api", "graphql"],
    "data": ["pandas", "numpy", "spark", "dbt", "airflow", "etl"],
    "retrieval": ["vector", "embedding", "semantic search", "retrieval", "knowledge retrieval"],
    "databases": ["postgresql", "supabase", "mongodb", "redis", "pinecone", "weaviate"],
    "devops": ["docker", "kubernetes", "github actions", "ci/cd", "railway", "vercel", "render"],
    "healthcare": ["healthcare", "hipaa", "ehr", "hl7", "fhir", "care management", "clinical"],
    "soft_skills": ["leadership", "collaboration", "communication", "initiative", "ownership"],
}


@lru_cache(maxsize=1)
def _get_ner_pipeline():
    """Load NER model once, cache it. Uses CPU — works on any free tier."""
    return pipeline(
        "ner",
        model="dslim/bert-base-NER",
        aggregation_strategy="simple",
        device=-1  # CPU
    )


@lru_cache(maxsize=1)
def _get_classifier():
    """Zero-shot classifier for culture fit assessment."""
    return pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli",
        device=-1
    )


def extract_entities(text: str) -> dict:
    """
    Extract named entities from resume text.
    Returns: {persons, organizations, locations, misc}
    """
    try:
        ner = _get_ner_pipeline()
        entities = ner(text[:512])  # BERT max tokens
        result = {"persons": [], "organizations": [], "locations": [], "misc": []}
        for ent in entities:
            label = ent["entity_group"].upper()
            word = ent["word"].strip()
            if label == "PER" and word not in result["persons"]:
                result["persons"].append(word)
            elif label == "ORG" and word not in result["organizations"]:
                result["organizations"].append(word)
            elif label == "LOC" and word not in result["locations"]:
                result["locations"].append(word)
            elif word not in result["misc"]:
                result["misc"].append(word)
        return result
    except Exception as e:
        return {"persons": [], "organizations": [], "locations": [], "misc": [], "error": str(e)}


def extract_skills(resume_text: str) -> list[dict]:
    """
    Match resume text against Phamily skill taxonomy.
    Returns ranked list of detected skills with categories.
    """
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
    """
    Score skill alignment 0-100 based on role requirements.
    """
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
    score = 0.0
    max_score = sum(weights.values()) * 3
    for s in skills:
        cat = s["category"]
        score += weights.get(cat, 0.5)
    return min(100.0, round((score / max_score) * 100, 1))


def assess_culture_fit(resume_text: str) -> str:
    """Zero-shot classify resume against Phamily's culture principles."""
    try:
        classifier = _get_classifier()
        labels = ["Strong culture fit", "Moderate culture fit", "Unclear culture fit"]
        hypothesis = "This person demonstrates builder mentality, initiative, and mission-driven work ethic."
        result = classifier(resume_text[:400], candidate_labels=labels)
        return result["labels"][0]
    except Exception:
        # Fallback: keyword heuristic
        keywords = ["built", "launched", "shipped", "designed", "led", "improved", "automated",
                    "initiative", "ownership", "mission", "impact"]
        hits = sum(1 for kw in keywords if kw in resume_text.lower())
        if hits >= 5:
            return "Strong culture fit"
        elif hits >= 2:
            return "Moderate culture fit"
        return "Unclear culture fit"


def parse_years_experience(text: str) -> int:
    """Extract years of experience from resume text."""
    patterns = [
        r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
        r'(\d+)\+?\s*yrs?\s*(?:of\s*)?experience',
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0
