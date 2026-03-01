"""
AGENT 8 - PREDICTION AUDITOR
==============================
Evaluates the quality of Agent 06's predictions on two levels:

1. QUALITATIVE AUDIT (every run, immediate)
   Evaluates the reasoning behind the predictions just produced:
   - Did Agent 06 properly weight the inputs?
   - Are the price targets reasonable?
   - Is the horizon weighting correct?

2. QUANTITATIVE AUDIT (based on historical data with price_actual filled in)
   Aggregates in Python all past predictions with a known price_actual:
   - avg error_pct per horizon
   - bias distribution (BULLISH/BEARISH/NEUTRAL)
   - confidence calibration (does HIGH confidence = lower error?)
   - trend over time (is it improving?)
   This summary is passed to Claude for deeper analysis
   and saved in prediction_audits to be read by Agent 06.

Runs AFTER Agent 06, BEFORE Agent 07.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.base_agent import BaseAgent, SONNET
from logger import log
from collections import defaultdict


class PredictionAuditorAgent(BaseAgent):

    def __init__(self, ticker):
        super().__init__("agent_8", "Prediction Auditor", SONNET, ticker)

    def get_system_prompt(self):
        return """You are an auditor specializing in evaluating financial predictions over time.
You assess whether predictions are well-reasoned, properly weighted, and historically accurate.
You identify systematic biases (too bullish/bearish) and evaluate confidence calibration.
You receive both qualitative reasoning analysis AND quantitative historical statistics.
Use both to produce actionable feedback that will help Agent 06 self-correct.
You MUST respond with valid JSON only. No other text. All fields must be written in English."""

    # ── DATA FETCHING ─────────────────────────────────────────

    def get_current_predictions(self):
        """Predictions just produced by Agent 06 today."""
        result = self.supabase.table("predictions") \
            .select("*").eq("ticker", self.ticker).eq("date", self.today) \
            .execute()
        return result.data if result.data else []

    def get_agent_outputs(self):
        result = self.supabase.table("agent_outputs") \
            .select("*").eq("ticker", self.ticker).eq("date", self.today) \
            .in_("agent_id", ["agent_1", "agent_2", "agent_3", "agent_4"]) \
            .execute()
        return result.data if result.data else []

    def get_judge_evaluations(self):
        result = self.supabase.table("judge_evaluations") \
            .select("*").eq("ticker", self.ticker).eq("date", self.today) \
            .execute()
        return {j["agent_id"]: j for j in result.data} if result.data else {}

    def get_resolved_predictions(self):
        """
        All past predictions with price_actual filled in (Step 1 updates them).
        These are the real quantitative data used to compute accuracy and bias.
        """
        result = self.supabase.table("predictions") \
            .select("*").eq("ticker", self.ticker) \
            .not_.is_("price_actual", "null") \
            .order("date", desc=True).limit(90) \
            .execute()
        return result.data if result.data else []

    def get_past_audits(self):
        """Historical audits already produced by Agent 08 — to track the trend."""
        result = self.supabase.table("prediction_audits") \
            .select("*").eq("ticker", self.ticker) \
            .order("date", desc=True).limit(30) \
            .execute()
        return result.data if result.data else []

    # ── HISTORICAL AGGREGATION (Python, not Claude) ───────────

    def aggregate_historical_stats(self, resolved):
        """
        Aggregates in Python the predictions with a known price_actual.
        Produces clean statistics to pass in the prompt.
        This calculation is not delegated to Claude — we do it here.
        """
        if not resolved:
            return None

        stats = {}

        # Group by horizon
        by_horizon = defaultdict(list)
        for p in resolved:
            by_horizon[p["horizon"]].append(p)

        for horizon, records in by_horizon.items():
            errors = [abs(r["error_pct"]) for r in records if r["error_pct"] is not None]
            signed_errors = [r["error_pct"] for r in records if r["error_pct"] is not None]

            # Distribuzione outlook
            outlook_counts = defaultdict(int)
            for r in records:
                outlook_counts[r["outlook"]] += 1

            # Calibrazione confidence
            by_confidence = defaultdict(list)
            for r in records:
                if r["error_pct"] is not None:
                    by_confidence[r["confidence"]].append(abs(r["error_pct"]))

            calibration = {}
            for conf, errs in by_confidence.items():
                calibration[conf] = round(sum(errs) / len(errs), 2) if errs else None

            # Trend: compare first half vs second half of errors
            trend = "insufficient_data"
            if len(errors) >= 6:
                mid = len(errors) // 2
                older_avg = sum(errors[mid:]) / len(errors[mid:])
                recent_avg = sum(errors[:mid]) / len(errors[:mid])
                if recent_avg < older_avg - 0.5:
                    trend = "improving"
                elif recent_avg > older_avg + 0.5:
                    trend = "degrading"
                else:
                    trend = "stable"

            # Systematic bias: if avg signed error is consistently positive
            # (price_target > actual = predictions too optimistic)
            avg_signed = round(sum(signed_errors) / len(signed_errors), 2) if signed_errors else None
            if avg_signed is not None:
                if avg_signed > 2.0:
                    systematic_bias = "BULLISH_BIAS"
                elif avg_signed < -2.0:
                    systematic_bias = "BEARISH_BIAS"
                else:
                    systematic_bias = "NEUTRAL"
            else:
                systematic_bias = "NEUTRAL"

            stats[horizon] = {
                "sample_size":       len(records),
                "avg_abs_error_pct": round(sum(errors) / len(errors), 2) if errors else None,
                "avg_signed_error":  avg_signed,
                "systematic_bias":   systematic_bias,
                "outlook_dist":      dict(outlook_counts),
                "confidence_calibration_errors": calibration,
                "accuracy_grade":    self._grade_accuracy(sum(errors) / len(errors) if errors else None),
                "trend":             trend,
                "recent_3":          [
                    {"date": r["date"], "horizon": r["horizon"],
                     "outlook": r["outlook"], "target": r["price_target"],
                     "actual": r["price_actual"], "error_pct": r["error_pct"],
                     "confidence": r["confidence"]}
                    for r in records[:3]
                ]
            }

        return stats

    def _grade_accuracy(self, avg_error):
        """Convert avg_error_pct to grade HIGH/MEDIUM/LOW."""
        if avg_error is None:
            return "MEDIUM"  # default if no data available
        if avg_error < 3.0:
            return "HIGH"
        if avg_error < 7.0:
            return "MEDIUM"
        return "LOW"

    def aggregate_audit_trend(self, past_audits):
        """
        Aggregates past audits to see if Agent 06's quality is improving.
        Returns a summary per horizon.
        """
        if not past_audits:
            return None

        by_horizon = defaultdict(list)
        for a in past_audits:
            by_horizon[a["horizon"]].append(a)

        SCORE = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        summary = {}

        for horizon, audits in by_horizon.items():
            rq_scores = [SCORE.get(a["reasoning_quality"], 2) for a in audits]
            avg_rq = round(sum(rq_scores) / len(rq_scores), 2) if rq_scores else None

            bias_counts = defaultdict(int)
            for a in audits:
                bias_counts[a.get("bias", "NEUTRAL")] += 1

            summary[horizon] = {
                "audit_count":          len(audits),
                "avg_reasoning_quality": avg_rq,
                "reasoning_trend":       self._trend_label(rq_scores),
                "bias_distribution":     dict(bias_counts),
                "dominant_bias":         max(bias_counts, key=bias_counts.get) if bias_counts else "NEUTRAL"
            }

        return summary

    def _trend_label(self, scores):
        if len(scores) < 4:
            return "insufficient_data"
        mid = len(scores) // 2
        older = sum(scores[mid:]) / len(scores[mid:])
        recent = sum(scores[:mid]) / len(scores[:mid])
        if recent > older + 0.3:
            return "improving"
        if recent < older - 0.3:
            return "degrading"
        return "stable"

    # ── PROMPT ────────────────────────────────────────────────

    def build_prompt(self, predictions, outputs, judgments, hist_stats, audit_trend):

        # Today's predictions
        pred_text = ""
        for p in predictions:
            change_pct = ((p['price_target'] - p['price_current']) / p['price_current'] * 100) if p['price_current'] else 0
            pred_text += f"""
