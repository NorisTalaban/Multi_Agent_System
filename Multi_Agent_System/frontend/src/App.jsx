import { useState, useEffect, useCallback } from 'react'
import { supabase } from './lib/supabase'
import { SearchBar, PipelineView, JudgePanel, PredictionsPanel, PortfolioPanel, JudgeHistoryChart, PredictionAuditPanel, PredictionLearningChart, ResolvedPredictionsTable } from './components'

export default function App() {
  const [ticker, setTicker]         = useState(null)
  const [date, setDate]             = useState(null)
  const [agents, setAgents]         = useState({})
  const [judge, setJudge]           = useState({})
  const [reliability, setRel]       = useState({})
  const [predictions, setPreds]     = useState([])
  const [portfolio, setPortfolio]   = useState(null)
  const [trades, setTrades]         = useState([])
  const [decisions, setDecisions]   = useState([])
  const [skips, setSkips]           = useState([])
  const [holdingPrices, setHoldingPrices] = useState({})
  const [loading, setLoading]       = useState(true)
  const [lastRun, setLastRun]       = useState(null)
  const [analyzedTickers, setAnalyzedTickers] = useState([])
  const [initDone, setInitDone]     = useState(false)

  // Global data (not filtered by ticker)
  const [judgeHistory, setJudgeHistory]   = useState([])
  const [predAudits, setPredAudits]       = useState([])
  const [resolvedPreds, setResolvedPreds] = useState([])

  // On mount: discover latest ticker and all analyzed tickers
  useEffect(() => {
    (async () => {
      const { data: allOutputs } = await supabase.from('agent_outputs').select('ticker,date').order('date', { ascending: false })
      
      const seen = new Map()
      allOutputs?.forEach(o => { if (!seen.has(o.ticker)) seen.set(o.ticker, o.date) })
      const tickers = Array.from(seen.entries()).map(([t, d]) => ({ ticker: t, date: d }))
      setAnalyzedTickers(tickers)

      const latestTicker = tickers[0]?.ticker || 'AAPL'
      setTicker(latestTicker)
      setInitDone(true)
    })()
  }, [])

  // Fetch GLOBAL data (all tickers) — judge history + prediction audits
  const fetchGlobal = useCallback(async () => {
    const { data: jh } = await supabase.from('judge_evaluations')
      .select('*').order('date', { ascending: true }).limit(500)
    setJudgeHistory(jh || [])

    const { data: pa } = await supabase.from('prediction_audits')
      .select('*').order('date', { ascending: false }).limit(100)
    setPredAudits(pa || [])

    // All predictions history (pending + resolved) — for learning curve and table
    const { data: rp } = await supabase.from('predictions')
      .select('date,ticker,horizon,price_target,price_actual,error_pct,confidence,outlook')
      .order('date', { ascending: false })
      .limit(500)
    setResolvedPreds(rp || [])
  }, [])

  const fetchData = useCallback(async (t) => {
    if (!t) return
    setLoading(true)

    // Sort by created_at (precise timestamp) to find the last analyzed ticker
    const { data: latestOutputs } = await supabase.from('agent_outputs')
      .select('date,ticker,created_at').order('created_at', { ascending: false }).limit(1)
    if (latestOutputs?.length) {
      setLastRun({ ticker: latestOutputs[0].ticker, date: latestOutputs[0].date })
    }

    const { data: latestForTicker } = await supabase.from('agent_outputs').select('date').eq('ticker', t).order('date', { ascending: false }).limit(1)
    const d = latestForTicker?.[0]?.date
    setDate(d)
    const today = d || new Date().toISOString().split('T')[0]

    const { data: outputs } = await supabase.from('agent_outputs').select('*').eq('ticker', t).eq('date', today)
    const am = {}; outputs?.forEach(o => am[o.agent_id] = o); setAgents(am)

    const { data: jd } = await supabase.from('judge_evaluations').select('*').eq('ticker', t).eq('date', today)
    const jm = {}; jd?.forEach(j => jm[j.agent_id] = j); setJudge(jm)

    const { data: rd } = await supabase.from('agent_reliability').select('*').eq('ticker', t)
    const rm = {}; rd?.forEach(r => rm[r.agent_id] = r); setRel(rm)

    const { data: pd } = await supabase.from('predictions').select('*').eq('ticker', t).eq('date', today)
    setPreds(pd || [])

    const { data: sd } = await supabase.from('portfolio_status').select('*').order('date', { ascending: false }).limit(1)
    setPortfolio(sd?.[0] || null)

    // Fetch latest prices for all held tickers
    const hp = {}
    if (sd?.[0]?.holdings) {
      const h = typeof sd[0].holdings === 'string' ? JSON.parse(sd[0].holdings || '{}') : (sd[0].holdings || {})
      const heldTickers = Object.entries(h).filter(([, s]) => parseFloat(s) > 0).map(([tk]) => tk)
      for (const tk of heldTickers) {
        const { data: priceData } = await supabase.from('daily_prices').select('price,date,change_pct').eq('ticker', tk).order('date', { ascending: false }).limit(1)
        if (priceData?.[0]) hp[tk] = priceData[0]
      }
    }
    setHoldingPrices(hp)

    // Trades from the trades table (3-table architecture)
    const { data: td } = await supabase.from('trades').select('*').order('date', { ascending: false }).limit(50)
    setTrades(td || [])

    // Decisions (HOLD + BUY/SELL narrative)
    const { data: dd } = await supabase.from('decisions').select('*').order('date', { ascending: false }).limit(50)
    setDecisions(dd || [])

    // Skips
    const { data: sk } = await supabase.from('skips').select('*').order('date', { ascending: false }).limit(50)
    setSkips(sk || [])

    // Also fetch global data
    await fetchGlobal()

    setLoading(false)
  }, [fetchGlobal])

  useEffect(() => { if (initDone && ticker) fetchData(ticker) }, [ticker, initDone, fetchData])

  useEffect(() => {
    if (!ticker) return
    const refreshAll = async () => {
      fetchData(ticker)
      const { data: allOutputs } = await supabase.from('agent_outputs').select('ticker,date').order('date', { ascending: false })
      const seen = new Map()
      allOutputs?.forEach(o => { if (!seen.has(o.ticker)) seen.set(o.ticker, o.date) })
      setAnalyzedTickers(Array.from(seen.entries()).map(([t, d]) => ({ ticker: t, date: d })))
    }
    const ch = supabase.channel('rt')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'agent_outputs' }, refreshAll)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'trades' }, () => fetchData(ticker))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'decisions' }, () => fetchData(ticker))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'skips' }, () => fetchData(ticker))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'portfolio_status' }, () => fetchData(ticker))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'predictions' }, () => fetchData(ticker))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'prediction_audits' }, () => fetchGlobal())
      .on('postgres_changes', { event: '*', schema: 'public', table: 'judge_evaluations' }, () => fetchGlobal())
      .subscribe()
    return () => supabase.removeChannel(ch)
  }, [ticker, fetchData, fetchGlobal])

  const handleSearch = (newTicker) => {
    if (newTicker && newTicker !== ticker) {
      setAgents({})
      setJudge({})
      setRel({})
      setPreds([])
      setTicker(newTicker)
    }
  }

  const hasData = Object.keys(agents).length > 0

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '40px 24px' }}>

      {/* HEADER */}
      <header className="fade-up" style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 16,
        paddingBottom: 24, marginBottom: 32,
        borderBottom: '1px solid #e4e4e7',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <h1 style={{ fontSize: 18, fontWeight: 700, color: '#09090b', letterSpacing: '-0.3px' }}>
              Agentic Finance
            </h1>
          </div>

          {lastRun && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 11, color: '#a1a1aa' }}>Viewing</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: '#09090b', fontFamily: 'var(--f-mono)', background: '#f4f4f5', padding: '1px 8px', borderRadius: 4 }}>{ticker}</span>
              {date && <span style={{ fontSize: 11, color: '#a1a1aa', fontFamily: 'var(--f-mono)' }}>{date}</span>}
              {lastRun.ticker !== ticker && (
                <span style={{ fontSize: 10, color: '#a1a1aa', marginLeft: 4 }}>
                  · last analyzed: <span style={{ fontFamily: 'var(--f-mono)', fontWeight: 600, cursor: 'pointer', color: '#3b82f6', textDecoration: 'underline' }} onClick={() => handleSearch(lastRun.ticker)}>{lastRun.ticker}</span>
                </span>
              )}
            </div>
          )}

          {analyzedTickers.length > 1 && (
            <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
              {analyzedTickers.map(({ ticker: t }) => (
                <button key={t} onClick={() => handleSearch(t)}
                  style={{
                    padding: '3px 10px', borderRadius: 6, border: `1.5px solid ${t === ticker ? '#18181b' : '#e4e4e7'}`,
                    background: t === ticker ? '#18181b' : '#fafafa', color: t === ticker ? '#fff' : '#52525b',
                    fontSize: 11, fontWeight: 700, fontFamily: 'var(--f-mono)', cursor: 'pointer', transition: 'all 0.15s',
                    letterSpacing: 0.5,
                  }}
                >{t}</button>
              ))}
            </div>
          )}
        </div>

        <SearchBar currentTicker={ticker} onSearch={handleSearch} />
      </header>

      {/* STATES */}
      {!initDone || (loading && !hasData) ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 280, gap: 14 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            {[0,1,2].map(i => <div key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: '#d4d4d8', animation: 'pulse 1.2s ease infinite', animationDelay: `${i*0.2}s` }} />)}
          </div>
          <p style={{ fontSize: 12, color: '#a1a1aa' }}>Loading system data…</p>
        </div>
      ) : !hasData ? (
        <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: 10, padding: 48, textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
          <div style={{ fontSize: 32, color: '#e4e4e7', marginBottom: 14 }}>○</div>
          <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>No data for {ticker}</p>
          <p style={{ fontSize: 12, color: '#a1a1aa' }}>
            Run{' '}
            <code style={{ fontSize: 12, fontFamily: 'var(--f-mono)', color: '#ea580c', background: '#fff7ed', padding: '2px 6px', borderRadius: 4, border: '1px solid #fed7aa' }}>
              python daily.py {ticker}
            </code>
            {' '}to start the analysis.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Pipeline */}
          <div className="fade-up fade-up-2">
            <PipelineView agents={agents} judge={judge} reliability={reliability} />
          </div>

          {/* Judge + Predictions row */}
          <div className="fade-up fade-up-3" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(540px, 1fr))', gap: 20 }}>
            <JudgePanel judge={judge} reliability={reliability} />
            <PredictionsPanel predictions={predictions} ticker={ticker} />
          </div>

          {/* Judge Quality Over Time — GLOBAL (all tickers) */}
          {judgeHistory.length > 0 && (
            <div className="fade-up fade-up-3">
              <JudgeHistoryChart history={judgeHistory} />
            </div>
          )}

          {/* Prediction Audit — GLOBAL (all tickers) */}
          {predAudits.length > 0 && (
            <div className="fade-up fade-up-3">
              <PredictionAuditPanel audits={predAudits} />
            </div>
          )}

          {/* Learning Curve — GLOBAL (resolved predictions only) */}
          {resolvedPreds.filter(p => p.price_actual != null).length > 0 && (
            <div className="fade-up fade-up-3">
              <PredictionLearningChart resolvedPredictions={resolvedPreds.filter(p => p.price_actual != null)} />
            </div>
          )}

          {/* Predictions Tracker — all predictions (pending + resolved) */}
          {resolvedPreds.length > 0 && (
            <div className="fade-up fade-up-3">
              <ResolvedPredictionsTable resolvedPredictions={resolvedPreds} />
            </div>
          )}

          {/* Portfolio */}
          <div className="fade-up fade-up-4">
            <PortfolioPanel
              portfolio={portfolio}
              trades={trades}
              decisions={decisions}
              skips={skips}
              ticker={ticker}
              holdingPrices={holdingPrices}
            />
          </div>
        </div>
      )}
    </div>
  )
}
