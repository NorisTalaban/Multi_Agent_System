"""
REFRESH PRICES — Free price updater using Yahoo Finance
========================================================
Updates prices for all tickers in the portfolio.
Uses yfinance (free, no API key, no rate limits).
Does NOT consume Alpha Vantage API calls.

Usage:
  python refresh_prices.py              # refresh all held tickers
  python refresh_prices.py AAPL META    # refresh specific tickers only

Install: pip install yfinance
"""

import os
import sys
import json
from datetime import date
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from logger import log, log_header, log_section, log_ok, log_err, log_info, log_warn

# ── CONFIG ───────────────────────────────────────────────────
TODAY     = date.today()
TODAY_STR = TODAY.strftime("%Y-%m-%d")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    log_err("Missing SUPABASE_URL or SUPABASE_KEY in .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ── GET PORTFOLIO TICKERS ────────────────────────────────────
def get_held_tickers():
    """Get all tickers with open positions."""
    try:
        result = supabase.table("portfolio_status") \
            .select("holdings").order("date", desc=True).limit(1).execute()
        if not result.data:
            return []
        holdings = result.data[0]["holdings"]
        if isinstance(holdings, str):
            holdings = json.loads(holdings or "{}")
        return [t for t, s in holdings.items() if float(s) > 0]
    except Exception as e:
        log_err(f"Cannot read portfolio: {e}")
        return []


# ── FETCH & SAVE PRICES ─────────────────────────────────────
def refresh_prices(tickers):
    """Fetch current prices via yfinance and save to daily_prices."""
    try:
        import yfinance as yf
    except ImportError:
        log_err("yfinance not installed — run: pip install yfinance")
        sys.exit(1)

    log_info(f"Fetching prices for {len(tickers)} ticker(s) via Yahoo Finance...")

    # yfinance can fetch multiple tickers in one call
    data = yf.download(tickers, period="1d", progress=False, group_by="ticker")

    refreshed = 0
    failed = []

    for ticker in tickers:
        try:
            if len(tickers) == 1:
                row = data
            else:
                row = data[ticker]

            if row.empty:
                log_warn(f"[{ticker}] No data from Yahoo Finance")
                failed.append(ticker)
                continue

            last = row.iloc[-1]
            price     = float(last["Close"])
            open_p    = float(last["Open"])
            high      = float(last["High"])
            low       = float(last["Low"])
            volume    = int(last["Volume"])

            # Calculate change_pct
            change_pct = round(((price - open_p) / open_p) * 100, 4) if open_p > 0 else 0

            supabase.table("daily_prices").upsert({
                "ticker":     ticker,
                "date":       TODAY_STR,
                "price":      round(price, 4),
                "open":       round(open_p, 4),
                "high":       round(high, 4),
                "low":        round(low, 4),
                "volume":     volume,
                "change_pct": change_pct,
            }, on_conflict="ticker,date").execute()

            log_ok(f"[{ticker}] ${price:.2f} ({change_pct:+.2f}%)")
            refreshed += 1

        except Exception as e:
            log_warn(f"[{ticker}] Error: {e}")
            failed.append(ticker)

    return refreshed, failed


# ── MAIN ─────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        tickers = [t.upper() for t in sys.argv[1:]]
        log_header(f"PRICE REFRESH  ·  {TODAY_STR}  ·  {', '.join(tickers)} (manual)")
    else:
        tickers = get_held_tickers()
        if not tickers:
            log_header(f"PRICE REFRESH  ·  {TODAY_STR}")
            log_info("No open positions — nothing to refresh")
            sys.exit(0)
        log_header(f"PRICE REFRESH  ·  {TODAY_STR}  ·  {len(tickers)} held ticker(s)")

    refreshed, failed = refresh_prices(tickers)

    log_header(f"REFRESH COMPLETE  ·  {refreshed}/{len(tickers)} updated  ·  0 API calls used")
    if failed:
        log_warn(f"Failed: {', '.join(failed)}")
