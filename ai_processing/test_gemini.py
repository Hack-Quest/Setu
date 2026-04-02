import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_processing.gemini_processor import process_need_text

# ── Test cases covering all categories and severities ──────────────────────

test_cases = [
    # (description, expected_category, expected_severity)
    ("A child has been seriously injured in a road accident near Main Chowk", "medical", "critical"),
    ("20 families have had no food for the past 2 days in Block C", "food", "high"),
    ("The community toilet is broken and overflowing onto the street", "sanitation", "medium"),
    ("We need notebooks and pens for the school kids next week", "education", "low"),
    ("Elderly man trapped under debris after building collapse", "rescue", "critical"),
    ("Minor skin rashes reported among children in the area", "medical", "medium"),
    ("No clean drinking water available in the village since 3 days", "medical", "critical"),
    ("Flood victims have no shelter, sleeping outside in rain", "shelter", "critical"),
    ("", "other", "medium"),  # edge case: empty input
]

# ── Runner ──────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("GEMINI PROCESSOR — TEST RESULTS")
print("="*60)

passed = 0
failed = 0

for description, exp_cat, exp_sev in test_cases:
    result = process_need_text(description)
    cat_ok = result["category"] == exp_cat
    sev_ok = result["severity"] == exp_sev
    status = "✅ PASS" if (cat_ok and sev_ok) else "⚠️  CHECK"

    if cat_ok and sev_ok:
        passed += 1
    else:
        failed += 1

    print(f"\n{status}")
    print(f"  Input   : {description[:60] or '[empty]'}")
    print(f"  Expected: category={exp_cat}, severity={exp_sev}")
    print(f"  Got     : category={result['category']}, severity={result['severity']}")

print("\n" + "="*60)
print(f"Results: {passed} passed, {failed} needs review")
print("="*60 + "\n")