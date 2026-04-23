"""
ai_processing/test_gemini.py
============================
Focused tests for strict classification behavior in gemini_processor.

All provider calls are mocked. No real Gemini or Groq API requests are made.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _gemini_response(text: str):
    """Create a minimal Gemini-like response object with a .text field."""
    response = MagicMock()
    response.text = text
    return response


def _classification_json(category: str, severity: str, consistency: int = 7) -> str:
    """Return strict JSON payload matching production schema."""
    return json.dumps(
        {
            "category": category,
            "severity": severity,
            "consistency": consistency,
        }
    )


@patch("ai_processing.gemini_processor._gemini_model")
def test_driver_transport_is_logistics_not_medical(mock_gemini_model):
    """Regression test: transport/driver requests must stay in logistics category."""
    mock_gemini_model.generate_content.return_value = _gemini_response(
        _classification_json("logistics", "medium", 8)
    )

    from ai_processing.gemini_processor import process_need_text

    result = process_need_text("Driver is needed to transport supplies at old age home")
    assert result["category"] == "logistics"
    assert result["category"] != "medical"
    assert result["severity"] in ["low", "medium"]


@patch("ai_processing.gemini_processor._gemini_model")
def test_building_collapse_trapped_is_rescue_critical(mock_gemini_model):
    """High-stakes emergency should map to rescue + critical."""
    mock_gemini_model.generate_content.return_value = _gemini_response(
        _classification_json("rescue", "critical", 9)
    )

    from ai_processing.gemini_processor import process_need_text

    result = process_need_text("Building collapsed, 3 people trapped")
    assert result["category"] == "rescue"
    assert result["severity"] == "critical"


@patch("ai_processing.gemini_processor._gemini_model")
def test_severity_uses_new_five_level_scale(mock_gemini_model):
    """Model output should support and preserve the new 5-level severity values."""
    accepted = ["low", "medium", "high", "very high", "critical"]

    from ai_processing.gemini_processor import process_need_text

    for severity in accepted:
        mock_gemini_model.generate_content.return_value = _gemini_response(
            _classification_json("supplies", severity, 6)
        )
        result = process_need_text(f"Test severity: {severity}")
        assert result["severity"] == severity


@patch("ai_processing.gemini_processor._gemini_model")
def test_processor_returns_exact_three_keys(mock_gemini_model):
    """Production contract should return only category, severity, and consistency."""
    mock_gemini_model.generate_content.return_value = _gemini_response(
        _classification_json("medical", "high", 8)
    )

    from ai_processing.gemini_processor import process_need_text

    result = process_need_text("Need first aid and medicines")
    assert sorted(result.keys()) == ["category", "consistency", "severity"]