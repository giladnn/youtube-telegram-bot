"""Fetch price + 150-day moving average per ticker from Yahoo Finance (free, no key)."""

import logging
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
YAHOO_TIMEOUT = 10
MA_WINDOW = 150

# Yahoo requires a browser-like User-Agent
_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def get_ticker_stats(ticker: str) -> Optional[Dict[str, float]]:
    """
    Fetch current price and 150-day simple moving average for a ticker.

    Args:
        ticker: Stock symbol (e.g. "META", "NICE.TA")

    Returns:
        Dict with keys: price, ma150, above_ma (bool) — or None on failure
    """
    if requests is None:
        return None

    try:
        response = requests.get(
            YAHOO_CHART_URL.format(ticker=ticker),
            params={"range": "1y", "interval": "1d"},
            headers=_HEADERS,
            timeout=YAHOO_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()["chart"]["result"][0]

        closes = [
            c for c in result["indicators"]["quote"][0]["close"] if c is not None
        ]
        if len(closes) < MA_WINDOW:
            logger.debug(f"{ticker}: only {len(closes)} closes, need {MA_WINDOW}")
            return None

        price = result["meta"].get("regularMarketPrice") or closes[-1]
        ma150 = sum(closes[-MA_WINDOW:]) / MA_WINDOW

        return {
            "price": round(price, 2),
            "ma150": round(ma150, 2),
            "above_ma": price >= ma150,
        }
    except Exception as e:
        logger.debug(f"Market data unavailable for {ticker}: {e}")
        return None


def enrich_tickers(tickers: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Fetch stats for a list of tickers, skipping any that fail.

    Israeli tickers without an exchange suffix are retried with ".TA".

    Args:
        tickers: List of ticker symbols

    Returns:
        Mapping of ticker -> stats dict (only successful lookups included)
    """
    stats = {}
    for ticker in tickers:
        data = get_ticker_stats(ticker)
        if data is None and "." not in ticker:
            # Might be a Tel Aviv symbol without its suffix
            data = get_ticker_stats(f"{ticker}.TA")
        if data:
            stats[ticker] = data
            logger.info(
                f"  {ticker}: price {data['price']}, MA150 {data['ma150']} "
                f"({'above' if data['above_ma'] else 'below'})"
            )
    return stats
