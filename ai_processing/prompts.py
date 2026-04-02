VALID_CATEGORIES = ["medical", "food", "shelter", "rescue", "sanitation", "education", "other"]
VALID_SEVERITIES = ["low", "medium", "high", "critical"]

def build_prompt(description: str) -> str:
    return f"""
        You are an AI assistant classifying community emergency reports for an NGO volunteer system.

        Analyze the report below and return ONLY a valid JSON object with exactly two fields:
        - "category": must be one of {VALID_CATEGORIES}
        - "severity": must be one of {VALID_SEVERITIES}

        Severity guide:
        - "critical" → immediate life threat (trapped, dying, no water for days)
        - "high"     → urgent but not immediately life-threatening (food shortage, injury)
        - "medium"   → important, can wait a few hours (hygiene issue, minor injury)
        - "low"      → general community need (awareness, minor supply request)

        Rules:
        - Return ONLY the JSON. No explanation. No markdown. No extra text.
        - If unsure about category, use "other"
        - If unsure about severity, use "medium"

        Report: "{description}"
        """