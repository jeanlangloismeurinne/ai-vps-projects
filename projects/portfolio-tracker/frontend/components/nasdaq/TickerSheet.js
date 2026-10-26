import { useEffect, useMemo, useState } from 'react'

const DPM = 30.4375
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'
const RANGES = [{ v: '1y', l: '1 an' }, { v: '5y', l: '5 ans' }, { v: 'max', l: 'Max' }]
const MAX_POINTS = 1500
const W = 900, H1 = 150, H2 = 170, ML = 46, MR = 12, GAP = 22

const dateOf = (n) => new Date(n * 86400000)
const fmtDay = (n) => dateOf(n).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit', timeZone: 'UTC' })

// Épisodes de saut : première séance de chaque série de séances où le saut sur 5 séances dépasse le seuil.
function episodes(s, hot) {
  const out = []
  let last = -99
  for (let i = 5; i < s.d.length; i++) {
    const j = ((s.a[i] - s.a[i - 5]) - (s.d[i] - s.d[i - 5])) / DPM
    if (j >= hot) {
      if (i - last > 5) out.push({ i, j, dn: s.d[i] })
      else out[out.length - 1].j = Math.max(out[out.length - 1].j, j)
      last = i
    }
  }
  return out
}

// Garde au plus MAX_POINTS points (dernier point toujours conservé) : un historique complet fait ~10 000 séances.
function decimate(s) {
  const n = s.d.length
  if (n <= MAX_POINTS) return s
  const step = Math.ceil(n / MAX_POINTS)
  const idx = []
  for (let i = n - 1; i >= 0; i -= step) idx.push(i)
  idx.reverse()
  const pick = (a) => idx.map(i => a[i])
  return { d: pick(s.d), p: pick(s.p), a: pick(s.a), l: pick(s.l) }
}

