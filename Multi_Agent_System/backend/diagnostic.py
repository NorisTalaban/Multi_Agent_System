"""
DIAGNOSTIC - Full System Control Panel
========================================
Detailed checks for every agent: what it sends, what it receives,
what it saves to DB, token usage, costs, data freshness.

Usage: python diagnostic.py
       python diagnostic.py AAPL
"""

import os
import sys
import json
from dotenv import load_dotenv
from supabase import create_client
from datetime import date

load_dotenv()

TICKER       = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"
TODAY        = date.today().strftime("%Y-%m-%d")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

G   = "\033[92m"
R   = "\033[91m"
Y   = "\033[93m"
B   = "\033[94m"
C   = "\033[96m"
W   = "\033[97m"
DIM = "\033[2m"
RST = "\033[0m"

def ok(msg):   print(f"  {G}✓{RST} {msg}")
def err(msg):  print(f"  {R}✗{RST} {msg}")
def warn(msg): print(f"  {Y}!{RST} {msg}")
def info(msg): print(f"  {B}→{RST} {msg}")
def dim(msg):  print(f"    {DIM}{msg}{RST}")

def header(title):
    print(f"\n{W}{'═' * 62}{RST}")
    print(f"{W}  {title}{RST}")
    print(f"{W}{'═' * 62}{RST}")

def section(title):
    print(f"\n{C}  ── {title} ──{RST}")

def agent_block(agent_id, name, model):
    mc = B if "sonnet" in model.lower() else C
    print(f"\n{W}  ┌─ {agent_id.upper()} — {name} [{mc}{model}{RST}{W}] ─{RST}")

def sub(label, value, color=""):
    print(f"  │  {label:<24} {color}{value}{RST}")

def saved(table, info_str=""):
    print(f"  │  {G}↓ DB save{RST}  →  {table}  {DIM}{info_str}{RST}")

def not_saved(reason=""):
    print(f"  │  {Y}↓ not saved{RST}  — {reason}")

def outlook_color(o):
    return G if o == "BULLISH" else R if o == "BEARISH" else Y

def quality_color(q):
    return G if q == "HIGH" else R if q == "LOW" else Y


# ============================================================
print()
header(f"DIAGNOSTIC PANEL  ·  {TICKER}  ·  {TODAY}")


# ── ENV ──────────────────────────────────────────────────────
section("ENVIRONMENT")
env_vars = {
    "SUPABASE_URL":      os.getenv("SUPABASE_URL"),
    "SUPABASE_KEY":      os.getenv("SUPABASE_KEY"),
    "ALPHA_VANTAGE_KEY": os.getenv("ALPHA_VANTAGE_KEY"),
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
}
missing = []
for key, val in env_vars.items():
    if val:
        masked = val[:6] + "..." + val[-4:] if len(val) > 10 else "***"
        ok(f"{key:<22} {DIM}{masked}{RST}")
    else:
        err(f"{key:<22} MISSING")
        missing.append(key)
if missing:
    err(f"Cannot continue — missing: {', '.join(missing)}")
    sys.exit(1)


# ── SUPABASE ─────────────────────────────────────────────────
section("SUPABASE CONNECTION")
try:
    db = create_client(SUPABASE_URL, SUPABASE_KEY)
    db.table("daily_prices").select("id").limit(1).execute()
    ok("Connected to Supabase")
except Exception as e:
    err(f"Connection failed: {e}")
    sys.exit(1)


# ── TABLES ───────────────────────────────────────────────────
section("TABLES")
TABLES = [
    "daily_prices", "news_sentiment", "fundamentals", "income_statements",
    "macro_data", "agent_outputs", "judge_evaluations", "agent_reliability",
    "predictions", "prediction_audits", "trades", "decisions", "skips",
    "portfolio_status", "collection_log"
]
for table in TABLES:
    try:
        r     = db.table(table).select("id", count="exact").limit(1).execute()
        count = r.count or 0
        ok(f"{table:<28} {DIM}{count:>6} rows{RST}")
    except Exception as e:
        err(f"{table:<28} {e}")


