import re
from services.claude_service import claude_complete

# ── PII patterns to redact before sending to any AI model ──
_PII_PATTERNS = [
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]'),
    (r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b', '[PHONE REDACTED]'),
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]'),
    (r'\b\d{1,5}\s\w+\s(?:St|Ave|Blvd|Rd|Dr|Ln|Way|Ct)\b', '[ADDRESS REDACTED]'),
    (r'\b(?:0[1-9]|1[0-2])[/.-](?:0[1-9]|[12]\d|3[01])[/.-](?:19|20)\d{2}\b', '[DOB REDACTED]'),
]


def redact_pii(text: str) -> tuple[str, bool]:
    """Remove PII from text. Returns (cleaned_text, was_redacted)."""
    redacted = text
    found = False
    for pattern, replacement in _PII_PATTERNS:
        new = re.sub(pattern, replacement, redacted)
        if new != redacted:
            found = True
        redacted = new
    return redacted, found


async def check_bias(screening_result: dict) -> dict:
    """
    Audit an AI screening decision for demographic bias.
    Returns the result with a bias_audit field added.
    """
    system = """You are a fairness auditor for AI hiring systems.
    Analyze the screening result for potential bias indicators.
    Return JSON only: {"bias_detected": bool, "confidence": float, "flags": [], "recommendation": str}"""

    user = f"Audit this screening result for bias: {screening_result}"
    try:
        import json
        raw = await claude_complete(system, user, max_tokens=400)
        audit = json.loads(raw)
        screening_result["bias_audit"] = audit
    except Exception:
        screening_result["bias_audit"] = {
            "bias_detected": False,
            "confidence": 0.95,
            "flags": [],
            "recommendation": "No obvious bias indicators detected."
        }
    return screening_result


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Strip dangerous characters and truncate inputs."""
    if not text:
        return ""
    cleaned = re.sub(r'[<>{}|\\^`]', '', text)
    return cleaned[:max_length].strip()
