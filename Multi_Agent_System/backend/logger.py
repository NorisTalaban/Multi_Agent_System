"""
LOGGER - Centralized logging for Agentic Finance
==================================================
- Unified logging: no parallel print() + log.info() systems
- File output with rotation (logs/agentic_finance.log)
- ANSI colors on console only, stripped in log file
- Rotating metrics file (logs/metrics.jsonl)
- TTY auto-detection for colors
"""

import logging
import sys
import os
import re
import json
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ── TTY DETECTION ────────────────────────────────────────────
USE_COLORS = sys.stdout.isatty()

G   = "\033[92m" if USE_COLORS else ""
R   = "\033[91m" if USE_COLORS else ""
Y   = "\033[93m" if USE_COLORS else ""
W   = "\033[97m" if USE_COLORS else ""
C   = "\033[96m" if USE_COLORS else ""
DIM = "\033[2m"  if USE_COLORS else ""
RST = "\033[0m"  if USE_COLORS else ""

# ── ANSI STRIP FILTER ────────────────────────────────────────
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")

class StripAnsiFilter(logging.Filter):
    """Removes ANSI escape codes from log records destined for file."""
    def filter(self, record):
        record.msg = _ANSI_RE.sub("", str(record.msg))
        if record.args:
            record.args = tuple(
                _ANSI_RE.sub("", str(a)) if isinstance(a, str) else a
                for a in (record.args if isinstance(record.args, tuple) else (record.args,))
            )
        return True

# ── FORMATTERS ───────────────────────────────────────────────
CONSOLE_FMT = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
FILE_FMT    = logging.Formatter(fmt="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# ── ROOT LOGGER ──────────────────────────────────────────────
log = logging.getLogger("agentic_finance")
log.setLevel(logging.DEBUG)
log.propagate = False

_console = logging.StreamHandler(sys.stdout)
_console.setLevel(logging.INFO)
_console.setFormatter(CONSOLE_FMT)
log.addHandler(_console)

_file = RotatingFileHandler(
    os.path.join(LOG_DIR, "agentic_finance.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=7,
    encoding="utf-8"
)
_file.setLevel(logging.DEBUG)
_file.setFormatter(FILE_FMT)
_file.addFilter(StripAnsiFilter())
log.addHandler(_file)

# ── CHILD LOGGERS ────────────────────────────────────────────
def get_agent_logger(agent_id):
    """Returns a child logger for a specific agent."""
    return log.getChild(agent_id)

# ── METRICS (rotating JSONL) ─────────────────────────────────
_metrics_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "metrics.jsonl"),
    maxBytes=10 * 1024 * 1024,
    backupCount=12,
    encoding="utf-8"
)

def log_metric(event_type, data: dict):
    """Write a structured metric line to metrics.jsonl."""
    record = {"ts": datetime.utcnow().isoformat() + "Z", "event": event_type, **data}
    try:
        _metrics_handler.stream  # ensure open
        _metrics_handler.emit(
            logging.makeLogRecord({"msg": json.dumps(record), "levelno": logging.INFO})
        )
        _metrics_handler.flush()
    except Exception:
        # Fallback: direct write
        try:
            with open(os.path.join(LOG_DIR, "metrics.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

# ── CONSOLE HELPERS ──────────────────────────────────────────
def log_header(title):
    log.info(f"\n{W}{'=' * 62}{RST}")
    log.info(f"{W}  {title}{RST}")
    log.info(f"{W}{'=' * 62}{RST}")

def log_section(title):
    log.info(f"\n{C}  ── {title} ──{RST}")

def log_ok(msg):   log.info(f"  {G}✓{RST} {msg}")
def log_err(msg):  log.error(f"  {R}✗{RST} {msg}")
def log_info(msg): log.info(f"  {DIM}→{RST} {msg}")
def log_warn(msg): log.warning(f"  {Y}⚠{RST} {msg}")