# ── COLLECTION LOG ───────────────────────────────────────────
section("COLLECTION LOG")
FREQ = {"price": 1, "news": 1, "fundamentals": 7, "income": 90, "macro": 30}
try:
    r = db.table("collection_log").select("*").execute()
    if r.data:
        for row in sorted(r.data, key=lambda x: (x.get("ticker") or "~", x["data_type"])):
            label    = row.get("ticker") or "GLOBAL"
            days_ago = (date.today() - date.fromisoformat(row["last_run"])).days
            freq     = FREQ.get(row["data_type"], 1)
            status   = f"{Y}DUE{RST}" if days_ago >= freq else f"{G}fresh{RST}"
            print(f"  [{label:<6}] {row['data_type']:<15} last:{row['last_run']}  {days_ago}d ago  {status}")
    else:
        warn("Empty — run daily.py first")
except Exception as e:
    err(f"collection_log: {e}")


# ── RAW DATA ─────────────────────────────────────────────────
section(f"RAW DATA AVAILABLE — {TICKER}")
print(f"  {DIM}(this is what agents/fetch_data.py provides to every agent){RST}\n")

# Prices
try:
    r = db.table("daily_prices").select("*").eq("ticker", TICKER).order("date", desc=True).limit(30).execute()
    price_count = len(r.data)
    if price_count > 0:
        l = r.data[0]
        ok(f"daily_prices      {price_count} rows | {l['date']} ${l['price']} {l.get('change_pct',0):+.2f}%")
        for row in r.data[:5]:
            dim(f"{row['date']}  ${row['price']}  {row.get('change_pct',0):+.2f}%  vol:{row.get('volume',0):,}")
    else:
        err(f"daily_prices      no data for {TICKER}")
        price_count = 0
except Exception as e:
    err(f"daily_prices: {e}")
    price_count = 0

# News
try:
    r_today = db.table("news_sentiment").select("*").eq("ticker", TICKER).eq("date", TODAY).order("relevance_score", desc=True).execute()
    r_all   = db.table("news_sentiment").select("id", count="exact").eq("ticker", TICKER).execute()
    news_count  = len(r_today.data)
    total_news  = r_all.count or 0
    if news_count > 0:
        ok(f"news_sentiment    {news_count} today / {total_news} total")
        for row in r_today.data[:5]:
            dim(f"[{row.get('sentiment_label','?'):<16}] rel:{row.get('relevance_score',0):.2f}  {row.get('title','')[:65]}")
    else:
        warn(f"news_sentiment    0 today ({total_news} total)")
        news_count = 0
except Exception as e:
    err(f"news_sentiment: {e}")
    news_count = 0

# Fundamentals
try:
    r = db.table("fundamentals").select("*").eq("ticker", TICKER).order("date", desc=True).limit(1).execute()
    fund_ok = bool(r.data)
    if fund_ok:
        f = r.data[0]
        ok(f"fundamentals      {f['date']} | P/E:{f.get('pe_ratio')} EPS:{f.get('eps')} MA50:{f.get('ma_50')} MA200:{f.get('ma_200')}")
    else:
        err(f"fundamentals      no data for {TICKER}")
except Exception as e:
    err(f"fundamentals: {e}")
    fund_ok = False

# Income
try:
    r = db.table("income_statements").select("*").eq("ticker", TICKER).order("date", desc=True).limit(1).execute()
    income_ok = bool(r.data)
    if income_ok:
        i = r.data[0]
        ok(f"income_statements period:{i.get('period')} rev:${i.get('total_revenue',0):,}")
    else:
        err(f"income_statements no data for {TICKER}")
except Exception as e:
    err(f"income_statements: {e}")
    income_ok = False

