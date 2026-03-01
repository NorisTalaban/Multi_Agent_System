"""
AGENT 7 - PORTFOLIO MANAGER
=============================
Global portfolio manager that reviews ALL open positions on every run,
not just the current ticker. Decides buy/sell/hold for each position
using the latest available signals from Supabase.

Capital: $500,000
Max per position: 5% of total portfolio (~$25,000)
Sell rules: partial at +20%, full at +30%, immediate on strong BEARISH

STORAGE ARCHITECTURE:
  trades    — BUY/SELL only, immutable ledger (upsert on date+ticker+action)
  decisions — HOLD with ref_trade_id linking to the opening BUY
  skips     — isolated, no FK, no interference
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.base_agent import BaseAgent, OPUS
from agents.fetch_data import fetch_all_data
from logger import log_metric

STARTING_CAPITAL = 500_000.0
MAX_POSITION_PCT  = 0.05   # 5% max per ticker
MIN_TRADE_PCT     = 0.02   # 2% minimum trade size (avoid tiny trades)

# ── CONTEXT WINDOW MANAGEMENT ────────────────────────────────
# Approximate token counts per section (measured empirically)
TOKENS_PER_TICKER   = 600   # ~550-650 tokens per ticker in format_signals()
TOKENS_PROMPT_BASE  = 900   # system prompt + instructions + portfolio state
TOKENS_OUTPUT_PER_T = 120   # ~120 tokens per ticker in JSON output
TOKENS_OUTPUT_BASE  = 100   # JSON wrapper overhead
MAX_INPUT_TOKENS    = 180_000  # Opus context = 200k, leave margin for output
MAX_BATCH_SIZE      = 12    # Hard cap: never more than 12 tickers per Claude call

AGENT_NAMES = {
    "agent_1": "Sentiment",
    "agent_2": "Technical",
    "agent_3": "Fundamental",
    "agent_4": "Macro"
}


class PortfolioManager(BaseAgent):

    def __init__(self, ticker):
        super().__init__("agent_7", "Portfolio Manager", OPUS, ticker)

    def get_system_prompt(self):
        return """You are an autonomous global portfolio manager with $500,000 starting capital.
You manage a multi-ticker portfolio and review ALL positions on every run.

INVESTMENT PHILOSOPHY:
- BULLISH-BIASED: actively look for opportunities to buy quality stocks.
- When signals are mixed but not clearly negative, prefer BUY over SKIP.
- Hold quality positions through short-term volatility.
- Be disciplined on exits — this is where most investors fail.

POSITION SIZING:
- Max 5% of total portfolio per ticker (~$25,000 on $500k).
- Minimum trade: 2% of portfolio (~$10,000) — no tiny positions.
- If a position already exists, only add if under the 5% limit.

BUYING RULES:
- BUY when sentiment or fundamental signals show bullish or mixed-bullish signals.
- Even NEUTRAL consensus is fine to buy if Judge scores are HIGH and fundamentals are strong.
- SKIP only when signals are uniformly and clearly BEARISH.

SELLING RULES (strict discipline):
- SELL 40% of position when P&L > +20%.
- SELL 100% of position when P&L > +30%.
- SELL 100% immediately if 3+ agents are BEARISH with STRONG strength.
- HOLD through minor corrections (<10%) if fundamentals remain strong.
- Never sell just because of short-term volatility.

HOLD RULES:
- HOLD if signals are NEUTRAL or mixed and P&L is between -10% and +20%.
- HOLD if recently bought and position hasn't had time to develop.

