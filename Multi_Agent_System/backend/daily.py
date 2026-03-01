"""
DAILY - Single entry point for the entire Agentic Finance system.
"""

import os
import sys
import requests
import time
from datetime import date, timedelta
from dotenv import load_dotenv
from supabase import create_client
from anthropic import Anthropic

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from logger import log, log_header, log_section, log_ok, log_err, log_info, log_warn, log_metric

# ── CONFIG ───────────────────────────────────────────────────
TICKERS      = [t.upper() for t in sys.argv[1:]] if len(sys.argv) > 1 else ["META"]
TODAY        = date.today()
TODAY_STR    = TODAY.strftime("%Y-%m-%d")
HORIZON_DAYS = {"1_week": 7, "1_month": 30, "1_quarter": 90}
FREQ         = {"price": 1, "news": 1, "fundamentals": 7, "income": 90, "macro": 30}
BASE_AV_URL  = "https://www.alphavantage.co/query"

API_KEY      = os.getenv("ALPHA_VANTAGE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([API_KEY, SUPABASE_URL, SUPABASE_KEY, os.getenv("ANTHROPIC_API_KEY")]):
    log.error("Missing keys in .env — check ALPHA_VANTAGE_KEY, SUPABASE_URL, SUPABASE_KEY, ANTHROPIC_API_KEY")
    sys.exit(1)

# Single shared Supabase client
supabase  = create_client(SUPABASE_URL, SUPABASE_KEY)
api_calls = 0


# ============================================================
# STEP 1 — UPDATE ACTUALS
# Compare past predictions with real prices
# ============================================================
def update_actuals():
    """Resolve ALL pending predictions across all tickers."""
    log_section("Step 1 — Update Actuals [ALL TICKERS]")
    try:
        predictions = supabase.table("predictions") \
            .select("*").is_("price_actual", "null").execute()
    except Exception as e:
        log_err(f"Cannot fetch predictions: {e}")
        return

    if not predictions.data:
        log_info("No pending predictions to update")
        return

    log_info(f"Found {len(predictions.data)} pending predictions")

    updated = 0
    skipped = 0
    for pred in predictions.data:
        pred_date   = date.fromisoformat(pred["date"])
        target_date = pred_date + timedelta(days=HORIZON_DAYS.get(pred["horizon"], 0))
        pred_ticker = pred["ticker"]

        if target_date > TODAY:
            skipped += 1
            continue

        try:
            result = supabase.table("daily_prices") \
                .select("price, date").eq("ticker", pred_ticker) \
                .lte("date", target_date.strftime("%Y-%m-%d")) \
                .order("date", desc=True).limit(1).execute()
        except Exception as e:
            log_err(f"Price lookup error ({pred_ticker}/{pred['horizon']}): {e}")
            continue

        if not result.data:
            continue

        actual_price = float(result.data[0]["price"])
        actual_date  = result.data[0]["date"]
        price_target = pred.get("price_target")
        error_pct    = round(((price_target - actual_price) / actual_price) * 100, 2) \
                       if price_target and actual_price else None

        try:
            supabase.table("predictions").update({
                "price_actual": actual_price,
                "error_pct":    error_pct
            }).eq("id", pred["id"]).execute()

            log_ok(f"[{pred_ticker}/{pred['horizon']}] predicted=${price_target} | actual=${actual_price} ({actual_date}) | error={error_pct}%")
            log_metric("prediction_resolved", {
                "ticker": pred_ticker, "horizon": pred["horizon"],
                "price_target": price_target, "price_actual": actual_price,
                "error_pct": error_pct,
            })
            updated += 1
        except Exception as e:
            log_err(f"Update error ({pred_ticker}/{pred['horizon']}): {e}")

    log_ok(f"Resolved {updated} predictions | {skipped} still pending")


# ============================================================
# STEP 2 — COLLECT DATA
# Fetch fresh market data respecting frequency limits
# ============================================================
def _av_wait():
    time.sleep(12)

def _should_collect(ticker, data_type):
    try:
        query = supabase.table("collection_log").select("last_run")
        query = query.eq("ticker", ticker) if ticker else query.is_("ticker", "null")
        result = query.eq("data_type", data_type).execute()
        if not result.data:
            return True
        days_passed = (TODAY - date.fromisoformat(result.data[0]["last_run"])).days
        freq = FREQ.get(data_type, 1)
        if days_passed < freq:
            log_info(f"[{data_type}] Fresh — {days_passed}d ago (every {freq}d)")
            return False
        return True
    except Exception as e:
        log_warn(f"[should_collect] Error: {e} — collecting anyway")
        return True

def _mark_collected(ticker, data_type):
    try:
        row = {"data_type": data_type, "last_run": TODAY_STR}
        if ticker:
            row["ticker"] = ticker
        supabase.table("collection_log").upsert(row, on_conflict="ticker,data_type").execute()
    except Exception as e:
        log_err(f"[collection_log] {e}")

def _call_av(params):
    global api_calls
    params["apikey"] = API_KEY
    try:
        response = requests.get(BASE_AV_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        api_calls += 1
        if "Error Message" in data:
            log_warn(f"[av] {data['Error Message']}")
            return None
        if "Note" in data or "Information" in data:
            log_warn(f"[av] Rate limit hit")
            return None
        return data
    except requests.RequestException as e:
        log_err(f"[av] Request failed: {e}")
        return None
    except ValueError as e:
        log_err(f"[av] JSON decode error: {e}")
        return None

def _collect_price(ticker):
    data = _call_av({"function": "GLOBAL_QUOTE", "symbol": ticker})
    if not data or not data.get("Global Quote", {}).get("05. price"):
        log_warn(f"[price] No data for {ticker}")
        return False
    q = data["Global Quote"]
    try:
        supabase.table("daily_prices").upsert({
            "ticker": ticker, "date": TODAY_STR,
            "price":      float(q.get("05. price", 0)),
            "open":       float(q.get("02. open", 0)),
            "high":       float(q.get("03. high", 0)),
            "low":        float(q.get("04. low", 0)),
            "volume":     int(q.get("06. volume", 0)),
            "change_pct": float(q.get("10. change percent", "0%").replace("%", ""))
        }, on_conflict="ticker,date").execute()
        log_ok(f"[price] ${q['05. price']} | {q['10. change percent']}")
        _mark_collected(ticker, "price")
        return True
    except Exception as e:
        log_err(f"[price] DB error: {e}")
        return False

def _collect_news(ticker):
    data = _call_av({"function": "NEWS_SENTIMENT", "tickers": ticker, "limit": "50"})
    if not data or "feed" not in data:
        log_warn(f"[news] No data for {ticker}")
        return False

    articles_to_save = []
    for article in data["feed"]:
        for ts in article.get("ticker_sentiment", []):
            if ts.get("ticker") != ticker or float(ts.get("relevance_score", 0)) < 0.5:
                continue
            articles_to_save.append({
                "ticker": ticker, "date": TODAY_STR,
                "title":           article.get("title", "")[:500],
                "source":          article.get("source", ""),
                "sentiment_label": ts.get("ticker_sentiment_label", ""),
                "sentiment_score": float(ts.get("ticker_sentiment_score", 0)),
                "relevance_score": float(ts.get("relevance_score", 0))
            })

    if not articles_to_save:
        log_info("[news] No relevant articles found")
        return False

    # Keep only top 7 by relevance score
    articles_to_save = sorted(articles_to_save, key=lambda x: x["relevance_score"], reverse=True)[:7]

    try:
        supabase.table("news_sentiment").delete()\
            .eq("ticker", ticker).eq("date", TODAY_STR).execute()
    except Exception as e:
        log_warn(f"[news] Could not clear old entries: {e}")

    saved = 0
    for article in articles_to_save:
        try:
            supabase.table("news_sentiment").insert(article).execute()
            saved += 1
        except Exception as e:
            log_warn(f"[news] Insert error: {e}")

    log_ok(f"[news] {saved} articles saved")
    if saved > 0:
        _mark_collected(ticker, "news")
    return saved > 0

def _collect_fundamentals(ticker):
    data = _call_av({"function": "OVERVIEW", "symbol": ticker})
    if not data or "Symbol" not in data:
        log_warn(f"[fundamentals] No data for {ticker}")
        return False
    try:
        supabase.table("fundamentals").upsert({
            "ticker": ticker, "date": TODAY_STR,
            "pe_ratio":      float(data.get("PERatio", 0) or 0),
            "forward_pe":    float(data.get("ForwardPE", 0) or 0),
            "eps":           float(data.get("EPS", 0) or 0),
            "profit_margin": float(data.get("ProfitMargin", 0) or 0),
            "week_52_high":  float(data.get("52WeekHigh", 0) or 0),
            "week_52_low":   float(data.get("52WeekLow", 0) or 0),
            "ma_50":         float(data.get("50DayMovingAverage", 0) or 0),
            "ma_200":        float(data.get("200DayMovingAverage", 0) or 0)
        }, on_conflict="ticker,date").execute()
        log_ok(f"[fundamentals] P/E: {data.get('PERatio')} | EPS: {data.get('EPS')}")
        _mark_collected(ticker, "fundamentals")
        return True
    except Exception as e:
        log_err(f"[fundamentals] DB error: {e}")
        return False

def _collect_income(ticker):
    data = _call_av({"function": "INCOME_STATEMENT", "symbol": ticker})
    if not data or "annualReports" not in data:
        log_warn(f"[income] No data for {ticker}")
        return False
    r = data["annualReports"][0]
    try:
        supabase.table("income_statements").upsert({
            "ticker": ticker, "date": TODAY_STR,
            "period":           r.get("fiscalDateEnding", ""),
            "total_revenue":    int(r.get("totalRevenue", 0) or 0),
            "gross_profit":     int(r.get("grossProfit", 0) or 0),
            "operating_income": int(r.get("operatingIncome", 0) or 0),
            "net_income":       int(r.get("netIncome", 0) or 0),
            "ebitda":           int(r.get("ebitda", 0) or 0)
        }, on_conflict="ticker,date").execute()
        log_ok(f"[income] Revenue: ${int(r.get('totalRevenue', 0) or 0):,}")
        _mark_collected(ticker, "income")
        return True
    except Exception as e:
        log_err(f"[income] DB error: {e}")
        return False

def _collect_macro():
    endpoints = [
        {"function": "FEDERAL_FUNDS_RATE", "name": "FEDERAL_FUNDS_RATE", "params": {"interval": "monthly"}},
        {"function": "CPI",                "name": "CPI",                "params": {"interval": "monthly"}},
        {"function": "UNEMPLOYMENT",       "name": "UNEMPLOYMENT",       "params": {}},
        {"function": "TREASURY_YIELD",     "name": "TREASURY_YIELD_10Y", "params": {"interval": "monthly", "maturity": "10year"}},
        {"function": "RETAIL_SALES",       "name": "RETAIL_SALES",       "params": {}},
    ]
    success = 0
    for i, ep in enumerate(endpoints):
        data = _call_av({"function": ep["function"], **ep["params"]})
        if data and "data" in data:
            for point in data["data"][:3]:
                if point.get("value") and point["value"] != ".":
                    try:
                        supabase.table("macro_data").upsert(
                            {"indicator": ep["name"], "date": point["date"], "value": float(point["value"])},
                            on_conflict="indicator,date"
                        ).execute()
                    except Exception as e:
                        log_warn(f"[macro] DB error ({ep['name']}): {e}")
            log_ok(f"[macro] {ep['name']}")
            success += 1
        else:
            log_warn(f"[macro] {ep['name']}: no data")
        if i < len(endpoints) - 1:
            _av_wait()

    if success > 0:
        _mark_collected(None, "macro")
    return success > 0

def collect_data(ticker):
    """Collect market data for a ticker. Returns True if minimum data is available."""
    log_section(f"Step 2 — Collect Data [{ticker}]")

    to_collect = []
    if _should_collect(ticker, "price"):        to_collect.append("price")
    if _should_collect(ticker, "news"):         to_collect.append("news")
    if _should_collect(ticker, "fundamentals"): to_collect.append("fundamentals")
    if _should_collect(ticker, "income"):       to_collect.append("income")
    if _should_collect(None,   "macro"):        to_collect.append("macro")

    if not to_collect:
        log_ok("All data is up to date")
        return True  # data already fresh

    log_info(f"Collecting: {', '.join(to_collect)}")

    results = {}
    handlers = {
        "price":        lambda: _collect_price(ticker),
        "news":         lambda: _collect_news(ticker),
        "fundamentals": lambda: _collect_fundamentals(ticker),
        "income":       lambda: _collect_income(ticker),
        "macro":        _collect_macro,
    }

    for i, dt in enumerate(to_collect):
        results[dt] = handlers[dt]()
        if i < len(to_collect) - 1 and dt != "macro":
            _av_wait()

    log_info(f"API calls used: {api_calls}/25")
    return True


def validate_data(ticker):
    """
    DATA GATE — Verify minimum data exists before running agents.
    Returns (ok: bool, missing: list of str).
    
    Minimum requirements:
      - Price data: at least 1 recent price (CRITICAL — blocks pipeline)
      - News OR Fundamentals: at least one available (WARNING — continues with caution)
    """
    log_section(f"Data Gate — Validating [{ticker}]")
    missing  = []
    warnings = []

    # CRITICAL: Price is mandatory — agents can't function without it
    try:
        result = supabase.table("daily_prices") \
            .select("price,date").eq("ticker", ticker) \
            .order("date", desc=True).limit(1).execute()
        if not result.data:
            missing.append("price")
        else:
            price_date = result.data[0]["date"]
            days_old = (TODAY - date.fromisoformat(price_date)).days
            if days_old > 5:
                warnings.append(f"price is {days_old} days old ({price_date})")
    except Exception as e:
        missing.append(f"price (error: {e})")

    # WARNING: News — useful but not critical
    try:
        result = supabase.table("news_sentiment") \
            .select("id", count="exact").eq("ticker", ticker).execute()
        if not result.count or result.count == 0:
            warnings.append("no news data available")
    except Exception:
        warnings.append("news check failed")

    # WARNING: Fundamentals — useful but not critical
    try:
        result = supabase.table("fundamentals") \
            .select("id").eq("ticker", ticker).limit(1).execute()
        if not result.data:
            warnings.append("no fundamentals data")
    except Exception:
        warnings.append("fundamentals check failed")

    # Report
    if missing:
        for m in missing:
            log_err(f"MISSING CRITICAL: {m}")
        log_err(f"Pipeline BLOCKED for {ticker} — cannot run agents without: {', '.join(missing)}")
        log_metric("data_gate_blocked", {"ticker": ticker, "missing": missing})
        return False, missing

    if warnings:
        for w in warnings:
            log_warn(f"{w}")
        log_info("Proceeding with available data (non-critical gaps)")
    else:
        log_ok("All data validated")

    return True, []


# ============================================================
# STEP 3 — RUN AGENTS
# ============================================================
def run_agents(ticker):
    log_section(f"Step 3 — Run Agents [{ticker}]")

    from agents.agent_1_sentiment   import SentimentAgent
    from agents.agent_2_technical   import TechnicalAgent
    from agents.agent_3_fundamental import FundamentalAgent
    from agents.agent_4_macro       import MacroAgent
    from agents.agent_5_judge       import JudgeAgent
    from agents.agent_6_synthesis   import SynthesisAgent
    from agents.agent_8_auditor     import PredictionAuditorAgent
    from agents.agent_7_portfolio   import PortfolioManager

    total_cost = 0.0
    results    = {}

    for AgentClass in [SentimentAgent, TechnicalAgent, FundamentalAgent,
                       MacroAgent, JudgeAgent, SynthesisAgent,
                       PredictionAuditorAgent, PortfolioManager]:
        agent  = AgentClass(ticker)
        result = agent.run()
        if result:
            total_cost              += result["cost"]
            results[agent.agent_id]  = result
            log_metric("agent_run", {
                "ticker":     ticker,
                "agent_id":   agent.agent_id,
                "agent_name": agent.name,
                "model":      agent.model,
                "tokens_in":  agent.tokens_in,
                "tokens_out": agent.tokens_out,
                "cost_usd":   result["cost"],
            })

    log_ok(f"All agents complete | Cost: ${total_cost:.6f}")
    log_metric("pipeline_complete", {
        "ticker":         ticker,
        "agents_run":     len(results),
        "total_cost_usd": total_cost,
    })
    return total_cost


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    log_header(f"DAILY PIPELINE  ·  {TODAY_STR}  ·  {', '.join(TICKERS)}")

    grand_total = 0.0
    blocked_tickers = []

    # Step 1: resolve ALL pending predictions (all tickers)
    update_actuals()

    # Step 2: collect data for each ticker in this run
    for ticker in TICKERS:
        log.info(f"\n  {'─' * 58}")
        log.info(f"  TICKER: {ticker}")
        log.info(f"  {'─' * 58}")
        collect_data(ticker)

    # Step 2b: Data Gate — validate data before running agents
    for ticker in TICKERS:
        ok, missing = validate_data(ticker)
        if not ok:
            blocked_tickers.append(ticker)

    runnable_tickers = [t for t in TICKERS if t not in blocked_tickers]

    if blocked_tickers:
        log_warn(f"BLOCKED tickers (no agents will run): {', '.join(blocked_tickers)}")
        log_info(f"Runnable tickers: {', '.join(runnable_tickers) if runnable_tickers else 'NONE'}")

    if not runnable_tickers:
        log_err("No tickers passed data validation — pipeline aborted")
        log_header(f"PIPELINE ABORTED  ·  {', '.join(TICKERS)}  ·  Missing data")
        sys.exit(1)

    # Step 3: run all agents for validated tickers only
    for ticker in runnable_tickers:
        log.info(f"\n  {'─' * 58}")
        log.info(f"  AGENTS: {ticker}")
        log.info(f"  {'─' * 58}")
        grand_total += run_agents(ticker)

    log_header(f"PIPELINE COMPLETE  ·  {', '.join(TICKERS)}  ·  Total: ${grand_total:.6f}")

    # ── Step 4: Refresh ALL portfolio prices via Yahoo Finance ──
    # Free, no API calls, backfills 1 month of prices for prediction resolution
    log_section("Step 4 — Refresh Portfolio Prices (Yahoo Finance)")
    try:
        import json
        import yfinance as yf

        status = supabase.table("portfolio_status") \
            .select("holdings").order("date", desc=True).limit(1).execute()

        if status.data:
            holdings = status.data[0]["holdings"]
            if isinstance(holdings, str):
                holdings = json.loads(holdings or "{}")
            held = [t for t, s in holdings.items() if float(s) > 0]

            if held:
                log_info(f"Refreshing {len(held)} ticker(s): {', '.join(held)}")
                data = yf.download(held, period="1mo", progress=False, group_by="ticker")
                refreshed = 0

                for tk in held:
                    try:
                        ticker_data = data[tk] if len(held) > 1 else data
                        if ticker_data.empty:
                            continue

                        # Backfill all days from the last month
                        for idx, row in ticker_data.iterrows():
                            try:
                                day_str = idx.strftime("%Y-%m-%d")
                                supabase.table("daily_prices").upsert({
                                    "ticker": tk, "date": day_str,
                                    "price": round(float(row["Close"]), 4),
                                    "open": round(float(row["Open"]), 4),
                                    "high": round(float(row["High"]), 4),
                                    "low": round(float(row["Low"]), 4),
                                    "volume": int(row["Volume"]),
                                    "change_pct": round(((float(row["Close"]) - float(row["Open"])) / float(row["Open"])) * 100, 4) if float(row["Open"]) > 0 else 0,
                                }, on_conflict="ticker,date").execute()
                            except Exception:
                                pass

                        last = ticker_data.iloc[-1]
                        price = float(last["Close"])
                        log_ok(f"[{tk}] ${price:.2f} · {len(ticker_data)} days backfilled")
                        refreshed += 1
                    except Exception as e:
                        log_warn(f"[{tk}] {e}")

                log_ok(f"Refreshed {refreshed}/{len(held)} · 0 API calls used")
            else:
                log_info("No open positions — skip")
        else:
            log_info("No portfolio yet — skip")

    except ImportError:
        log_warn("yfinance not installed — skip price refresh (pip install yfinance)")
    except Exception as e:
        log_warn(f"Price refresh failed: {e} — non-critical, continuing")
