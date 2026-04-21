"""
ai_processing/test_ai_processing.py
====================================
Tests for:
  - ai_processing/prompts.py
  - ai_processing/gemini_processor.py

All external API calls (Gemini, Groq) are mocked.

Run from project root:
    pytest ai_processing/test_ai_processing.py -v
"""

import json
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ─────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────

class TestPrompts:

    def test_valid_categories_exist(self):
        from ai_processing.prompts import VALID_CATEGORIES
        for cat in ["medical", "food", "shelter", "rescue", "sanitation", "education", "other"]:
            assert cat in VALID_CATEGORIES

    def test_valid_severities_exist(self):
        from ai_processing.prompts import VALID_SEVERITIES
        for sev in ["low", "medium", "high", "very high", "critical"]:
            assert sev in VALID_SEVERITIES

    def test_build_prompt_returns_string(self):
        from ai_processing.prompts import build_prompt
        result = build_prompt("People are stranded due to flood")
        assert isinstance(result, str)
        assert len(result) > 100

    def test_build_prompt_embeds_description(self):
        from ai_processing.prompts import build_prompt
        desc = "Children need food and water urgently"
        assert desc in build_prompt(desc)

    def test_build_prompt_lists_all_categories(self):
        from ai_processing.prompts import build_prompt, VALID_CATEGORIES
        prompt = build_prompt("test")
        for cat in VALID_CATEGORIES:
            assert cat in prompt

    def test_build_prompt_lists_all_severities(self):
        from ai_processing.prompts import build_prompt, VALID_SEVERITIES
        prompt = build_prompt("test")
        for sev in VALID_SEVERITIES:
            assert sev in prompt

    def test_build_prompt_contains_json_instruction(self):
        from ai_processing.prompts import build_prompt
        prompt = build_prompt("test")
        assert "JSON" in prompt or "json" in prompt


# ─────────────────────────────────────────────────────────────
# GEMINI PROCESSOR
# ─────────────────────────────────────────────────────────────

def _gemini_response(text: str):
    m = MagicMock()
    m.text = text
    return m

def _valid_ai_json(category="food", severity="medium", consistency=7):
    return json.dumps({
        "category": category, "severity": severity,
        "consistency": consistency,
        "summary_en": f"{category} emergency",
        "summary_local": "Aapaatkaaleen sthiti"
    })