--- {p['horizon'].upper()} ---
Outlook:       {p['outlook']}
Price current: ${p['price_current']}
Price target:  ${p['price_target']} ({change_pct:+.2f}%)
Confidence:    {p['confidence']}
Reasoning:     {p['reasoning']}
Bullets:       {p['bullets']}
"""

        # Inputs that Agent 06 had available
        agents_text = ""
        for o in outputs:
            j = judgments.get(o["agent_id"], {})
            agents_text += f"  {o['agent_id'].upper()}: {o['outlook']} ({o['strength']}) | Judge: {j.get('overall', 'N/A')}\n"

        # Statistiche storiche aggregate (calcolate in Python)
        hist_text = "No historical resolved predictions yet."
        if hist_stats:
            hist_text = ""
            for horizon, s in hist_stats.items():
                hist_text += f"""
{horizon.upper()} — {s['sample_size']} resolved predictions:
  Avg absolute error:    {s['avg_abs_error_pct']}%
  Avg signed error:      {s['avg_signed_error']}% (positive = predictions too optimistic)
  Systematic bias:       {s['systematic_bias']}
  Accuracy grade:        {s['accuracy_grade']}
  Accuracy trend:        {s['trend']}
  Outlook distribution:  {s['outlook_dist']}
  Confidence calibration (avg error by confidence level):
    {s['confidence_calibration_errors']}
  Last 3 resolved:
    {s['recent_3']}
