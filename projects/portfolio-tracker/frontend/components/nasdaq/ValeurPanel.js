import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export const C = { infl: '#9ca3af', real: '#34d399', mult: '#f59e0b', div: '#a78bfa', sp: '#e5e7eb', bad: '#ef4444', band: 'rgba(52,211,153,0.14)' }
export const PERIODS = [{ v: '3y', l: '3 ans' }, { v: '5y', l: '5 ans' }, { v: '10y', l: '10 ans' }, { v: '2010', l: 'Depuis 2010' }]
export const LABELS = { infl: 'Inflation', real: 'Bénéfices réels', mult: 'Multiple', div: 'Dividendes' }

export const pct = (x, d = 1) => x == null ? '—' : `${x >= 0 ? '+' : ''}${(100 * x).toLocaleString('fr-FR', { minimumFractionDigits: d, maximumFractionDigits: d })} %`
export const times = (x, d = 1) => x == null ? '—' : `×${x.toLocaleString('fr-FR', { minimumFractionDigits: d, maximumFractionDigits: d })}`
const num = (x, d = 1) => x == null ? '—' : x.toLocaleString('fr-FR', { minimumFractionDigits: d, maximumFractionDigits: d })
const usd = (x) => x == null ? '—' : `${x.toLocaleString('fr-FR', { maximumFractionDigits: x < 10 ? 2 : 0 })} $`
const monthFr = (m) => m ? `${m.slice(5)}/${m.slice(0, 4)}` : ''

export function ratioColor(r, degraded) {
  if (degraded || r == null) return 'text-red-400'
  return r <= 2 ? 'text-emerald-300' : r <= 3 ? 'text-amber-300' : 'text-red-300'
}

export function useValeur(ticker, period) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => {
    let live = true
    setErr(null)
    fetch(`${API}/nasdaq/valeur/${encodeURIComponent(ticker)}?period=${period}`)
      .then(r => (r.ok ? r.json() : r.json().then(j => Promise.reject(new Error(j.detail || `HTTP ${r.status}`)))))
      .then(j => live && setData(j))
      .catch(e => live && setErr(String(e.message || e)))
    return () => { live = false }
  }, [ticker, period])
  return { data, err }
}

export function Sentence({ d, name }) {
  const p = d.period
  if (!p) return null
  const from = monthFr(p.start)
  const shift = p.shifted ? ` (départ décalé au premier bénéfice positif mesurable)` : ''
  if (!p.ok) {
    return <p className="text-sm text-gray-300"><span className="text-red-400">{name} : décomposition impossible depuis {from}, {p.reason}.</span> Le cours a rapporté {pct(p.annual?.total)} par an dividendes compris, contre {pct(p.annual?.sp)} pour le S&P 500.</p>
  }
  const a = p.annual
  return (
    <p className="text-sm text-gray-300 leading-relaxed">
      Depuis {from}{shift}, {name} a rapporté <b className="text-white">{pct(a.total)} par an</b> dividendes compris, contre {pct(a.sp)} pour le S&amp;P 500.{' '}
      <span style={{ color: C.infl }}>L'inflation</span> explique {pct(a.infl)} par an, <span style={{ color: C.real }}>la croissance réelle des bénéfices</span> {pct(a.real)},{' '}
      <span style={{ color: C.mult }}>le multiple</span> {pct(a.mult)} (de {num(p.pe0)} à {num(p.pe1)} fois les bénéfices) et <span style={{ color: C.div }}>les dividendes</span> {pct(a.div)}.{' '}
      {p.borrowed > 0.05
        ? <>Environ <b className="text-amber-300">{Math.round(100 * p.borrowed)} % de la hausse du cours est empruntée</b> au multiple.</>
        : <>La hausse est <b className="text-emerald-300">entièrement méritée</b> : le multiple n'a pas augmenté.</>}
    </p>
  )
}

function Waterfall({ d }) {
  const p = d.period
  if (!p?.ok) return null
  const f = p.factor
  const P1 = d.price, P0 = P1 / f.price
  const steps = []
  let lv = P0
  steps.push({ l: `Cours ${monthFr(p.start)}`, a: 0, b: P0, c: '#6b7280' })
  for (const k of ['infl', 'real', 'mult']) { const nv = lv * f[k]; steps.push({ l: LABELS[k], a: lv, b: nv, c: C[k] }); lv = nv }
  steps.push({ l: "Cours aujourd'hui", a: 0, b: P1, c: C.sp })
  steps.push({ l: 'Dividendes', a: P1, b: P1 * f.div, c: C.div })
  steps.push({ l: 'Total', a: 0, b: P1 * f.div, c: '#38bdf8' })
  if (f.sp) steps.push({ l: 'Même mise S&P 500', a: 0, b: P0 * f.sp, c: C.sp, outline: true })
  const W = 900, H = 230, ML = 54, MB = 34, top = 10
  const vmax = Math.max(...steps.map(s => Math.max(s.a, s.b))) * 1.05
  const y = v => top + (1 - v / vmax) * (H - top - MB)
  const bw = (W - ML - 10) / steps.length
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(t => t * vmax)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Cascade de décomposition du cours">
      {ticks.map((v, i) => <g key={i}><line x1={ML} x2={W - 10} y1={y(v)} y2={y(v)} stroke="#1f2937" /><text x={ML - 6} y={y(v) + 3} fontSize="10" fill="#9ca3af" textAnchor="end">{usd(v)}</text></g>)}
      {steps.map((s, i) => {
        const x = ML + i * bw + bw * 0.15, w = bw * 0.7, y1 = y(Math.max(s.a, s.b)), y0 = y(Math.min(s.a, s.b))
        const dn = s.b < s.a
        return (
          <g key={i}>
            <rect x={x} y={y1} width={w} height={Math.max(1, y0 - y1)} rx="2" fill={s.outline ? 'none' : s.c} stroke={s.outline ? s.c : 'none'} strokeWidth="1.5" opacity={dn ? 0.55 : 1} />
            <text x={x + w / 2} y={y1 - 4} fontSize="10" fill="#d1d5db" textAnchor="middle">{s.a === 0 ? usd(s.b) : times(s.b / s.a, 2)}</text>
            <text x={x + w / 2} y={H - MB + 14} fontSize="10" fill="#9ca3af" textAnchor="middle">{s.l}</text>
          </g>
        )
      })}
    </svg>
  )
}

