import json
import os
import re
from typing import Any, Dict
import requests
from dotenv import load_dotenv
from google import genai
from ai_processing.prompts import build_prompt, VALID_CATEGORIES, VALID_SEVERITIES

# Load from shared config folder
load_dotenv(dotenv_path="config/.env")

# For the new google-genai SDK
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Create a mockable _gemini_model helper that the test suite patches.
# In production, this delegates to client.models.
class GeminiModelWrapper:
    def generate_content(self, contents, **kwargs):
        # gemini-2.0-flash is a supported model name.
        return client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            **kwargs
        )

_gemini_model = GeminiModelWrapper()

_GROQ_MODEL = "llama-3.3-70b-versatile"
_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

_SAFE_DEFAULT_RESULT = {
    "category": "other",
    "severity": "medium",
    "consistency": 5,
}

def _extract_json_text(raw_response: Any) -> str:
    """Extract a JSON object string from arbitrary model output."""
    if raw_response is None:
        raise ValueError("AI response is empty")

    if isinstance(raw_response, (dict, list)):
        return json.dumps(raw_response)

    raw_text = str(raw_response).strip()
    if not raw_text:
        raise ValueError("AI response text is empty")

    # First preference: explicit fenced JSON block.
    fenced_match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, flags=re.DOTALL | re.IGNORECASE
    )
    if fenced_match:
        return fenced_match.group(1).strip()

    # Second preference: first object-like segment between { and }.
    first_brace = raw_text.find("{")
    last_brace = raw_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return raw_text[first_brace : last_brace + 1].strip()

    raise ValueError("No JSON object found in AI response")

def _normalize_classification(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize classifications to strict schema validation."""
    category = str(parsed.get("category", "other")).strip().lower()
    if category not in VALID_CATEGORIES:
        category = "other"

    severity = (
        str(parsed.get("severity", "medium"))
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )
    if severity not in VALID_SEVERITIES:
        severity = "medium"

    try:
        consistency = int(parsed.get("consistency", 5))
    except (TypeError, ValueError):
        consistency = 5
    consistency = max(1, min(10, consistency))

    return {
        "category": category,
        "severity": severity,
        "consistency": consistency,
    }

def _parse_and_validate(raw_response: Any) -> Dict[str, Any]:
    """Parse raw response text, clean, validate and normalize."""
    json_text = _extract_json_text(raw_response)
    parsed = json.loads(json_text)

    if not isinstance(parsed, dict):
        raise ValueError("AI response JSON is not an object")

    return _normalize_classification(parsed)

def _extract_gemini_text(response: Any) -> str:
    """Extract text from Gemini SDK response object safely."""
    direct_text = (getattr(response, "text", "") or "").strip()
    if direct_text:
        return direct_text

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = (getattr(part, "text", "") or "").strip()
            if part_text:
                return part_text

    return ""

def _call_groq(prompt: str) -> Dict[str, Any]:
    """Groq API fallback caller."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is not set in config/.env")

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }

    response = requests.post(_GROQ_API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    response_json = response.json()
    raw_text = (
        response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
    )
    return _parse_and_validate(raw_text)

def process_need_text(description: str) -> Dict[str, Any]:
    """
    Input:  raw community need description (string)
    Output: {"category": "...", "severity": "...", "consistency": ...}
    """
    if not description or not description.strip():
        return {**_SAFE_DEFAULT_RESULT, "error": "empty input"}

    prompt = build_prompt(description)

    try:
        if _gemini_model is None:
            raise ValueError("Gemini model is not configured")

        response = _gemini_model.generate_content(prompt)
        raw_text = _extract_gemini_text(response)
        return _parse_and_validate(raw_text)

    except Exception as gemini_error:
        print(f"[Gemini] Failed: {gemini_error}. Switching to Groq fallback.")

    try:
        return _call_groq(prompt)
    except Exception as groq_error:
        print(f"[Groq] Failed: {groq_error}. Returning safe defaults.")

    return _SAFE_DEFAULT_RESULT.copy()