"""

        # Trend degli audit passati
        trend_text = "No past audits yet."
        if audit_trend:
            trend_text = ""
            for horizon, t in audit_trend.items():
                trend_text += f"""
{horizon.upper()}: {t['audit_count']} past audits
  Avg reasoning quality: {t['avg_reasoning_quality']}/3 | Trend: {t['reasoning_trend']}
  Bias distribution: {t['bias_distribution']} | Dominant: {t['dominant_bias']}
"""

        return f"""Audit the predictions made by Agent 06 (Synthesis) for {self.ticker}.

TODAY'S PREDICTIONS FROM AGENT 06:
{pred_text}

AGENT INPUTS AGENT 06 HAD AVAILABLE:
{agents_text}

QUANTITATIVE HISTORICAL STATISTICS (pre-aggregated from resolved predictions):
{hist_text}

TREND OF PAST AUDITS (Agent 06 reasoning quality over time):
{trend_text}

INSTRUCTIONS:
Evaluate each horizon (1_week, 1_month, 1_quarter) combining:

1. reasoning_quality (HIGH/MEDIUM/LOW):
   - Did Agent 06 properly weight agents based on judge scores?
   - Is the horizon-weighting correct?
     (1_week → sentiment+technical, 1_quarter → fundamental+macro)
   - Are price targets mathematically reasonable?
   - Does today's prediction show self-correction from known past biases?

2. accuracy_score (HIGH/MEDIUM/LOW):
   - Use the pre-aggregated accuracy_grade from historical stats above
   - If no historical data: MEDIUM

3. bias (BULLISH_BIAS / BEARISH_BIAS / NEUTRAL):
   - Use systematic_bias from historical stats
   - Cross-check with today's prediction direction

4. confidence_calibration (HIGH/MEDIUM/LOW):
   - Use confidence_calibration_errors from historical stats
   - HIGH confidence predictions should have LOWER errors than LOW confidence
   - If HIGH confidence has higher avg error: calibration is LOW

5. notes: 1-2 sentences of ACTIONABLE feedback for Agent 06 to self-correct
   Be specific: mention the bias direction, the horizon most affected,
   and what Agent 06 should do differently next time.

