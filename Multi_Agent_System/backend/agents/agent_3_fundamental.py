"""AGENT 3 - FUNDAMENTAL ANALYST"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base_agent import BaseAgent, SONNET
from agents.fetch_data import format_fundamentals, format_income

class FundamentalAgent(BaseAgent):
    def __init__(self, ticker):
        super().__init__("agent_3", "Fundamental Analyst", SONNET, ticker)

    def get_system_prompt(self):
        return """You are a fundamental equity analyst. Your primary lens is valuation and financial health.
Assess P/E ratios, earnings quality, revenue growth, and margin trends.
You MUST respond with valid JSON only. No other text. All fields must be written in English."""

    def check_data(self, data):
        if not data["fundamentals"] and not data["income"]:
            return False, "No fundamental data available."
        return True, None

    def build_prompt(self, data):
        return f"""Perform fundamental analysis for {self.ticker}.

CURRENT PRICE: ${data['current_price']}

FUNDAMENTALS:
{format_fundamentals(data['fundamentals'])}

INCOME STATEMENT (most recent annual):
{format_income(data['income'])}

Your analysis must:
1. Evaluate valuation (P/E vs historical and sector)
2. Assess earnings quality and profitability
3. Identify revenue growth trends
4. Comment on margin health
5. Note any red flags or strengths in the financials

Respond with valid JSON only:
{{
    "outlook":    "<BULLISH | BEARISH | NEUTRAL>",
    "strength":   "<STRONG | MODERATE | WEAK>",
    "key_points": ["<main fundamental strength>", "<optional second>"],
    "risks":      ["<main fundamental risk>", "<optional second>"],
    "reasoning":  "<extended analysis in 3-5 sentences, in English>"
}}"""
