"""
AGENT 6 - SYNTHESIS & PREDICTIONS
====================================
Aggregates reasoning from agents 1-4 with Judge evaluations.
Produces a synthesis narrative and predictions for 3 time horizons.

FEEDBACK LOOP:
Reads historical audits from Agent 08 (prediction_audits) to self-correct:
- If it has a systematic BULLISH_BIAS on 1_week → compensates
- If HIGH confidence has high errors → lowers confidence
- If reasoning_quality is declining → re-evaluates its own approach
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.base_agent import BaseAgent, OPUS
from agents.fetch_data import fetch_all_data
from collections import defaultdict

AGENT_NAMES = {
    "agent_1": "Sentiment Analyst",
    "agent_2": "Technical Analyst",
    "agent_3": "Fundamental Analyst",
    "agent_4": "Macro Analyst"
}


class SynthesisAgent(BaseAgent):

    def __init__(self, ticker):
        super().__init__("agent_6", "Synthesis & Predictions", OPUS, ticker)

    def get_system_prompt(self):
        return """You are the final synthesizer in a multi-agent financial analysis system.
You receive reasoning from 4 specialized analysts and quality judgments from an external reviewer.
You also receive a self-correction summary from a Prediction Auditor that tracks your historical biases.
Your job is to synthesize everything into a coherent view and produce predictions for 3 time horizons.
Think like a senior analyst weighing colleagues' opinions based on their reliability.
IMPORTANT: Take the auditor's self-correction notes seriously and adjust your predictions accordingly.
You MUST respond with valid JSON only. No other text. All fields must be written in English."""

    # ── DATA FETCHING ─────────────────────────────────────────

    def get_outputs_and_judgments(self):
        outputs = self.supabase.table("agent_outputs") \
            .select("*").eq("ticker", self.ticker).eq("date", self.today) \
            .in_("agent_id", ["agent_1", "agent_2", "agent_3", "agent_4"]).execute()
        judgments = self.supabase.table("judge_evaluations") \
            .select("*").eq("ticker", self.ticker).eq("date", self.today).execute()
        reliability = self.supabase.table("agent_reliability") \
            .select("*").eq("ticker", self.ticker).execute()
        return (
            outputs.data if outputs.data else [],
            {j["agent_id"]: j for j in judgments.data} if judgments.data else {},
            {r["agent_id"]: r for r in reliability.data} if reliability.data else {}
        )

    def get_audit_feedback(self):
        """
        Reads historical audits from Agent 08 for this ticker.
        Aggregates relevant statistics in Python for self-correction.
        Returns None if there is insufficient data.
        """
        result = self.supabase.table("prediction_audits") \
            .select("*").eq("ticker", self.ticker) \
            .order("date", desc=True).limit(30) \
            .execute()

        audits = result.data if result.data else []
        if not audits:
            return None

        # Group by horizon
        by_horizon = defaultdict(list)
        for a in audits:
            by_horizon[a["horizon"]].append(a)

        SCORE = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        feedback = {}

        for horizon, records in by_horizon.items():
            if not records:
                continue

            # Compute reasoning quality trend
            rq_scores = [SCORE.get(r["reasoning_quality"], 2) for r in records]
            avg_rq = round(sum(rq_scores) / len(rq_scores), 2)

            # Bias distribution
            bias_counts = defaultdict(int)
            for r in records:
                bias_counts[r.get("bias", "NEUTRAL")] += 1
            dominant_bias = max(bias_counts, key=bias_counts.get)

            # Average calibration
            cal_scores = [SCORE.get(r["confidence_calibration"], 2) for r in records]
            avg_cal = round(sum(cal_scores) / len(cal_scores), 2)

            # Average accuracy
            acc_scores = [SCORE.get(r["accuracy_score"], 2) for r in records]
            avg_acc = round(sum(acc_scores) / len(acc_scores), 2)

            # Most recent notes (last 3 per horizon)
            recent_notes = [r["notes"] for r in records[:3] if r.get("notes")]

            feedback[horizon] = {
                "audit_count":         len(records),
                "avg_reasoning_quality": avg_rq,
                "dominant_bias":       dominant_bias,
                "bias_distribution":   dict(bias_counts),
                "avg_calibration":     avg_cal,
                "avg_accuracy":        avg_acc,
                "recent_notes":        recent_notes,
                # Self-correction flags
                "has_systematic_bias": dominant_bias != "NEUTRAL" and bias_counts[dominant_bias] > len(records) * 0.5,
                "calibration_poor":    avg_cal < 2.0,
                "accuracy_poor":       avg_acc < 2.0,
            }

        return feedback if feedback else None

    # ── PROMPT ────────────────────────────────────────────────

    def build_prompt(self, outputs, judgments, reliability, data, audit_feedback):
        agents_text = ""
        for o in outputs:
            aid  = o["agent_id"]
            j    = judgments.get(aid, {})
            r    = reliability.get(aid, {})
            name = AGENT_NAMES.get(aid, aid)
            agents_text += f"""
