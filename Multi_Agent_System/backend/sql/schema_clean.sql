-- ============================================================
-- AGENTIC FINANCE - CLEAN SCHEMA (FULL RESET)
-- Drop everything and start fresh
-- ============================================================

DROP TABLE IF EXISTS decisions CASCADE;
DROP TABLE IF EXISTS skips CASCADE;
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS prediction_audits CASCADE;
DROP TABLE IF EXISTS predictions CASCADE;
DROP TABLE IF EXISTS agent_reliability CASCADE;
DROP TABLE IF EXISTS judge_evaluations CASCADE;
DROP TABLE IF EXISTS agent_outputs CASCADE;
DROP TABLE IF EXISTS income_statements CASCADE;
DROP TABLE IF EXISTS fundamentals CASCADE;
DROP TABLE IF EXISTS news_sentiment CASCADE;
DROP TABLE IF EXISTS daily_prices CASCADE;
DROP TABLE IF EXISTS macro_data CASCADE;
DROP TABLE IF EXISTS portfolio CASCADE;
DROP TABLE IF EXISTS portfolio_status CASCADE;
DROP TABLE IF EXISTS collection_log CASCADE;

-- ============================================================
-- DATA TABLES
-- ============================================================

create table daily_prices (
  id           uuid default gen_random_uuid() primary key,
  ticker       text not null,
  date         date not null,
  price        float not null,
  open         float,
  high         float,
  low          float,
  volume       bigint,
  change_pct   float,
  created_at   timestamptz default now(),
  unique(ticker, date)
);

create table news_sentiment (
  id               uuid default gen_random_uuid() primary key,
  ticker           text not null,
  date             date not null,
  title            text,
  source           text,
  sentiment_label  text,
  sentiment_score  float,
  relevance_score  float,
  created_at       timestamptz default now()
);

create table fundamentals (
  id             uuid default gen_random_uuid() primary key,
  ticker         text not null,
  date           date not null,
  pe_ratio       float,
  forward_pe     float,
  eps            float,
  profit_margin  float,
  week_52_high   float,
  week_52_low    float,
  ma_50          float,
  ma_200         float,
  created_at     timestamptz default now(),
  unique(ticker, date)
);

create table income_statements (
  id               uuid default gen_random_uuid() primary key,
  ticker           text not null,
  date             date not null,
  period           text,
  total_revenue    bigint,
  gross_profit     bigint,
  operating_income bigint,
  net_income       bigint,
  ebitda           bigint,
  created_at       timestamptz default now(),
  unique(ticker, date)
);

create table macro_data (
  id         uuid default gen_random_uuid() primary key,
  indicator  text not null,
  date       date not null,
  value      float,
  created_at timestamptz default now(),
  unique(indicator, date)
);

-- ============================================================
-- AGENT TABLES
-- ============================================================

create table agent_outputs (
  id          uuid default gen_random_uuid() primary key,
  ticker      text not null,
  date        date not null,
  agent_id    text not null,
  outlook     text,
  strength    text,
  key_points  jsonb,
  risks       jsonb,
  reasoning   text,
  created_at  timestamptz default now(),
  unique(ticker, date, agent_id)
);

create table judge_evaluations (
  id             uuid default gen_random_uuid() primary key,
  ticker         text not null,
  date           date not null,
  agent_id       text not null,
  coherence      text,
  completeness   text,
  data_adherence text,
  overall        text,
  notes          text,
  created_at     timestamptz default now(),
  unique(ticker, date, agent_id)
);

create table agent_reliability (
  id            uuid default gen_random_uuid() primary key,
  agent_id      text not null,
  ticker        text not null,
  runs          integer default 0,
  score_sum     float default 0,
  score_avg     float default 0,
  trend         text default 'stable',
  last_updated  date,
  created_at    timestamptz default now(),
  unique(agent_id, ticker)
);

create table predictions (
  id             uuid default gen_random_uuid() primary key,
  ticker         text not null,
  date           date not null,
  horizon        text not null,
  outlook        text,
  price_current  float,
  price_target   float,
  confidence     text,
  reasoning      text,
  bullets        jsonb,
  price_actual   float,
  error_pct      float,
  created_at     timestamptz default now(),
  unique(ticker, date, horizon)
);

create table prediction_audits (
  id                       uuid default gen_random_uuid() primary key,
  date                     date not null,
  ticker                   text not null,
  horizon                  text not null,
  reasoning_quality        text,
  accuracy_score           text,
  bias                     text,
  confidence_calibration   text,
  notes                    text,
  created_at               timestamptz default now(),
  unique(ticker, date, horizon)
);

-- ============================================================
-- PORTFOLIO TABLES (3-table architecture)
-- ============================================================

create table trades (
  id              uuid default gen_random_uuid() primary key,
  date            date not null,
  ticker          text not null,
  action          text not null,
  shares          float not null,
  price           float not null,
  cash_remaining  float,
  total_value     float,
  created_at      timestamptz default now(),
  unique(date, ticker, action)
);

create table decisions (
  id              uuid default gen_random_uuid() primary key,
  date            date not null,
  ticker          text not null,
  action          text not null,
  ref_trade_id    uuid references trades(id) on delete set null,
  reasoning       text,
  bullets         jsonb,
  created_at      timestamptz default now()
);

create table skips (
  id              uuid default gen_random_uuid() primary key,
  date            date not null,
  ticker          text not null,
  reasoning       text,
  created_at      timestamptz default now()
);

create table portfolio_status (
  id            uuid default gen_random_uuid() primary key,
  date          date not null unique,
  total_value   float,
  cash          float,
  holdings      jsonb,
  total_pnl     float,
  total_pnl_pct float,
  created_at    timestamptz default now()
);

-- ============================================================
-- SYSTEM TABLES
-- ============================================================

create table collection_log (
  id         uuid default gen_random_uuid() primary key,
  ticker     text,
  data_type  text not null,
  last_run   date not null,
  created_at timestamptz default now(),
  unique(ticker, data_type)
);