You MUST respond with valid JSON only. No other text. All fields in English."""

    # ── DATA FETCHING ────────────────────────────────────────

    def get_portfolio_state(self):
        """Get current portfolio status — cash and all holdings."""
        result = self.supabase.table("portfolio_status") \
            .select("*").order("date", desc=True).limit(1).execute()
        if result.data:
            s = result.data[0]
            holdings = s["holdings"] if isinstance(s["holdings"], dict) \
                       else json.loads(s["holdings"] or "{}")
            return float(s["cash"]), holdings, float(s["total_value"])
        return STARTING_CAPITAL, {}, STARTING_CAPITAL

    def get_latest_signals(self, ticker):
        """Get most recent agent outputs + judge scores for any ticker."""
        outputs = self.supabase.table("agent_outputs") \
            .select("*").eq("ticker", ticker) \
            .order("date", desc=True).limit(4).execute()

        judgments = self.supabase.table("judge_evaluations") \
            .select("*").eq("ticker", ticker) \
            .order("date", desc=True).limit(4).execute()

        predictions = self.supabase.table("predictions") \
            .select("*").eq("ticker", ticker) \
            .order("date", desc=True).limit(3).execute()

        # Read trade history from the trades table
        trade_history = self.supabase.table("trades") \
            .select("*").eq("ticker", ticker) \
            .order("date", desc=True).limit(30).execute()

        return {
            "outputs":      outputs.data if outputs.data else [],
            "judgments":    {j["agent_id"]: j for j in judgments.data} if judgments.data else {},
            "predictions":  predictions.data if predictions.data else [],
            "trades":       trade_history.data if trade_history.data else [],
        }

    def get_current_price(self, ticker):
        """Get latest available price for a ticker."""
        result = self.supabase.table("daily_prices") \
            .select("price, date").eq("ticker", ticker) \
            .order("date", desc=True).limit(1).execute()
        if result.data:
            return float(result.data[0]["price"]), result.data[0]["date"]
        return None, None

    def get_all_open_tickers(self, holdings):
        """Return list of tickers with open positions (shares > 0)."""
        return [t for t, s in holdings.items() if float(s) > 0]

    def get_last_review_date(self, ticker):
        """Last date on which Agent 07 made a decision on this ticker."""
        result = self.supabase.table("decisions") \
            .select("date").eq("ticker", ticker) \
            .order("date", desc=True).limit(1).execute()
        return result.data[0]["date"] if result.data else None

    def needs_review(self, ticker, pnl_pct, bearish_strong_count):
        """
        Determines whether an open position should be reviewed today.
        Rules (in priority order):
          1. Always if P&L > +20% (profit taking)
          2. Always if P&L > +30% (full sell)
          3. Always if 3+ agents BEARISH STRONG (urgent signal)
          4. If last review >= 30 days ago (monthly review)
          5. If never reviewed before
        """
        if pnl_pct >= 30:
            return True, "P&L >= +30% → full sell urgent"
        if pnl_pct >= 20:
            return True, "P&L >= +20% → profit taking check"
        if bearish_strong_count >= 3:
            return True, f"{bearish_strong_count} agents BEARISH STRONG → urgent"

        last = self.get_last_review_date(ticker)
        if last is None:
            return True, "never reviewed"

        from datetime import date
        today     = date.fromisoformat(self.today)
        last_date = date.fromisoformat(last)
        days_since = (today - last_date).days

        if days_since >= 30:
            return True, f"last review {days_since}d ago (monthly review)"

        return False, f"last review {days_since}d ago — skip for {30 - days_since} more days"

    def get_open_trade_id(self, ticker):
        """Find the most recent open BUY trade for a ticker.
        An open BUY is one where net shares > 0 (not fully sold)."""
        result = self.supabase.table("trades") \
            .select("id,shares,action").eq("ticker", ticker) \
            .order("created_at", desc=True).limit(50).execute()
        if not result.data:
            return None
        # Walk trades chronologically to find if position is still open
        net_shares = 0
        last_buy_id = None
        for t in reversed(result.data):  # chronological order
            if t["action"] == "BUY":
                net_shares += float(t["shares"])
                last_buy_id = t["id"]
            elif t["action"] == "SELL":
                net_shares -= float(t["shares"])
        return last_buy_id if net_shares > 0 else None

    # ── CALCULATIONS ─────────────────────────────────────────

    def calculate_pnl(self, ticker, current_price, trades):
        """AVCO method: proportional cost reduction on sells."""
        if not trades or current_price <= 0:
            return None, None

        running_shares = 0.0
        running_cost   = 0.0

        for t in reversed(trades):  # chronological order
            action = t["action"]
            shares = float(t["shares"])
            price  = float(t["price"])

            if action == "BUY" and shares > 0:
                running_shares += shares
                running_cost   += shares * price
            elif action == "SELL" and shares > 0 and running_shares > 0:
                sell_ratio      = min(shares, running_shares) / running_shares
                running_cost   -= running_cost * sell_ratio
                running_shares  = max(0.0, running_shares - min(shares, running_shares))

        if running_shares <= 0:
            return None, None

        avg_buy_price = running_cost / running_shares
        pnl_pct       = ((current_price - avg_buy_price) / avg_buy_price) * 100
        return round(avg_buy_price, 2), round(pnl_pct, 2)

    def calculate_total_value(self, cash, holdings):
        """Calculate true total portfolio value using latest prices."""
        total = cash
        for ticker_symbol, shares_held in holdings.items():
            shares_held = float(shares_held)
            if shares_held <= 0:
                continue
            price, _ = self.get_current_price(ticker_symbol)
            if price:
                total += shares_held * price
        return total

    # ── BATCHING (CONTEXT WINDOW MANAGEMENT) ────────────────

    def estimate_prompt_tokens(self, n_tickers):
        """Estimate total tokens (input + output) for N tickers."""
        input_tokens  = TOKENS_PROMPT_BASE + (TOKENS_PER_TICKER * n_tickers)
        output_tokens = TOKENS_OUTPUT_BASE + (TOKENS_OUTPUT_PER_T * n_tickers)
        return input_tokens, output_tokens

    def split_into_batches(self, review_tickers):
        """
        Split tickers into batches that fit within context window.
        Priority order:
          1. Tickers needing urgent action (P&L > 20%, bearish signals)
          2. Current day's ticker (self.ticker)
          3. All others
        Each batch stays under MAX_BATCH_SIZE and estimated token limits.
        """
        if len(review_tickers) <= MAX_BATCH_SIZE:
            est_in, est_out = self.estimate_prompt_tokens(len(review_tickers))
            if est_in < MAX_INPUT_TOKENS:
                return [review_tickers]  # Everything fits in one call

        # Prioritize: urgent sells first, then current ticker, then rest
        urgent  = []
        current = []
        normal  = []

        for item in review_tickers:
            pnl = item.get("pnl_pct") or 0
            if pnl >= 20 or pnl <= -15:
                urgent.append(item)
            elif item["ticker"] == self.ticker:
                current.append(item)
            else:
                normal.append(item)

        ordered = urgent + current + normal

        # Split into batches
        batches = []
        batch   = []
        for item in ordered:
            test_size = len(batch) + 1
            est_in, est_out = self.estimate_prompt_tokens(test_size)
            if test_size > MAX_BATCH_SIZE or est_in >= MAX_INPUT_TOKENS:
                if batch:
                    batches.append(batch)
                batch = [item]
            else:
                batch.append(item)
        if batch:
            batches.append(batch)

        return batches

    # ── PROMPT BUILDING ──────────────────────────────────────

    def format_signals(self, ticker, signals, current_price, avg_buy_price, pnl_pct, shares_held, compact=False):
        """Format signals for a single ticker into prompt text.
        compact=True: shorter output for large batches (saves ~40% tokens per ticker)."""
        outputs     = signals["outputs"]
        judgments   = signals["judgments"]
        predictions = signals["predictions"]

        position_section = ""
        if shares_held > 0 and avg_buy_price and pnl_pct is not None:
            sell_flag = ""
            if pnl_pct >= 30:
                sell_flag = "  ⚠ SELL RULE: P&L > 30% → SELL 100%"
            elif pnl_pct >= 20:
                sell_flag = "  ⚠ SELL RULE: P&L > 20% → SELL 40%"
            position_section = f"""
  Current position: {int(shares_held)} shares @ avg ${avg_buy_price} | P&L: {pnl_pct:+.2f}%{sell_flag}"""

        reasoning_limit = 60 if compact else 100
        agents_text = ""
        for o in outputs:
            j    = judgments.get(o["agent_id"], {})
            name = AGENT_NAMES.get(o["agent_id"], o["agent_id"])
            agents_text += f"  {name}: {o['outlook']} ({o['strength']}) | Judge: {j.get('overall','N/A')} | {o.get('reasoning','')[:reasoning_limit]}\n"

        pred_text = ""
        for p in predictions:
            pred_text += f"  {p['horizon']}: {p['outlook']} → ${p.get('price_target','N/A')} ({p['confidence']})\n"

        return f"""