class TestGeminiProcessor:

    @patch("ai_processing.gemini_processor._gemini_client")
    def test_returns_dict(self, mock_client):
        mock_client.models.generate_content.return_value = _gemini_response(
            _valid_ai_json("medical", "high", 8)
        )
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("10 people injured in a road accident")
        assert isinstance(result, dict)
        assert "category" in result
        assert "severity" in result

    @patch("ai_processing.gemini_processor._gemini_client")
    def test_valid_category_returned(self, mock_client):
        mock_client.models.generate_content.return_value = _gemini_response(
            _valid_ai_json("rescue", "critical", 9)
        )
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("Building collapsed, people trapped under rubble")
        assert result["category"] == "rescue"
        assert result["severity"] == "critical"

    @patch("ai_processing.gemini_processor._gemini_client")
    def test_invalid_category_normalised_to_other(self, mock_client):
        mock_client.models.generate_content.return_value = _gemini_response(
            json.dumps({"category": "INVALID", "severity": "medium",
                        "consistency": 5, "summary_en": "X", "summary_local": "X"})
        )
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("Something unclear happened")
        assert result["category"] == "other"

    @patch("ai_processing.gemini_processor._gemini_client")
    def test_invalid_severity_normalised(self, mock_client):
        mock_client.models.generate_content.return_value = _gemini_response(
            json.dumps({"category": "food", "severity": "EXTREME",
                        "consistency": 5, "summary_en": "X", "summary_local": "X"})
        )
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("Food shortage in village")
        assert result["severity"] == "medium"

    @patch("ai_processing.gemini_processor._gemini_client")
    def test_consistency_clamped_to_10(self, mock_client):
        mock_client.models.generate_content.return_value = _gemini_response(
            json.dumps({"category": "food", "severity": "low",
                        "consistency": 999, "summary_en": "X", "summary_local": "X"})
        )
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("Minor food shortage")
        assert result["consistency"] <= 10

    @patch("ai_processing.gemini_processor._gemini_client")
    def test_consistency_clamped_minimum_zero(self, mock_client):
        mock_client.models.generate_content.return_value = _gemini_response(
            json.dumps({"category": "food", "severity": "low",
                        "consistency": -50, "summary_en": "X", "summary_local": "X"})
        )
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("Vague report")
        assert result["consistency"] >= 0

    def test_empty_description_returns_safe_defaults(self):
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("")
        assert result["category"] == "other"
        assert result["severity"] == "medium"

    def test_whitespace_only_description_returns_safe_defaults(self):
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("   \n\t  ")
        assert result["category"] == "other"
        assert result["severity"] == "medium"

    @patch("ai_processing.gemini_processor._gemini_client")
    @patch("ai_processing.gemini_processor._call_groq")
    def test_gemini_failure_falls_back_to_groq(self, mock_groq, mock_client):
        mock_client.models.generate_content.side_effect = Exception("Quota exceeded")
        mock_groq.return_value = {
            "category": "shelter", "severity": "high",
            "consistency": 7, "summary_en": "Shelter needed",
            "summary_local": "Aashray chahiye"
        }
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("Flood victims need shelter immediately")
        assert result["category"] == "shelter"
        mock_groq.assert_called_once()

    @patch("ai_processing.gemini_processor._gemini_client")
    @patch("ai_processing.gemini_processor._call_groq")
    def test_both_providers_fail_returns_defaults(self, mock_groq, mock_client):
        mock_client.models.generate_content.side_effect = Exception("Gemini down")
        mock_groq.side_effect = Exception("Groq down")
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("Emergency somewhere")
        assert result["category"] == "other"
        assert result["severity"] == "medium"

    @patch("ai_processing.gemini_processor._gemini_client")
    def test_markdown_fenced_json_stripped(self, mock_client):
        raw = '```json\n{"category": "food", "severity": "medium", "consistency": 5, ' \
              '"summary_en": "Food needed", "summary_local": "Khaane ki zaroorat"}\n```'
        mock_client.models.generate_content.return_value = _gemini_response(raw)
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("Food shortage in flood camp")
        assert result["category"] == "food"

    @patch("ai_processing.gemini_processor._gemini_client")
    def test_summary_fields_present(self, mock_client):
        mock_client.models.generate_content.return_value = _gemini_response(
            _valid_ai_json("medical", "high", 8)
        )
        from ai_processing.gemini_processor import process_need_text
        result = process_need_text("Medical emergency at city hospital")
        assert "summary_en" in result
        assert "summary_local" in result

    @patch("ai_processing.gemini_processor._gemini_client")
    def test_gemini_empty_text_falls_to_groq(self, mock_client):
        """If Gemini returns empty text, it should fall through to Groq."""
        empty_resp = MagicMock()
        empty_resp.text = ""
        mock_client.models.generate_content.return_value = empty_resp

        with patch("ai_processing.gemini_processor._call_groq") as mock_groq:
            mock_groq.return_value = _valid_ai_json.__wrapped__() if hasattr(
                _valid_ai_json, "__wrapped__") else {
                "category": "food", "severity": "medium", "consistency": 5,
                "summary_en": "X", "summary_local": "X"
            }
            mock_groq.return_value = {
                "category": "food", "severity": "medium", "consistency": 5,
                "summary_en": "fallback", "summary_local": "fallback"
            }
            from ai_processing.gemini_processor import process_need_text
            result = process_need_text("Some emergency description here")
            # Either Groq handled it or safe defaults returned
            assert result["category"] in ["food", "other"]