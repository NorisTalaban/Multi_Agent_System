import { useState } from 'react'

// ─── TOKENS ──────────────────────────────────
const C = {
  BULLISH: { color: '#4a9065', bg: '#f4faf6', border: '#a7d5b8' },
  BEARISH: { color: '#b85450', bg: '#faf4f4', border: '#daa8a6' },
  NEUTRAL: { color: '#71717a', bg: '#f4f4f5', border: '#d4d4d8' },
}
const Q = {
  HIGH:   { color: '#4a9065', bg: '#f4faf6', border: '#a7d5b8' },
  MEDIUM: { color: '#71717a', bg: '#f4f4f5', border: '#d4d4d8' },
  LOW:    { color: '#b85450', bg: '#faf4f4', border: '#daa8a6' },
}
const BIAS_MAP = {
  BULLISH_BIAS: { color: '#4a9065', bg: '#f4faf6', border: '#a7d5b8' },
  BEARISH_BIAS: { color: '#b85450', bg: '#faf4f4', border: '#daa8a6' },
  NEUTRAL:      { color: '#71717a', bg: '#f4f4f5', border: '#d4d4d8' },
}
const A = {
  BUY:  { color: '#4a9065', bg: '#f4faf6', border: '#a7d5b8', icon: '↑' },
  SELL: { color: '#b85450', bg: '#faf4f4', border: '#daa8a6', icon: '↓' },
  HOLD: { color: '#71717a', bg: '#f4f4f5', border: '#d4d4d8', icon: '→' },
  SKIP: { color: '#a1a1aa', bg: '#fafafa', border: '#d4d4d8', icon: '○' },
}
const BULL_ICON = ['↑', '↓', '→']
const BULL_COL  = ['#4a9065', '#b85450', '#8a8a90']
const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })

// ─── PRIMITIVES ──────────────────────────────
function Chip({ value, map, size = 'md' }) {
  const s = (map && map[value]) || {}
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      fontSize: size === 'sm' ? 10 : 11, fontWeight: 600,
      color: s.color || '#52525b', background: s.bg || '#f4f4f5',
      border: `1.5px solid ${s.border || '#d4d4d8'}`,
      borderRadius: 5, padding: size === 'sm' ? '1px 7px' : '3px 10px', letterSpacing: 0.2,
    }}>{value || '—'}</span>
  )
}

function BarLine({ pct }) {
  const p = pct || 0
  const color = p > 75 ? '#4a9065' : p > 40 ? '#8a8a90' : '#b85450'
  return (
    <div style={{ height: 4, background: '#e4e4e7', borderRadius: 2 }}>
      <div style={{ height: '100%', width: `${Math.min(p, 100)}%`, borderRadius: 2, background: color, transition: 'width 0.5s' }} />
    </div>
  )
}

function Card({ children, style }) {
  return (
    <div style={{ background: '#fff', border: '1.5px solid #e4e4e7', borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.08)', transition: 'box-shadow 0.15s,border-color 0.15s', ...style }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12)'; e.currentTarget.style.borderColor = '#c4c4c8' }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'; e.currentTarget.style.borderColor = '#e4e4e7' }}
    >{children}</div>
  )
}

// ─── SEARCH BAR ──────────────────────────────
export function SearchBar({ currentTicker, onSearch }) {
  const [v, setV] = useState('')
  const [focused, setFocused] = useState(false)
  const submit = (e) => {
    e?.preventDefault()
    const t = v.trim().toUpperCase()
    if (t && t.length >= 1 && t.length <= 5) { onSearch(t); setV('') }
  }
  return (
    <form onSubmit={submit} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <div style={{ position: 'relative' }}>
        <input value={v} onChange={e => setV(e.target.value.toUpperCase())} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
          placeholder="Search ticker…" maxLength={5}
          style={{ width: 160, padding: '8px 14px', fontSize: 12, fontWeight: 600, fontFamily: 'var(--f-mono)', background: '#fafafa', border: `1.5px solid ${focused ? '#b4b4bc' : '#e4e4e7'}`, borderRadius: 8, outline: 'none', color: '#09090b', letterSpacing: 1, transition: 'border-color 0.15s' }}
        />
      </div>
      <button type="submit" style={{ padding: '8px 16px', fontSize: 12, fontWeight: 700, color: '#fff', background: '#18181b', border: '1.5px solid #18181b', borderRadius: 8, cursor: 'pointer', transition: 'all 0.15s', letterSpacing: 0.3 }}
        onMouseEnter={e => { e.currentTarget.style.background = '#3f3f46' }}
        onMouseLeave={e => { e.currentTarget.style.background = '#18181b' }}
      >Go</button>
    </form>
  )
}

// ─── PIPELINE LAYOUT ─────────────────────────
const NW = 155, NH = 68, CANVAS_W = 1100, CANVAS_H = 700
const HUB = { x: 550, y: 270 }

const PIPE_NODES = [
  { id: 'agent_1', num: '01', label: 'Sentiment',   sub: 'News · Social · Analyst',  color: '#5b7fb5', x: 30,  y: 40 },
  { id: 'agent_2', num: '02', label: 'Technical',   sub: 'Price · Indicators',        color: '#8b6aaf', x: 260, y: 40 },
  { id: 'agent_3', num: '03', label: 'Fundamental', sub: 'Earnings · Valuation',      color: '#4d8a5e', x: 680, y: 40 },
  { id: 'agent_4', num: '04', label: 'Macro',       sub: 'Rates · Economy',           color: '#c07a3e', x: 910, y: 40 },
  { id: 'agent_5', num: '05', label: 'Judge',       sub: 'Evaluates Agents 1-4',      color: '#a07840', x: 860, y: 420 },
  { id: 'agent_6', num: '06', label: 'Predictions', sub: 'Synthesis · Targets',       color: '#4d8a9a', x: 70,  y: 420 },
  { id: 'agent_8', num: '08', label: 'Auditor',     sub: 'Audits Predictions',        color: '#7a6aaf', x: 70,  y: 560 },
  { id: 'agent_7', num: '07', label: 'Portfolio',   sub: 'Execution · Risk Mgmt',     color: '#2d2d30', x: 470, y: 420 },
]

function nodeBottom(n) { return { x: n.x + NW / 2, y: n.y + NH } }
function nodeTop(n)    { return { x: n.x + NW / 2, y: n.y } }
function bezierPath(x1, y1, x2, y2) { const m = (y1 + y2) / 2; return `M${x1},${y1} C${x1},${m} ${x2},${m} ${x2},${y2}` }