function logScale(vals, H, top, bottom) {
  const v = vals.filter(x => x != null && x > 0)
  const lo = Math.log(Math.min(...v)), hi = Math.log(Math.max(...v))
  return (x) => top + (1 - (Math.log(x) - lo) / (hi - lo || 1)) * (H - top - bottom)
}

function niceLogTicks(min, max) {
  const out = []
  for (let e = Math.floor(Math.log10(min)) - 1; e <= Math.ceil(Math.log10(max)); e++) {
    for (const m of [1, 2, 5]) { const v = m * 10 ** e; if (v >= min * 0.98 && v <= max * 1.02) out.push(v) }
  }
  return out
}

function yearTicks(ms) {
  const span = ms.length / 12
  const every = span > 12 ? 2 : 1
  return ms.map((m, i) => [m, i]).filter(([m]) => m.endsWith('-01') && (+m.slice(0, 4)) % every === 0)
}

function FloorChart({ s, i0 }) {
  const W = 900, H = 260, ML = 54, MR = 10, top = 10, MB = 22
  const idx = s.m.map((_, i) => i).filter(i => i >= i0)
  const all = idx.flatMap(i => [s.p[i], s.lo[i], s.hi[i], s.ghost[i]]).filter(v => v != null && v > 0)
  if (!all.length) return null
  const y = logScale(all, H, top, MB)
  const n = idx.length
  const x = k => ML + (k / Math.max(1, n - 1)) * (W - ML - MR)
  const path = (arr) => {
    let d = '', pen = false
    idx.forEach((i, k) => { const v = arr[i]; if (v == null || v <= 0) { pen = false; return } d += `${pen ? 'L' : 'M'}${x(k).toFixed(1)},${y(v).toFixed(1)}`; pen = true })
    return d
  }
  const band = (() => {
    const seg = []; let cur = []
    idx.forEach((i, k) => { if (s.lo[i] != null) cur.push(k); else if (cur.length) { seg.push(cur); cur = [] } })
    if (cur.length) seg.push(cur)
    return seg.map(ks => ks.map(k => `${x(k).toFixed(1)},${y(s.hi[idx[k]]).toFixed(1)}`).join(' ') + ' ' + [...ks].reverse().map(k => `${x(k).toFixed(1)},${y(s.lo[idx[k]]).toFixed(1)}`).join(' '))
  })()
  const segs = []
  for (let k = 1; k < n; k++) {
    const a = idx[k - 1], b = idx[k]
    if (s.p[a] && s.p[b]) segs.push(<line key={k} x1={x(k - 1)} y1={y(s.p[a])} x2={x(k)} y2={y(s.p[b])} stroke={s.degraded[b] ? C.bad : C.sp} strokeWidth="1.8" />)
  }
  const mn = Math.min(...all), mx = Math.max(...all)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Cours et fourchette de plancher">
      {niceLogTicks(mn, mx).map(v => <g key={v}><line x1={ML} x2={W - MR} y1={y(v)} y2={y(v)} stroke="#1f2937" /><text x={ML - 6} y={y(v) + 3} fontSize="10" fill="#9ca3af" textAnchor="end">{usd(v)}</text></g>)}
      {yearTicks(idx.map(i => s.m[i])).map(([m, k]) => <text key={m} x={x(k)} y={H - 6} fontSize="10" fill="#9ca3af" textAnchor="middle">{m.slice(0, 4)}</text>)}
      {band.map((pts, j) => <polygon key={j} points={pts} fill={C.band} />)}
      <path d={path(s.mid)} fill="none" stroke={C.real} strokeDasharray="5 4" strokeWidth="1.3" />
      <path d={path(s.ghost)} fill="none" stroke={C.mult} strokeDasharray="2 3" strokeWidth="1.3" />
      {segs}
    </svg>
  )
}

