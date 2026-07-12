"""Gemini-based Hebrew financial summarization for YouTube transcripts.

This module provides functions to summarize YouTube video transcripts using
Google's Gemini API with a Hebrew finance-focused prompt. It extracts:
- Stock tickers mentioned (in English symbols)
- Main financial claims (in Hebrew)
- Investment recommendations (in Hebrew)
- Risk flags and warnings (in Hebrew)
- Concise Hebrew summaries

Usage:
    >>> from youtube_telegram_bot.summarizer import summarize_transcript
    >>> result = summarize_transcript(transcript, "Video Title")
    >>> print(result["tickers"])  # List of stock symbols
    >>> print(result["recommendation"])  # Hebrew recommendation

Environment Variables:
    GEMINI_API_KEY: Required. Google Generative AI API key for Gemini models
"""

import os
import logging
import re
from typing import Dict, List, Tuple, Any, Optional

# Try to import google-generativeai, provide graceful error if missing
try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

# Hebrew finance prompt template
HEBREW_FINANCE_PROMPT = """You are an expert financial analyst. Analyze this investment/stock analysis transcript and provide a structured summary in Hebrew.

Return your analysis with this exact structure:

**Tickers:** [comma-separated stock symbols in English, e.g., META, TEVA, NICE.TA]
**Claim:** [The main financial claim or recommendation in 1-2 sentences, in Hebrew]
**Recommendation:** [BUY / HOLD / SELL / WATCH, in Hebrew]
**Risk Flag:** [Any risks or warnings mentioned in Hebrew, or "ללא" if none]
**Tips:** [Every concrete, actionable trading tip the speaker gives, one per line starting with "-". Capture SPECIFICS in Hebrew: exact price levels for entry/exit/stop, support and resistance levels, open gaps and their price targets, volume conditions for confirming a breakout, moving-average levels (e.g. ממוצע 150), chart patterns to watch, timing conditions ("wait for earnings", "wait for the Fed decision"), and general trading rules the speaker teaches. If a tip has a number in it, ALWAYS include the number. Write "ללא" if no actionable tips are given.]
**Summary:** [3–5 sentence summary of the analysis in Hebrew]

Keep the analysis concise and actionable. Use English ticker symbols (TEVA, NICE, ICL, etc.) when discussing stock names. Never invent price levels that are not in the transcript.

Transcript:
{transcript}
"""

# Gemini model configuration
# Models are tried in order — each has a separate free-tier daily quota,
# so if the primary is exhausted (429) the next one takes over
GEMINI_MODEL = "gemini-flash-latest"
GEMINI_FALLBACK_MODELS = ["gemini-flash-lite-latest", "gemini-2.0-flash"]
GEMINI_API_TIMEOUT = 30


def _initialize_gemini_client() -> Optional[Any]:
    """
    Initialize Gemini client with API key from environment.

    Returns:
        Configured Gemini GenerativeModel or None if initialization fails

    Raises:
        ValueError: If GEMINI_API_KEY is not set
    """
    if genai is None:
        raise ImportError("google-generativeai library is not installed")

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)

    # Try to create model - will fail gracefully if API key is invalid
    try:
        return genai.GenerativeModel(GEMINI_MODEL)
    except Exception as e:
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        raise


def _extract_field_value(response_text: str, field_name: str) -> str:
    """
    Extract a field value from structured response text.

    Handles multiple possible markers:
    - **FieldName:** (bold markdown)
    - **FieldName**: (bold markdown with colon)
    - FieldName: (plain text)

    Args:
        response_text: Full response text
        field_name: Name of the field to extract

    Returns:
        Extracted field value, or empty string if not found
    """
    patterns = [
        rf"\*\*{field_name}:\*\*\s*(.+?)(?=\*\*|$)",  # **FieldName:** ... next **
        rf"\*\*{field_name}\*\*\s*(.+?)(?=\*\*|$)",   # **FieldName** ... next **
        rf"{field_name}:\s*(.+?)(?=\n|$)",            # FieldName: ... newline
    ]

    for pattern in patterns:
        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Remove trailing markers and clean up
            value = re.sub(r"\*\*.*$", "", value).strip()
            if value:
                return value

    return ""


