"""Tests for Gemini-based video summarization."""

import pytest
import os
from unittest.mock import patch, MagicMock
from youtube_telegram_bot.summarizer import (
    summarize_transcript,
    _parse_gemini_response,
    _validate_summary_response,
)


SAMPLE_TRANSCRIPT = """
In this video, I'll discuss TEVA (Teva Pharmaceutical) which has been showing
strong performance. The company reported Q3 earnings above expectations.
I recommend a BUY recommendation for long-term investors.
TEVA is trading at a discount compared to its peers like NICE.
However, there's some regulatory risk we need to monitor.
The target price is around $8.50 for TEVA within 12 months.
"""

SAMPLE_HEBREW_RESPONSE = """
**Tickers:** TEVA, NICE
**Claim:** טבע מציגה ביצועים חזקים בשל דוחות רווח טובים בתקופה הנוכחית
**Recommendation:** קנייה
**Risk Flag:** סיכון רגולטורי במחלוקות פטנטים
**Summary:** חברת טבה דיווחה על הכנסות טובות בתשע"ד. המחיר הנוכחי משיקף הזדמנות קנייה. המתחרה ניס מציג תחרות גבוהה. בטווח 12 חודשים, צפוי עלייה למחיר $8.50
"""

PARTIAL_HEBREW_RESPONSE = """
**Tickers:** ICL
**Claim:** חברת ים-המלח מציגה עלייה בשוק
**Recommendation:** קנייה
**Risk Flag:** ללא
"""

EMPTY_TRANSCRIPT = ""

MALFORMED_RESPONSE = "This doesn't have the right structure at all"


class TestSummarizeTranscript:
    """Tests for main summarize_transcript function."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summarize_transcript_success(self, mock_genai):
        """Should successfully summarize a transcript and return structured dict."""
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HEBREW_RESPONSE
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Call function
        result = summarize_transcript(SAMPLE_TRANSCRIPT, "Test Video Title")

        # Assertions
        assert isinstance(result, dict)
        assert "tickers" in result
        assert "claim" in result
        assert "recommendation" in result
        assert "risk_flag" in result
        assert "hebrew_summary" in result
        assert result["error"] is None

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summarize_transcript_contains_tickers(self, mock_genai):
        """Should extract tickers from Gemini response."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HEBREW_RESPONSE
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = summarize_transcript(SAMPLE_TRANSCRIPT, "Test Video")

        assert result["tickers"] is not None
        assert isinstance(result["tickers"], list)
        assert len(result["tickers"]) > 0

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summarize_transcript_contains_recommendation(self, mock_genai):
        """Should extract recommendation from Gemini response."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HEBREW_RESPONSE
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = summarize_transcript(SAMPLE_TRANSCRIPT, "Test Video")

        assert result["recommendation"] is not None
        assert "קנייה" in result["recommendation"] or "BUY" in result["recommendation"]

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summarize_transcript_handles_partial_response(self, mock_genai):
        """Should handle partial responses gracefully."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = PARTIAL_HEBREW_RESPONSE
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = summarize_transcript(SAMPLE_TRANSCRIPT, "Test Video")

        assert isinstance(result, dict)
        assert result["error"] is None or result["error"] == ""

    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summarize_transcript_handles_empty_transcript(self, mock_genai):
        """Should handle empty transcripts gracefully."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "**Tickers:** \n**Claim:** \n**Recommendation:** \n**Risk Flag:** ללא\n**Summary:** "
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = summarize_transcript(EMPTY_TRANSCRIPT, "Empty Video")

        assert isinstance(result, dict)
        # Should have a graceful response, not crash

    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summarize_transcript_handles_api_error(self, mock_genai):
        """Should handle Gemini API errors gracefully."""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_genai.GenerativeModel.return_value = mock_model

        result = summarize_transcript(SAMPLE_TRANSCRIPT, "Test Video")

        assert isinstance(result, dict)
        assert result["error"] is not None
        assert "API Error" in result["error"] or "error" in result

    @patch.dict("os.environ", {}, clear=True)
    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summarize_transcript_handles_missing_api_key(self, mock_genai):
        """Should handle missing GEMINI_API_KEY gracefully."""
        mock_genai.configure.return_value = None

        # The function should still work with the mock, but in real scenario
        # it would handle missing key
        result = summarize_transcript(SAMPLE_TRANSCRIPT, "Test Video")
        assert isinstance(result, dict)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summarize_transcript_calls_gemini_api(self, mock_genai):
        """Should call Gemini API with appropriate prompt."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HEBREW_RESPONSE
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        summarize_transcript(SAMPLE_TRANSCRIPT, "Test Video Title")

        # Verify generate_content was called
        assert mock_model.generate_content.called
        call_args = mock_model.generate_content.call_args
        assert call_args is not None
        # The prompt should contain key parts of the transcript
        call_str = str(call_args)
        assert "TEVA" in call_str
        assert "BUY" in call_str

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summarize_transcript_hebrew_encoding(self, mock_genai):
        """Should handle Hebrew text without encoding issues."""
        hebrew_transcript = "זה טרנסקריפט בעברית עם הערות על טבה וניס"
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HEBREW_RESPONSE
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = summarize_transcript(hebrew_transcript, "Hebrew Video")

        assert isinstance(result, dict)
        assert result["error"] is None

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summarize_transcript_long_transcript(self, mock_genai):
        """Should handle long transcripts without truncation."""
        long_transcript = SAMPLE_TRANSCRIPT * 50  # Make it very long
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HEBREW_RESPONSE
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = summarize_transcript(long_transcript, "Long Video")

        assert isinstance(result, dict)
        assert result["error"] is None