function RatioChart({ s, i0 }) {
  const W = 900, H = 170, ML = 54, MR = 10, top = 10, MB = 22
  const idx = s.m.map((_, i) => i).filter(i => i >= i0)
  const vals = idx.map(i => s.ratio[i]).filter(v => v != null && v > 0)
  if (!vals.length) return <p className="text-xs text-gray-500">Pas de rapport au plancher sur la période : pas de bénéfice moyen positif sur 3 ans.</p>
  const lo = Math.min(0.5, ...vals), hi = Math.max(4, ...vals)
  const y = logScale([lo, hi], H, top, MB)
  const n = idx.length
  const x = k => ML + (k / Math.max(1, n - 1)) * (W - ML - MR)
  let d = '', pen = false
  idx.forEach((i, k) => { const v = s.ratio[i]; if (v == null || v <= 0) { pen = false; return } d += `${pen ? 'L' : 'M'}${x(k).toFixed(1)},${y(v).toFixed(1)}`; pen = true })
  const lines = [0.5, 1, 2, 3, 5, 10, 20, 50].filter(v => v >= lo && v <= hi)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Rapport du cours au plancher">
      <rect x={ML} y={y(hi)} width={W - ML - MR} height={Math.max(0, y(3) - y(hi))} fill="rgba(239,68,68,0.08)" />
      <rect x={ML} y={y(1)} width={W - ML - MR} height={Math.max(0, y(lo) - y(1))} fill="rgba(52,211,153,0.08)" />
      {lines.map(v => <g key={v}><line x1={ML} x2={W - MR} y1={y(v)} y2={y(v)} stroke={v === 1 ? C.real : v === 3 ? '#7f1d1d' : '#1f2937'} strokeDasharray={v === 1 || v === 3 ? '4 3' : undefined} /><text x={ML - 6} y={y(v) + 3} fontSize="10" fill="#9ca3af" textAnchor="end">{times(v, v < 1 ? 1 : 0)}</text></g>)}
      {yearTicks(idx.map(i => s.m[i])).map(([m, k]) => <text key={m} x={x(k)} y={H - 6} fontSize="10" fill="#9ca3af" textAnchor="middle">{m.slice(0, 4)}</text>)}
      <path d={d} fill="none" stroke={C.sp} strokeWidth="1.8" />
    </svg>
  )
}

