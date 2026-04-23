VALID_CATEGORIES = ["medical", "rescue", "supplies", "logistics", "other"]
VALID_SEVERITIES = ["low", "medium", "high", "very high", "critical"]


def build_prompt(description: str) -> str:
    return f"""
You are a strict emergency-report classifier for an NGO disaster response system.

Your task: read ONE report and return ONE JSON object with EXACTLY these fields:
- "category": one of {VALID_CATEGORIES}
- "severity": one of {VALID_SEVERITIES}
- "consistency": integer 1-10 (1 = incoherent/unbelievable, 10 = highly coherent and believable)

Allowed categories (no other labels are permitted):
1) medical
- Use when the primary need is treatment, injuries, illness, ambulance, doctor, nurse, medicine, first-aid.
2) rescue
- Use when people are trapped, missing, stranded in immediate danger, drowning risk, collapse entrapment, evacuation-from-danger.
3) supplies
- Use when the primary need is consumable/basic goods: food, drinking water, blankets, tents, hygiene kits, diapers, fuel-for-cooking.
4) logistics
- Use when the primary need is transport, drivers, vehicles, loading/unloading, moving goods, delivery coordination, route support.
- IMPORTANT: "driver needed", "transport supplies", "truck/van needed" MUST be logistics, not medical.
5) other
- Use only when none of the above categories clearly apply.

Severity scale (strict):
- low: routine/non-urgent request; no immediate danger to life.
- medium: important request, should be addressed soon, but no direct life threat now.
- high: urgent and potentially escalating; serious impact likely if delayed.
- very high: severe and near life-threatening; immediate response strongly needed.
- critical: active immediate life threat right now (for example trapped in collapse, active drowning, major uncontrolled injury).

Severity examples:
- "Driver is needed to transport supplies at old age home" -> category=logistics, severity=low or medium.
- "Building collapsed, 3 people trapped" -> category=rescue, severity=critical.

Consistency scoring rules (1-10 integer only):
- Lower scores for contradictory, extremely vague, or nonsensical reports.
- Higher scores for coherent details such as people count, location clues, concrete need, and timeline.
- If uncertain, use 5.

Hard output constraints (must follow exactly):
- Return ONLY valid JSON. No markdown. No code fences. No prose.
- JSON must contain exactly 3 keys: category, severity, consistency.
- Do not add extra keys.
- category must be one of {VALID_CATEGORIES}.
- severity must be one of {VALID_SEVERITIES}.
- consistency must be an integer from 1 to 10.
- If uncertain category -> "other". If uncertain severity -> "medium".

Report:
"{description}"
"""