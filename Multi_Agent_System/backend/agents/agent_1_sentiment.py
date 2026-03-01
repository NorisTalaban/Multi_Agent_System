"""AGENT 1 - SENTIMENT ANALYST"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.base_agent import BaseAgent, SONNET
from agents.fetch_data import format_news, format_prices

class SentimentAgent(BaseAgent):
    def __init__(self, ticker):
        super().__init__("agent_1", "Sentiment Analyst", SONNET, ticker)

    def get_system_prompt(self):
        return """You are a financial sentiment analyst. Your primary lens is news flow and market perception.
Distinguish between noise (routine filings, ETF mentions) and real signals (products, lawsuits, acquisitions).
You MUST respond with valid JSON only. No other text. All fields must be written in English."""

    def check_data(self, data):
        if not data["news"] and not data["prices"]:
            return False, "No news or price data available."
        if not data["news"]:
            return True, "No news today — analysis based on prices only."
        return True, None

    def build_prompt(self, data):
        return f"""Analyze the sentiment for {self.ticker}.

CURRENT PRICE: ${data['current_price']}

RECENT PRICES:
{format_prices(data['prices'])}

TODAY'S NEWS:
{format_news(data['news'], data.get('news_date'))}

Your analysis must:
1. Assess the overall news tone (positive / negative / mixed)
2. Distinguish real signals from noise
3. Identify any emerging catalysts or risks
4. Consider how sentiment aligns or contradicts price movement

Respond with valid JSON only:
{{
    "outlook":    "<BULLISH | BEARISH | NEUTRAL>",
    "strength":   "<STRONG | MODERATE | WEAK>",
    "key_points": ["<main positive point>", "<optional second point>"],
    "risks":      ["<main risk>", "<optional second risk>"],
    "reasoning":  "<extended analysis in 3-5 sentences, in English>"
}}"""