# Macro
try:
    indicators  = ["FEDERAL_FUNDS_RATE","CPI","UNEMPLOYMENT","TREASURY_YIELD_10Y","RETAIL_SALES"]
    macro_count = 0
    for ind in indicators:
        r = db.table("macro_data").select("*").eq("indicator", ind).order("date", desc=True).limit(1).execute()
        if r.data:
            ok(f"macro {ind:<22} {r.data[0]['date']} = {r.data[0]['value']}")
            macro_count += 1
        else:
            warn(f"macro {ind:<22} no data")
except Exception as e:
    err(f"macro: {e}")
    macro_count = 0


# ── AGENT BREAKDOWN ──────────────────────────────────────────
section("AGENT-BY-AGENT BREAKDOWN")
print(f"  {DIM}(input · output · DB save status){RST}")

def get_output(agent_id):
    try:
        r = db.table("agent_outputs").select("*").eq("ticker", TICKER).eq("date", TODAY).eq("agent_id", agent_id).execute()
        return r.data[0] if r.data else None
    except: return None

def get_judge(agent_id):
    try:
        r = db.table("judge_evaluations").select("*").eq("ticker", TICKER).eq("date", TODAY).eq("agent_id", agent_id).execute()
        return r.data[0] if r.data else None
    except: return None

def get_rel(agent_id):
    try:
        r = db.table("agent_reliability").select("*").eq("agent_id", agent_id).eq("ticker", TICKER).execute()
        return r.data[0] if r.data else None
    except: return None

def print_output(out):
    if out:
        oc = outlook_color(out.get("outlook",""))
        sub("OUTPUT outlook",     out.get("outlook","?"), oc)
        sub("OUTPUT strength",    out.get("strength","?"))
        sub("OUTPUT key_points",  str(out.get("key_points",[])))
        sub("OUTPUT risks",       str(out.get("risks",[])))
        sub("OUTPUT reasoning",   out.get("reasoning","")[:80] + "...")
        saved("agent_outputs", f"agent_id={out['agent_id']} date={TODAY}")
    else:
        not_saved("agent has not run today")

def print_rel(agent_id):
    rel = get_rel(agent_id)
    if rel:
        bar = "█" * int((rel.get("score_avg",0) or 0) * 10) + "░" * (10 - int((rel.get("score_avg",0) or 0) * 10))
        sc  = G if (rel.get("score_avg",0) or 0) >= 0.7 else R if (rel.get("score_avg",0) or 0) < 0.4 else Y
        sub("RELIABILITY", f"[{sc}{bar}{RST}] {rel.get('score_avg',0):.2f}  {rel.get('trend','?')}  {rel.get('runs',0)} runs")
    else:
        sub("RELIABILITY", "no history yet")


# Agent 1
agent_block("agent_1", "Sentiment", "claude-sonnet-4-6")
sub("INPUT news today",    f"{news_count} articles")
sub("INPUT prices",        f"{price_count} days")
sub("INPUT all data",      "full context (fundamentals, macro, income)")
print_output(get_output("agent_1"))
print_rel("agent_1")

# Agent 2
agent_block("agent_2", "Technical", "claude-sonnet-4-6")
sub("INPUT prices",        f"{price_count} days")
sub("INPUT MA50/MA200",    "from fundamentals table")
sub("INPUT 52w high/low",  "from fundamentals table")
sub("INPUT all data",      "full context")
print_output(get_output("agent_2"))
print_rel("agent_2")

# Agent 3
agent_block("agent_3", "Fundamental", "claude-sonnet-4-6")
sub("INPUT fundamentals",  "available" if fund_ok else f"{R}MISSING{RST}")
sub("INPUT income stmt",   "available" if income_ok else f"{R}MISSING{RST}")
sub("INPUT all data",      "full context")
print_output(get_output("agent_3"))
print_rel("agent_3")

# Agent 4
agent_block("agent_4", "Macro", "claude-sonnet-4-6")
sub("INPUT macro inds",    f"{macro_count}/5 indicators available")
sub("INPUT all data",      "full context")
print_output(get_output("agent_4"))
print_rel("agent_4")

# Agent 5 — Judge
outputs_today = db.table("agent_outputs").select("agent_id").eq("ticker", TICKER).eq("date", TODAY).execute().data or []
output_ids    = [o["agent_id"] for o in outputs_today]
judged        = []

