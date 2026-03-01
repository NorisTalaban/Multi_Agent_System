"""
FETCH DATA - Centralized data retrieval from Supabase
======================================================
All agents call this function to get the same fresh data
from the database. Falls back to most recent available data
if today's data is not yet collected.
"""

from datetime import date, timedelta


def fetch_all_data(supabase, ticker):
    """
    Retrieves all available data for the given ticker.
    Returns a dictionary with all sections.
    """
    today = date.today().strftime("%Y-%m-%d")
    data  = {}

    # 1. Recent prices (last 30 days)
    result = supabase.table("daily_prices") \
        .select("*") \
        .eq("ticker", ticker) \
        .order("date", desc=True) \
        .limit(30) \
        .execute()
    data["prices"] = result.data if result.data else []

    # 2. News — today first, fallback to most recent available
    result = supabase.table("news_sentiment") \
        .select("*") \
        .eq("ticker", ticker) \
        .eq("date", today) \
        .order("relevance_score", desc=True) \
        .limit(15) \
        .execute()

    if result.data:
        data["news"]      = result.data
        data["news_date"] = today
    else:
        result = supabase.table("news_sentiment") \
            .select("*") \
            .eq("ticker", ticker) \
            .order("date", desc=True) \
            .order("relevance_score", desc=True) \
            .limit(15) \
            .execute()
        data["news"]      = result.data if result.data else []
        data["news_date"] = result.data[0]["date"] if result.data else None

    # 3. Most recent fundamentals
    result = supabase.table("fundamentals") \
        .select("*") \
        .eq("ticker", ticker) \
        .order("date", desc=True) \
        .limit(1) \
        .execute()
    data["fundamentals"] = result.data[0] if result.data else {}

    # 4. Most recent income statement
    result = supabase.table("income_statements") \
        .select("*") \
        .eq("ticker", ticker) \
        .order("date", desc=True) \
        .limit(1) \
        .execute()
    data["income"] = result.data[0] if result.data else {}

    # 5. Macro data (last 3 values per indicator)
    indicators = ["FEDERAL_FUNDS_RATE", "CPI", "UNEMPLOYMENT", "TREASURY_YIELD_10Y", "RETAIL_SALES"]
    macro = {}
    for ind in indicators:
        result = supabase.table("macro_data") \
            .select("*") \
            .eq("indicator", ind) \
            .order("date", desc=True) \
            .limit(3) \
            .execute()
        if result.data:
            macro[ind] = result.data
    data["macro"] = macro

    # Current price
    data["current_price"] = data["prices"][0]["price"] if data["prices"] else None

    return data


def format_prices(prices):
    """Formats prices for the prompt."""
    if not prices:
        return "  No data available"
    text = ""
    for p in prices[:10]:
        text += f"  {p['date']} | ${p['price']} | {p.get('change_pct', 0):+.2f}% | vol: {p.get('volume', 0):,}\n"
    return text


def format_news(news, news_date=None):
    """Formats news for the prompt."""
    if not news:
        return "  No news available"
    header = f"  (from {news_date})\n" if news_date else ""
    text   = header
    for i, n in enumerate(news):
        text += f"  [{i+1}] {n['title']}\n"
        text += f"      Source: {n['source']} | Sentiment: {n['sentiment_label']} ({n['sentiment_score']:.2f}) | Relevance: {n['relevance_score']:.2f}\n"
    return text


def format_fundamentals(f):
    """Formats fundamentals for the prompt."""
    if not f:
        return "  No data available"
    return f"""  P/E:           {f.get('pe_ratio', 'N/A')}
  Forward P/E:   {f.get('forward_pe', 'N/A')}
  EPS:           ${f.get('eps', 'N/A')}
  Profit Margin: {f.get('profit_margin', 'N/A')}
  MA 50:         ${f.get('ma_50', 'N/A')}
  MA 200:        ${f.get('ma_200', 'N/A')}
  52w High:      ${f.get('week_52_high', 'N/A')}
  52w Low:       ${f.get('week_52_low', 'N/A')}"""


def format_income(i):
    """Formats the income statement for the prompt."""
    if not i:
        return "  No data available"
    return f"""  Period:           {i.get('period', 'N/A')}
  Revenue:          ${i.get('total_revenue', 0):,}
  Gross Profit:     ${i.get('gross_profit', 0):,}
  Operating Income: ${i.get('operating_income', 0):,}
  Net Income:       ${i.get('net_income', 0):,}
  EBITDA:           ${i.get('ebitda', 0):,}"""


def format_macro(macro):
    """Formats macro data for the prompt."""
    if not macro:
        return "  No data available"
    text = ""
    for indicator, points in macro.items():
        text += f"  {indicator}:\n"
        for p in points:
            text += f"    {p['date']}: {p['value']}\n"
    return text
