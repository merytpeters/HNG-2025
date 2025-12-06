import os
import json
from typing import Dict, Any

import httpx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "gpt-4o-mini")
OPENROUTER_URL = os.getenv(
    "OPENROUTER_API_URL", "https://api.openrouter.ai/v1/chat/completions"
)


def _safe_parse_json(m: str) -> Any:
    try:
        return json.loads(m)
    except Exception:
        start = m.find("{")
        end = m.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(m[start : end + 1])
            except Exception:
                return None
        return None


def analyze_text(text: str) -> Dict[str, Any]:
    """Send text to OpenRouter and expect a JSON response with summary, doc_type and attributes."""
    if not OPENROUTER_API_KEY:
        return {
            "summary": (text[:1000] + "...") if len(text) > 1000 else text,
            "doc_type": "unknown",
            "attributes": {},
        }

    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    system = {
        "role": "system",
        "content": (
            "You are a JSON-only assistant. Given a document text, return a JSON object with keys:\n"
            "- summary: a concise summary string\n- doc_type: a single word describing the document type (invoice, cv, report, letter, etc.)\n"
            "- attributes: a JSON object containing extracted metadata like date, sender, total_amount, email, phone, etc.\n"
            "Only return valid JSON."
        ),
    }
    user = {"role": "user", "content": f"Document text:\n\n{text}"}

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [system, user],
        "max_tokens": 800,
    }

    try:
        resp = httpx.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            parsed = _safe_parse_json(content)
            if parsed:
                return {
                    "summary": parsed.get("summary") or "",
                    "doc_type": parsed.get("doc_type") or "",
                    "attributes": parsed.get("attributes") or {},
                }

            return {"summary": content, "doc_type": "unknown", "attributes": {}}
        return {"summary": "", "doc_type": "unknown", "attributes": {}}
    except Exception:
        return {"summary": "", "doc_type": "unknown", "attributes": {}}