export default function TickerSheet({ row, ticker, hot, onClose }) {
  const [range, setRange] = useState('1y')
  const [cache, setCache] = useState({})
  const [err, setErr] = useState(null)
  const key = `${ticker}:${range}`
  useEffect(() => {
    if (cache[key]) return
    setErr(null)
    fetch(`${API}/nasdaq/series/${encodeURIComponent(ticker)}?range=${range}`)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => setCache(c => ({ ...c, [key]: j })))
      .catch(e => setErr(String(e.message || e)))
  }, [key]) // eslint-disable-line
  const full = cache[key]
  const ev = useMemo(() => (full ? episodes(full, hot) : []), [full, hot])
  const s = useMemo(() => (full ? decimate(full) : null), [full])
  if (!row) return null
  const head = (
    <div className="flex items-center gap-3 mb-2 flex-wrap">
      <h3 className="text-sm font-semibold text-white">{row.ticker} <span className="font-normal text-gray-400">{row.name.replace(/ - .*$/, '')}</span></h3>
      <div className="flex rounded border border-gray-700 overflow-hidden">
        {RANGES.map(o => (
          <button key={o.v} onClick={() => setRange(o.v)}
            className={`px-2.5 py-1 text-xs ${range === o.v ? 'bg-sky-900 text-white' : 'text-gray-400 hover:text-white'}`}>{o.l}</button>
        ))}
      </div>
      {full && <span className="text-xs text-gray-500">{full.d.length} séances · sauts ≥ {hot} mois sur 5 séances en rouge{range !== '1y' ? ' (les 6 plus forts)' : ''}</span>}
      <button onClick={onClose} className="ml-auto text-xs px-2 py-1 rounded border border-gray-700 text-gray-300 hover:text-white">Fermer</button>
    </div>
  )
  if (!s) return <div>{head}<p className="text-sm text-gray-500">{err ? `Série indisponible pour ${row.ticker} (${err}).` : 'Chargement…'}</p></div>

  const n = s.d.length
  const d0 = s.d[0], d1 = s.d[n - 1]
  const x = (i) => ML + ((s.d[i] - d0) / (d1 - d0 || 1)) * (W - ML - MR)
  const xd = (dn) => ML + ((dn - d0) / (d1 - d0 || 1)) * (W - ML - MR)
  const ages = s.a.map(a => a / DPM)
  const amax = Math.max(12, ...ages) * 1.08
  const ya = (v) => 8 + (1 - v / amax) * (H1 - 8 - 6)
  const pmin = Math.min(...s.p), pmax = Math.max(...s.p)
  const useLog = range !== '1y' && pmin > 0
  const f = (v) => (useLog ? Math.log(v) : v)
  const yp = (v) => 8 + (1 - (f(v) - f(pmin)) / (f(pmax) - f(pmin) || 1)) * (H2 - 8 - 6)
  const top2 = H1 + GAP
  const total = H1 + GAP + H2 + 22

  const spanY = (d1 - d0) / 365.25
  const tickEvery = spanY <= 1.5 ? 2 : spanY <= 6 ? 12 : spanY <= 15 ? 24 : 60 // mois entre deux repères
  const monthTicks = []
  for (let i = 0; i < n; i++) {
    const d = dateOf(s.d[i])
    const m = d.getUTCFullYear() * 12 + d.getUTCMonth()
    if (i === 0 || m !== (() => { const q = dateOf(s.d[i - 1]); return q.getUTCFullYear() * 12 + q.getUTCMonth() })()) {
      if (m % tickEvery === 0) monthTicks.push([i, d.toLocaleDateString('fr-FR', tickEvery >= 12 ? { year: 'numeric', timeZone: 'UTC' } : { month: 'short', year: '2-digit', timeZone: 'UTC' })])
    }
  }
  const agePath = ages.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${ya(v).toFixed(1)}`).join(' ')
  const pricePath = s.p.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${yp(v).toFixed(1)}`).join(' ')
  const labelled = new Set([...ev].sort((a, b) => b.j - a.j).slice(0, range === '1y' ? 8 : 6).map(e => e.dn))
  const yTicksA = [0, 6, 12, 24, 36, 60, 120, 240, 360].filter((v, k, all) => v < amax && (amax < 100 || v === 0 || v >= 12) && (amax < 200 || v % 24 === 0 || v === 12))

  return (
    <div>
      {head}
      <svg viewBox={`0 0 ${W} ${total}`} className="w-full" role="img" aria-label={`Ancienneté et cours de ${row.ticker}`}>
        {yTicksA.map(v => (
          <g key={v}>
            <line x1={ML} x2={W - MR} y1={ya(v)} y2={ya(v)} stroke={v === 12 ? '#7f1d1d' : '#1f2937'} strokeDasharray={v === 12 ? '4 3' : undefined} />
            <text x={ML - 5} y={ya(v) + 3} fontSize="10" fill="#9ca3af" textAnchor="end">{v}</text>
          </g>
        ))}
        <text x={4} y={12} fontSize="10" fill="#9ca3af">mois</text>
        {ev.filter(e => range === '1y' || labelled.has(e.dn)).map(e => (
          <g key={e.dn}>
            <line x1={xd(e.dn)} x2={xd(e.dn)} y1={0} y2={total - 22} stroke="#ef4444" strokeOpacity="0.5" strokeDasharray="3 3" />
            {labelled.has(e.dn) && <text x={Math.min(xd(e.dn) + 3, W - 150)} y={12} fontSize="10" fill="#fca5a5">+{e.j.toFixed(0)} m · {fmtDay(e.dn)}</text>}
          </g>
        ))}
        <path d={agePath} fill="none" stroke="#38bdf8" strokeWidth="1.6" />
        {s.l.map((v, i) => v ? <circle key={i} cx={x(i)} cy={ya(ages[i])} r="1.8" fill="#ef4444" /> : null)}
        <text x={W - MR} y={H1 + 12} fontSize="10" fill="#6b7280" textAnchor="end">Ancienneté du cours (mois) — pointillé : 12 mois, points rouges : plus bas historique</text>

        {[pmin, useLog ? Math.sqrt(pmin * pmax) : (pmin + pmax) / 2, pmax].map((v, k) => (
          <g key={k}>
            <line x1={ML} x2={W - MR} y1={top2 + yp(v)} y2={top2 + yp(v)} stroke="#1f2937" />
            <text x={ML - 5} y={top2 + yp(v) + 3} fontSize="10" fill="#9ca3af" textAnchor="end">{v.toFixed(0)}</text>
          </g>
        ))}
        <path d={pricePath} transform={`translate(0,${top2})`} fill="none" stroke="#e5e7eb" strokeWidth="1.4" />
        {monthTicks.map(([i, l]) => (
          <text key={i} x={x(i)} y={top2 + H2 + 14} fontSize="10" fill="#9ca3af" textAnchor="middle">{l}</text>
        ))}
        <text x={W - MR} y={top2 + 12} fontSize="10" fill="#6b7280" textAnchor="end">Cours ajusté ($){useLog ? ' — échelle log' : ''}</text>
      </svg>
    </div>
  )
}