def _parse_gemini_response(response_text: str) -> Dict[str, Any]:
    """
    Parse structured Gemini API response.

    Extracts tickers, claim, recommendation, risk flag, and summary from
    the formatted response text. Robust against various formatting styles.

    Args:
        response_text: Raw response text from Gemini API

    Returns:
        Dictionary with keys: tickers (list), claim, recommendation,
        risk_flag, hebrew_summary

    Examples:
        >>> response = "**Tickers:** TEVA, NICE\\n**Claim:** Strong earnings..."
        >>> result = _parse_gemini_response(response)
        >>> result["tickers"]
        ['TEVA', 'NICE']
    """
    result = {
        "tickers": [],
        "claim": "",
        "recommendation": "",
        "risk_flag": "",
        "tips": [],
        "hebrew_summary": "",
    }

    # Extract each field
    tickers_text = _extract_field_value(response_text, "Tickers")
    if tickers_text:
        # Split by comma and/or newline, clean up
        ticker_list = re.split(r"[,\n]", tickers_text)
        tickers = [
            t.strip() for t in ticker_list
            if t.strip() and not t.strip().startswith("**")
        ]
        # Keep only strings that look like real ticker symbols
        # (uppercase letters, optional dots/digits, e.g. META or NICE.TA) —
        # models sometimes leak explanatory Hebrew text into this field
        tickers = [
            t for t in tickers
            if re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", t)
        ]
        result["tickers"] = tickers

    result["claim"] = _extract_field_value(response_text, "Claim")
    result["recommendation"] = _extract_field_value(response_text, "Recommendation")
    result["risk_flag"] = _extract_field_value(response_text, "Risk Flag")

    # Tips: multi-line field, one tip per "-" line
    tips_text = _extract_field_value(response_text, "Tips")
    if tips_text and tips_text.strip().lower() not in ("ללא", "none"):
        result["tips"] = [
            line.lstrip("-• ").strip()
            for line in tips_text.split("\n")
            if line.strip().lstrip("-• ").strip()
        ]

    # Summary field might be called "Summary" or have multi-line content
    summary = _extract_field_value(response_text, "Summary")
    if not summary:
        # Try alternative names
        summary = _extract_field_value(response_text, "Hebrew Summary")
    result["hebrew_summary"] = summary

    return result


def _estimate_tokens(text: str) -> int:
    """
    Estimate token count for text (rough approximation).

    For Gemini API, tokens are roughly 4 characters per token on average.
    This is a conservative estimate for cost tracking.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    # Rough estimate: 1 token per 4 characters
    # Conservative for safety (actual may vary)
    return max(1, len(text) // 4)


def _validate_summary_response(response: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate parsed summary response structure and content.

    Checks that response has required keys and at least minimal content.
    Does not fail on minimal responses, just warns.

    Args:
        response: Parsed response dictionary

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
    """
    required_keys = ["tickers", "claim", "recommendation", "risk_flag", "hebrew_summary"]

    # Check all required keys exist
    for key in required_keys:
        if key not in response:
            return False, f"Missing required key: {key}"

    # Check if we have at least some content
    has_content = (
        (response.get("tickers") and len(response["tickers"]) > 0) or
        (response.get("claim") and len(response["claim"]) > 0) or
        (response.get("recommendation") and len(response["recommendation"]) > 0)
    )

    if not has_content:
        # Don't fail - just log that it's minimal
        logger.warning("Summary response has minimal content")
        return True, None

    return True, None