function PipelineSVG({ agents }) {
  const topNodes  = PIPE_NODES.slice(0, 4)
  const judgeNode = PIPE_NODES[4], synthNode = PIPE_NODES[5], auditNode = PIPE_NODES[6], portNode = PIPE_NODES[7]
  const anyTop = topNodes.some(n => !!agents[n.id])
  const judgeActive = !!agents['agent_5'], synthActive = !!agents['agent_6'], portActive = !!agents['agent_7']
  const LINE_ON = '#9ca3af', LINE_OFF = '#d4d4d8', DOT_FILL = '#18181b'

  const topLines = topNodes.map(n => ({ path: bezierPath(nodeBottom(n).x, nodeBottom(n).y, HUB.x, HUB.y), active: !!agents[n.id], id: n.id }))
  const hubToJudge = bezierPath(HUB.x, HUB.y, nodeTop(judgeNode).x, nodeTop(judgeNode).y)
  const hubToSynth = bezierPath(HUB.x, HUB.y, nodeTop(synthNode).x, nodeTop(synthNode).y)
  const hubToPort  = bezierPath(HUB.x, HUB.y, nodeTop(portNode).x, nodeTop(portNode).y)

  // LOOP: Predictions → down to Auditor → left → up → back to Predictions
  const predBot = { x: synthNode.x + NW / 2, y: synthNode.y + NH }
  const predLeft = { x: synthNode.x, y: synthNode.y + NH / 2 }
  const auditTop = { x: auditNode.x + NW / 2, y: auditNode.y }
  const auditLeftMid = { x: auditNode.x, y: auditNode.y + NH / 2 }
  const loopX = Math.min(synthNode.x, auditNode.x) - 45
  const loopR = 12

  const loopFull = [
    `M${predBot.x},${predBot.y}`,
    `L${auditTop.x},${auditTop.y}`,
    `L${auditLeftMid.x},${auditLeftMid.y}`,
    `L${loopX + loopR},${auditLeftMid.y}`,
    `Q${loopX},${auditLeftMid.y} ${loopX},${auditLeftMid.y - loopR}`,
    `L${loopX},${predLeft.y + loopR}`,
    `Q${loopX},${predLeft.y} ${loopX + loopR},${predLeft.y}`,
    `L${predLeft.x},${predLeft.y}`,
  ].join(' ')

  const auditActive  = !!agents['agent_8']

  // Lateral: Judge→Portfolio
  const jL = { x: judgeNode.x, y: judgeNode.y + NH / 2 }, pR = { x: portNode.x + NW, y: portNode.y + NH / 2 }
  const judgeToPort = `M${jL.x},${jL.y} C${jL.x-50},${jL.y} ${pR.x+50},${pR.y} ${pR.x},${pR.y}`
  const synthR = { x: synthNode.x + NW, y: synthNode.y + NH / 2 }, portL = { x: portNode.x, y: portNode.y + NH / 2 }
  const synthToPort = `M${synthR.x},${synthR.y} C${synthR.x+60},${synthR.y} ${portL.x-60},${portL.y} ${portL.x},${portL.y}`

  const LOOP_COLOR = '#7a6aaf'

  const renderLink = (pathD, pathId, active, dur, delay, thick) => (
    <g key={pathId}>
      <path d={pathD} fill="none" stroke={active ? LINE_ON : LINE_OFF} strokeWidth={active ? (thick ? 1.5 : 1) : 0.7} strokeLinecap="round" opacity={active ? 0.28 : 0.14} />
      <path d={pathD} fill="none" stroke={active ? LINE_ON : LINE_OFF} strokeWidth={active ? 0.7 : 0.5} strokeLinecap="round" strokeDasharray={active ? '3 10' : '3 8'} markerEnd={active ? 'url(#arrow-gray)' : 'url(#arrow-off)'} opacity={active ? 0.25 : 0.18} />
      {active && (<><path id={pathId} d={pathD} fill="none" stroke="none" /><circle r={thick?2:1.5} fill={DOT_FILL} opacity="0"><animateMotion dur={dur} repeatCount="indefinite" begin={delay}><mpath href={`#${pathId}`} /></animateMotion><animate attributeName="opacity" values="0;0.45;0.45;0" keyTimes="0;0.1;0.85;1" dur={dur} repeatCount="indefinite" begin={delay} /></circle></>)}
    </g>
  )

  // Loop renderer — always visible rectangular orbit with orbiting dot
  const renderLoopLink = (pathD, pathId, active) => (
    <g key={pathId}>
      {/* Always show the rectangular loop structure */}
      <path d={pathD} fill="none" stroke={LOOP_COLOR} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" opacity={active ? 0.05 : 0.03} />
      <path d={pathD} fill="none" stroke={LOOP_COLOR} strokeWidth={active ? 1.2 : 0.8} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={active ? '6 5' : '5 6'} opacity={active ? 0.5 : 0.25} />
      {/* Orbiting dot — always visible */}
      <path id={pathId} d={pathD} fill="none" stroke="none" />
      <circle r={active ? 2.2 : 1.8} fill={LOOP_COLOR} opacity={active ? 0.8 : 0.4}>
        <animateMotion dur="4s" repeatCount="indefinite" begin="0s"><mpath href={`#${pathId}`} /></animateMotion>
      </circle>
      <circle r={active ? 5 : 4} fill={LOOP_COLOR} opacity={active ? 0.12 : 0.06}>
        <animateMotion dur="4s" repeatCount="indefinite" begin="0s"><mpath href={`#${pathId}`} /></animateMotion>
      </circle>
    </g>
  )

  return (
    <svg width="100%" viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`} style={{ position: 'absolute', inset: 0, width: CANVAS_W, height: CANVAS_H, pointerEvents: 'none', zIndex: 0, overflow: 'visible' }}>
      <defs>
        <pattern id="dotGrid" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="14" cy="14" r="0.7" fill="#d4d4d8" opacity="0.3" /></pattern>
        <marker id="arrow-gray" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M0,0.5 L0,7.5 L7,4 Z" fill={LINE_ON} opacity="0.6" /></marker>
        <marker id="arrow-off" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto" markerUnits="strokeWidth"><path d="M0,0.5 L0,6.5 L6,3.5 Z" fill={LINE_OFF} opacity="0.4" /></marker>
        <marker id="arrow-loop" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M0,0.5 L0,7.5 L7,4 Z" fill={LOOP_COLOR} opacity="0.9" /></marker>
      </defs>
      <rect width={CANVAS_W} height={CANVAS_H} fill="url(#dotGrid)" />
      {topLines.map(({ path, active, id }, idx) => renderLink(path, `top-${id}`, active, `${1.6+idx*0.25}s`, `${idx*0.35}s`, false))}
      {renderLink(hubToJudge, 'hub-judge', judgeActive||anyTop, '2s', '1.6s', false)}
      {renderLink(hubToSynth, 'hub-synth', synthActive||anyTop, '2.2s', '1.8s', false)}
      {renderLink(hubToPort, 'hub-port', portActive||anyTop, '1.8s', '1.2s', true)}
      {renderLink(synthToPort, 'synth-port', (synthActive||anyTop)&&(portActive||anyTop), '2.4s', '3.0s', false)}
      {renderLink(judgeToPort, 'judge-port', (judgeActive||anyTop)&&(portActive||anyTop), '2.4s', '2.8s', false)}

      {/* LOOP 06 ↔ 08 — rectangular orbit */}
      {renderLoopLink(loopFull, 'loop-06-08', auditActive || synthActive)}

      {anyTop && <circle cx={HUB.x} cy={HUB.y} r="8" fill="none" stroke="#b4b4bc" strokeWidth="0.8" opacity="0"><animate attributeName="r" from="6" to="20" dur="3s" repeatCount="indefinite" /><animate attributeName="opacity" from="0.18" to="0" dur="3s" repeatCount="indefinite" /></circle>}
      <circle cx={HUB.x} cy={HUB.y} r={anyTop?5:3.5} fill={anyTop?'#18181b':'#d4d4d8'} stroke="#e4e4e7" strokeWidth="2" />
      {anyTop && <circle cx={HUB.x} cy={HUB.y} r="2" fill="#fafafa" opacity="0.4" />}
    </svg>
  )
}

function FlowNode({ node, data, judgeData }) {
  const has = !!data, isDark = node.id === 'agent_7'
  return (
    <div style={{ position: 'absolute', left: node.x, top: node.y, width: NW, background: isDark ? '#1e1e22' : '#fff', border: `2px solid ${has ? node.color+'55' : node.color+'25'}`, borderRadius: 10, padding: '10px 12px', boxShadow: has ? `0 2px 10px ${node.color}18` : '0 1px 3px rgba(0,0,0,0.04)', transition: 'all 0.2s ease', minHeight: NH }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = `0 6px 20px ${node.color}28`; e.currentTarget.style.transform = 'translateY(-1px)' }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = has ? `0 2px 10px ${node.color}18` : '0 1px 3px rgba(0,0,0,0.04)'; e.currentTarget.style.transform = 'translateY(0)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: has ? 6 : 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 22, height: 22, borderRadius: 6, flexShrink: 0, background: node.color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, fontWeight: 800, color: '#fff', fontFamily: 'var(--f-mono)' }}>{node.num}</div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, lineHeight: 1.2, color: isDark ? '#e2e8f0' : '#09090b' }}>{node.label}</div>
            <div style={{ fontSize: 8, marginTop: 1, color: isDark ? '#6b7280' : '#a1a1aa' }}>{node.sub}</div>
          </div>
        </div>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: has ? '#4a9065' : '#e4e4e7', flexShrink: 0 }} />
      </div>
      {has && <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}><Chip value={data.outlook} map={C} size="sm" />{judgeData?.overall && <Chip value={judgeData.overall} map={Q} size="sm" />}</div>}
      {!has && <div style={{ fontSize: 9, color: isDark ? '#6b7280' : '#a1a1aa', marginTop: 2 }}>Waiting…</div>}
    </div>
  )
}

// ─── AGENT DETAIL CARD ───────────────────────
const AGENT_INFO = {
  agent_1: { num: '01', label: 'Sentiment',   sub: 'News · Social · Analyst',  color: '#5b7fb5' },
  agent_2: { num: '02', label: 'Technical',   sub: 'Price · Indicators',        color: '#8b6aaf' },
  agent_3: { num: '03', label: 'Fundamental', sub: 'Earnings · Valuation',      color: '#4d8a5e' },
  agent_4: { num: '04', label: 'Macro',       sub: 'Rates · Economy',           color: '#c07a3e' },
}

function AgentDetailCard({ id, data, judgeData, relData, open, onToggle }) {
  const info = AGENT_INFO[id]
  if (!info) return null
  const has = !!data, pct = relData ? Math.round((relData.score_avg || 0) * 100) : 0
  return (
    <div style={{ background: '#fff', border: `1.5px solid ${has ? info.color+'40' : '#e4e4e7'}`, borderRadius: 12, overflow: 'hidden', transition: 'box-shadow 0.2s', boxShadow: open ? `0 6px 24px ${info.color}15` : '0 1px 3px rgba(0,0,0,0.04)' }}>
      <div onClick={() => has && onToggle(id)} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', cursor: has ? 'pointer' : 'default', userSelect: 'none', background: open ? '#fafbfc' : '#fff' }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: has ? info.color : '#f4f4f5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, color: has ? '#fff' : '#a1a1aa', fontFamily: 'var(--f-mono)', flexShrink: 0 }}>{info.num}</div>
        <div style={{ flex: 1 }}><div style={{ fontSize: 13, fontWeight: 700, color: has ? '#09090b' : '#a1a1aa' }}>{info.label}</div><div style={{ fontSize: 9, color: '#a1a1aa' }}>{info.sub}</div></div>
        {has && <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}><Chip value={data.outlook} map={C} size="sm" />{judgeData?.overall && <Chip value={judgeData.overall} map={Q} size="sm" />}</div>}
        <div style={{ width: 7, height: 7, borderRadius: '50%', background: has ? '#4a9065' : '#e4e4e7', flexShrink: 0 }} />
        {has && <span style={{ fontSize: 11, color: '#a1a1aa', display: 'inline-block', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>▾</span>}
      </div>
      {open && has && (
        <div style={{ padding: '16px 18px', borderTop: '1px solid #f0f0f2' }}>
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginBottom: 14 }}>
            {judgeData && <div style={{ display: 'flex', gap: 6 }}>{[['Coherence',judgeData.coherence],['Completeness',judgeData.completeness],['Data Adherence',judgeData.data_adherence]].map(([k,v])=><div key={k} style={{background:'#fafafa',border:'1px solid #e4e4e7',borderRadius:8,padding:'8px 14px',textAlign:'center'}}><div style={{fontSize:9,color:'#9ca3af',fontWeight:600,marginBottom:4}}>{k}</div><Chip value={v} map={Q} /></div>)}</div>}
            {pct > 0 && <div style={{ minWidth: 160, alignSelf: 'center' }}><div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}><span style={{fontSize:10,color:'#9ca3af'}}>Reliability</span><span style={{fontSize:10,color:'#71717a',fontWeight:600}}>{pct}% · {relData.runs} runs</span></div><BarLine pct={pct} /></div>}
          </div>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            {data.key_points?.length > 0 && <div style={{flex:1,minWidth:220}}><div style={{fontSize:10,fontWeight:700,color:'#4a9065',marginBottom:6,letterSpacing:0.5}}>KEY POINTS</div>{data.key_points.slice(0,3).map((kp,i)=><div key={i} style={{display:'flex',gap:6,marginBottom:4}}><span style={{fontSize:10,color:'#4a9065',flexShrink:0,marginTop:2}}>↑</span><span style={{fontSize:11,color:'#52525b',lineHeight:1.6}}>{kp}</span></div>)}</div>}
            {data.risks?.length > 0 && <div style={{flex:1,minWidth:220}}><div style={{fontSize:10,fontWeight:700,color:'#b85450',marginBottom:6,letterSpacing:0.5}}>RISKS</div>{data.risks.slice(0,2).map((r,i)=><div key={i} style={{display:'flex',gap:6,marginBottom:4}}><span style={{fontSize:10,color:'#b85450',flexShrink:0,marginTop:2}}>↓</span><span style={{fontSize:11,color:'#52525b',lineHeight:1.6}}>{r}</span></div>)}</div>}
          </div>
          {judgeData?.notes && <div style={{marginTop:12,padding:'10px 14px',background:'#faf8f4',borderRadius:8,border:'1px solid #e8dcc8'}}><span style={{fontSize:10,fontWeight:700,color:'#a07840'}}>Judge — </span><span style={{fontSize:11,color:'#7a6035',lineHeight:1.6}}>{judgeData.notes}</span></div>}
        </div>
      )}
    </div>
  )
}

// ─── PIPELINE VIEW ───────────────────────────
export function PipelineView({ agents, judge, reliability }) {
  const [openCard, setOpenCard] = useState(null)
  const toggleCard = id => setOpenCard(o => o === id ? null : id)
  const counts = { BULLISH: 0, NEUTRAL: 0, BEARISH: 0 }
  PIPE_NODES.slice(0, 4).forEach(n => { if (agents[n.id]?.outlook) counts[agents[n.id].outlook]++ })
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#18181b' }}>Agent Pipeline</span>
        <div style={{ flex: 1, height: '1.5px', background: 'linear-gradient(90deg,#e4e4e7,transparent)' }} />
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {['BULLISH','NEUTRAL','BEARISH'].map(o => counts[o] > 0 && <span key={o} style={{fontSize:11,fontWeight:700,color:C[o].color,background:C[o].bg,border:`1px solid ${C[o].border}`,borderRadius:5,padding:'2px 8px'}}>{o[0]} {counts[o]}/4</span>)}
          {top && top[1] > 0 && <span style={{fontSize:11,color:'#6b7280'}}>Consensus: <strong style={{color:C[top[0]]?.color}}>{top[0]}</strong></span>}
        </div>
      </div>
      <div style={{ position: 'relative', width: '100%', overflowX: 'auto', background: '#fafbfc', borderRadius: 16, border: '1px solid #e8eaed', padding: '16px 0' }}>
        <div style={{ position: 'relative', width: CANVAS_W, height: CANVAS_H, margin: '0 auto' }}>
          <PipelineSVG agents={agents} />
          <div style={{ position: 'absolute', top: 8, left: 0, right: 0, display: 'flex', justifyContent: 'center', pointerEvents: 'none' }}><span style={{fontSize:9,fontWeight:700,color:'#b4b4bc',letterSpacing:1.2}}>① DATA COLLECTION</span></div>
          {PIPE_NODES.map(node => <FlowNode key={node.id} node={node} data={agents[node.id]} judgeData={judge[node.id]} />)}
        </div>
      </div>
      <div style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <span style={{fontSize:13,fontWeight:700,color:'#18181b'}}>Agent Details</span>
          <div style={{flex:1,height:'1.5px',background:'linear-gradient(90deg,#e4e4e7,transparent)'}} />
          <span style={{fontSize:10,color:'#a1a1aa'}}>Click to expand</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {PIPE_NODES.slice(0,4).map(node => <AgentDetailCard key={node.id} id={node.id} data={agents[node.id]} judgeData={judge[node.id]} relData={reliability[node.id]} open={openCard===node.id} onToggle={toggleCard} />)}
        </div>
      </div>
    </div>
  )
}

// ─── JUDGE PANEL ─────────────────────────────
const ANAMES = { agent_1: { num: '01', label: 'Sentiment' }, agent_2: { num: '02', label: 'Technical' }, agent_3: { num: '03', label: 'Fundamental' }, agent_4: { num: '04', label: 'Macro' } }

export function JudgePanel({ judge, reliability }) {
  const ids = ['agent_1','agent_2','agent_3','agent_4']
  return (
    <Card style={{ padding: '20px 22px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: '#a07840', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, color: '#fff', fontFamily: 'var(--f-mono)', flexShrink: 0 }}>05</div>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#18181b' }}>Judge — Agent Evaluation</span>
        <div style={{ flex: 1, height: '1.5px', background: 'linear-gradient(90deg,#e4e4e7,transparent)' }} />
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 20 }}>
        <thead><tr style={{ background: '#fafafa' }}>{['Agent','Reliability','Coh','Comp','Data','Overall'].map(h=><th key={h} style={{fontSize:10,fontWeight:700,color:'#71717a',textAlign:h==='Agent'||h==='Reliability'?'left':'center',padding:'8px 6px',borderBottom:'2px solid #e4e4e7'}}>{h}</th>)}</tr></thead>
        <tbody>{ids.map((id,i) => {
          const j = judge[id], rel = reliability[id]; if (!j && !rel) return null
          const pct = rel ? Math.round((rel.score_avg||0)*100) : 0, info = ANAMES[id]
          return (<tr key={id} style={{background:i%2===0?'#fff':'#fafafa'}}>
            <td style={{padding:'12px 6px',borderBottom:'1px solid #f4f4f5'}}><div style={{display:'flex',alignItems:'center',gap:7}}><span style={{fontSize:9,fontWeight:700,fontFamily:'var(--f-mono)',color:'#a1a1aa'}}>{info.num}</span><span style={{fontSize:13,fontWeight:700,color:'#09090b'}}>{info.label}</span></div></td>
            <td style={{padding:'12px 6px',borderBottom:'1px solid #f4f4f5',minWidth:120}}><div style={{display:'flex',alignItems:'center',gap:8}}><div style={{flex:1}}><BarLine pct={pct} /></div><span style={{fontSize:10,color:'#71717a',whiteSpace:'nowrap',fontWeight:600}}>{pct}% · {rel?.runs||0}r</span></div></td>
            {['coherence','completeness','data_adherence'].map(k=><td key={k} style={{textAlign:'center',padding:'12px 4px',borderBottom:'1px solid #f4f4f5'}}><Chip value={j?.[k]} map={Q} size="sm" /></td>)}
            <td style={{textAlign:'center',padding:'12px 6px',borderBottom:'1px solid #f4f4f5'}}><Chip value={j?.overall} map={Q} /></td>
          </tr>)
        })}</tbody>
      </table>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {ids.map(id => judge[id]?.notes && <div key={id} style={{padding:'13px 16px',background:'#faf8f4',borderRadius:9,border:'1px solid #e8dcc8',borderLeft:'3px solid #c4a060'}}>
          <div style={{display:'flex',alignItems:'center',gap:6,marginBottom:5}}><span style={{fontSize:9,fontWeight:700,fontFamily:'var(--f-mono)',color:'#a07840',letterSpacing:0.5}}>{ANAMES[id].num}</span><strong style={{fontSize:12,fontWeight:700,color:'#6b5530'}}>{ANAMES[id].label}</strong></div>
          <span style={{fontSize:11.5,color:'#52525b',lineHeight:1.7}}>{judge[id].notes}</span>
        </div>)}
      </div>
    </Card>
  )
}

// ─── JUDGE QUALITY OVER TIME (GLOBAL) ────────
const AG_COLORS = { agent_1: '#5b7fb5', agent_2: '#8b6aaf', agent_3: '#4d8a5e', agent_4: '#c07a3e' }
const AG_LABELS = { agent_1: '01 Sentiment', agent_2: '02 Technical', agent_3: '03 Fundamental', agent_4: '04 Macro' }
const AG_NUMS   = { agent_1: '01', agent_2: '02', agent_3: '03', agent_4: '04' }
const SCORE_VAL = { HIGH: 3, MEDIUM: 2, LOW: 1 }

function AgentQualityMiniChart({ agentId, runs, color }) {
  const pts = runs.filter(r => r.scores[agentId] != null)
  if (pts.length < 1) return (
    <div style={{ flex: 1, minWidth: 180, background: '#fafafa', border: '1px solid #e4e4e7', borderRadius: 10, padding: '14px 16px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <span style={{ fontSize: 10, color: '#a1a1aa' }}>No data yet</span>
    </div>
  )

  const W = 320, H = 130, P = { top: 16, right: 12, bottom: 36, left: 36 }
  const iW = W - P.left - P.right, iH = H - P.top - P.bottom
  const xS = i => P.left + (pts.length === 1 ? iW / 2 : (i / (pts.length - 1)) * iW)
  const yS = v => P.top + iH - ((v - 0.5) / 2.5) * iH

  // Compute avg and trend
  const scores = pts.map(p => p.scores[agentId])
  const avg = scores.reduce((s, v) => s + v, 0) / scores.length
  const mid = Math.floor(scores.length / 2)
  const recentAvg = scores.slice(mid).reduce((s,v)=>s+v,0) / scores.slice(mid).length
  const olderAvg  = mid > 0 ? scores.slice(0,mid).reduce((s,v)=>s+v,0) / scores.slice(0,mid).length : recentAvg
  const trend = scores.length < 3 ? null : recentAvg > olderAvg + 0.2 ? '↑' : recentAvg < olderAvg - 0.2 ? '↓' : '→'
  const trendColor = trend === '↑' ? '#4a9065' : trend === '↓' ? '#b85450' : '#71717a'
  const avgLabel = avg >= 2.5 ? 'HIGH' : avg >= 1.5 ? 'MED' : 'LOW'

  const polyPoints = pts.map((p, i) => `${xS(i)},${yS(p.scores[agentId])}`).join(' ')

  return (
    <div style={{ flex: 1, minWidth: 180, background: '#fff', border: `1.5px solid ${color}22`, borderTop: `3px solid ${color}`, borderRadius: 10, padding: '14px 16px', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 9, fontWeight: 800, fontFamily: 'var(--f-mono)', color: '#fff', background: color, borderRadius: 4, padding: '1px 5px' }}>{AG_NUMS[agentId]}</span>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#09090b' }}>{AG_LABELS[agentId].slice(3)}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ fontSize: 10, fontWeight: 700, color, fontFamily: 'var(--f-mono)' }}>{avgLabel}</span>
          {trend && <span style={{ fontSize: 12, fontWeight: 800, color: trendColor }}>{trend}</span>}
        </div>
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ overflow: 'visible' }}>
        {/* Grid lines */}
        {[1,2,3].map(v => (
          <g key={v}>
            <line x1={P.left} y1={yS(v)} x2={W-P.right} y2={yS(v)} stroke={v===2?`${color}20`:'#f0f0f2'} strokeWidth={v===2?1.5:1} strokeDasharray={v===2?'none':'3 4'} />
            <text x={P.left-4} y={yS(v)+4} fontSize="9" fill="#c4c4c8" textAnchor="end" fontFamily="monospace">{v===3?'H':v===2?'M':'L'}</text>
          </g>
        ))}
        {/* Area fill */}
        <polygon
          points={`${xS(0)},${yS(0.5)} ${polyPoints} ${xS(pts.length-1)},${yS(0.5)}`}
          fill={color} opacity="0.06"
        />
        {/* Line */}
        <polyline points={polyPoints} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" opacity="0.9" />
        {/* Dots */}
        {pts.map((p, i) => (
          <circle key={i} cx={xS(i)} cy={yS(p.scores[agentId])} r="3.5" fill={color} stroke="#fff" strokeWidth="1.5" />
        ))}
        {/* X labels */}
        {pts.map((p, i) => (pts.length <= 10 || i % Math.ceil(pts.length / 10) === 0) && (
          <text key={i} x={xS(i)} y={H - 4} fontSize="8" fill="#a1a1aa" textAnchor="middle" fontFamily="monospace"
            transform={pts.length > 6 ? `rotate(-30,${xS(i)},${H-4})` : ''}>{p.label}</text>
        ))}
      </svg>
      <div style={{ marginTop: 4, fontSize: 9, color: '#a1a1aa' }}>{pts.length} eval · avg {avg.toFixed(1)}/3{trend ? ` · ${trend === '↑' ? 'improving' : trend === '↓' ? 'declining' : 'stable'}` : ''}</div>
    </div>
  )
}

export function JudgeHistoryChart({ history }) {
  const runs = [], runMap = new Map()
  history.forEach(h => {
    const key = `${h.ticker} ${h.date}`
    if (!runMap.has(key)) { runMap.set(key, { label: `${h.ticker} ${h.date.slice(5)}`, scores: {} }); runs.push(runMap.get(key)) }
    runMap.get(key).scores[h.agent_id] = SCORE_VAL[h.overall] || 2
  })
  if (runs.length < 1) return null

  return (
    <Card style={{ padding: '20px 22px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: '#a07840', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, color: '#fff', fontFamily: 'var(--f-mono)', flexShrink: 0 }}>05</div>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#18181b' }}>Judge — Agent Quality Over Time</span>
        <div style={{ flex: 1, height: '1.5px', background: 'linear-gradient(90deg,#e4e4e7,transparent)' }} />
        <span style={{ fontSize: 10, color: '#a1a1aa' }}>All tickers · {runs.length} evaluations</span>
      </div>
      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
        {['agent_1','agent_2','agent_3','agent_4'].map(id => (
          <AgentQualityMiniChart key={id} agentId={id} runs={runs} color={AG_COLORS[id]} />
        ))}
      </div>
      <div style={{ marginTop: 10 }}><span style={{ fontSize: 9, color: '#d4d4d8' }}>H=HIGH · M=MEDIUM · L=LOW · Score 1-3 · Trend based on first vs second half of evaluations</span></div>
    </Card>
  )
}

// ─── PREDICTION AUDIT (GLOBAL) ───────────────
const HLABEL_A = { '1_week': '1 Week', '1_month': '1 Month', '1_quarter': '1 Quarter' }

// ─── AUDIT AGGREGATION (frontend, mirrors agent_8 Python logic) ──────────────
function aggregateAuditStats(audits) {
  // Group by horizon and compute aggregate statistics
  const SCORE = { HIGH: 3, MEDIUM: 2, LOW: 1 }
  const byHorizon = {}
  audits.forEach(a => {
    if (!byHorizon[a.horizon]) byHorizon[a.horizon] = []
    byHorizon[a.horizon].push(a)
  })
  const stats = {}
  Object.entries(byHorizon).forEach(([horizon, records]) => {
    const rqScores = records.map(r => SCORE[r.reasoning_quality] || 2)
    const accScores = records.map(r => SCORE[r.accuracy_score] || 2)
    const calScores = records.map(r => SCORE[r.confidence_calibration] || 2)
    const avg = arr => arr.length ? (arr.reduce((s,v)=>s+v,0)/arr.length) : null
    const biasCounts = {}
    records.forEach(r => { biasCounts[r.bias || 'NEUTRAL'] = (biasCounts[r.bias || 'NEUTRAL'] || 0) + 1 })
    const dominantBias = Object.entries(biasCounts).sort((a,b)=>b[1]-a[1])[0]?.[0] || 'NEUTRAL'
    const hasBias = dominantBias !== 'NEUTRAL' && (biasCounts[dominantBias] || 0) > records.length * 0.5
    // Trend: compare first half vs second half
    let trend = 'insufficient_data'
    if (rqScores.length >= 4) {
      const mid = Math.floor(rqScores.length / 2)
      const recent = avg(rqScores.slice(0, mid)), older = avg(rqScores.slice(mid))
      trend = recent > older + 0.3 ? 'improving' : recent < older - 0.3 ? 'degrading' : 'stable'
    }
    stats[horizon] = {
      n: records.length,
      avgRq: avg(rqScores), avgAcc: avg(accScores), avgCal: avg(calScores),
      dominantBias, hasBias, biasCounts, trend,
      recentNotes: records.slice(0, 3).map(r => r.notes).filter(Boolean)
    }
  })
  return stats
}

const TREND_ICON = { improving: '↑', degrading: '↓', stable: '→', insufficient_data: '·' }
const TREND_COLOR = { improving: '#4a9065', degrading: '#b85450', stable: '#71717a', insufficient_data: '#a1a1aa' }

export function PredictionAuditPanel({ audits }) {
  const groups = new Map()
  audits.forEach(a => { const k=`${a.ticker}|${a.date}`; if(!groups.has(k)) groups.set(k,{ticker:a.ticker,date:a.date,audits:[]}); groups.get(k).audits.push(a) })
  const groupList = Array.from(groups.values())
  const [expanded, setExpanded] = useState(null)

  // Global aggregation across all audits (for the summary at the top)
  const globalStats = aggregateAuditStats(audits)

  return (
    <Card style={{ padding: '20px 22px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: '#7a6aaf', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, color: '#fff', fontFamily: 'var(--f-mono)', flexShrink: 0 }}>08</div>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#18181b' }}>Prediction Auditor — All Tickers</span>
        <div style={{ flex: 1, height: '1.5px', background: 'linear-gradient(90deg,#e4e4e7,transparent)' }} />
        <span style={{ fontSize: 10, color: '#a1a1aa' }}>{audits.length} audits · Agent 08 Sonnet</span>
      </div>

      {/* Aggregate summary by horizon — monochrome */}
      {Object.keys(globalStats).length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 18 }}>
          {['1_week','1_month','1_quarter'].map(h => {
            const s = globalStats[h]; if (!s) return null
            const trend = s.trend, tIcon = TREND_ICON[trend]
            const barWidth = v => `${Math.round((v / 3) * 100)}%`
            const biasLabel = s.dominantBias === 'BULLISH_BIAS' ? 'Bullish Bias' : s.dominantBias === 'BEARISH_BIAS' ? 'Bearish Bias' : 'Neutral'
            return (
              <div key={h} style={{ background: '#fafafa', border: '1px solid #e4e4e7', borderRadius: 12, padding: '16px 18px', position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: '#18181b' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                  <span style={{ fontSize: 12, fontWeight: 800, color: '#18181b', letterSpacing: 0.3 }}>{HLABEL_A[h]?.toUpperCase()}</span>
                  <span style={{ fontSize: 10, fontWeight: 700, color: '#71717a', background: '#f4f4f5', padding: '2px 8px', borderRadius: 4 }}>{tIcon} {trend}</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {[['Reasoning', s.avgRq], ['Accuracy', s.avgAcc], ['Calibration', s.avgCal]].map(([label, val]) => (
                    <div key={label}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontSize: 10, color: '#71717a', fontWeight: 600 }}>{label}</span>
                        <span style={{ fontSize: 10, fontWeight: 800, color: '#18181b', fontFamily: 'var(--f-mono)' }}>{val?.toFixed(1)}/3</span>
                      </div>
                      <div style={{ height: 6, background: '#e4e4e7', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: barWidth(val), borderRadius: 3, background: '#71717a', transition: 'width 0.5s' }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 12, padding: '8px 12px', background: '#f4f4f5', borderRadius: 8, border: '1px solid #e4e4e7', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#18181b' }} />
                    <span style={{ fontSize: 10, fontWeight: 700, color: '#18181b' }}>{biasLabel}</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#71717a', fontFamily: 'var(--f-mono)' }}>{s.n} samples</span>
                </div>
                {s.hasBias && (
                  <div style={{ marginTop: 6, fontSize: 9, color: '#52525b', fontWeight: 600 }}>
                    ⚠ Systematic bias detected — Agent 06 is self-correcting
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {groupList.length === 0 ? <p style={{fontSize:12,color:'#a1a1aa',textAlign:'center',padding:'20px 0'}}>No prediction audits yet</p> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {groupList.map(g => {
            const key = `${g.ticker}|${g.date}`, isOpen = expanded === key
            const sorted = ['1_week','1_month','1_quarter'].map(h => g.audits.find(a=>a.horizon===h)).filter(Boolean)
            const groupStats = aggregateAuditStats(g.audits)
            return (
              <div key={key} style={{ border: '1px solid #e4e4e7', borderRadius: 10, overflow: 'hidden', boxShadow: isOpen ? '0 4px 16px rgba(0,0,0,0.08)' : 'none' }}>
                <div onClick={() => setExpanded(isOpen ? null : key)} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', cursor: 'pointer', userSelect: 'none', background: isOpen ? '#fafbfc' : '#fff' }}>
                  <span style={{fontSize:12,fontWeight:700,fontFamily:'var(--f-mono)',color:'#09090b',background:'#f4f4f5',padding:'2px 8px',borderRadius:4}}>{g.ticker}</span>
                  <span style={{fontSize:11,color:'#a1a1aa',fontFamily:'var(--f-mono)'}}>{g.date}</span>
                  <div style={{flex:1}} />
                  {sorted.slice(0,3).map(a => <Chip key={a.horizon} value={a.reasoning_quality} map={Q} size="sm" />)}
                  {/* Systematic bias badge */}
                  {Object.values(groupStats).some(s => s.hasBias) && (
                    <span style={{ fontSize: 9, fontWeight: 700, color: '#ea580c', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 4, padding: '1px 6px' }}>bias</span>
                  )}
                  <span style={{fontSize:11,color:'#a1a1aa',transform:isOpen?'rotate(180deg)':'none',transition:'transform 0.2s'}}>▾</span>
                </div>
                {isOpen && (
                  <div style={{ borderTop: '1px solid #f0f0f2', padding: 16 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead><tr style={{background:'#fafafa'}}>{['Horizon','Reasoning','Accuracy','Bias','Calibration','Trend'].map(h=><th key={h} style={{fontSize:10,fontWeight:700,color:'#71717a',textAlign:'center',padding:'8px 6px',borderBottom:'2px solid #e4e4e7'}}>{h}</th>)}</tr></thead>
                      <tbody>{sorted.map((a,i) => {
                        const hs = groupStats[a.horizon] || {}
                        return (
                          <tr key={a.horizon} style={{background:i%2===0?'#fff':'#fafafa'}}>
                            <td style={{padding:'10px 8px',borderBottom:'1px solid #f4f4f5',fontWeight:700,fontSize:11,color:'#09090b'}}>{HLABEL_A[a.horizon]||a.horizon}</td>
                            <td style={{textAlign:'center',padding:'10px 4px',borderBottom:'1px solid #f4f4f5'}}><Chip value={a.reasoning_quality} map={Q} size="sm" /></td>
                            <td style={{textAlign:'center',padding:'10px 4px',borderBottom:'1px solid #f4f4f5'}}><Chip value={a.accuracy_score} map={Q} size="sm" /></td>
                            <td style={{textAlign:'center',padding:'10px 4px',borderBottom:'1px solid #f4f4f5'}}><Chip value={a.bias} map={BIAS_MAP} size="sm" /></td>
                            <td style={{textAlign:'center',padding:'10px 4px',borderBottom:'1px solid #f4f4f5'}}><Chip value={a.confidence_calibration} map={Q} size="sm" /></td>
                            <td style={{textAlign:'center',padding:'10px 4px',borderBottom:'1px solid #f4f4f5'}}>
                              <span style={{ fontSize: 11, fontWeight: 700, color: TREND_COLOR[hs.trend] || '#a1a1aa' }}>{TREND_ICON[hs.trend] || '·'}</span>
                            </td>
                          </tr>
                        )
                      })}</tbody>
                    </table>
                    {sorted.map(a => {
                      const hs = groupStats[a.horizon] || {}
                      return (
                        <div key={a.horizon}>
                          {a.notes && <div style={{marginTop:8,padding:'10px 14px',background:'#f8f6fc',borderRadius:8,border:'1px solid #e0d8f0',borderLeft:'3px solid #7a6aaf'}}>
                            <span style={{fontSize:10,fontWeight:700,color:'#7a6aaf'}}>{HLABEL_A[a.horizon]} — </span>
                            <span style={{fontSize:11,color:'#52525b',lineHeight:1.6}}>{a.notes}</span>
                          </div>}
                          {hs.hasBias && <div style={{marginTop:6,padding:'8px 12px',background:'#fff7ed',borderRadius:7,border:'1px solid #fed7aa',display:'flex',alignItems:'center',gap:8}}>
                            <span style={{fontSize:10,fontWeight:700,color:'#ea580c'}}>⚠ {HLABEL_A[a.horizon]}</span>
                            <span style={{fontSize:10,color:'#c2410c'}}>systematic {hs.dominantBias.replace('_',' ')} detected across {hs.n} audits — Agent 06 is self-correcting</span>
                          </div>}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}

// ─── PREDICTIONS ─────────────────────────────
const HLABEL = { '1_week': '1 Week', '1_month': '1 Month', '1_quarter': '1 Quarter' }
const CWIDTH = { HIGH: '100%', MEDIUM: '60%', LOW: '25%' }

function PredCard({ pred, audit }) {
  const s = C[pred.outlook] || {}
  const bullets = Array.isArray(pred.bullets) ? pred.bullets.filter(Boolean) : []
  const selfCorrected = audit && (audit.bias !== 'NEUTRAL' || audit.confidence_calibration === 'LOW')
  return (
    <div style={{ flex: 1, minWidth: 160, background: '#fff', border: '1.5px solid #e4e4e7', borderRadius: 12, padding: '18px 20px', position: 'relative', overflow: 'hidden', boxShadow: '0 2px 8px rgba(0,0,0,0.07)' }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: s.color || '#e4e4e7' }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: '#a1a1aa', letterSpacing: 0.5 }}>{HLABEL[pred.horizon]}</span>
        {selfCorrected && (
          <span title="Agent 06 applied self-correction from Auditor feedback" style={{ fontSize: 9, fontWeight: 700, color: '#7a6aaf', background: '#f8f6fc', border: '1px solid #e0d8f0', borderRadius: 4, padding: '1px 6px', cursor: 'default' }}>✦ self-corrected</span>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 14 }}>
        <span style={{ fontSize: 28, fontWeight: 800, color: '#09090b', letterSpacing: '-1.5px' }}>${pred.price_target}</span>
        <Chip value={pred.outlook} map={C} size="sm" />
      </div>
      <div style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
          <span style={{fontSize:10,color:'#a1a1aa'}}>Confidence</span>
          <span style={{fontSize:10,fontWeight:700,color:'#52525b'}}>{pred.confidence}</span>
        </div>
        <div style={{ height: 4, background: '#f4f4f5', borderRadius: 2 }}>
          <div style={{ height: '100%', width: CWIDTH[pred.confidence]||'50%', borderRadius: 2, background: s.color||'#d4d4d8', transition: 'width 0.5s' }} />
        </div>
      </div>
      {bullets.length > 0 && <div style={{display:'flex',flexDirection:'column',gap:6,marginBottom:12}}>{bullets.map((b,i)=><div key={i} style={{display:'flex',gap:8,alignItems:'flex-start'}}><span style={{fontSize:10,color:BULL_COL[i],marginTop:3,flexShrink:0,fontWeight:700}}>{BULL_ICON[i]}</span><span style={{fontSize:11,color:'#52525b',lineHeight:1.6}}>{b}</span></div>)}</div>}
      {pred.reasoning && <p style={{fontSize:10,color:'#a1a1aa',lineHeight:1.6,borderTop:'1px solid #f4f4f5',paddingTop:10}}>{pred.reasoning.slice(0,160)}{pred.reasoning.length>160?'…':''}</p>}
      {/* Audit context sotto la card */}
      {audit && (
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #f4f4f5', display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 9, color: '#a1a1aa', fontWeight: 600 }}>Audit 08</span>
          <Chip value={audit.reasoning_quality} map={Q} size="sm" />
          <Chip value={audit.bias} map={BIAS_MAP} size="sm" />
          {audit.confidence_calibration === 'LOW' && (
            <span style={{ fontSize: 9, fontWeight: 700, color: '#b85450', background: '#faf4f4', border: '1px solid #daa8a6', borderRadius: 4, padding: '1px 6px' }}>cal LOW</span>
          )}
        </div>
      )}
    </div>
  )
}

export function PredictionsPanel({ predictions, ticker, predAudits = [] }) {
  const sorted = ['1_week','1_month','1_quarter'].map(h => predictions.find(p=>p.horizon===h)).filter(Boolean)
  // Trova gli audit sincronizzati con la data delle predictions correnti
  const latestDate = sorted[0]?.date
  const todayAudits = predAudits
    .filter(a => a.ticker === ticker && a.date === latestDate)
    .reduce((acc, a) => { acc[a.horizon] = a; return acc }, {})
  const anySelfCorrected = Object.values(todayAudits).some(a => a.bias !== 'NEUTRAL' || a.confidence_calibration === 'LOW')
  return (
    <Card style={{ padding: '20px 22px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <div style={{width:28,height:28,borderRadius:7,background:'#4d8a9a',display:'flex',alignItems:'center',justifyContent:'center',fontSize:10,fontWeight:800,color:'#fff',fontFamily:'var(--f-mono)',flexShrink:0}}>06</div>
        <span style={{fontSize:13,fontWeight:700,color:'#18181b'}}>Predictions — {ticker}</span>
        <div style={{flex:1,height:'1.5px',background:'linear-gradient(90deg,#e4e4e7,transparent)'}} />
        {anySelfCorrected && (
          <span title="Agent 06 applied self-corrections from Auditor feedback on at least one horizon" style={{ fontSize: 10, fontWeight: 700, color: '#7a6aaf', background: '#f8f6fc', border: '1px solid #e0d8f0', borderRadius: 5, padding: '3px 8px' }}>✦ self-corrected</span>
        )}
      </div>
      {!sorted.length ? <p style={{fontSize:12,color:'#a1a1aa',textAlign:'center',padding:'24px 0'}}>No predictions yet</p>
        : <div style={{display:'flex',gap:14,flexWrap:'wrap'}}>{sorted.map(p=><PredCard key={p.horizon} pred={p} audit={todayAudits[p.horizon]} />)}</div>}
    </Card>
  )
}

// ─── PREDICTION LEARNING CURVE ───────────────
const H_COLORS = { '1_week': '#5b7fb5', '1_month': '#4d8a5e', '1_quarter': '#c07a3e' }
const H_LABELS = { '1_week': '1 Week', '1_month': '1 Month', '1_quarter': '1 Quarter' }

export function PredictionLearningChart({ resolvedPredictions }) {
  if (!resolvedPredictions || resolvedPredictions.length === 0) return null

  // Raggruppa per orizzonte e ordina per data
  const byHorizon = {}
  resolvedPredictions.forEach(p => {
    if (p.error_pct == null) return
    if (!byHorizon[p.horizon]) byHorizon[p.horizon] = []
    byHorizon[p.horizon].push({ date: p.date, absError: Math.abs(p.error_pct), signedError: p.error_pct, confidence: p.confidence })
  })

  // Ordina per data
  Object.keys(byHorizon).forEach(h => {
    byHorizon[h].sort((a, b) => a.date > b.date ? 1 : -1)
  })

  const horizons = Object.keys(byHorizon).filter(h => byHorizon[h].length >= 2)
  if (horizons.length === 0) return null

  // Calcola rolling avg (finestra 3) per smussare la curva
  const rollingAvg = (arr, key, window = 3) => {
    return arr.map((_, i) => {
      const slice = arr.slice(Math.max(0, i - window + 1), i + 1)
      return slice.reduce((s, v) => s + v[key], 0) / slice.length
    })
  }

  // Tutte le date uniche per l'asse X
  const allDates = [...new Set(resolvedPredictions.filter(p => p.error_pct != null).map(p => p.date))].sort()

  const W = 800, H = 220
  const P = { top: 30, right: 30, bottom: 50, left: 55 }
  const iW = W - P.left - P.right, iH = H - P.top - P.bottom

  // Max error per scala Y (cap a 20% per leggibilità)
  const allErrors = Object.values(byHorizon).flat().map(p => Math.abs(p.absError))
  const maxErr = Math.min(Math.max(...allErrors) * 1.1, 20)

  const xS = date => {
    const i = allDates.indexOf(date)
    return allDates.length === 1 ? P.left + iW / 2 : P.left + (i / (allDates.length - 1)) * iW
  }
  const yS = v => P.top + iH - (Math.min(v, maxErr) / maxErr) * iH

  // Stats summary per ogni orizzonte
  const stats = {}
  horizons.forEach(h => {
    const pts = byHorizon[h]
    const errors = pts.map(p => p.absError)
    const signed = pts.map(p => p.signedError)
    const avg = arr => arr.reduce((s, v) => s + v, 0) / arr.length
    // Trend: confronta prima vs seconda metà
    const mid = Math.floor(errors.length / 2)
    const recentAvg = avg(errors.slice(mid))
    const olderAvg = avg(errors.slice(0, mid))
    const improving = recentAvg < olderAvg - 0.3
    const degrading = recentAvg > olderAvg + 0.3
    stats[h] = {
      n: pts.length,
      avgError: avg(errors).toFixed(1),
      avgSigned: avg(signed).toFixed(1),
      trend: improving ? 'improving' : degrading ? 'degrading' : 'stable',
      recentAvg: recentAvg.toFixed(1),
    }
  })

  return (
    <Card style={{ padding: '20px 22px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: '#4d8a9a', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, color: '#fff', fontFamily: 'var(--f-mono)', flexShrink: 0 }}>06</div>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#18181b' }}>Prediction Learning Curve</span>
        <div style={{ flex: 1, height: '1.5px', background: 'linear-gradient(90deg,#e4e4e7,transparent)' }} />
        <span style={{ fontSize: 10, color: '#a1a1aa' }}>{resolvedPredictions.filter(p => p.error_pct != null).length} resolved · all tickers</span>
      </div>

      {/* Stats summary per orizzonte */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 10, marginBottom: 16 }}>
        {horizons.map(h => {
          const s = stats[h]
          const tc = TREND_COLOR[s.trend], ti = TREND_ICON[s.trend]
          const biasColor = parseFloat(s.avgSigned) > 1 ? '#b85450' : parseFloat(s.avgSigned) < -1 ? '#5b7fb5' : '#4a9065'
          return (
            <div key={h} style={{ background: '#fafafa', border: `1px solid ${H_COLORS[h]}30`, borderLeft: `3px solid ${H_COLORS[h]}`, borderRadius: 8, padding: '10px 14px' }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: H_COLORS[h], marginBottom: 6 }}>{H_LABELS[h]}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ fontSize: 10, color: '#a1a1aa' }}>Avg error</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#09090b', fontFamily: 'var(--f-mono)' }}>{s.avgError}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ fontSize: 10, color: '#a1a1aa' }}>Bias</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: biasColor, fontFamily: 'var(--f-mono)' }}>{parseFloat(s.avgSigned) > 0 ? '+' : ''}{s.avgSigned}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 10, color: '#a1a1aa' }}>Trend</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: tc }}>{ti} {s.trend}</span>
              </div>
              <div style={{ fontSize: 9, color: '#a1a1aa', marginTop: 4 }}>{s.n} samples · recent avg {s.recentAvg}%</div>
            </div>
          )
        })}
      </div>

      {/* Grafico */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 10, flexWrap: 'wrap' }}>
        {horizons.map(h => (
          <div key={h} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 12, height: 3, borderRadius: 2, background: H_COLORS[h] }} />
            <span style={{ fontSize: 10, color: '#71717a', fontWeight: 600 }}>{H_LABELS[h]}</span>
          </div>
        ))}
        <span style={{ fontSize: 10, color: '#a1a1aa', marginLeft: 'auto' }}>rolling avg (3)</span>
      </div>

      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ overflow: 'visible' }}>
        {/* Grid */}
        {[0, 5, 10, 15, 20].filter(v => v <= maxErr).map(v => (
          <g key={v}>
            <line x1={P.left} y1={yS(v)} x2={W - P.right} y2={yS(v)} stroke="#e4e4e7" strokeWidth="1" strokeDasharray={v === 0 ? 'none' : '4 3'} />
            <text x={P.left - 8} y={yS(v) + 4} fontSize="10" fill="#a1a1aa" textAnchor="end" fontFamily="monospace">{v}%</text>
          </g>
        ))}

        {/* Linee per orizzonte */}
        {horizons.map(h => {
          const pts = byHorizon[h]
          const rolling = rollingAvg(pts, 'absError')
          // Linea raw (opaca)
          const rawPoints = pts.map(p => `${xS(p.date)},${yS(p.absError)}`).join(' ')
          // Linea rolling (piena)
          const rollPoints = pts.map((p, i) => `${xS(p.date)},${yS(rolling[i])}`).join(' ')
          const color = H_COLORS[h]
          return (
            <g key={h}>
              {/* Raw points */}
              <polyline points={rawPoints} fill="none" stroke={color} strokeWidth="1" opacity="0.2" strokeLinejoin="round" />
              {/* Rolling avg line */}
              <polyline points={rollPoints} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" opacity="0.9" />
              {/* Dots sui punti reali */}
              {pts.map((p, i) => (
                <circle key={i} cx={xS(p.date)} cy={yS(p.absError)} r="3" fill={color} stroke="#fff" strokeWidth="1.5" opacity="0.6" />
              ))}
            </g>
          )
        })}

        {/* Asse X — date */}
        {allDates.map((d, i) => (allDates.length <= 12 || i % Math.ceil(allDates.length / 12) === 0) && (
          <text key={d} x={xS(d)} y={H - 6} fontSize="9" fill="#a1a1aa" textAnchor="middle" fontFamily="monospace"
            transform={allDates.length > 8 ? `rotate(-25,${xS(d)},${H - 6})` : ''}>{d.slice(5)}</text>
        ))}
      </svg>

      <div style={{ marginTop: 8, fontSize: 9, color: '#d4d4d8' }}>
        Error = |price_target − price_actual| / price_actual · Bias = signed avg (positive = over-optimistic)
      </div>
    </Card>
  )
}

// ─── PREDICTIONS TRACKER TABLE ──────────────
export function ResolvedPredictionsTable({ resolvedPredictions }) {
  if (!resolvedPredictions || resolvedPredictions.length === 0) return null

  const HORIZON_LABEL = { '1_week': '1W', '1_month': '1M', '1_quarter': '1Q' }
  const HORIZON_COLOR = { '1_week': '#3b82f6', '1_month': '#8b5cf6', '1_quarter': '#f97316' }
  const HORIZON_DAYS  = { '1_week': 7, '1_month': 30, '1_quarter': 90 }

  const pending  = resolvedPredictions.filter(p => p.price_actual == null)
  const resolved = resolvedPredictions.filter(p => p.price_actual != null)

  const today = new Date()

  const sorted = [
    ...pending.sort((a, b) => {
      const ta = new Date(a.date).getTime() + (HORIZON_DAYS[a.horizon]||7)*86400000
      const tb = new Date(b.date).getTime() + (HORIZON_DAYS[b.horizon]||7)*86400000
      return ta - tb
    }),
    ...resolved.sort((a, b) => b.date > a.date ? 1 : b.date < a.date ? -1 : 0)
  ]

  const renderRow = (p, i) => {
    const isPending = p.price_actual == null
    const predDate = new Date(p.date)
    const targetDate = new Date(predDate.getTime() + (HORIZON_DAYS[p.horizon]||7)*86400000)
    const daysLeft = Math.ceil((targetDate - today) / 86400000)
    const targetStr = targetDate.toISOString().slice(0, 10)

    let errColor = '#71717a', resultLabel = '', resultColor = '#71717a'
    if (!isPending) {
      const absErr = Math.abs(p.error_pct)
      errColor = absErr < 3 ? '#4a9065' : absErr > 7 ? '#b85450' : '#71717a'
      resultLabel = p.error_pct > 0.5 ? 'Too High' : p.error_pct < -0.5 ? 'Too Low' : 'Accurate'
      resultColor = p.error_pct > 0.5 ? '#b85450' : p.error_pct < -0.5 ? '#3b82f6' : '#4a9065'
    }

    const outlookIcon = p.outlook === 'BULLISH' ? '↑' : p.outlook === 'BEARISH' ? '↓' : '→'
    const outlookColor = p.outlook === 'BULLISH' ? '#4a9065' : p.outlook === 'BEARISH' ? '#b85450' : '#71717a'

    return (
      <tr key={`${p.date}-${p.ticker}-${p.horizon}-${i}`} style={{ borderBottom: '1px solid #f4f4f5', background: isPending ? '#fffbeb' : 'transparent' }}>
        <td style={{ padding: '8px 10px', fontFamily: 'var(--f-mono)', color: '#52525b', fontSize: 10 }}>{p.date}</td>
        <td style={{ padding: '8px 10px', fontWeight: 700, color: '#18181b', fontSize: 12 }}>{p.ticker}</td>
        <td style={{ padding: '8px 10px', textAlign: 'center' }}>
          <span style={{ fontSize: 9, fontWeight: 700, color: HORIZON_COLOR[p.horizon] || '#71717a', background: `${HORIZON_COLOR[p.horizon] || '#71717a'}15`, padding: '2px 6px', borderRadius: 4 }}>{HORIZON_LABEL[p.horizon] || p.horizon}</span>
        </td>
        <td style={{ padding: '8px 10px', textAlign: 'center', color: outlookColor, fontWeight: 600, fontSize: 11 }}>{outlookIcon} {p.outlook}</td>
        <td style={{ padding: '8px 10px', textAlign: 'center' }}>
          <Chip value={p.confidence} map={Q} size="sm" />
        </td>
        <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--f-mono)', fontWeight: 600, color: '#18181b' }}>${fmt(p.price_target)}</td>
        <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--f-mono)', color: '#71717a', fontSize: 10 }}>{targetStr}</td>
        <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--f-mono)', fontWeight: 600, color: isPending ? '#a1a1aa' : '#18181b' }}>
          {isPending ? '—' : `$${fmt(p.price_actual)}`}
        </td>
        <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--f-mono)', fontWeight: 700, color: isPending ? '#a1a1aa' : errColor }}>
          {isPending ? '—' : `${p.error_pct >= 0 ? '+' : ''}${fmt(p.error_pct)}%`}
        </td>
        <td style={{ padding: '8px 10px', textAlign: 'right' }}>
          {isPending ? (
            <span style={{ fontSize: 9, fontWeight: 700, color: daysLeft <= 0 ? '#d97706' : '#3b82f6', background: daysLeft <= 0 ? '#fef3c7' : '#eff6ff', border: `1px solid ${daysLeft <= 0 ? '#fcd34d' : '#bfdbfe'}`, padding: '2px 8px', borderRadius: 4 }}>
              {daysLeft <= 0 ? 'Overdue' : `${daysLeft}d left`}
            </span>
          ) : (
            <span style={{ fontSize: 9, fontWeight: 700, color: resultColor, background: `${resultColor}12`, border: `1px solid ${resultColor}30`, padding: '2px 8px', borderRadius: 4 }}>{resultLabel}</span>
          )}
        </td>
      </tr>
    )
  }

  return (
    <Card style={{ padding: '20px 22px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: '#4a9065', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 800, color: '#fff', fontFamily: 'var(--f-mono)', flexShrink: 0 }}>✓</div>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#18181b' }}>Predictions Tracker</span>
        <div style={{ flex: 1, height: '1.5px', background: 'linear-gradient(90deg,#e4e4e7,transparent)' }} />
        <span style={{ fontSize: 10, color: '#d97706', fontWeight: 600 }}>{pending.length} pending</span>
        <span style={{ fontSize: 10, color: '#4a9065', fontWeight: 600 }}>{resolved.length} resolved</span>
      </div>

      <div style={{ overflowX: 'auto', maxHeight: 500, overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e4e4e7', position: 'sticky', top: 0, background: '#fff', zIndex: 1 }}>
              {['Date', 'Ticker', 'Horizon', 'Outlook', 'Conf', 'Target $', 'Due', 'Actual', 'Error', 'Status'].map(h => (
                <th key={h} style={{ padding: '8px 10px', fontSize: 9, fontWeight: 700, color: '#71717a', letterSpacing: 0.8, textAlign: h === 'Date' || h === 'Ticker' ? 'left' : h === 'Horizon' || h === 'Outlook' || h === 'Conf' ? 'center' : 'right', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.slice(0, 50).map(renderRow)}
          </tbody>
        </table>
      </div>

      {sorted.length > 50 && <div style={{ fontSize: 10, color: '#a1a1aa', textAlign: 'center', marginTop: 10 }}>Showing 50 of {sorted.length}</div>}
    </Card>
  )
}

// ─── CAPITAL CHART ───────────────────────────
function CapitalChart({ trades, holdingPrices = {} }) {
  const sorted = [...trades].sort((a,b)=>new Date(a.date)-new Date(b.date))
  let cash = 500000; const shares = {}; const prices = {}; const snaps = []
  sorted.forEach(t => {
    const tk=t.ticker, s=Number(t.shares||0), p=Number(t.price||0)
    if (t.action==='BUY'&&s>0&&p) { shares[tk]=(shares[tk]||0)+s; cash-=s*p; prices[tk]=p }
    else if (t.action==='SELL'&&s>0&&p) { cash+=s*p; shares[tk]=Math.max(0,(shares[tk]||0)-s); prices[tk]=p }
    let inv=0; Object.entries(shares).forEach(([stk, sh]) => { inv+=sh*(prices[stk]||0) }); snaps.push({date:t.date,value:cash+inv,cash})
  })
  // Update last snapshot with fresh prices from holdingPrices
  if (snaps.length > 0) {
    const lastSnap = snaps[snaps.length - 1]
    let freshInv = 0
    Object.entries(shares).forEach(([tk, sh]) => {
      const freshPrice = holdingPrices[tk]?.price || prices[tk] || 0
      freshInv += sh * freshPrice
    })
    lastSnap.value = lastSnap.cash + freshInv
  }
  const W=600,H=160
  if (snaps.length<2) return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:14}}>
        <span style={{fontSize:13,fontWeight:700,color:'#ffffff'}}>Capital Over Time</span>
        <span style={{fontSize:14,fontWeight:600,color:'#71717a',fontFamily:'var(--f-mono)'}}>$500,000.00</span>
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{display:'block'}}>
        <line x1="60" y1={H/2} x2={W-20} y2={H/2} stroke="rgba(255,255,255,0.07)" strokeWidth="1" strokeDasharray="6 4" />
        <text x="50" y={H/2+4} fontSize="11" fill="#6b7280" textAnchor="end" fontFamily="monospace">$500k</text>
        <text x={W/2} y={H/2+28} fontSize="11" fill="#4b5563" textAnchor="middle">Waiting for trading data…</text>
      </svg>
    </div>
  )
  const P={top:20,right:20,bottom:32,left:72},iW=W-P.left-P.right,iH=H-P.top-P.bottom
  const vals=snaps.map(s=>s.value),minV=Math.min(...vals)*0.995,maxV=Math.max(...vals)*1.005,range=maxV-minV||1
  const xS=i=>P.left+(i/(snaps.length-1))*iW, yS=v=>P.top+iH-((v-minV)/range)*iH
  const pts=snaps.map((s,i)=>`${xS(i)},${yS(s.value)}`).join(' ')
  const area=`${P.left},${P.top+iH} ${pts} ${xS(snaps.length-1)},${P.top+iH}`
  const isUp=snaps[snaps.length-1].value>=snaps[0].value, lc=isUp?'#7ac090':'#d08888'
  const pctChange=((snaps[snaps.length-1].value-snaps[0].value)/snaps[0].value*100)
  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:14}}>
        <span style={{fontSize:13,fontWeight:700,color:'#ffffff'}}>Capital Over Time</span>
        <span style={{fontSize:16,fontWeight:700,color:lc}}>{isUp?'+':''}{fmt(pctChange)}%</span>
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{overflow:'visible',display:'block'}}>
        <defs><linearGradient id="capitalGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={lc} stopOpacity="0.25" /><stop offset="100%" stopColor={lc} stopOpacity="0.02" /></linearGradient></defs>
        {[0,0.25,0.5,0.75,1].map(t=>{const y=P.top+t*iH,v=maxV-t*range;return<g key={t}><line x1={P.left} y1={y} x2={W-P.right} y2={y} stroke="rgba(255,255,255,0.07)" strokeWidth="1" /><text x={P.left-10} y={y+4} fontSize="10" fill="#6b7280" textAnchor="end" fontFamily="monospace">${Math.round(v/1000)}k</text></g>})}
        <polygon points={area} fill="url(#capitalGrad)" />
        <polyline points={pts} fill="none" stroke={lc} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        {snaps.map((s,i)=><circle key={i} cx={xS(i)} cy={yS(s.value)} r="4" fill={lc} stroke="rgba(0,0,0,0.3)" strokeWidth="1.5" />)}
        {snaps.map((s,i)=>(snaps.length<=10||i%Math.ceil(snaps.length/10)===0)&&<text key={`d${i}`} x={xS(i)} y={H-4} fontSize="10" fill="#6b7280" textAnchor="middle" fontFamily="monospace">{s.date.slice(5)}</text>)}
      </svg>
    </div>
  )
}

// ─── ALLOCATION PIE ──────────────────────────
const PIE_COLORS = ['#3b82f6','#8b5cf6','#ec4899','#f97316','#14b8a6','#eab308','#ef4444']

function AllocationPie({ portfolio, holdingPrices = {} }) {
  const cash=portfolio?.cash||0
  const holdings=portfolio?(typeof portfolio.holdings==='string'?JSON.parse(portfolio.holdings||'{}'):(portfolio.holdings||{})):{}
  const slices=[]; let colorIdx=0
  const he=Object.entries(holdings).filter(([,s])=>parseFloat(s)>0)
  let totalInv = 0
  he.forEach(([tk,sh])=>{const shares=parseFloat(sh), price=holdingPrices[tk]?.price||0, val=shares*price; totalInv+=val; slices.push({label:tk,value:val,shares:Math.round(shares),color:PIE_COLORS[colorIdx++%PIE_COLORS.length]})})
  slices.push({label:'Cash',value:cash,color:'#d4d4d8'})
  const total = cash + totalInv
  const sz=140,cx=sz/2,cy=sz/2,r=54,ir=32;let cum=-Math.PI/2
  const arcs=slices.map(s=>{const pct=s.value/total,ang=pct*Math.PI*2,sa=cum,ea=cum+ang;cum=ea;const la=ang>Math.PI?1:0
    const x1=cx+r*Math.cos(sa),y1=cy+r*Math.sin(sa),x2=cx+r*Math.cos(ea),y2=cy+r*Math.sin(ea)
    const ix1=cx+ir*Math.cos(ea),iy1=cy+ir*Math.sin(ea),ix2=cx+ir*Math.cos(sa),iy2=cy+ir*Math.sin(sa)
    const path=pct>=0.999?`M${cx+r},${cy} A${r},${r} 0 1,1 ${cx-r},${cy} A${r},${r} 0 1,1 ${cx+r},${cy} Z M${cx+ir},${cy} A${ir},${ir} 0 1,0 ${cx-ir},${cy} A${ir},${ir} 0 1,0 ${cx+ir},${cy} Z`
      :`M${x1},${y1} A${r},${r} 0 ${la},1 ${x2},${y2} L${ix1},${iy1} A${ir},${ir} 0 ${la},0 ${ix2},${iy2} Z`
    return{...s,path,pct}})
  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}><span style={{fontSize:13,fontWeight:700,color:'#ffffff'}}>Asset Allocation</span></div>
      <div style={{display:'flex',alignItems:'center',gap:28}}>
        <div style={{flexShrink:0}}><svg width={sz} height={sz} viewBox={`0 0 ${sz} ${sz}`}>{arcs.map((a,i)=><path key={i} d={a.path} fill={a.color} stroke="rgba(0,0,0,0.3)" strokeWidth="1.5" />)}<text x={cx} y={cy-4} textAnchor="middle" fontSize="10" fontWeight="700" fill="#6b7280" fontFamily="var(--f-mono)">Total</text><text x={cx} y={cy+10} textAnchor="middle" fontSize="11" fontWeight="800" fill="#ffffff" fontFamily="var(--f-mono)">${fmt(total,0)}</text></svg></div>
        <div style={{display:'flex',flexDirection:'column',gap:10,flex:1}}>
          {arcs.filter(a=>a.pct>0.001).map((a,i)=><div key={i} style={{display:'flex',alignItems:'center',gap:10}}><div style={{width:10,height:10,borderRadius:3,background:a.color,flexShrink:0}} /><div style={{flex:1}}><div style={{fontSize:11,fontWeight:700,color:'#e2e8f0'}}>{a.label}</div><div style={{fontSize:10,color:'#6b7280'}}>${fmt(a.value,0)} · {(a.pct*100).toFixed(1)}%</div></div></div>)}
        </div>
      </div>
    </div>
  )
}

// ─── TRADE CARD & DECISION HISTORY ──────────
const TRADES_PER_PAGE = 5
const ITEMS_PER_COL = 5

function TradeCard({ trade, index }) {
  const style = A[trade.action] || A.HOLD
  return (
    <div style={{ display:'flex',alignItems:'center',gap:16,padding:'14px 18px',background:'rgba(255,255,255,0.03)',border:'1px solid rgba(255,255,255,0.06)',borderRadius:10,marginBottom:8 }}>
      <div style={{width:32,height:32,borderRadius:8,background:style.bg,display:'flex',alignItems:'center',justifyContent:'center',fontSize:14,fontWeight:800,color:style.color,border:`1.5px solid ${style.border}`,flexShrink:0}}>{style.icon}</div>
      <div style={{flex:1,minWidth:0}}>
        <div style={{display:'flex',alignItems:'center',gap:7,marginBottom:4}}>
          <ActionBadge action={trade.action} />
          <span style={{fontSize:13,fontWeight:700,color:'#e2e8f0'}}>{trade.ticker}</span>
          <span style={{fontSize:10,color:'#6b7280',fontFamily:'var(--f-mono)',marginLeft:'auto'}}>{trade.date}</span>
        </div>
        {trade.shares > 0 && <div style={{fontSize:11,color:'#9ca3af'}}>{trade.shares} shares @ ${fmt(trade.price)}{trade.shares>0&&trade.price>0&&<span style={{color:'#6b7280'}}> = ${fmt(trade.shares*trade.price,0)}</span>}</div>}
      </div>
      {trade.cash_remaining != null && <div style={{textAlign:'right',flexShrink:0}}><div style={{fontSize:9,color:'#475569',fontWeight:600,letterSpacing:0.5}}>CASH AFTER</div><div style={{fontSize:15,fontWeight:700,color:'#ffffff',fontFamily:'var(--f-mono)'}}>${fmt(trade.cash_remaining,0)}</div></div>}
    </div>
  )
}

function PaginatedColumn({ items, renderItem, emptyMsg }) {
  const [page, setPage] = useState(0)
  const tp = Math.ceil(items.length / ITEMS_PER_COL)
  const pi = items.slice(page * ITEMS_PER_COL, (page+1) * ITEMS_PER_COL)
  return (
    <div>
      {items.length === 0 ? <p style={{fontSize:11,color:'#6b7280',textAlign:'center',padding:'16px 0'}}>{emptyMsg}</p> : (
        <>
          <div style={{maxHeight:420,overflowY:'auto',paddingRight:4}}>
            {pi.map((item, i) => renderItem(item, page * ITEMS_PER_COL + i))}
          </div>
          {tp > 1 && <div style={{display:'flex',alignItems:'center',justifyContent:'center',gap:4,marginTop:10}}>
            <button onClick={()=>setPage(p=>Math.max(0,p-1))} disabled={page===0} style={{padding:'3px 8px',borderRadius:5,border:'1px solid rgba(255,255,255,0.1)',background:'transparent',cursor:page===0?'not-allowed':'pointer',fontSize:10,color:page===0?'#4b5563':'#d4d4d8',fontWeight:600}}>←</button>
            {Array.from({length:tp},(_,i)=><button key={i} onClick={()=>setPage(i)} style={{width:22,height:22,borderRadius:5,border:`1px solid ${i===page?'rgba(255,255,255,0.25)':'rgba(255,255,255,0.06)'}`,background:i===page?'rgba(255,255,255,0.1)':'transparent',cursor:'pointer',fontSize:10,fontWeight:700,color:i===page?'#e2e8f0':'#6b7280'}}>{i+1}</button>)}
            <button onClick={()=>setPage(p=>Math.min(tp-1,p+1))} disabled={page===tp-1} style={{padding:'3px 8px',borderRadius:5,border:'1px solid rgba(255,255,255,0.1)',background:'transparent',cursor:page===tp-1?'not-allowed':'pointer',fontSize:10,color:page===tp-1?'#4b5563':'#d4d4d8',fontWeight:600}}>→</button>
          </div>}
        </>
      )}
    </div>
  )
}

// Badge colori per action
const BADGE_STYLE = {
  BUY:  { bg: '#1a3a2a', border: '#2d6a4a', text: '#4ade80', label: 'BUY'  },
  SELL: { bg: '#3a1a1a', border: '#6a2d2d', text: '#f87171', label: 'SELL' },
  HOLD: { bg: '#ffffff', border: '#d4d4d8', text: '#52525b', label: 'HOLD' },
  SKIP: { bg: '#ffffff', border: '#d4d4d8', text: '#71717a', label: 'SKIP' },
}

function ActionBadge({ action }) {
  const s = BADGE_STYLE[action] || BADGE_STYLE.HOLD
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      fontSize: 9, fontWeight: 800, letterSpacing: 1,
      color: s.text, background: s.bg,
      border: `1px solid ${s.border}`,
      borderRadius: 5, padding: '2px 7px',
      fontFamily: 'var(--f-mono)', flexShrink: 0
    }}>{s.label}</span>
  )
}

function DecisionCard({ decision }) {
  const style = A[decision.action] || A.HOLD
  const bullets = Array.isArray(decision.bullets) ? decision.bullets.filter(Boolean) : []
  return (
    <div style={{padding:'12px 14px',background:'rgba(255,255,255,0.03)',border:'1px solid rgba(255,255,255,0.06)',borderRadius:10,marginBottom:6}}>
      <div style={{display:'flex',alignItems:'center',gap:7,marginBottom:6}}>
        <ActionBadge action={decision.action} />
        <span style={{fontSize:12,fontWeight:700,color:'#e2e8f0'}}>{decision.ticker}</span>
        <span style={{fontSize:9,color:'#6b7280',fontFamily:'var(--f-mono)',marginLeft:'auto'}}>{decision.date}</span>
      </div>
      {decision.reasoning && <p style={{fontSize:10,color:'#9ca3af',lineHeight:1.5,marginBottom:bullets.length?6:0}}>{decision.reasoning.slice(0,120)}{decision.reasoning.length>120?'…':''}</p>}
      {bullets.length > 0 && <div style={{display:'flex',flexDirection:'column',gap:3}}>{bullets.map((b,i)=><div key={i} style={{display:'flex',gap:5}}><span style={{fontSize:9,color:BULL_COL[i],marginTop:2,flexShrink:0}}>{BULL_ICON[i]}</span><span style={{fontSize:10,color:'#9ca3af',lineHeight:1.4}}>{b}</span></div>)}</div>}
    </div>
  )
}

function SkipCard({ skip }) {
  return (
    <div style={{padding:'12px 14px',background:'rgba(255,255,255,0.03)',border:'1px solid rgba(255,255,255,0.06)',borderRadius:10,marginBottom:6}}>
      <div style={{display:'flex',alignItems:'center',gap:7,marginBottom:6}}>
        <ActionBadge action="SKIP" />
        <span style={{fontSize:12,fontWeight:700,color:'#e2e8f0'}}>{skip.ticker}</span>
        <span style={{fontSize:9,color:'#6b7280',fontFamily:'var(--f-mono)',marginLeft:'auto'}}>{skip.date}</span>
      </div>
      {skip.reasoning && <p style={{fontSize:10,color:'#6b7280',lineHeight:1.5}}>{skip.reasoning.slice(0,120)}{skip.reasoning.length>120?'…':''}</p>}
    </div>
  )
}

// ─── PORTFOLIO PANEL ─────────────────────────
export function PortfolioPanel({ portfolio, trades, decisions = [], skips = [], ticker, holdingPrices = {} }) {
  const [page, setPage] = useState(0)
  const holdings = portfolio ? (typeof portfolio.holdings==='string' ? JSON.parse(portfolio.holdings||'{}') : (portfolio.holdings||{})) : {}

  // Compute REAL P&L from fresh prices and trade history (not stale portfolio_status)
  const holdingEntries = Object.entries(holdings).filter(([, s]) => parseFloat(s) > 0)
  let realTotalPnl = 0, realInvestedValue = 0, realCurrentValue = 0
  holdingEntries.forEach(([t, s]) => {
    const sh = parseFloat(s), hp = holdingPrices[t], price = hp?.price || 0
    let tc = 0, ts = 0
    trades.filter(tr => tr.ticker === t).sort((a, b) => a.date > b.date ? 1 : -1).forEach(tr => {
      const trs = parseFloat(tr.shares || 0), trp = parseFloat(tr.price || 0)
      if (tr.action === 'BUY' && trs > 0) { tc += trs * trp; ts += trs }
      else if (tr.action === 'SELL' && trs > 0 && ts > 0) { const r = Math.min(trs, ts) / ts; tc *= (1 - r); ts = Math.max(0, ts - trs) }
    })
    const avg = ts > 0 ? tc / ts : 0
    realInvestedValue += sh * avg
    realCurrentValue += sh * price
    realTotalPnl += sh * (price - avg)
  })
  const cash = portfolio?.cash || 0
  const realTotalValue = cash + realCurrentValue
  const realPnlPct = realInvestedValue > 0 ? (realTotalPnl / realInvestedValue) * 100 : 0

  const pnl = realTotalPnl, pnlPct = realPnlPct
  const pnlColor = pnl >= 0 ? '#7ac090' : '#d08888'
  const totalPages = Math.ceil(trades.length / TRADES_PER_PAGE)
  const pageTrades = trades.slice(page * TRADES_PER_PAGE, (page+1) * TRADES_PER_PAGE)

  // Compute last update: most recent price date across all holdings
  const priceDates = Object.values(holdingPrices).map(hp => hp?.date).filter(Boolean).sort()
  const lastPriceUpdate = priceDates.length > 0 ? priceDates[priceDates.length - 1] : null
  const portfolioDate = portfolio?.date || null
  const lastUpdate = lastPriceUpdate || portfolioDate

  // Split decisions
  const buySellDec = decisions.filter(d => d.action==='BUY'||d.action==='SELL')
  const holdDec = decisions.filter(d => d.action==='HOLD')

  return (
    <div style={{ background: 'linear-gradient(180deg, #2a2a2e 0%, #232326 100%)', borderRadius: 16, padding: '28px 30px', boxShadow: '0 12px 48px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.06)' }}>
      {/* Header */}
      <div style={{ display:'flex',alignItems:'center',gap:14,marginBottom:26,paddingBottom:22,borderBottom:'1px solid rgba(255,255,255,0.06)' }}>
        <div style={{width:48,height:48,borderRadius:12,background:'linear-gradient(135deg,#3a3a3e,#2d2d30)',display:'flex',alignItems:'center',justifyContent:'center',fontSize:14,fontWeight:800,color:'#fff',fontFamily:'var(--f-mono)',boxShadow:'0 6px 20px rgba(45,45,48,0.4)',flexShrink:0}}>07</div>
        <div style={{flex:1}}>
          <div style={{fontSize:20,fontWeight:700,color:'#ffffff',letterSpacing:'-0.3px'}}>Portfolio Manager</div>
          <div style={{fontSize:11,color:'#6b7280',marginTop:3}}>Agent 07 — Execution & Risk Management · $500k initial capital · 5% max position</div>
          {lastUpdate && <div style={{fontSize:10,color:'#52525b',marginTop:4,fontFamily:'var(--f-mono)'}}>Last update: {lastUpdate}</div>}
        </div>
        {portfolio && <div style={{textAlign:'right'}}><div style={{fontSize:9,fontWeight:700,color:'#6b7280',letterSpacing:1,marginBottom:4}}>TOTAL VALUE</div><div style={{fontSize:26,fontWeight:700,color:'#ffffff',fontFamily:'var(--f-mono)',letterSpacing:'-0.5px'}}>${fmt(realTotalValue,0)}</div></div>}
      </div>

      {/* Stats row — only Cash and P&L (holdings info is in the table below) */}
      {portfolio && (
        <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,marginBottom:28,maxWidth:400 }}>
          {[
            {label:'CASH',value:`$${fmt(cash,0)}`,sub:`${((cash/realTotalValue)*100).toFixed(1)}% liquid`,color:'#ffffff'},
            {label:'P&L',value:`${pnl>=0?'+':''}$${fmt(Math.abs(pnl),0)}`,sub:`${pnl>=0?'+':''}${fmt(pnlPct)}%`,color:pnlColor},
          ].map((item,i)=>(
            <div key={i} style={{background:'rgba(255,255,255,0.04)',border:'1px solid rgba(255,255,255,0.08)',borderRadius:10,padding:'14px 16px'}}>
              <div style={{fontSize:10,fontWeight:600,color:'#71717a',letterSpacing:1,marginBottom:8}}>{item.label}</div>
              <div style={{fontSize:24,fontWeight:700,color:item.color,letterSpacing:'-0.5px'}}>{item.value}</div>
              {item.sub&&<div style={{fontSize:11,color:item.subColor||'#71717a',marginTop:4,fontFamily:'var(--f-mono)'}}>{item.sub}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Open Positions Table */}
      {portfolio && (() => {
        const holdingEntries = Object.entries(holdings).filter(([, s]) => parseFloat(s) > 0)
        if (holdingEntries.length === 0) return null
        const holdingRows = holdingEntries.map(([t, s]) => {
          const sh = parseFloat(s), hp = holdingPrices[t], price = hp?.price || 0, priceDate = hp?.date || null
          let tc = 0, ts = 0
          trades.filter(tr => tr.ticker === t).sort((a, b) => a.date > b.date ? 1 : -1).forEach(tr => {
            const trs = parseFloat(tr.shares || 0), trp = parseFloat(tr.price || 0)
            if (tr.action === 'BUY' && trs > 0) { tc += trs * trp; ts += trs }
            else if (tr.action === 'SELL' && trs > 0 && ts > 0) { const r = Math.min(trs, ts) / ts; tc *= (1 - r); ts = Math.max(0, ts - trs) }
          })
          const avg = ts > 0 ? tc / ts : 0, pv = sh * price, pp = avg > 0 ? ((price - avg) / avg) * 100 : 0, ppa = sh * (price - avg)
          // Detect stale price: if avg price ≈ current price (within 0.01%), price hasn't been updated since buy
          const isStale = avg > 0 && price > 0 && Math.abs(price - avg) / avg < 0.0001
          return { ticker: t, shares: sh, avgPrice: avg, price, posValue: pv, posPnl: pp, posPnlAbs: ppa, isStale, priceDate }
        })
        const hasStale = holdingRows.some(r => r.isStale)
        return (
          <div style={{ marginBottom: 28 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#71717a', letterSpacing: 0.5 }}>Open Positions</span>
              {hasStale && <span style={{ fontSize: 9, color: '#d97706', background: 'rgba(217,119,6,0.12)', border: '1px solid rgba(217,119,6,0.25)', borderRadius: 5, padding: '2px 8px', fontWeight: 600 }}>Some prices not yet updated — run daily.py to refresh</span>}
            </div>
            <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 10, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                  {['Ticker', 'Shares', 'Avg Price', 'Current Price', 'Value', 'P&L'].map(h => (
                    <th key={h} style={{ padding: '10px 14px', fontSize: 9, fontWeight: 700, color: '#6b7280', letterSpacing: 1, textAlign: h === 'Ticker' ? 'left' : 'right', textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>{holdingRows.map(r => {
                  const pc = r.isStale ? '#d97706' : r.posPnl >= 0 ? '#7ac090' : '#d08888'
                  return (
                    <tr key={r.ticker} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '12px 14px', fontFamily: 'var(--f-mono)' }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#ffffff' }}>{r.ticker}</div>
                        {r.priceDate && <div style={{ fontSize: 9, color: '#52525b', marginTop: 2 }}>{r.priceDate}</div>}
                      </td>
                      <td style={{ padding: '12px 14px', fontSize: 12, color: '#d4d4d8', textAlign: 'right', fontFamily: 'var(--f-mono)' }}>{Math.round(r.shares)}</td>
                      <td style={{ padding: '12px 14px', fontSize: 12, color: '#a1a1aa', textAlign: 'right', fontFamily: 'var(--f-mono)' }}>${fmt(r.avgPrice)}</td>
                      <td style={{ padding: '12px 14px', fontSize: 12, color: r.isStale ? '#d97706' : '#d4d4d8', textAlign: 'right', fontFamily: 'var(--f-mono)' }}>
                        ${fmt(r.price)}{r.isStale && <span style={{ fontSize: 9, color: '#d97706', marginLeft: 6 }} title="Price not updated since purchase">⚠</span>}
                      </td>
                      <td style={{ padding: '12px 14px', fontSize: 12, color: '#d4d4d8', textAlign: 'right', fontFamily: 'var(--f-mono)', fontWeight: 600 }}>${fmt(r.posValue, 0)}</td>
                      <td style={{ padding: '12px 14px', fontSize: 12, color: pc, textAlign: 'right', fontFamily: 'var(--f-mono)', fontWeight: 600 }}>
                        {r.isStale ? <span style={{ color: '#d97706', fontSize: 11 }}>awaiting update</span> : r.avgPrice > 0 ? `${r.posPnl >= 0 ? '+' : ''}$${fmt(Math.abs(r.posPnlAbs), 0)} (${r.posPnl >= 0 ? '+' : ''}${fmt(r.posPnl)}%)` : '—'}
                      </td>
                    </tr>
                  )
                })}</tbody>
              </table>
            </div>
          </div>
        )
      })()}

      {/* Charts */}
      <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:20,marginBottom:28 }}>
        <div style={{background:'rgba(255,255,255,0.03)',border:'1px solid rgba(255,255,255,0.06)',borderRadius:12,padding:20}}><CapitalChart trades={trades} holdingPrices={holdingPrices} /></div>
        <div style={{background:'rgba(255,255,255,0.03)',border:'1px solid rgba(255,255,255,0.06)',borderRadius:12,padding:20}}><AllocationPie portfolio={portfolio} holdingPrices={holdingPrices} /></div>
      </div>

      {/* Decision History — 3 Columns */}
      <div style={{marginBottom:28}}>
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:14}}>
          <span style={{fontSize:13,fontWeight:700,color:'#ffffff'}}>Decision History</span>
          <span style={{fontSize:11,color:'#6b7280'}}>{buySellDec.length} trades · {holdDec.length} holds · {skips.length} skips</span>
        </div>
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:16}}>
          {/* BUY / SELL column */}
          <div>
            <div style={{fontSize:10,fontWeight:700,color:'#4a9065',letterSpacing:0.5,marginBottom:10,textAlign:'center'}}>BUY / SELL</div>
            <PaginatedColumn items={buySellDec} emptyMsg="No trades yet" renderItem={(d,i) => <DecisionCard key={d.id||i} decision={d} />} />
          </div>
          {/* HOLD column */}
          <div>
            <div style={{fontSize:10,fontWeight:700,color:'#71717a',letterSpacing:0.5,marginBottom:10,textAlign:'center'}}>HOLD</div>
            <PaginatedColumn items={holdDec} emptyMsg="No holds yet" renderItem={(d,i) => <DecisionCard key={d.id||i} decision={d} />} />
          </div>
          {/* SKIP column */}
          <div>
            <div style={{fontSize:10,fontWeight:700,color:'#a1a1aa',letterSpacing:0.5,marginBottom:10,textAlign:'center'}}>SKIP</div>
            <PaginatedColumn items={skips} emptyMsg="No skips yet" renderItem={(s,i) => <SkipCard key={s.id||i} skip={s} />} />
          </div>
        </div>
      </div>

      {/* Trade Ledger */}
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:14}}>
        <span style={{fontSize:13,fontWeight:700,color:'#ffffff'}}>Trade Ledger</span>
        {trades.length>0&&<span style={{fontSize:11,color:'#6b7280'}}>{trades.length} operations</span>}
      </div>
      {trades.length===0 ? <p style={{fontSize:12,color:'#a1a1aa',textAlign:'center',padding:'20px 0'}}>No trades yet</p> : (
        <>
          {pageTrades.map((t,i)=><TradeCard key={t.id||i} trade={t} index={page*TRADES_PER_PAGE+i+1} />)}
          {totalPages>1&&(
            <div style={{display:'flex',alignItems:'center',justifyContent:'center',gap:6,marginTop:16,paddingTop:16,borderTop:'1px solid rgba(255,255,255,0.06)'}}>
              <button onClick={()=>setPage(p=>Math.max(0,p-1))} disabled={page===0} style={{padding:'5px 14px',borderRadius:8,border:'1px solid rgba(255,255,255,0.12)',background:'rgba(255,255,255,0.04)',cursor:page===0?'not-allowed':'pointer',fontSize:12,color:page===0?'#4b5563':'#e2e8f0',fontWeight:600,transition:'all 0.15s'}}>←</button>
              {Array.from({length:totalPages},(_,i)=><button key={i} onClick={()=>setPage(i)} style={{width:32,height:32,borderRadius:8,border:`1px solid ${i===page?'rgba(255,255,255,0.3)':'rgba(255,255,255,0.08)'}`,background:i===page?'rgba(255,255,255,0.12)':'transparent',cursor:'pointer',fontSize:12,fontWeight:700,color:i===page?'#f1f5f9':'#6b7280',transition:'all 0.15s'}}>{i+1}</button>)}
              <button onClick={()=>setPage(p=>Math.min(totalPages-1,p+1))} disabled={page===totalPages-1} style={{padding:'5px 14px',borderRadius:8,border:'1px solid rgba(255,255,255,0.12)',background:'rgba(255,255,255,0.04)',cursor:page===totalPages-1?'not-allowed':'pointer',fontSize:12,color:page===totalPages-1?'#4b5563':'#e2e8f0',fontWeight:600,transition:'all 0.15s'}}>→</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