agent_block("agent_5", "Judge", "claude-opus-4-6")
sub("INPUT agent outputs", f"{len(output_ids)} today: {output_ids}")
sub("INPUT reliability",   "historical scores per agent")
sub("INPUT raw data",      "same data snapshot for reference")

for aid in ["agent_1","agent_2","agent_3","agent_4"]:
    j = get_judge(aid)
    if j:
        qc = quality_color(j.get("overall",""))
        sub(f"OUTPUT [{aid}] overall",   j.get("overall","?"), qc)
        sub(f"OUTPUT [{aid}] coh/comp/data", f"{j.get('coherence','?')} / {j.get('completeness','?')} / {j.get('data_adherence','?')}")
        sub(f"OUTPUT [{aid}] notes",     j.get("notes","")[:70])
        judged.append(aid)

if judged:
    saved("judge_evaluations", f"{len(judged)} rows")
    saved("agent_reliability",  "score updated per agent")
else:
    not_saved("judge has not run today")

# Agent 6 — Synthesis
preds_today = db.table("predictions").select("*").eq("ticker", TICKER).eq("date", TODAY).execute().data or []
preds_count = len(preds_today)

agent_block("agent_6", "Synthesis + Predictions", "claude-opus-4-6")
sub("INPUT agent_outputs",     f"{len(output_ids)} reasoning blocks")
sub("INPUT judge_evaluations", f"{len(judged)} quality judgments")
sub("INPUT agent_reliability", "historical scores for weighting")

if preds_today:
    sub("OUTPUT synthesis",    "narrative (in predictions.reasoning)")
    for p in preds_today:
        oc = outlook_color(p.get("outlook",""))
        sub(f"OUTPUT {p['horizon']}", f"{p.get('outlook','?')} → ${p.get('price_target','?')} conf:{p.get('confidence','?')}", oc)
        bullets = p.get("bullets", [])
        if bullets:
            sub(f"       bullets", f"{bullets[:3]}")
    saved("predictions", f"3 rows: 1_week, 1_month, 1_quarter")
else:
    not_saved("synthesis has not run today")

# Agent 8 — Prediction Auditor
audits_today = db.table("prediction_audits").select("*").eq("ticker", TICKER).eq("date", TODAY).execute().data or []

agent_block("agent_8", "Prediction Auditor", "claude-sonnet-4-6")
sub("INPUT predictions",    f"{preds_count} current predictions")
sub("INPUT agent_outputs",  f"{len(output_ids)} for cross-reference")
sub("INPUT judge scores",   f"{len(judged)} quality judgments")
sub("INPUT pred history",   "past predictions with error_pct")

if audits_today:
    for a in audits_today:
        qc = quality_color(a.get("reasoning_quality",""))
        sub(f"OUTPUT [{a['horizon']}] quality",     a.get("reasoning_quality","?"), qc)
        sub(f"OUTPUT [{a['horizon']}] accuracy",    a.get("accuracy_score","?"))
        sub(f"OUTPUT [{a['horizon']}] bias",        a.get("bias","?"))
        sub(f"OUTPUT [{a['horizon']}] calibration", a.get("confidence_calibration","?"))
        sub(f"OUTPUT [{a['horizon']}] notes",       (a.get("notes","") or "")[:70])
    saved("prediction_audits", f"{len(audits_today)} rows")
else:
    not_saved("prediction auditor has not run today")

# Agent 7 — Portfolio
agent_block("agent_7", "Portfolio Manager", "claude-opus-4-6")
sub("INPUT agent_outputs",  f"{len(output_ids)} from agents 1-4")
sub("INPUT predictions",    f"{preds_count} horizons")
sub("INPUT judge scores",   f"{len(judged)} quality judgments")

