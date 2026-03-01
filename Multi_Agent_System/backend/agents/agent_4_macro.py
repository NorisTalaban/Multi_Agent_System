"""AGENT 4 - MACRO ANALYST"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base_agent import BaseAgent, SONNET
from agents.fetch_data import format_macro

class MacroAgent(BaseAgent):
    def __init__(self, ticker):
        super().__init__("agent_4", "Macro Analyst", SONNET, ticker)

    def get_system_prompt(self):
        return """You are a macroeconomic analyst. Your primary lens is how the economic environment affects equity valuations.
Assess interest rates, inflation, consumer spending, and their impact on the stock.
You MUST respond with valid JSON only. No other text. All fields must be written in English."""

    def check_data(self, data):
        if not data["macro"]:
            return False, "No macro data available."
        return True, None

    def build_prompt(self, data):
        return f"""Analyze the macro environment for {self.ticker}.

CURRENT PRICE: ${data['current_price']}

MACRO INDICATORS:
{format_macro(data['macro'])}

Your analysis must:
1. Assess the current interest rate environment and trajectory
2. Evaluate inflation trends and their impact on valuation
3. Consider consumer spending and economic growth signals
4. Analyze how the macro environment specifically affects {self.ticker}
5. Identify macro tailwinds and headwinds

Respond with valid JSON only:
{{
    "outlook":    "<BULLISH | BEARISH | NEUTRAL>",
    "strength":   "<STRONG | MODERATE | WEAK>",
    "key_points": ["<main macro tailwind>", "<optional second>"],
    "risks":      ["<main macro headwind>", "<optional second>"],
    "reasoning":  "<extended macro analysis in 3-5 sentences, in English>"
}}"""
