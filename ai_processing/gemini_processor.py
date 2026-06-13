import json
import os
from dotenv import load_dotenv
import google as genai
from ai_processing.prompts import build_prompt, VALID_CATEGORIES, VALID_SEVERITIES

# Load from shared config folder
load_dotenv(dotenv_path="config/.env")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def process_need_text(description: str) -> dict:
    """
    Input:  raw community need description (string)
    Output: {"category": "...", "severity": "..."}

    This is the ONLY function Khare needs to import.
    """

    if not description or not description.strip():
        return {"category": "other", "severity": "medium", "error": "empty input"}

    prompt = build_prompt(description)

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        raw = response.text.strip()

        # Clean markdown if Gemini wraps output in backticks
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()

        result = json.loads(raw)

        # Validate — never trust AI output blindly
        if result.get("category") not in VALID_CATEGORIES:
            result["category"] = "other"
        if result.get("severity") not in VALID_SEVERITIES:
            result["severity"] = "medium"

        return {
            "category": result["category"],
            "severity": result["severity"]
        }

    except json.JSONDecodeError:
        print(f"[Gemini] JSON parse failed. Raw output was: {raw}")
        return {"category": "other", "severity": "medium"}

    except Exception as e:
        print(f"[Gemini] Unexpected error: {e}")
        return {"category": "other", "severity": "medium"}