try:
    status_r = db.table("portfolio_status").select("*").order("date", desc=True).limit(1).execute().data
    if status_r:
        s = status_r[0]
        sub("INPUT portfolio",  f"cash:${s.get('cash',0):,.2f} total:${s.get('total_value',0):,.2f}")
    else:
        sub("INPUT portfolio",  "no history — starting capital $500,000")
except:
    sub("INPUT portfolio",  "error reading")

try:
    trade = db.table("trades").select("*").eq("ticker", TICKER).order("created_at", desc=True).limit(1).execute().data
    decision = db.table("decisions").select("*").eq("ticker", TICKER).order("created_at", desc=True).limit(1).execute().data
    skip = db.table("skips").select("*").eq("ticker", TICKER).order("created_at", desc=True).limit(1).execute().data

    if trade and trade[0]["date"] == TODAY:
        t  = trade[0]
        ac = G if t["action"]=="BUY" else R if t["action"]=="SELL" else Y
        sub("OUTPUT action",    t.get("action","?"), ac)
        sub("OUTPUT shares",    str(int(t.get("shares",0))))
        saved("trades",          "1 trade row")
    if decision:
        d = decision[0]
        sub("OUTPUT decision",  f"{d.get('action','?')} — {(d.get('reasoning','') or '')[:60]}")
        saved("decisions",       f"with ref_trade_id: {d.get('ref_trade_id','none')}")
    if skip and skip[0]["date"] == TODAY:
        sub("OUTPUT skip",      f"{(skip[0].get('reasoning','') or '')[:60]}")
        saved("skips",           "1 skip row")
    if not trade and not decision and not skip:
        not_saved("portfolio manager has not run today")
    saved("portfolio_status", "daily snapshot updated")
except Exception as e:
    err(f"portfolio check: {e}")


# ── PREDICTIONS HISTORY ──────────────────────────────────────
section("PREDICTIONS HISTORY & ACCURACY")
try:
    r = db.table("predictions").select("*").eq("ticker", TICKER).order("date", desc=True).limit(12).execute()
    if r.data:
        cur_date = None
        for row in r.data:
            if row["date"] != cur_date:
                cur_date = row["date"]
                print(f"\n  {DIM}── {row['date']}  current price: ${row.get('price_current','?')} ──{RST}")
            oc     = outlook_color(row.get("outlook",""))
            actual = f"actual=${row['price_actual']}" if row.get("price_actual") else f"{Y}pending{RST}"
            error  = f"  err={row['error_pct']}%" if row.get("error_pct") is not None else ""
            print(f"  {row['horizon']:<12} {oc}{row.get('outlook','?'):<8}{RST} target=${row.get('price_target','?'):<8} {actual}{error}")
            bullets = row.get("bullets", [])
            if bullets and any(bullets):
                print(f"  {DIM}             bullets: {bullets[:3]}{RST}")
    else:
        warn("No predictions in DB yet")
except Exception as e:
    err(f"predictions history: {e}")


# ── PORTFOLIO STATUS ─────────────────────────────────────────
section("PORTFOLIO STATUS")
try:
    status_rows = db.table("portfolio_status").select("*").order("date", desc=True).limit(5).execute().data
    if status_rows:
        s       = status_rows[0]
        pnl     = s.get("total_pnl", 0) or 0
        pnl_pct = s.get("total_pnl_pct", 0) or 0
        holdings = s.get("holdings", {})
        if isinstance(holdings, str): holdings = json.loads(holdings or "{}")
        pc = G if pnl >= 0 else R
        ok(f"Last update: {s['date']}")
        sub("Total value",  f"${s.get('total_value',0):,.2f}")
        sub("Cash",         f"${s.get('cash',0):,.2f}")
        sub("P&L",          f"${pnl:,.2f} ({pnl_pct:+.2f}%)", pc)
        sub("Holdings",     str(holdings) if holdings else "none")
        print(f"\n  {DIM}Value history:{RST}")
        for s in status_rows:
            p  = s.get("total_pnl",0) or 0
            pc = G if p >= 0 else R
            print(f"    {s['date']}  ${s.get('total_value',0):>10,.2f}  P&L: {pc}${p:,.2f}{RST}")
    else:
        warn("No portfolio status yet")