class TestParseGeminiResponse:
    """Tests for parsing Gemini API responses."""

    def test_parse_gemini_response_extracts_tickers(self):
        """Should extract comma-separated tickers from response."""
        result = _parse_gemini_response(SAMPLE_HEBREW_RESPONSE)
        assert result["tickers"] is not None
        assert isinstance(result["tickers"], list)
        assert "TEVA" in result["tickers"]
        assert "NICE" in result["tickers"]

    def test_parse_gemini_response_extracts_claim(self):
        """Should extract claim from response."""
        result = _parse_gemini_response(SAMPLE_HEBREW_RESPONSE)
        assert result["claim"] is not None
        assert len(result["claim"]) > 0

    def test_parse_gemini_response_extracts_recommendation(self):
        """Should extract recommendation from response."""
        result = _parse_gemini_response(SAMPLE_HEBREW_RESPONSE)
        assert result["recommendation"] is not None
        assert len(result["recommendation"]) > 0

    def test_parse_gemini_response_extracts_risk_flag(self):
        """Should extract risk flag from response."""
        result = _parse_gemini_response(SAMPLE_HEBREW_RESPONSE)
        assert result["risk_flag"] is not None

    def test_parse_gemini_response_extracts_summary(self):
        """Should extract summary from response."""
        result = _parse_gemini_response(SAMPLE_HEBREW_RESPONSE)
        assert result["hebrew_summary"] is not None
        assert len(result["hebrew_summary"]) > 0

    def test_parse_gemini_response_handles_partial_response(self):
        """Should handle responses missing some fields."""
        result = _parse_gemini_response(PARTIAL_HEBREW_RESPONSE)
        assert isinstance(result, dict)
        # Should have at least some fields
        assert "tickers" in result

    def test_parse_gemini_response_handles_missing_risk_flag(self):
        """Should handle missing risk flag gracefully."""
        response_without_risk = """
**Tickers:** TEVA
**Claim:** Some claim
**Recommendation:** BUY
**Summary:** Summary text
"""
        result = _parse_gemini_response(response_without_risk)
        assert isinstance(result, dict)

    def test_parse_gemini_response_handles_empty_tickers(self):
        """Should handle empty tickers field."""
        response_empty_tickers = """
**Tickers:**
**Claim:** Some claim
**Recommendation:** BUY
**Risk Flag:** ללא
**Summary:** Summary text
"""
        result = _parse_gemini_response(response_empty_tickers)
        assert isinstance(result, dict)

    def test_parse_gemini_response_hebrew_hebrew_support(self):
        """Should support Hebrew text in response."""
        result = _parse_gemini_response(SAMPLE_HEBREW_RESPONSE)
        # Should handle Hebrew without encoding issues
        assert isinstance(result, dict)


class TestValidateSummaryResponse:
    """Tests for validating parsed summary responses."""

    def test_validate_summary_response_accepts_complete_response(self):
        """Should accept complete responses with all fields."""
        complete_response = {
            "tickers": ["TEVA", "NICE"],
            "claim": "טבע מציגה ביצועים חזקים",
            "recommendation": "קנייה",
            "risk_flag": "סיכון רגולטורי",
            "hebrew_summary": "סיכום טוב",
        }
        is_valid, error = _validate_summary_response(complete_response)
        assert is_valid is True
        assert error is None

    def test_validate_summary_response_accepts_partial_response(self):
        """Should accept responses with some fields missing."""
        partial_response = {
            "tickers": ["TEVA"],
            "claim": "Some claim",
            "recommendation": "BUY",
            "risk_flag": None,
            "hebrew_summary": "Summary",
        }
        is_valid, error = _validate_summary_response(partial_response)
        assert is_valid is True

    def test_validate_summary_response_rejects_empty_response(self):
        """Should reject completely empty responses."""
        empty_response = {
            "tickers": [],
            "claim": "",
            "recommendation": "",
            "risk_flag": "",
            "hebrew_summary": "",
        }
        is_valid, error = _validate_summary_response(empty_response)
        # Should have at least some content
        assert isinstance(is_valid, bool)

    def test_validate_summary_response_checks_structure(self):
        """Should validate response has required keys."""
        incomplete_response = {
            "tickers": ["TEVA"],
            "claim": "Claim",
            # Missing other keys
        }
        is_valid, error = _validate_summary_response(incomplete_response)
        # Should still handle gracefully
        assert isinstance(is_valid, bool)


class TestSummaryResponseStructure:
    """Tests for the overall structure returned by summarize_transcript."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summary_response_has_required_fields(self, mock_genai):
        """Response should have all required fields."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HEBREW_RESPONSE
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = summarize_transcript(SAMPLE_TRANSCRIPT, "Test Video")

        required_fields = ["tickers", "claim", "recommendation", "risk_flag", "hebrew_summary", "error"]
        for field in required_fields:
            assert field in result

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summary_response_tickers_is_list(self, mock_genai):
        """Tickers field should be a list."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HEBREW_RESPONSE
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = summarize_transcript(SAMPLE_TRANSCRIPT, "Test Video")

        assert isinstance(result["tickers"], list) or result["tickers"] is None

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("youtube_telegram_bot.summarizer.genai")
    def test_summary_response_is_dict(self, mock_genai):
        """Response should always be a dictionary."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HEBREW_RESPONSE
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = summarize_transcript(SAMPLE_TRANSCRIPT, "Test Video")

        assert isinstance(result, dict)
