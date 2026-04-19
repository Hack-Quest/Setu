VALID_CATEGORIES = ["medical", "food", "shelter", "rescue", "sanitation", "education", "other"]
VALID_SEVERITIES = ["low", "medium", "high", "critical"]

def build_prompt(description: str) -> str:
    return f"""
        You are an AI assistant classifying community emergency reports for an NGO volunteer system.

        Analyze the report below and return ONLY a valid JSON object with exactly three fields:
        - "category": must be one of {VALID_CATEGORIES}
        - "severity": must be one of {VALID_SEVERITIES}
        - "consistency": an integer from 0 to 10 rating how believable and internally consistent this report is.
          (0 = clearly fake/nonsensical, 5 = plausible but vague, 10 = very detailed and credible)

        Language Rules:
        - The report may be in English, Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, or any other Indian regional language.
        - The report might also be written using Latin/Roman script (e.g., Hinglish, Tanglish).
        - Please analyze, translate internally, and understand the core intent before evaluating.

        Severity guide:
        - "critical" → immediate life threat (trapped, dying, no water for days)
        - "high"     → urgent but not immediately life-threatening (food shortage, injury)
        - "medium"   → important, can wait a few hours (hygiene issue, minor injury)
        - "low"      → general community need (awareness, minor supply request)

        Consistency guide:
        - Penalise vague, contradictory, very short, or implausible descriptions.
        - Reward specific details: named location, number of people, timeline, type of disaster.

        Output Rules:
        - Return ONLY the JSON. No explanation. No markdown. No extra text.
        - ALWAYS output English keys and values as specified, regardless of the input language.
        - If unsure about category, use "other"
        - If unsure about severity, use "medium"
        - If unsure about consistency, use 5

        Report: "{description}"
        """