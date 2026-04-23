"""
ai_processing/test_ai_processing.py
==================================
Unit tests for strict prompt schema and robust processor behavior.

These tests are fully offline and use mocks for all provider interactions.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _gemini_response(text: str):
    """Create a mock Gemini response with the same surface used in production."""
    response = MagicMock()
    response.text = text
    return response


def _as_json(category: str = "supplies", severity: str = "medium", consistency: int = 7) -> str:
    """Return strict JSON string that matches the processor output contract."""
    return json.dumps(
        {
            "category": category,
            "severity": severity,
            "consistency": consistency,
        }
    )


class TestPrompts:
    """Prompt-level assertions to prevent schema and category drift."""

    def test_valid_categories_are_strict(self):
        from ai_processing.prompts import VALID_CATEGORIES

        assert VALID_CATEGORIES == ["medical", "rescue", "supplies", "logistics", "other"]

    def test_valid_severities_are_five_levels(self):
        from ai_processing.prompts import VALID_SEVERITIES

        assert VALID_SEVERITIES == ["low", "medium", "high", "very high", "critical"]

    def test_prompt_requires_exact_three_json_keys(self):
        from ai_processing.prompts import build_prompt

        prompt = build_prompt("Driver is needed to transport supplies at old age home")
        assert "exactly 3 keys" in prompt.lower()
        assert "category" in prompt
        assert "severity" in prompt
        assert "consistency" in prompt

    def test_prompt_contains_driver_logistics_guardrail(self):
        from ai_processing.prompts import build_prompt

        prompt = build_prompt("driver needed")
        assert "driver needed" in prompt.lower()
        assert "must be logistics" in prompt.lower()


class TestGeminiProcessor:
    """Processor behavior tests for parsing, validation, and fallback safety."""

    @patch("ai_processing.gemini_processor._gemini_model")
    def test_successful_gemini_parse_returns_strict_schema(self, mock_model):
        mock_model.generate_content.return_value = _gemini_response(
            _as_json("medical", "high", 8)
        )

        from ai_processing.gemini_processor import process_need_text

        result = process_need_text("Multiple injuries after bus accident")
        assert result == {"category": "medical", "severity": "high", "consistency": 8}

    @patch("ai_processing.gemini_processor._gemini_model")
    def test_markdown_wrapped_json_is_safely_parsed(self, mock_model):
        raw = """```json
        {
          "category": "supplies",
          "severity": "medium",
          "consistency": 6
        }
        ```"""
        mock_model.generate_content.return_value = _gemini_response(raw)

        from ai_processing.gemini_processor import process_need_text

        result = process_need_text("Need food and drinking water")
        assert result["category"] == "supplies"
        assert result["severity"] == "medium"
        assert result["consistency"] == 6

    @patch("ai_processing.gemini_processor._gemini_model")
    def test_invalid_category_is_normalized_to_other(self, mock_model):
        mock_model.generate_content.return_value = _gemini_response(
            _as_json("transportation", "medium", 7)
        )

        from ai_processing.gemini_processor import process_need_text

        result = process_need_text("Need transport coordination")
        assert result["category"] == "other"

    @patch("ai_processing.gemini_processor._gemini_model")
    def test_invalid_severity_is_normalized_to_medium(self, mock_model):
        raw = json.dumps(
            {
                "category": "logistics",
                "severity": "urgent",
                "consistency": 7,
            }
        )
        mock_model.generate_content.return_value = _gemini_response(raw)

        from ai_processing.gemini_processor import process_need_text

        result = process_need_text("Driver required for supply movement")
        assert result["severity"] == "medium"

    @patch("ai_processing.gemini_processor._gemini_model")
    def test_consistency_is_clamped_to_1_to_10(self, mock_model):
        from ai_processing.gemini_processor import process_need_text

        mock_model.generate_content.return_value = _gemini_response(
            _as_json("rescue", "critical", 99)
        )
        high_result = process_need_text("People trapped in debris")
        assert high_result["consistency"] == 10

        mock_model.generate_content.return_value = _gemini_response(
            _as_json("rescue", "critical", -8)
        )
        low_result = process_need_text("People trapped in debris")
        assert low_result["consistency"] == 1

    @patch("ai_processing.gemini_processor._gemini_model")
    @patch("ai_processing.gemini_processor._call_groq")
    def test_gemini_failure_falls_back_to_groq(self, mock_call_groq, mock_model):
        mock_model.generate_content.side_effect = Exception("Gemini quota exceeded")
        mock_call_groq.return_value = {
            "category": "logistics",
            "severity": "medium",
            "consistency": 7,
        }

        from ai_processing.gemini_processor import process_need_text

        result = process_need_text("Driver needed to move supplies")
        assert result["category"] == "logistics"
        assert result["severity"] == "medium"
        mock_call_groq.assert_called_once()

    @patch("ai_processing.gemini_processor._gemini_model")
    @patch("ai_processing.gemini_processor._call_groq")
    def test_if_both_providers_fail_returns_safe_defaults(self, mock_call_groq, mock_model):
        mock_model.generate_content.side_effect = Exception("Gemini down")
        mock_call_groq.side_effect = Exception("Groq down")

        from ai_processing.gemini_processor import process_need_text

        result = process_need_text("Unknown emergency")
        assert result == {"category": "other", "severity": "medium", "consistency": 5}

    def test_empty_input_returns_safe_defaults_with_error(self):
        from ai_processing.gemini_processor import process_need_text

        result = process_need_text("")
        assert result["category"] == "other"
        assert result["severity"] == "medium"
        assert result["consistency"] == 5
        assert result.get("error") == "empty input"

    @patch("ai_processing.gemini_processor._gemini_model")
    def test_edge_case_driver_old_age_home_is_not_medical(self, mock_model):
        """Required edge case from the bug report."""
        mock_model.generate_content.return_value = _gemini_response(
            _as_json("logistics", "low", 8)
        )

        from ai_processing.gemini_processor import process_need_text

        result = process_need_text("Driver is needed to transport supplies at old age home")
        assert result["category"] == "logistics"
        assert result["category"] != "medical"
        assert result["severity"] in ["low", "medium"]

    @patch("ai_processing.gemini_processor._gemini_model")
    def test_edge_case_collapse_trapped_is_rescue_critical(self, mock_model):
        """Required edge case for high-stakes emergency classification."""
        mock_model.generate_content.return_value = _gemini_response(
            _as_json("rescue", "critical", 9)
        )

        from ai_processing.gemini_processor import process_need_text

        result = process_need_text("Building collapsed, 3 people trapped")
        assert result["category"] == "rescue"
        assert result["severity"] == "critical"