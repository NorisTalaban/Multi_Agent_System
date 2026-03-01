"""AGENT 2 - TECHNICAL ANALYST"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base_agent import BaseAgent, SONNET
from agents.fetch_data import format_prices, format_fundamentals

class TechnicalAgent(BaseAgent):
    def __init__(self, ticker):
        super().__init__("agent_2", "Technical Analyst", SONNET, ticker)

    def get_system_prompt(self):
        return """You are a technical analysis expert. Your primary lens is price action, moving averages, and momentum.
Analyze charts, trends, support/resistance levels, and volume patterns.
You MUST respond with valid JSON only. No other text. All fields must be written in English."""

    def check_data(self, data):
        if not data["prices"]:
            return False, "No price data available."
        return True, None

    def build_prompt(self, data):
        return f"""Perform technical analysis for {self.ticker}.

CURRENT PRICE: ${data['current_price']}

PRICE HISTORY (last 10 days):
{format_prices(data['prices'])}

KEY TECHNICAL LEVELS (from fundamentals):
{format_fundamentals(data['fundamentals'])}

Your analysis must:
1. Identify the current trend (uptrend / downtrend / sideways)
2. Assess momentum and volume signals
3. Identify key support and resistance levels
4. Compare price to moving averages (MA50, MA200)
5. Note proximity to 52-week high/low

Respond with valid JSON only:
{{
    "outlook":    "<BULLISH | BEARISH | NEUTRAL>",
    "strength":   "<STRONG | MODERATE | WEAK>",
    "key_points": ["<main bullish technical signal>", "<optional second>"],
    "risks":      ["<main bearish technical signal>", "<optional second>"],
    "reasoning":  "<extended technical analysis in 3-5 sentences, in English>"
}}"""