Respond with valid JSON only:
{{
    "1_week": {{
        "reasoning_quality":       "<HIGH|MEDIUM|LOW>",
        "accuracy_score":          "<HIGH|MEDIUM|LOW>",
        "bias":                    "<BULLISH_BIAS|BEARISH_BIAS|NEUTRAL>",
        "confidence_calibration":  "<HIGH|MEDIUM|LOW>",
        "notes":                   "<actionable feedback for Agent 06>"
    }},
    "1_month": {{
        "reasoning_quality":       "<HIGH|MEDIUM|LOW>",
        "accuracy_score":          "<HIGH|MEDIUM|LOW>",
        "bias":                    "<BULLISH_BIAS|BEARISH_BIAS|NEUTRAL>",
        "confidence_calibration":  "<HIGH|MEDIUM|LOW>",
        "notes":                   "<actionable feedback for Agent 06>"
    }},
    "1_quarter": {{
        "reasoning_quality":       "<HIGH|MEDIUM|LOW>",
        "accuracy_score":          "<HIGH|MEDIUM|LOW>",
        "bias":                    "<BULLISH_BIAS|BEARISH_BIAS|NEUTRAL>",
        "confidence_calibration":  "<HIGH|MEDIUM|LOW>",
        "notes":                   "<actionable feedback for Agent 06>"
    }}
}}"""

    # ── VALIDATION ────────────────────────────────────────────

    def validate_audit(self, result):
        valid_scores = {"HIGH", "MEDIUM", "LOW"}
        valid_bias = {"BULLISH_BIAS", "BEARISH_BIAS", "NEUTRAL"}
        for horizon in ["1_week", "1_month", "1_quarter"]:
            if horizon not in result:
                raise ValueError(f"Missing horizon: {horizon}")
            h = result[horizon]
            for field in ["reasoning_quality", "accuracy_score", "confidence_calibration"]:
                if h.get(field) not in valid_scores:
                    h[field] = "MEDIUM"
            if h.get("bias") not in valid_bias:
                h["bias"] = "NEUTRAL"
            if "notes" not in h or not h["notes"]:
                h["notes"] = "No specific feedback."
        return result

    # ── RUN ───────────────────────────────────────────────────

    def run(self):
        self.log_header()

        self.log.info("Fetching current predictions...")
        predictions = self.get_current_predictions()
        if not predictions:
            self.log.warning("No predictions from Agent 06. Run it first.")
            return None

        self.log.info(f"Found {len(predictions)} predictions to audit")

        outputs   = self.get_agent_outputs()
        judgments = self.get_judge_evaluations()

        # Historical aggregation in Python
        self.log.info("Aggregating historical resolved predictions...")
        resolved    = self.get_resolved_predictions()
        past_audits = self.get_past_audits()

        self.log.info(f"Historical data: {len(resolved)} resolved predictions | {len(past_audits)} past audits")

        hist_stats   = self.aggregate_historical_stats(resolved)
        audit_trend  = self.aggregate_audit_trend(past_audits)

        if hist_stats:
            for h, s in hist_stats.items():
                self.log.info(f"  [{h}] n={s['sample_size']} | avg_err={s['avg_abs_error_pct']}% | bias={s['systematic_bias']} | trend={s['trend']}")
        else:
            self.log.info("  No resolved predictions yet — qualitative audit only")

        prompt = self.build_prompt(predictions, outputs, judgments, hist_stats, audit_trend)

        self.log.info(f"Calling {self.model}...")
        try:
            result = self.call_claude(prompt, max_tokens=1500)
            result = self.validate_audit(result)
        except (ValueError, Exception) as e:
            self.log.error(f"Error: {e}")
            return None

        cost = self.calculate_cost()

        # Save to prediction_audits
        for horizon, audit in result.items():
            # Enrich with aggregate statistics computed in Python
            hs = hist_stats.get(horizon, {}) if hist_stats else {}
            row = {
                "date":                   self.today,
                "ticker":                 self.ticker,
                "horizon":                horizon,
                "reasoning_quality":      audit["reasoning_quality"],
                "accuracy_score":         audit["accuracy_score"],
                "bias":                   audit["bias"],
                "confidence_calibration": audit["confidence_calibration"],
                "notes":                  audit["notes"],
            }
            try:
                self.supabase.table("prediction_audits").upsert(
                    row, on_conflict="ticker,date,horizon"
                ).execute()
            except Exception as e:
                self.log.error(f"DB error ({horizon}): {e}")

            self.log.info(
                f"  {horizon}: quality={audit['reasoning_quality']} | "
                f"accuracy={audit['accuracy_score']} | bias={audit['bias']} | "
                f"calibration={audit['confidence_calibration']}"
            )
            self.log.info(f"    → {audit['notes']}")

        self.log_footer(cost)

        return {
            "audits":     result,
            "hist_stats": hist_stats,
            "ticker":     self.ticker,
            "cost":       cost
        }