except Exception as e:
    err(f"portfolio_status: {e}")

try:
    trades = db.table("trades").select("*").eq("ticker", TICKER).order("created_at", desc=True).limit(10).execute().data
    if trades:
        print(f"\n  {DIM}Trade history ({TICKER}):{RST}")
        for t in trades:
            ac = G if t["action"]=="BUY" else R if t["action"]=="SELL" else DIM
            print(f"    {t['date']}  {ac}{t['action']:<5}{RST}  {int(t.get('shares',0)):>5} @ ${t.get('price','?'):<10}  cash: ${t.get('cash_remaining',0):,.2f}")
    else:
        warn("No trades yet")
except Exception as e:
    err(f"trade history: {e}")


# ── TOKEN & COST ─────────────────────────────────────────────
section("TOKEN & COST ESTIMATE PER RUN")
AGENTS_COST = [
    ("agent_1", "Sentiment",   "sonnet-4", 0.003, 0.015,  800,  300, "agent_outputs"),
    ("agent_2", "Technical",   "sonnet-4", 0.003, 0.015,  900,  300, "agent_outputs"),
    ("agent_3", "Fundamental", "sonnet-4", 0.003, 0.015,  700,  300, "agent_outputs"),
    ("agent_4", "Macro",       "sonnet-4", 0.003, 0.015,  600,  300, "agent_outputs"),
    ("agent_5", "Judge",       "opus-4",   0.015, 0.075, 2000,  700, "judge_evaluations, agent_reliability"),
    ("agent_6", "Synthesis",   "opus-4",   0.015, 0.075, 2500,  900, "predictions"),
    ("agent_8", "Pred Auditor","sonnet-4", 0.003, 0.015, 1200,  500, "prediction_audits"),
    ("agent_7", "Portfolio",   "opus-4",   0.015, 0.075, 1800,  500, "trades, decisions, skips, portfolio_status"),
]
print(f"\n  {'Agent':<10} {'Name':<14} {'Model':<9} {'~In':>7} {'~Out':>7} {'Est.$':>8}  {'Saves to'}")
print(f"  {'─'*76}")
total_est = 0
for aid, name, model, c_in, c_out, avg_in, avg_out, saves in AGENTS_COST:
    cost = (avg_in * c_in + avg_out * c_out) / 1000
    total_est += cost
    mc = B if "sonnet" in model else C
    print(f"  {aid:<10} {name:<14} {mc}{model:<9}{RST} {avg_in:>7,} {avg_out:>7,} {G}${cost:.4f}{RST}  {DIM}{saves}{RST}")
print(f"  {'─'*76}")
print(f"  {'TOTAL':<35} {W}${total_est:.4f} per ticker per run{RST}")
print(f"  {DIM}Estimates only. Actual usage varies with data volume.{RST}")


# ── SUMMARY & NEXT STEPS ─────────────────────────────────────
section("SYSTEM STATUS & NEXT STEPS")

checks = {
    "Price data":         price_count > 0,
    "News today":         news_count > 0,
    "Fundamentals":       fund_ok,
    "Income statement":   income_ok,
    "Macro data":         macro_count > 0,
    "Agent outputs today": len(outputs_today) == 4,
    "Judge ran today":    len(judged) == 4,
    "Predictions today":  preds_count == 3,
    "Pred audit today":   len(audits_today) == 3,
}
for label, status in checks.items():
    (ok if status else warn)(label)

print(f"\n  {DIM}── Suggested next action ──{RST}")
if price_count == 0:
    info(f"python daily.py {TICKER}          # collect data + run agents")
    info(f"python refresh_prices.py {TICKER}  # or just refresh price via Yahoo")
elif len(outputs_today) < 4:
    info(f"python daily.py {TICKER}          # full pipeline (collect → agents)")
else:
    ok("All done for today.")
    info(f"Tomorrow: python daily.py {TICKER}")

print(f"\n{'═' * 62}\n")
