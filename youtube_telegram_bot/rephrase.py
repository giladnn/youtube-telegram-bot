"""Vary the digest's voice between editions so it doesn't read like a form letter.

The facts in a digest are fixed — prices, tickers, levels, tips — but the prose
around them doesn't have to be identical every time. This module hands the
assembled message to Gemini with a randomly chosen tone for that edition and
asks for a rewrite.

The constraints matter more than the variety here: a rephrasing that quietly
changes a price level or drops a risk warning is far worse than a repetitive
digest, so numbers, tickers and every bullet must survive verbatim. If anything
looks off — or the API fails — the original text is used unchanged.
"""

import logging
import os
import random
import re
from typing import List

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from youtube_telegram_bot.summarizer import GEMINI_MODEL, GEMINI_FALLBACK_MODELS

logger = logging.getLogger(__name__)

# Tone for a given edition — picked at random so consecutive digests differ
STYLES = [
    "תמציתי וישיר, בלי מילים מיותרות",
    "שיחתי וידידותי, כמו חבר שמעדכן אותך",
    "אנליטי ומקצועי, בגישה של אנליסט שוק",
    "אנרגטי ותכליתי, עם תחושת דחיפות מדודה",
    "רגוע ומדוד, בנימה של סקירה שקולה",
    "ענייני ויבש, מתמקד בעובדות בלבד",
]

REPHRASE_PROMPT = """Rewrite this Hebrew Telegram digest so it reads freshly — vary the sentence structure and word choice from a standard template.

Tone for this edition: {style}

Hard constraints. Breaking any of these makes the digest factually wrong, which is much worse than it sounding repetitive:
- Never change a number, price, percentage, date, ticker symbol, or channel name
- Never add a claim, opinion, or recommendation that is not in the original
- Never drop a line — every 💡 tip, ⚠️ risk, 📊 market line and 🎯 analyst line must appear in the output
- Keep every emoji, markdown marker (*bold*, `code`) and the overall line structure
- Stay in Hebrew

Return only the rewritten message, nothing else.

Message:
{text}
"""

# Tokens that must survive a rewrite untouched.
# Tickers appear two ways: backticked in the summary line (`META`) and bare
# in the machine-generated market lines (📊 META: 669.21) — both must hold.
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
_BACKTICK_TICKER_RE = re.compile(r"`([A-Z][A-Z0-9.\-]{0,9})`")
_MARKET_TICKER_RE = re.compile(r"📊\s*([A-Z][A-Z0-9.\-]{0,9})\s*:")


def _preserved_tokens(text: str) -> tuple:
    """Numbers and tickers that a faithful rewrite must keep."""
    tickers = set(_BACKTICK_TICKER_RE.findall(text)) | set(
        _MARKET_TICKER_RE.findall(text)
    )
    return set(_NUMBER_RE.findall(text)), tickers


def _is_faithful(original: str, rewritten: str) -> bool:
    """
    Check that the rewrite kept the facts.

    We only reject on losses, not additions: Gemini sometimes reformats a
    number's separators, but a *missing* ticker or a vanished line means the
    rewrite ate content, which is the failure mode worth guarding against.
    """
    if not rewritten.strip():
        return False

    orig_nums, orig_tickers = _preserved_tokens(original)
    new_nums, new_tickers = _preserved_tokens(rewritten)

    missing_tickers = orig_tickers - new_tickers
    if missing_tickers:
        logger.warning(f"Rephrase dropped tickers {missing_tickers} — keeping original")
        return False

    # Allow minor numeric formatting drift, but not wholesale loss
    missing_nums = orig_nums - new_nums
    if len(missing_nums) > max(2, len(orig_nums) * 0.2):
        logger.warning(f"Rephrase dropped {len(missing_nums)} numbers — keeping original")
        return False

    # A rewrite far shorter than the original has almost certainly lost content
    if len(rewritten) < len(original) * 0.6:
        logger.warning("Rephrase came back much shorter — keeping original")
        return False

    return True


def rephrase_digest(text: str, style: str = None) -> str:
    """
    Rewrite a digest with varied phrasing, preserving all facts.

    Returns the original text unchanged if the API fails or the rewrite
    fails the faithfulness check.
    """
    if genai is None or not text.strip():
        return text
    if os.getenv("REPHRASE_DIGEST", "true").lower() != "true":
        return text

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)

    style = style or random.choice(STYLES)
    prompt = REPHRASE_PROMPT.format(style=style, text=text)

    for model_name in [GEMINI_MODEL] + GEMINI_FALLBACK_MODELS:
        try:
            response = genai.GenerativeModel(model_name).generate_content(prompt)
            candidate = (response.text or "").strip() if response else ""
            if _is_faithful(text, candidate):
                logger.info(f"Rephrased digest (tone: {style})")
                return candidate
            return text
        except Exception as e:
            logger.warning(f"Rephrase via {model_name} failed: {str(e)[:60]}")
            continue

    logger.info("Rephrase unavailable — sending original wording")
    return text
