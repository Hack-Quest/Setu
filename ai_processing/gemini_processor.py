import json
import os
import requests
from dotenv import load_dotenv
from google import genai
from ai_processing.prompts import build_prompt, VALID_CATEGORIES, VALID_SEVERITIES

# Load from shared config folder
load_dotenv(dotenv_path="config/.env")

# Primary AI: Gemini
_gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Secondary AI: Groq
_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"


def _parse_and_validate(raw: str) -> dict:
    """
    Parse and validate a raw JSON string from any AI model.
    Returns a validated dict with 'category', 'severity', and 'consistency'.
    Raises json.JSONDecodeError if parsing fails.
    """
    # Clean markdown if model wraps output in backticks
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    result = json.loads(raw)  # raises JSONDecodeError if invalid

    # Validate — never trust AI output blindly
    if result.get("category") not in VALID_CATEGORIES:
        result["category"] = "other"
    if result.get("severity") not in VALID_SEVERITIES:
        result["severity"] = "medium"

    # Extract consistency score (0-10); default to 5 if missing or non-integer
    try:
        consistency = int(result.get("consistency", 5))
        consistency = max(0, min(10, consistency))  # clamp to valid range
    except (TypeError, ValueError):
        consistency = 5

    return {
        "category": result["category"],
        "severity": result["severity"],
        "consistency": consistency
    }



def _call_groq(prompt: str) -> dict:
    """
    Fallback: Call Groq API with llama-3.3-70b-versatile.
    Returns a validated dict with 'category' and 'severity'.
    Raises on any network or parsing failure.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is not set in config/.env")

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": _GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }

    response = requests.post(_GROQ_API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    raw = response.json()["choices"][0]["message"]["content"].strip()
    return _parse_and_validate(raw)


def process_need_text(description: str) -> dict:
    """
    Input:  raw community need description (string)
    Output: {"category": "...", "severity": "..."}

    Tries Gemini first. If Gemini fails (quota, API error, etc.),
    automatically falls back to Groq (llama-3.3-70b-versatile).
    Only returns guessed defaults if BOTH providers fail.

    This is the ONLY function Khare needs to import.
    """

    if not description or not description.strip():
        return {"category": "other", "severity": "medium", "error": "empty input"}

    prompt = build_prompt(description)

    # --- Primary: Gemini ---
    try:
        response = _gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        raw = response.text.strip()
        result = _parse_and_validate(raw)
        print("[Gemini] Successfully processed request.")
        return result

    except json.JSONDecodeError:
        print(f"[Gemini] JSON parse failed. Raw output was: {raw!r}. Falling back to Groq...")
    except Exception as e:
        print(f"[Gemini] Error: {e}. Falling back to Groq...")

    # --- Fallback: Groq ---
    try:
        result = _call_groq(prompt)
        print(f"[Groq Fallback] Successfully processed request using {_GROQ_MODEL}.")
        return result

    except json.JSONDecodeError as e:
        print(f"[Groq Fallback] JSON parse failed: {e}")
    except requests.HTTPError as e:
        print(f"[Groq Fallback] HTTP error: {e}")
    except Exception as e:
        print(f"[Groq Fallback] Unexpected error: {e}")

    # --- Both failed ---
    print("[AI System] Both Gemini and Groq failed. Returning safe defaults.")
    return {"category": "other", "severity": "medium"}