def summarize_transcript(transcript: str, video_title: str) -> Dict[str, Any]:
    """
    Summarize a YouTube video transcript using Gemini API.

    Calls Gemini API with a Hebrew finance prompt to extract:
    - Stock tickers mentioned (English symbols)
    - Main financial claim (Hebrew)
    - Buy/Hold/Sell recommendation (Hebrew)
    - Risk flags and warnings (Hebrew)
    - Concise Hebrew summary (3-5 sentences)

    Uses Gemini 2.5 Flash model on the free tier (1M tokens/day).
    Estimated cost: $0 (free tier).

    Args:
        transcript: Raw video transcript text (may contain Hebrew)
        video_title: Title of the YouTube video (for logging/debugging)

    Returns:
        Dictionary with keys:
        - tickers: List[str] of stock symbols mentioned (or empty list)
        - claim: str. Main financial claim in Hebrew
        - recommendation: str. Investment action in Hebrew (קנייה/מכירה/החזקה)
        - risk_flag: str. Risk warnings in Hebrew or "ללא" if none
        - hebrew_summary: str. 3-5 sentence Hebrew summary
        - error: Optional[str]. Error message if summarization failed, None if successful

    Raises:
        No exceptions raised. All errors caught and returned in "error" field.

    Examples:
        >>> result = summarize_transcript("TEVA is up 5%...", "Stock Analysis")
        >>> print(result["tickers"])
        ['TEVA']
        >>> print(result["recommendation"])
        'קנייה'
        >>> if result["error"]:
        ...     print("Failed:", result["error"])
    """
    # Initialize with error default
    default_response = {
        "tickers": [],
        "claim": "",
        "recommendation": "",
        "risk_flag": "",
        "hebrew_summary": "",
        "error": None,
    }

    logger.info(f"Starting summarization for: {video_title}")

    try:
        # Handle empty transcript
        if not transcript or not transcript.strip():
            logger.warning(f"Empty transcript for video '{video_title}'")
            default_response["error"] = "Empty transcript"
            return default_response

        # Initialize Gemini client
        try:
            model = _initialize_gemini_client()
        except (ImportError, ValueError) as e:
            error_msg = f"Cannot initialize Gemini: {e}"
            logger.error(error_msg)
            default_response["error"] = str(e)
            return default_response

        # Prepare prompt and estimate tokens
        prompt = HEBREW_FINANCE_PROMPT.format(transcript=transcript)
        prompt_tokens = _estimate_tokens(prompt)
        logger.debug(
            f"Prompt size: {len(prompt)} chars (~{prompt_tokens} tokens). "
            f"Transcript: {len(transcript)} chars"
        )

        # Call Gemini API, falling back to alternate models on quota errors
        response = None
        last_error = None
        for model_name in [GEMINI_MODEL] + GEMINI_FALLBACK_MODELS:
            try:
                logger.debug(f"Calling Gemini API with model: {model_name}")
                response = genai.GenerativeModel(model_name).generate_content(prompt)
                if model_name != GEMINI_MODEL:
                    logger.info(f"Used fallback model: {model_name}")
                break
            except Exception as api_error:
                last_error = api_error
                if "429" in str(api_error) or "RESOURCE_EXHAUSTED" in str(api_error):
                    logger.warning(f"Model {model_name} quota exhausted, trying next")
                    continue
                break  # Non-quota error: don't burn other models' quota

        if response is None:
            error_msg = f"Gemini API call failed: {last_error}"
            logger.error(error_msg)
            default_response["error"] = error_msg
            return default_response

        if not response or not response.text:
            error_msg = "Empty response from Gemini API"
            logger.error(f"{error_msg} for '{video_title}'")
            default_response["error"] = error_msg
            return default_response

        # Parse and validate response
        response_tokens = _estimate_tokens(response.text)
        logger.debug(f"Response: {len(response.text)} chars (~{response_tokens} tokens)")

        parsed = _parse_gemini_response(response.text)

        # Validate response structure
        is_valid, validation_error = _validate_summary_response(parsed)
        if not is_valid:
            logger.warning(f"Invalid response structure for '{video_title}': {validation_error}")

        # Build successful response
        result = {
            "tickers": parsed["tickers"],
            "claim": parsed["claim"],
            "recommendation": parsed["recommendation"],
            "risk_flag": parsed["risk_flag"],
            "tips": parsed["tips"],
            "hebrew_summary": parsed["hebrew_summary"],
            "error": None,
        }

        # Log success with summary
        logger.info(
            f"Successfully summarized '{video_title}'. "
            f"Found {len(result['tickers'])} ticker(s): {result['tickers']}"
        )

        return result

    except Exception as e:
        error_msg = f"Unexpected error summarizing '{video_title}': {e}"
        logger.error(error_msg, exc_info=True)
        default_response["error"] = error_msg
        return default_response