function StackChart({ cu }) {
  const W = 900, H = 240, ML = 54, MR = 10, top = 10, MB = 22
  const n = cu.m.length
  if (n < 2) return null
  const layers = ['infl', 'real', 'mult', 'div']
  const pos = layers.map(() => []), neg = layers.map(() => [])
  for (let i = 0; i < n; i++) {
    let pb = 0, nb = 0
    layers.forEach((k, j) => {
      const v = cu[k][i] || 0
      if (v >= 0) { pos[j].push([pb, pb + v]); neg[j].push([nb, nb]); pb += v } else { neg[j].push([nb, nb + v]); pos[j].push([pb, pb]); nb += v }
    })
  }
  const ext = [...pos.flat(2), ...neg.flat(2), ...cu.total.filter(v => v != null), ...cu.sp.filter(v => v != null)]
  const lo = Math.min(0, ...ext), hi = Math.max(0, ...ext)
  const y = v => top + (1 - (v - lo) / (hi - lo || 1)) * (H - top - MB)
  const x = i => ML + (i / (n - 1)) * (W - ML - MR)
  const poly = (arr) => arr.map(([, b], i) => `${x(i).toFixed(1)},${y(b).toFixed(1)}`).join(' ') + ' ' + [...arr].map(([a], i) => [i, a]).reverse().map(([i, a]) => `${x(i).toFixed(1)},${y(a).toFixed(1)}`).join(' ')
  const line = (arr) => { let d = '', pen = false; arr.forEach((v, i) => { if (v == null) { pen = false; return } d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`; pen = true }); return d }
  const ticks = []
  for (let e = Math.ceil(lo / Math.LN2); e <= Math.floor(hi / Math.LN2); e++) ticks.push(e * Math.LN2)
  const step = Math.max(1, Math.ceil(ticks.length / 7))
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Décomposition cumulée de la hausse">
      {ticks.filter((_, k) => k % step === 0).map(v => <g key={v}><line x1={ML} x2={W - MR} y1={y(v)} y2={y(v)} stroke={Math.abs(v) < 1e-9 ? '#4b5563' : '#1f2937'} /><text x={ML - 6} y={y(v) + 3} fontSize="10" fill="#9ca3af" textAnchor="end">{times(Math.exp(v), Math.exp(v) < 1 ? 2 : 0)}</text></g>)}
      {yearTicks(cu.m).map(([m, i]) => <text key={m} x={x(i)} y={H - 6} fontSize="10" fill="#9ca3af" textAnchor="middle">{m.slice(0, 4)}</text>)}
      {layers.map((k, j) => <polygon key={`p${k}`} points={poly(pos[j])} fill={C[k]} opacity="0.75" />)}
      {layers.map((k, j) => <polygon key={`n${k}`} points={poly(neg[j])} fill={C[k]} opacity="0.45" />)}
      <path d={line(cu.sp)} fill="none" stroke={C.sp} strokeWidth="1.2" strokeDasharray="4 3" />
      <path d={line(cu.total)} fill="none" stroke="#38bdf8" strokeWidth="2" />
    </svg>
  )
}

function Legend({ items }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
      {items.map(([c, l, dash]) => <span key={l} className="inline-flex items-center gap-1.5"><span className="inline-block w-3 h-2.5 rounded-sm" style={dash ? { borderTop: `2px dashed ${c}`, height: 0 } : { background: c }} />{l}</span>)}
    </div>
  )
}

function Forward({ d }) {
  const f = d.forward
  if (!f) return <p className="text-xs text-gray-500">Pas de consensus des analystes disponible pour ce titre.</p>
  const X = v => Math.max(0, Math.min(100, (100 * v) / 60))
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
        <div><div className="text-xs text-gray-500">PER des 12 derniers mois</div><div className="text-white font-semibold">{d.pe_ttm ? num(d.pe_ttm) : 'perte'}</div></div>
        <div><div className="text-xs text-gray-500">PER à terme (exercice suivant)</div><div className="text-white font-semibold">{f.pe ? num(f.pe) : '—'}</div></div>
        <div><div className="text-xs text-gray-500">Soit, par rapport au multiple plancher de 15</div><div className={`font-semibold ${ratioColor(f.ratio)}`}>{times(f.ratio)} le plancher</div></div>
        <div><div className="text-xs text-gray-500">Analystes</div><div className="text-white font-semibold">{f.n_analysts}</div></div>
      </div>
      {f.pe_lo && f.pe_hi && (
        <div>
          <div className="relative h-4 w-full max-w-md rounded bg-gray-800">
            <div className="absolute top-1 h-2 rounded bg-sky-700" style={{ left: `${X(f.pe_lo)}%`, width: `${Math.max(1, X(f.pe_hi) - X(f.pe_lo))}%` }} />
            <div className="absolute -top-0.5 h-5 border-l-2 border-dashed border-emerald-400" style={{ left: `${X(15)}%` }} />
            <div className="absolute top-0 h-4 w-0.5 bg-white" style={{ left: `${X(f.pe)}%` }} />
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Fourchette des analystes : de {num(f.pe_lo)} (le plus optimiste) à {num(f.pe_hi)} (le plus prudent) fois le bénéfice attendu ; échelle de 0 à 60, pointillé vert = 15.
            Plus la fourchette est large, moins le consensus est sûr. Photo du {f.as_of ? new Date(f.as_of).toLocaleDateString('fr-FR') : '—'}, enregistrée chaque semaine{d.forward_history?.length > 1 ? ` (${d.forward_history.length} photos)` : ''}.
          </p>
        </div>
      )}
    </div>
  )
}

export default function ValeurPanel({ ticker, name }) {
  const [period, setPeriod] = useState('10y')
  const [more, setMore] = useState(false)
  const { data: d, err } = useValeur(ticker, period)
  if (err) return <p className="text-sm text-gray-500">Valeur indisponible pour {ticker} ({err}).</p>
  if (!d) return <p className="text-sm text-gray-500">Chargement…</p>
  if (!d.series) return <p className="text-sm text-gray-400">Pas d'analyse de valeur pour {ticker}{d.note ? ` : ${d.note}` : ''}.</p>
  const i0 = Math.max(0, d.series.m.indexOf(d.cumul?.m?.[0]))
  const dg = d.degraded
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded border border-gray-700 overflow-hidden">
          {PERIODS.map(o => <button key={o.v} onClick={() => setPeriod(o.v)} className={`px-2.5 py-1 text-xs ${period === o.v ? 'bg-sky-900 text-white' : 'text-gray-400 hover:text-white'}`}>{o.l}</button>)}
        </div>
        {d.note && <span className="text-xs text-amber-300">⚠ {d.note}</span>}
      </div>

      <section className="space-y-2">
        <Sentence d={d} name={name || ticker} />
        <Waterfall d={d} />
        <p className="text-xs text-gray-500">Chaque marche multiplie la précédente : son ordre change sa hauteur en dollars, pas son rendement annuel. Bénéfices des 12 derniers mois (comptes SEC), inflation américaine, cours bruts.</p>
      </section>

      <section className="space-y-2">
        <h4 className="text-sm font-semibold text-white">Le cours face au plancher</h4>
        <p className="text-sm text-gray-300">
          Aujourd'hui : cours {usd(d.price)}, plancher {usd(d.floor_lo)} à {usd(d.floor_hi)}, soit{' '}
          <b className={ratioColor(d.ratio, dg)}>{d.ratio ? `${times(d.ratio)} le plancher` : 'pas de plancher'}</b>.{' '}
          {d.ratio == null ? "Bénéfice moyen sur 3 ans négatif ou nul : rien ne soutient le cours. Sur 2 118 titres du Nasdaq (2011-2025), après une chute de 20 % ou plus, une entreprise en perte a perdu plus de la moitié de sa valeur dans l'année 24 % du temps, contre 7 % pour une entreprise bénéficiaire." : dg
            ? <span className="text-red-400">L'état actuel est inférieur de plus de 10 % au meilleur état des 10 ans : le plancher est caduc.</span>
            : 'Le plancher est valide : les bénéfices tiennent.'}
        </p>
        <Legend items={[[C.sp, 'Cours'], [C.real, 'Plancher : bénéfice moyen 3 ans × 12 à × 20'], [C.mult, "Si l'état avait tenu (meilleur des 10 ans, indexé, × 15)", true], [C.bad, 'État dégradé : plancher caduc']]} />
        <FloorChart s={d.series} i0={i0} />
        <h4 className="text-sm font-semibold text-white pt-1">Combien de fois le plancher</h4>
        <RatioChart s={d.series} i0={i0} />
        <p className="text-xs text-gray-500">Le rapport se lit sans l'effet de la croissance qui écrase les écarts sur la courbe du cours. Zone verte : sous le plancher. Zone rouge, au-delà de ×3 : sur 42 valeurs de croissance de 2011 à 2025, une chute de 20 % ou plus dans l'année y a été plus fréquente (24 % des mois, contre 14 à 16 % entre ×1 et ×3), sans rendement moyen plus faible.</p>
      </section>

      <section className="space-y-2">
        <h4 className="text-sm font-semibold text-white">Le PER à terme : cher par rapport aux perspectives ?</h4>
        <Forward d={d} />
      </section>

      <section className="space-y-2">
        <button onClick={() => setMore(m => !m)} className="text-sm text-sky-300 hover:text-white">{more ? '▾' : '▸'} Quand la hausse a été méritée ou empruntée</button>
        {more && d.cumul && (
          <>
            <Legend items={[[C.infl, 'Inflation'], [C.real, 'Bénéfices réels'], [C.mult, 'Multiple'], [C.div, 'Dividendes'], ['#38bdf8', 'Total (somme des couches)'], [C.sp, 'S&P 500', true]]} />
            <StackChart cu={d.cumul} />
            <p className="text-xs text-gray-500">Facteur cumulé depuis le départ (échelle logarithmique) : les couches s'empilent et leur somme est le rendement total. Au-dessus de ×1, ce qui a fait monter ; en dessous, ce qui a fait baisser.</p>
          </>
        )}
      </section>
    </div>
  )
}