--- {ticker} ---
  Price: ${current_price}{position_section}
  Agents:
{agents_text}  Predictions:
{pred_text}"""

    def build_prompt(self, review_tickers, cash, total_value, holdings):
        """Build prompt covering ALL tickers to review."""
        max_per_ticker = total_value * MAX_POSITION_PCT
        min_trade      = total_value * MIN_TRADE_PCT
        compact        = len(review_tickers) > 6  # compress reasoning when many tickers

        tickers_section = ""
        for item in review_tickers:
            tickers_section += self.format_signals(
                item["ticker"], item["signals"], item["price"],
                item["avg_buy_price"], item["pnl_pct"], item["shares"],
                compact=compact
            )

        ticker_list = [item["ticker"] for item in review_tickers]

        return f"""Manage the portfolio. Review ALL tickers listed and decide action for each.

PORTFOLIO STATE:
  Total value:      ${total_value:,.2f}
  Cash available:   ${cash:,.2f}
  Max per ticker:   ${max_per_ticker:,.2f} (5%)
  Min trade size:   ${min_trade:,.2f} (2%)
  Starting capital: ${STARTING_CAPITAL:,.0f}

TICKERS TO REVIEW:
{tickers_section}

INSTRUCTIONS:
For EACH ticker listed, provide:
- action: BUY | SELL | HOLD | SKIP
- shares: integer — MANDATORY for BUY/SELL (must be > 0). Use 0 only for HOLD/SKIP.
  For BUY: calculate shares as floor(available_cash * 0.05 / price). Never say BUY with 0 shares.
  For SELL: specify exact number of shares to sell.
