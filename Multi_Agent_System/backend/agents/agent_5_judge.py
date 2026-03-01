"""
AGENT 5 - JUDGE
================
Evaluates the quality of outputs from agents 1-4.
Updates reliability scores in the database.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.base_agent import BaseAgent, OPUS
from agents.fetch_data import fetch_all_data
from logger import log

SCORE_MAP = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.2}
AGENT_NAMES = {
    "agent_1": "Sentiment Analyst",
    "agent_2": "Technical Analyst",
    "agent_3": "Fundamental Analyst",
    "agent_4": "Macro Analyst"
}


class JudgeAgent(BaseAgent):

    def __init__(self, ticker):
        super().__init__("agent_5", "Judge", OPUS, ticker)

    def get_system_prompt(self):
        return """You are an external quality reviewer evaluating the outputs of financial analysis agents.
Your job is to verify that each agent produced coherent, complete, and data-grounded analysis.
You do NOT evaluate whether the analysis is correct in hindsight — you evaluate reasoning quality.
You MUST respond with valid JSON only. No other text. All fields must be written in English."""

    def get_agent_outputs(self):
        result = self.supabase.table("agent_outputs") \
            .select("*") \
            .eq("ticker", self.ticker) \
            .eq("date", self.today) \
            .in_("agent_id", ["agent_1", "agent_2", "agent_3", "agent_4"]) \
            .execute()
        return result.data if result.data else []

    def build_prompt(self, outputs, data):
        agents_text = ""
        for o in outputs:
            rel = self.get_reliability_for(o["agent_id"])
            name = AGENT_NAMES.get(o["agent_id"], o["agent_id"])
            agents_text += f"""
--- {o['agent_id'].upper()} — {name} ---
Outlook:     {o['outlook']} ({o['strength']})
Key points:  {o['key_points']}
Risks:       {o['risks']}
Reasoning:   {o['reasoning']}
Reliability: score_avg={rel['score_avg']} | trend={rel['trend']} | runs={rel['runs']}
"""

        return f"""Evaluate the quality of the 4 analysis agents' outputs for {self.ticker}.

CURRENT PRICE: ${data['current_price']}
NEWS AVAILABLE:  {len(data['news'])} articles
PRICES AVAILABLE: {len(data['prices'])} days
FUNDAMENTALS: {'available' if data['fundamentals'] else 'not available'}
MACRO: {'available' if data['macro'] else 'not available'}

AGENT OUTPUTS:
{agents_text}

For each agent, evaluate on 3 dimensions:
- coherence:      Is the reasoning internally consistent? (outlook, strength, key_points, risks aligned?)
- completeness:   Did the agent consider all relevant available data?
- data_adherence: Is the reasoning grounded in real data, or generic/hallucinated?

Scale: HIGH | MEDIUM | LOW

Then assign an overall score and specific notes in English.

Respond with valid JSON only:
{{
    "agent_1": {{
        "coherence":      "<HIGH|MEDIUM|LOW>",
        "completeness":   "<HIGH|MEDIUM|LOW>",
        "data_adherence": "<HIGH|MEDIUM|LOW>",
        "overall":        "<HIGH|MEDIUM|LOW>",
        "notes":          "<1-2 sentences of specific feedback in English>"
    }},
    "agent_2": {{
        "coherence":      "<HIGH|MEDIUM|LOW>",
        "completeness":   "<HIGH|MEDIUM|LOW>",
        "data_adherence": "<HIGH|MEDIUM|LOW>",
        "overall":        "<HIGH|MEDIUM|LOW>",
        "notes":          "<1-2 sentences of specific feedback in English>"
    }},
    "agent_3": {{
        "coherence":      "<HIGH|MEDIUM|LOW>",
        "completeness":   "<HIGH|MEDIUM|LOW>",
        "data_adherence": "<HIGH|MEDIUM|LOW>",
        "overall":        "<HIGH|MEDIUM|LOW>",
        "notes":          "<1-2 sentences of specific feedback in English>"
    }},
    "agent_4": {{
        "coherence":      "<HIGH|MEDIUM|LOW>",
        "completeness":   "<HIGH|MEDIUM|LOW>",
        "data_adherence": "<HIGH|MEDIUM|LOW>",
        "overall":        "<HIGH|MEDIUM|LOW>",
        "notes":          "<1-2 sentences of specific feedback in English>"
    }}
}}"""

    def get_reliability_for(self, agent_id):
        try:
            result = self.supabase.table("agent_reliability") \
                .select("score_avg, trend, runs") \
                .eq("agent_id", agent_id) \
                .eq("ticker", self.ticker) \
                .execute()
            return result.data[0] if result.data else {"score_avg": None, "trend": "unknown", "runs": 0}
        except Exception as e:
            log.warning(f"{self.tag} get_reliability_for({agent_id}) error: {e}")
            return {"score_avg": None, "trend": "unknown", "runs": 0}

    def run(self):
        self.log_header()
        self.log.info("Fetching agent outputs...")
        outputs = self.get_agent_outputs()

        if not outputs:
            self.log.warning("No outputs from agents 1-4. Run them first.")
            return None

        self.log.info(f"Found {len(outputs)} outputs to evaluate")
        data   = fetch_all_data(self.supabase, self.ticker)
        prompt = self.build_prompt(outputs, data)

        self.log.info(f"Calling {self.model}...")
        try:
            result = self.call_claude(prompt, max_tokens=1500)
            result = self.validate_judge(result)
        except (ValueError, Exception) as e:
            self.log.error(f"Error: {e}")
            return None

        cost = self.calculate_cost()

        for agent_id, judgment in result.items():
            row = {
                "ticker": self.ticker, "date": self.today, "agent_id": agent_id,
                "coherence": judgment["coherence"], "completeness": judgment["completeness"],
                "data_adherence": judgment["data_adherence"], "overall": judgment["overall"],
                "notes": judgment["notes"]
            }
            try:
                self.supabase.table("judge_evaluations").upsert(row, on_conflict="ticker,date,agent_id").execute()
            except Exception as e:
                self.log.error(f"DB error ({agent_id}): {e}")

            score = SCORE_MAP.get(judgment["overall"], 0.6)
            try:
                existing = self.supabase.table("agent_reliability") \
                    .select("*").eq("agent_id", agent_id).eq("ticker", self.ticker).execute()
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
                    }).eq("agent_id", agent_id).eq("ticker", self.ticker).execute()
                else:
                    self.supabase.table("agent_reliability").insert({
                        "agent_id": agent_id, "ticker": self.ticker,
                        "runs": 1, "score_sum": score, "score_avg": score,
                        "trend": "stable", "last_updated": self.today
                    }).execute()
            except Exception as e:
                self.log.error(f"Reliability update error ({agent_id}): {e}")

            name = AGENT_NAMES.get(agent_id, agent_id)
            self.log.info(f"{name}: overall={judgment['overall']} | {judgment['notes']}")

        self.log_footer(cost)
        return {"judgments": result, "ticker": self.ticker, "cost": cost}
