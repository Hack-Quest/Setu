VALID_CATEGORIES = ["medical", "food", "shelter", "rescue", "sanitation", "education", "other"]
VALID_SEVERITIES = ["low", "medium", "high", "very high", "critical"]

def build_prompt(description: str) -> str:
    return f"""
        You are an AI assistant classifying community emergency reports for an NGO volunteer system.

        Analyze the report below and return ONLY a valid JSON object with exactly 5 fields:
        - "category": must be one of {VALID_CATEGORIES}
        - "severity": must be one of {VALID_SEVERITIES}
        - "consistency": an integer from 0 to 10 rating how believable and internally consistent this report is.
          (0 = clearly fake/nonsensical, 5 = plausible but vague, 10 = very detailed and credible)
        - "summary_en": a short 5-6 word English summary of the emergency.
        - "summary_local": short 5-6 word translation of the summary in Hindi or the local language detected.

        Multilingual & Regional Language Rules:
        - The report may be in English, Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, or any other Indian regional language.
        - The report might also be written using Latin/Roman script (e.g., Hinglish, Tanglish).
        - You MUST analyze, translate internally, and understand the core intent before evaluating.
        - IMPORTANT: Regardless of the input language, you MUST maintain the exact JSON structure. Do NOT output anything in the regional language outside of the "summary_local" field.

        Severity guide:
        - "critical"  → immediate life threat (trapped in collapse, active drowning, life at risk now)
        - "very high" → impending life threat (food/water exhausted for days, rising floodwaters)
        - "high"      → urgent but currently stable (medical supplies needed, non-lethal injuries)
        - "medium"    → important and time-sensitive but can wait a few hours
        - "low"       → resource requests or infrastructure/community issues (sanitation, books)

        Consistency guide:
        - Penalise vague, contradictory, very short, or implausible descriptions.
        - Reward specific details: named location, number of people, timeline, type of disaster.

        Strict Output Rules (CRITICAL FOR PARSING):
        - Return ONLY the raw JSON object. Do NOT wrap the JSON in ```json ... ``` blocks or use markdown formatting.
        - NO conversational text. NO explanations before or after the JSON.
        - ALL keys and values MUST be in English, except for the "summary_local" value.
        - The output must be strictly valid JSON that can be parsed by `json.loads()`.
        - The "severity" value must be exactly one of: {VALID_SEVERITIES}
        - If unsure about category, use "other"
        - If unsure about severity, use "medium"
        - If unsure about consistency, use 5

        Report: "{description}"
        """