- reasoning: 1-2 sentences explaining the decision
- bullets: exactly 3 short bullet points (max 12 words each):
    * bullet 1: main reason for this action
    * bullet 2: main risk or concern
    * bullet 3: what would change this decision

Consider:
1. Sell rules: P&L > 20% → sell 40%, P&L > 30% → sell 100%
2. Position limits: max 5% of total portfolio per ticker
3. Cash availability: you have ${cash:,.2f} to deploy
4. For BUY: max shares = floor(min(${cash:,.2f}, total_value * 5%) / current_price)
5. Be BULLISH-BIASED on new positions with good signals
6. SKIP only if signals are uniformly BEARISH

Respond with valid JSON only:
{{
{chr(10).join(f'    "{t}": {{"action": "<BUY|SELL|HOLD|SKIP>", "shares": <int>, "reasoning": "<1-2 sentences>", "bullets": ["<main reason>", "<main risk>", "<what changes this>"]}},' for t in ticker_list)}
}}"""

    # ── EXECUTION ────────────────────────────────────────────

    def execute_trades(self, decisions, cash, holdings, review_tickers):
        """Execute all decisions and return updated cash + holdings + logs."""
        trades_log = []
        price_map  = {item["ticker"]: item["price"] for item in review_tickers}

        for ticker, decision in decisions.items():
            action = decision["action"]
            shares = float(decision["shares"])
            price  = price_map.get(ticker, 0)

            if price <= 0:
                self.log.warning(f"No valid price for {ticker} — skipping")
                continue

            current_shares = float(holdings.get(ticker, 0))

            if action == "BUY":
                # If agent said BUY but shares=0, auto-calculate max position
                if shares <= 0:
                    total_value = self.calculate_total_value(cash, holdings)
                    current_pos_value = current_shares * price
                    available = (total_value * MAX_POSITION_PCT) - current_pos_value
                    shares = int(min(available, cash) / price) if price > 0 else 0
                    self.log.info(f"  {ticker}: BUY with 0 shares requested — auto-calculated {int(shares)} shares")

                if shares > 0:
                    # Enforce max 5% limit
                    total_value        = self.calculate_total_value(cash, holdings)
                    current_pos_value  = current_shares * price
                    available          = (total_value * MAX_POSITION_PCT) - current_pos_value
                    if available <= 0:
                        self.log.info(f"  {ticker}: already at max position — HOLD")
                        action, shares = "HOLD", 0
                    else:
                        trade_cost = shares * price
                        trade_cost = min(trade_cost, cash, available)
                        shares     = int(trade_cost / price)
                        trade_cost = shares * price
                        if shares > 0 and trade_cost >= (self.calculate_total_value(cash, holdings) * MIN_TRADE_PCT):
                            cash                   -= trade_cost
                            holdings[ticker]        = current_shares + shares
                            self.log.info(f"  BUY  {ticker}: {int(shares)} shares @ ${price} = ${trade_cost:,.2f}")
                            trades_log.append({"ticker": ticker, "action": "BUY", "shares": shares, "price": price, "cash_remaining": cash})
                        else:
                            action, shares = "HOLD", 0
                else:
                    action, shares = "HOLD", 0

            elif action == "SELL" and shares > 0:
                shares = min(shares, current_shares)
                if shares > 0:
                    trade_value         = shares * price
                    cash               += trade_value
                    holdings[ticker]    = max(0.0, current_shares - shares)
                    self.log.info(f"  SELL {ticker}: {int(shares)} shares @ ${price} = ${trade_value:,.2f}")
                    trades_log.append({"ticker": ticker, "action": "SELL", "shares": shares, "price": price, "cash_remaining": cash})
                else:
                    action = "HOLD"

            # For HOLD/SKIP: log in trades_log for routing to correct table
            if action in ("HOLD", "SKIP"):
                trades_log.append({"ticker": ticker, "action": action, "shares": 0, "price": price, "cash_remaining": cash})
                self.log.info(f"  {action} {ticker}")

        return cash, holdings, trades_log

    # ── SAVE METHODS (THREE TABLES) ──────────────────────────

    def save_all(self, trades_log, decisions):
        """Route each decision to the correct table:
        BUY/SELL → trades table (upsert on date+ticker+action)
        HOLD     → decisions table (INSERT, with ref_trade_id)
        SKIP     → skips table (INSERT, isolated)
        """
        for t in trades_log:
            action  = t["action"]
            ticker  = t["ticker"]
            dec     = decisions.get(ticker, {})
            reasoning = dec.get("reasoning", "")
            bullets   = dec.get("bullets", ["", "", ""])
            if not isinstance(bullets, list):
                bullets = ["", "", ""]
            while len(bullets) < 3:
                bullets.append("")

            try:
                if action in ("BUY", "SELL") and t["shares"] > 0:
                    # ── TRADES TABLE (upsert — idempotent on re-run) ──
                    self.supabase.table("trades").upsert({
                        "date":          self.today,
                        "ticker":        ticker,
                        "action":        action,
                        "shares":        t["shares"],
                        "price":         t["price"],
                        "cash_remaining": t["cash_remaining"],
                        "total_value":   0,
                    }, on_conflict="date,ticker,action").execute()

                    # Also log in decisions for the narrative timeline
                    ref_id = None
                    if action == "BUY":
                        # Find the trade we just upserted
                        ref_result = self.supabase.table("trades") \
                            .select("id").eq("ticker", ticker).eq("date", self.today) \
                            .eq("action", "BUY").limit(1).execute()
                        ref_id = ref_result.data[0]["id"] if ref_result.data else None
                    elif action == "SELL":
                        # Reference the original BUY being closed
                        ref_id = self.get_open_trade_id(ticker)

                    self.supabase.table("decisions").insert({
                        "date":          self.today,
                        "ticker":        ticker,
                        "action":        action,
                        "ref_trade_id":  ref_id,
                        "reasoning":     reasoning,
                        "bullets":       bullets,
                    }).execute()

                    self.log.info(f"  ✓ Saved {action} {ticker} → trades + decisions")

                elif action == "HOLD":
                    # ── DECISIONS TABLE (INSERT — no overwrite risk) ──
                    ref_id = self.get_open_trade_id(ticker)
                    self.supabase.table("decisions").insert({
                        "date":          self.today,
                        "ticker":        ticker,
                        "action":        "HOLD",
                        "ref_trade_id":  ref_id,
                        "reasoning":     reasoning,
                        "bullets":       bullets,
                    }).execute()
                    self.log.info(f"  ✓ Saved HOLD {ticker} → decisions (ref: {ref_id or 'none'})")

                elif action == "SKIP":
                    # ── SKIPS TABLE (INSERT — completely isolated) ──
                    self.supabase.table("skips").insert({
                        "date":          self.today,
                        "ticker":        ticker,
                        "reasoning":     reasoning,
                    }).execute()
                    self.log.info(f"  ✓ Saved SKIP {ticker} → skips")

            except Exception as e:
                self.log.error(f"Save error ({ticker} {action}): {e}")

    def save_portfolio_status(self, cash, holdings, total_value):
        """Save daily portfolio snapshot."""
        total_pnl     = total_value - STARTING_CAPITAL
        total_pnl_pct = (total_pnl / STARTING_CAPITAL) * 100
        try:
            existing = self.supabase.table("portfolio_status") \
                .select("id").eq("date", self.today).execute()
            row = {
                "date":          self.today,
                "total_value":   total_value,
                "cash":          cash,
                "holdings":      holdings,
                "total_pnl":     total_pnl,
                "total_pnl_pct": total_pnl_pct
            }
            if existing.data:
                self.supabase.table("portfolio_status").update(row).eq("date", self.today).execute()
            else:
                self.supabase.table("portfolio_status").insert(row).execute()
        except Exception as e:
            self.log.error(f"Status save error: {e}")
        return total_pnl, total_pnl_pct

    # ── MAIN RUN ─────────────────────────────────────────────

    def run(self):
        self.log_header()
        self.log.info("Loading portfolio state...")

        cash, holdings, _ = self.get_portfolio_state()

        # Tickers to review = current ticker + open positions that need review
        open_tickers = self.get_all_open_tickers(holdings)

        # For each open position, compute P&L and count BEARISH STRONG signals
        # to decide whether to include it in today's review
        all_tickers = [self.ticker]  # current day's ticker always included

        for t in open_tickers:
            if t == self.ticker:
                continue  # already included

            # Compute approximate P&L for the profit-taking rule
            try:
                pnl_data = self.calculate_pnl(t)
                pnl_pct  = pnl_data.get("pnl_pct", 0) if pnl_data else 0
            except Exception:
                pnl_pct  = 0

            # Count BEARISH STRONG agents from DB (if available)
            try:
                agents_today = self.supabase.table("agent_outputs")                     .select("outlook,strength").eq("ticker", t).eq("date", self.today).execute()
                bearish_strong = sum(
                    1 for a in (agents_today.data or [])
                    if a.get("outlook") == "BEARISH" and a.get("strength") == "STRONG"
                )
            except Exception:
                bearish_strong = 0

            include, reason = self.needs_review(t, pnl_pct, bearish_strong)
            if include:
                all_tickers.append(t)
                self.log.info(f"  [{t}] included → {reason}")
            else:
                self.log.info(f"  [{t}] skipped → {reason}")

        all_tickers = list(dict.fromkeys(all_tickers))  # dedup
        self.log.info(f"Reviewing {len(all_tickers)} ticker(s): {', '.join(all_tickers)}")

        # Consistency check: holdings with no trade history = ghost data
        if holdings and not any(
            self.supabase.table("trades").select("id").eq("ticker", t).execute().data
            for t in holdings
        ):
            self.log.warning("Ghost data detected — resetting to clean state")
            cash, holdings = STARTING_CAPITAL, {}
            try:
                self.supabase.table("portfolio_status").update({
                    "cash": STARTING_CAPITAL, "holdings": {},
                    "total_value": STARTING_CAPITAL, "total_pnl": 0, "total_pnl_pct": 0
                }).eq("date", self.today).execute()
            except Exception as e:
                self.log.error(f"Could not reset ghost data: {e}")

        # Build review list with signals and prices for each ticker
        review_tickers = []
        for ticker in all_tickers:
            price, price_date = self.get_current_price(ticker)
            if not price:
                self.log.warning(f"No price for {ticker} — skipping from review")
                continue

            signals       = self.get_latest_signals(ticker)
            shares        = float(holdings.get(ticker, 0))
            avg_buy, pnl  = self.calculate_pnl(ticker, price, signals["trades"])

            review_tickers.append({
                "ticker":        ticker,
                "price":         price,
                "price_date":    price_date,
                "signals":       signals,
                "shares":        shares,
                "avg_buy_price": avg_buy,
                "pnl_pct":       pnl,
            })

            if shares > 0 and pnl is not None:
                self.log.info(f"  {ticker}: {int(shares)} shares @ avg ${avg_buy} | P&L: {pnl:+.2f}%")

        if not review_tickers:
            self.log.error("No tickers with valid prices — aborting")
            return None

        # Calculate true total value before trades
        total_value = self.calculate_total_value(cash, holdings)

        # ── BATCHED CLAUDE CALLS ──────────────────────────────
        batches = self.split_into_batches(review_tickers)
        self.log.info(f"Split {len(review_tickers)} ticker(s) into {len(batches)} batch(es): "
                      + " | ".join(f"[{', '.join(i['ticker'] for i in b)}]" for b in batches))

        decisions  = {}
        total_cost = 0.0

        for batch_idx, batch in enumerate(batches):
            batch_tickers = [item["ticker"] for item in batch]
            est_in, est_out = self.estimate_prompt_tokens(len(batch))
            max_tokens_out  = max(2000, est_out + 500)  # dynamic output budget

            self.log.info(f"Batch {batch_idx + 1}/{len(batches)}: {', '.join(batch_tickers)} "
                          f"(~{est_in} input tokens, max_output={max_tokens_out})")

            prompt = self.build_prompt(batch, cash, total_value, holdings)

            try:
                raw_result = self.call_claude(prompt, max_tokens=max_tokens_out)

                for ticker in batch_tickers:
                    if ticker not in raw_result:
                        self.log.warning(f"No decision for {ticker} — defaulting to HOLD")
                        decisions[ticker] = {"action": "HOLD", "shares": 0, "reasoning": "No decision provided."}
                    else:
                        d = raw_result[ticker]
                        validated = self.validate_portfolio(d)
                        decisions[ticker] = {**validated, "reasoning": d.get("reasoning", "")}

                total_cost += self.calculate_cost()

            except (ValueError, Exception) as e:
                self.log.error(f"Claude error on batch {batch_idx + 1}: {e}")
                # Default all tickers in failed batch to HOLD
                for ticker in batch_tickers:
                    decisions[ticker] = {"action": "HOLD", "shares": 0,
                                         "reasoning": f"Batch {batch_idx+1} failed: {str(e)[:80]}"}

        cost = total_cost

        # Execute all trades
        self.log.info("\n  Executing decisions:")
        cash, holdings, trades_log = self.execute_trades(decisions, cash, holdings, review_tickers)

        # Recalculate total value after trades
        total_value           = self.calculate_total_value(cash, holdings)
        total_pnl, pnl_pct    = self.save_portfolio_status(cash, holdings, total_value)

        # Save to three tables: trades, decisions, skips
        self.save_all(trades_log, decisions)

        # Log summary
        self.log.info(f"\n  PORTFOLIO SUMMARY:")
        self.log.info(f"  Cash:        ${cash:,.2f}")
        self.log.info(f"  Total value: ${total_value:,.2f}")
        self.log.info(f"  P&L:         ${total_pnl:,.2f} ({pnl_pct:+.2f}%)")
        for item in review_tickers:
            t      = item["ticker"]
            s      = float(holdings.get(t, 0))
            dec    = decisions.get(t, {})
            self.log.info(f"  {t}: {dec.get('action','?')} | {int(s)} shares | {dec.get('reasoning','')[:80]}")

        self.log_footer(cost)

        log_metric("portfolio_run", {
            "tickers_reviewed": [item["ticker"] for item in review_tickers],
            "total_value":      total_value,
            "cash":             cash,
            "total_pnl":        total_pnl,
            "total_pnl_pct":    pnl_pct,
            "cost_usd":         cost,
        })

        return {
            "decisions":   decisions,
            "total_value": total_value,
            "pnl":         total_pnl,
            "ticker":      self.ticker,
            "cost":        cost
        }
