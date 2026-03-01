"""
BASE AGENT - Parent class for all agents
==========================================
Provides: Supabase singleton, Claude API with retry, cost tracking,
          template run() for analysis agents 1-4, validators, logging.
"""

import os
import json
import time
from dotenv import load_dotenv
from supabase import create_client
from anthropic import Anthropic
from datetime import date

load_dotenv()

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from logger import log, get_agent_logger, log_metric

SONNET = "claude-sonnet-4-6"
OPUS   = "claude-opus-4-6"

# Anthropic pricing per million tokens
COSTS = {
    SONNET: {"in": 3.00,  "out": 15.00},
    OPUS:   {"in": 15.00, "out": 75.00},
}

VALID_OUTLOOK  = {"BULLISH", "BEARISH", "NEUTRAL"}
VALID_STRENGTH = {"STRONG", "MODERATE", "WEAK"}
VALID_QUALITY  = {"HIGH", "MEDIUM", "LOW"}
VALID_ACTIONS  = {"BUY", "SELL", "HOLD", "SKIP"}

# ── SUPABASE SINGLETON ───────────────────────────────────────
_supabase_client = None

def _get_supabase():
    global _supabase_client
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")
        _supabase_client = create_client(url, key)
    return _supabase_client


class BaseAgent:

    def __init__(self, agent_id, name, model, ticker):
        self.agent_id   = agent_id
        self.name       = name
        self.model      = model
        self.ticker     = ticker
        self.today      = date.today().strftime("%Y-%m-%d")
        self.supabase   = _get_supabase()
        self.client     = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.tokens_in  = 0
        self.tokens_out = 0
        self.log        = get_agent_logger(agent_id)   # child logger for per-agent filtering

    @property
    def tag(self):
        return f"[{self.agent_id.upper()}: {self.name}]"

    def get_system_prompt(self):
        return "You are a financial analysis agent. Always respond with valid JSON only."

    # ── CLAUDE CALL WITH RETRY ────────────────────────────────
    def call_claude(self, prompt, max_tokens=1000, retries=3):
        """Call Claude with exponential backoff retry on transient errors."""
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=0.1,
                    system=self.get_system_prompt(),
                    messages=[{"role": "user", "content": prompt}]
                )
                self.tokens_in  = response.usage.input_tokens
                self.tokens_out = response.usage.output_tokens

                raw   = response.content[0].text.strip()
                clean = raw
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[1]
                    clean = clean.rsplit("```", 1)[0].strip()
                try:
                    return json.loads(clean)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON: {e} | Raw: {raw[:300]}")

            except ValueError:
                raise  # JSON errors — no point retrying
            except Exception as e:
                last_error = e
                if attempt < retries:
                    wait = 5 * (2 ** (attempt - 1))  # 5s, 10s, 20s
                    self.log.warning(f"Attempt {attempt}/{retries} failed: {e} — retry in {wait}s")
                    time.sleep(wait)
        raise last_error

    # ── TEMPLATE METHOD: run() for analysis agents 1-4 ───────
    def check_data(self, data):
        """
        Override in each agent to define the minimum data requirement.
        Return (ok: bool, warning_msg: str | None)
        """
        return True, None

    def build_prompt(self, data):
        raise NotImplementedError("Each agent must implement build_prompt()")

    def run(self):
        """
        Template run() shared by analysis agents 1-4.
        Agents only need to implement: get_system_prompt, build_prompt, check_data.
        """
        from agents.fetch_data import fetch_all_data
        self.log_header()
        self.log.info("Fetching data...")
        data = fetch_all_data(self.supabase, self.ticker)

        ok, warning = self.check_data(data)
        if not ok:
            self.log.warning(f"{self.tag} {warning}")
            return None
        if warning:
            self.log.warning(f"{self.tag} {warning}")

        prompt = self.build_prompt(data)
        self.log.info(f"Calling {self.model}...")
        try:
            result = self.call_claude(prompt)
            result = self.validate_analysis(result)
        except (ValueError, Exception) as e:
            self.log.error(f"{self.tag} Error: {e}")
            return None

        cost = self.calculate_cost()
        try:
            self.supabase.table("agent_outputs").upsert({
                "ticker":     self.ticker,
                "date":       self.today,
                "agent_id":   self.agent_id,
                "outlook":    result["outlook"],
                "strength":   result["strength"],
                "key_points": result["key_points"],
                "risks":      result["risks"],
                "reasoning":  result["reasoning"],
            }, on_conflict="ticker,date,agent_id").execute()
        except Exception as e:
            self.log.error(f"{self.tag} DB error: {e}")

        self.log.info(f"Outlook:    {result['outlook']} ({result['strength']})")
        self.log.info(f"Key points: {result['key_points']}")
        self.log.info(f"Risks:      {result['risks']}")
        self.log.info(f"Reasoning:  {result['reasoning'][:200]}")
        self.log_footer(cost)

        log_metric("agent_run", {
            "ticker":     self.ticker,
            "agent_id":   self.agent_id,
            "agent_name": self.name,
            "model":      self.model,
            "outlook":    result["outlook"],
            "strength":   result["strength"],
            "tokens_in":  self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd":   cost,
        })

        return {**result, "agent_id": self.agent_id, "ticker": self.ticker, "cost": cost}

    # ── VALIDATORS ───────────────────────────────────────────
    def validate_analysis(self, result):
        for field in ["outlook", "strength", "key_points", "risks", "reasoning"]:
            if field not in result:
                raise ValueError(f"Missing field: '{field}'")
        if result["outlook"] not in VALID_OUTLOOK:
            self.log.warning(f"Invalid outlook '{result['outlook']}' → NEUTRAL")
            result["outlook"] = "NEUTRAL"
        if result["strength"] not in VALID_STRENGTH:
            self.log.warning(f"Invalid strength '{result['strength']}' → MODERATE")
            result["strength"] = "MODERATE"
        if not isinstance(result["key_points"], list):
            result["key_points"] = [str(result["key_points"])]
        if not isinstance(result["risks"], list):
            result["risks"] = [str(result["risks"])]
        return result

    def validate_judge(self, result):
        required_agents = ["agent_1", "agent_2", "agent_3", "agent_4"]
        required_fields = ["coherence", "completeness", "data_adherence", "overall", "notes"]
        result = {k: v for k, v in result.items() if k in required_agents}
        for agent_id in required_agents:
            if agent_id not in result:
                self.log.warning(f"Missing judgment for {agent_id} — inserting default")
                result[agent_id] = {f: "MEDIUM" for f in required_fields[:-1]}
                result[agent_id]["notes"] = "Judgment not provided."
                continue
            j = result[agent_id]
            for field in required_fields:
                if field not in j:
                    raise ValueError(f"Missing '{field}' in judgment for {agent_id}")
            for dim in ["coherence", "completeness", "data_adherence", "overall"]:
                if j[dim] not in VALID_QUALITY:
                    self.log.warning(f"Invalid {dim} '{j[dim]}' for {agent_id} → MEDIUM")
                    j[dim] = "MEDIUM"
        return result

    def validate_synthesis(self, result):
        for field in ["synthesis", "consensus", "main_risks", "week", "month", "quarter"]:
            if field not in result:
                raise ValueError(f"Missing field: '{field}'")
        for horizon in ["week", "month", "quarter"]:
            h = result[horizon]
            for field in ["outlook", "price_target", "confidence", "reasoning"]:
                if field not in h:
                    raise ValueError(f"Missing '{field}' in horizon '{horizon}'")
            try:
                result[horizon]["price_target"] = float(h["price_target"])
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid price_target in '{horizon}': {h.get('price_target')} — {e}")
            if h["outlook"] not in VALID_OUTLOOK:
                result[horizon]["outlook"] = "NEUTRAL"
            if h["confidence"] not in VALID_QUALITY:
                result[horizon]["confidence"] = "MEDIUM"
        if not isinstance(result["main_risks"], list):
            result["main_risks"] = [str(result["main_risks"])]
        return result

    def validate_portfolio(self, result):
        for field in ["action", "shares", "reasoning"]:
            if field not in result:
                raise ValueError(f"Missing field: '{field}'")
        if result["action"] not in VALID_ACTIONS:
            self.log.warning(f"Invalid action '{result['action']}' → SKIP")
            result["action"] = "SKIP"
        try:
            result["shares"] = int(float(result["shares"]))
        except (ValueError, TypeError):
            self.log.warning("Invalid shares → 0")
            result["shares"] = 0
        return result

    # ── RELIABILITY ──────────────────────────────────────────
    def update_reliability(self, score):
        try:
            existing = self.supabase.table("agent_reliability") \
                .select("*").eq("agent_id", self.agent_id).eq("ticker", self.ticker).execute()
            if existing.data:
                r         = existing.data[0]
                runs      = r["runs"] + 1
                score_sum = r["score_sum"] + score
                score_avg = round(score_sum / runs, 4)
                prev_avg  = r["score_avg"]
                trend = "improving" if score_avg > prev_avg + 0.05 else \
                        "declining" if score_avg < prev_avg - 0.05 else "stable"
                self.supabase.table("agent_reliability").update({
                    "runs": runs, "score_sum": score_sum,
                    "score_avg": score_avg, "trend": trend, "last_updated": self.today
                }).eq("agent_id", self.agent_id).eq("ticker", self.ticker).execute()
            else:
                self.supabase.table("agent_reliability").insert({
                    "agent_id": self.agent_id, "ticker": self.ticker,
                    "runs": 1, "score_sum": score, "score_avg": score,
                    "trend": "stable", "last_updated": self.today
                }).execute()
        except Exception as e:
            self.log.error(f"update_reliability error: {e}")

    def get_reliability(self):
        try:
            result = self.supabase.table("agent_reliability") \
                .select("score_avg, trend, runs") \
                .eq("agent_id", self.agent_id).eq("ticker", self.ticker).execute()
            return result.data[0] if result.data else {"score_avg": None, "trend": "unknown", "runs": 0}
        except Exception as e:
            self.log.warning(f"get_reliability error: {e}")
            return {"score_avg": None, "trend": "unknown", "runs": 0}

    def calculate_cost(self):
        c = COSTS.get(self.model, COSTS[SONNET])
        return round((self.tokens_in * c["in"] + self.tokens_out * c["out"]) / 1_000_000, 6)

    def log_header(self):
        self.log.info(f"{'=' * 60}")
        self.log.info(f"{self.tag} - {self.ticker}")
        self.log.info(f"Date: {self.today} | Model: {self.model}")
        self.log.info(f"{'=' * 60}")

    def log_footer(self, cost):
        self.log.info(f"Tokens: {self.tokens_in} in / {self.tokens_out} out | Cost: ${cost:.6f}")
        self.log.info(f"{'=' * 60}")