=== {aid.upper()} — {name} ===
Outlook:     {o['outlook']} ({o['strength']})
Key points:  {o['key_points']}
Risks:       {o['risks']}
Reasoning:   {o['reasoning']}
Judge score: coherence={j.get('coherence','N/A')} | completeness={j.get('completeness','N/A')} | data_adherence={j.get('data_adherence','N/A')} | overall={j.get('overall','N/A')}
Judge notes: {j.get('notes', 'N/A')}
Reliability: score_avg={r.get('score_avg','N/A')} | trend={r.get('trend','N/A')} | runs={r.get('runs',0)}
"""

        # Self-correction section — empty if no audits available
        self_correction_text = ""
        if audit_feedback:
            self_correction_text = "\nSELF-CORRECTION FROM PREDICTION AUDITOR (your historical biases):\n"
            self_correction_text += "IMPORTANT: Use this data to actively correct your known systematic errors.\n"

            for horizon, fb in audit_feedback.items():
                label = {"1_week": "1 WEEK", "1_month": "1 MONTH", "1_quarter": "1 QUARTER"}.get(horizon, horizon)
                self_correction_text += f"""
{label} ({fb['audit_count']} past audits):
  Reasoning quality avg: {fb['avg_reasoning_quality']}/3
  Dominant bias:         {fb['dominant_bias']} (distribution: {fb['bias_distribution']})
  Confidence calibration avg: {fb['avg_calibration']}/3 {'← POOR: your HIGH confidence predictions are NOT more accurate' if fb['calibration_poor'] else ''}
  Accuracy avg:          {fb['avg_accuracy']}/3 {'← POOR: your price targets are frequently wrong' if fb['accuracy_poor'] else ''}
  Recent auditor notes:
    {chr(10).join(f'  - {n}' for n in fb['recent_notes'])}

  {'⚠ SELF-CORRECT: You have a systematic ' + fb['dominant_bias'] + ' on ' + label + '. Actively compensate.' if fb['has_systematic_bias'] else ''}
  {'⚠ SELF-CORRECT: Your confidence calibration is poor. Prefer MEDIUM over HIGH confidence.' if fb['calibration_poor'] else ''}
"""
        else:
            self_correction_text = "\nSELF-CORRECTION FROM PREDICTION AUDITOR: No historical audit data yet. Proceed normally.\n"

        return f"""Synthesize the analysis for {self.ticker} and produce predictions for 3 time horizons.

CURRENT PRICE: ${data['current_price']}

ANALYSIS FROM 4 AGENTS WITH QUALITY SCORES:
{agents_text}
{self_correction_text}

INSTRUCTIONS:
1. Weight each analysis by the Judge's quality score and historical reliability
2. Identify consensus and divergences among agents
3. Synthesize into a coherent narrative view (in English)
4. Apply self-corrections from the Auditor's feedback above
5. Produce predictions for 3 horizons:
   - 1 week:    weight sentiment and technical more heavily
   - 1 month:   weight all 4 agents equally
   - 1 quarter: weight fundamental and macro more heavily

For each prediction include:
- outlook: BULLISH | BEARISH | NEUTRAL
- price_target: specific number
- confidence: HIGH | MEDIUM | LOW
- reasoning: 2-3 sentences (mention any self-correction applied)
- bullets: exactly 3 concise bullet points (driver, key risk, what would change the view)
  Each bullet is a short phrase (max 15 words).

