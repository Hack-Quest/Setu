import json
import importlib
import os
import re
from typing import Any, Dict

import requests
from dotenv import load_dotenv

from ai_processing.prompts import VALID_CATEGORIES, VALID_SEVERITIES, build_prompt

try:
    # Primary provider client requested by the new architecture.
    # Package: google-generativeai
    google_generativeai = importlib.import_module("google.generativeai")
except Exception:  # pragma: no cover - covered indirectly via fallback tests
    google_generativeai = None


# Load API keys once during module import so all calls share the same environment.
load_dotenv(dotenv_path="config/.env")

# Fallback provider configuration.
_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"

# Safe defaults used whenever providers fail or return malformed output.
_SAFE_DEFAULT_RESULT = {
    "category": "other",
    "severity": "medium",
    "consistency": 5,
    "reasoning": "fallback default",
}


def _init_gemini_model():
    """
    Initialize Gemini model once at import time.

    Why this exists:
    - We keep setup in one place for easier testing and fallback behavior.
    - If package/key is missing, we return None and allow Groq fallback.
    """
    if google_generativeai is None:
        return None

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        return None

    google_generativeai.configure(api_key=gemini_api_key)
    return google_generativeai.GenerativeModel("gemini-2.0-flash")


# Shared model instance for runtime efficiency and easier mocking in tests.
_gemini_model = _init_gemini_model()


def _extract_json_text(raw_response: Any) -> str:
    """
    Extract a JSON object string from arbitrary model output.

    Handles common bad formats safely:
    - Markdown code fences (```json ... ```)
    - Extra prose before/after JSON
    - Non-string payloads (dicts/lists) from SDK variations
    """
    if raw_response is None:
        raise ValueError("AI response is empty")

    # If provider already returned a Python object, serialize it directly.
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

    # If no object can be extracted, fail fast so fallback can run.
    raise ValueError("No JSON object found in AI response")


def _normalize_classification(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce strict production schema and normalize unsafe values.

    Output contract is intentionally rigid:
    {
      "category": <allowed category>,
      "severity": <allowed severity>,
      "consistency": <int 1..10>
    }
    """
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
    reasoning = str(parsed.get("reasoning", "")).strip()

    return {
        "category": category,
        "severity": severity,
        "consistency": consistency,
        "reasoning": reasoning[:200],  # keep it small
    }


def _parse_and_validate(raw_response: Any) -> Dict[str, Any]:
    """
    Parse model output to strict JSON and validate schema.

    This is the parsing firewall that protects the API layer from model drift.
    Any malformed text raises an exception so fallback logic can take over.
    """
    json_text = _extract_json_text(raw_response)
    parsed = json.loads(json_text)

    if not isinstance(parsed, dict):
        raise ValueError("AI response JSON is not an object")

    return _normalize_classification(parsed)


def _extract_gemini_text(response: Any) -> str:
    """
    Extract raw text from Gemini SDK responses safely.

    Different SDK versions may expose text via:
    - response.text
    - candidate/content parts
    This helper prevents brittle assumptions in main flow.
    """
    direct_text = (getattr(response, "text", "") or "").strip()
    if direct_text:
        return direct_text

    # Defensive fallback for alternate response shapes.
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
    """
    Fallback provider call.

    Groq is used only when Gemini fails due to package/key/runtime/parsing issues.
    We still pass the same strict prompt and run the same validation firewall.
    """
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
    Classify a free-text need safely.

    Routing order:
    1) Gemini (google-generativeai, gemini-2.0-flash)
    2) Groq fallback (llama-3.3-70b-versatile)
    3) Safe local default (never crash caller)

    Returned object is always schema-safe:
    {"category": ..., "severity": ..., "consistency": ...}
    """
    if not description or not description.strip():
        return {**_SAFE_DEFAULT_RESULT, "error": "empty input"}

    prompt = build_prompt(description)

    # Primary path: Gemini.
    # Any exception here is intentional trigger for fallback.
    try:
        if _gemini_model is None:
            raise ValueError("Gemini model is not configured")

        response = _gemini_model.generate_content(
            prompt,
            generation_config={
                "temperature": 0,
                "response_mime_type": "application/json",
            },
        )
        raw_text = _extract_gemini_text(response)
        return _parse_and_validate(raw_text)

    except Exception as gemini_error:
        print(f"[Gemini] Failed: {gemini_error}. Switching to Groq fallback.")

    # Mandatory fallback path: Groq.
    try:
        return _call_groq(prompt)
    except Exception as groq_error:
        print(f"[Groq] Failed: {groq_error}. Returning safe defaults.")

    # Final safety net: never raise from this function in production request flow.
    return _SAFE_DEFAULT_RESULT.copy()