Respond with valid JSON only:
{{
    "synthesis":  "<overall narrative in 4-6 sentences>",
    "consensus":  "<BULLISH | BEARISH | NEUTRAL | MIXED>",
    "main_risks": ["<main risk>", "<second risk>"],
    "week": {{
        "outlook":      "<BULLISH|BEARISH|NEUTRAL>",
        "price_target": <number>,
        "confidence":   "<HIGH|MEDIUM|LOW>",
        "reasoning":    "<2-3 sentences>",
        "bullets":      ["<driver>", "<risk>", "<what changes the view>"]
    }},
    "month": {{
        "outlook":      "<BULLISH|BEARISH|NEUTRAL>",
        "price_target": <number>,
        "confidence":   "<HIGH|MEDIUM|LOW>",
        "reasoning":    "<2-3 sentences>",
        "bullets":      ["<driver>", "<risk>", "<what changes the view>"]
    }},
    "quarter": {{
        "outlook":      "<BULLISH|BEARISH|NEUTRAL>",
        "price_target": <number>,
        "confidence":   "<HIGH|MEDIUM|LOW>",
        "reasoning":    "<2-3 sentences>",
        "bullets":      ["<driver>", "<risk>", "<what changes the view>"]
    }}
}}"""

    # ── VALIDATION ────────────────────────────────────────────

    def validate_synthesis(self, result):
        """Extended validation that also checks bullets field."""
        result = super().validate_synthesis(result)
        for horizon in ["week", "month", "quarter"]:
            h = result[horizon]
            if "bullets" not in h or not isinstance(h["bullets"], list):
                h["bullets"] = ["No bullet points provided.", "", ""]
            while len(h["bullets"]) < 3:
                h["bullets"].append("")
            h["bullets"] = h["bullets"][:3]
        return result

    # ── RUN ───────────────────────────────────────────────────

    def run(self):
        self.log_header()
        self.log.info("Fetching outputs, judgments and audit feedback...")

        outputs, judgments, reliability = self.get_outputs_and_judgments()

        if not outputs:
            self.log.warning("No outputs from agents 1-4.")
            return None

        # Read historical feedback from the Auditor
        audit_feedback = self.get_audit_feedback()
        if audit_feedback:
            self.log.info(f"Audit feedback loaded for {len(audit_feedback)} horizons:")
            for h, fb in audit_feedback.items():
                self.log.info(
                    f"  [{h}] bias={fb['dominant_bias']} | "
                    f"cal={fb['avg_calibration']:.1f}/3 | "
                    f"acc={fb['avg_accuracy']:.1f}/3 | "
                    f"n={fb['audit_count']}"
                )
            correcting = [h for h, fb in audit_feedback.items() if fb["has_systematic_bias"] or fb["calibration_poor"]]
            if correcting:
                self.log.info(f"  Self-corrections active for: {', '.join(correcting)}")
        else:
            self.log.info("No audit feedback yet — proceeding without self-correction")

        data   = fetch_all_data(self.supabase, self.ticker)
        prompt = self.build_prompt(outputs, judgments, reliability, data, audit_feedback)

        self.log.info(f"Calling {self.model}...")
        try:
            result = self.call_claude(prompt, max_tokens=2000)
            result = self.validate_synthesis(result)
        except (ValueError, Exception) as e:
            self.log.error(f"Error: {e}")
            return None

        cost          = self.calculate_cost()
        current_price = data["current_price"]

        for horizon_key, horizon_label in [("week", "1_week"), ("month", "1_month"), ("quarter", "1_quarter")]:
            pred = result[horizon_key]
            row = {
                "ticker":        self.ticker,
                "date":          self.today,
                "horizon":       horizon_label,
                "outlook":       pred["outlook"],
                "price_current": current_price,
                "price_target":  pred["price_target"],
                "confidence":    pred["confidence"],
                "reasoning":     pred["reasoning"],
                "bullets":       pred["bullets"],
                "price_actual":  None,
                "error_pct":     None
            }
            try:
                self.supabase.table("predictions").upsert(row, on_conflict="ticker,date,horizon").execute()
            except Exception as e:
                self.log.error(f"DB error ({horizon_label}): {e}")

        self.log.info(f"\n  SYNTHESIS: {result['synthesis'][:120]}...")
        self.log.info(f"  Consensus: {result['consensus']}")
        for h, hl in [("week","1w"), ("month","1m"), ("quarter","1q")]:
            p = result[h]
            self.log.info(f"  {hl}: {p['outlook']} → ${p['price_target']} ({p['confidence']}) | {p['bullets']}")
        self.log_footer(cost)

        return {
            "synthesis":      result["synthesis"],
            "consensus":      result["consensus"],
            "main_risks":     result["main_risks"],
            "predictions":    {"week": result["week"], "month": result["month"], "quarter": result["quarter"]},
            "self_corrected": bool(audit_feedback),
            "ticker":         self.ticker,
            "cost":           cost
        }
