import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import SlidePanes, { useSelectedTicker } from '../../components/nasdaq/SlidePanes'
import TickerSheet from '../../components/nasdaq/TickerSheet'
import { C, LABELS, PERIODS, pct, times } from '../../components/nasdaq/ValeurPanel'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'
const LAYERS = ['infl', 'real', 'mult', 'div']
const ratioHex = (r, degraded) => (degraded || r == null ? '#f87171' : r <= 2 ? '#6ee7b7' : r <= 3 ? '#fcd34d' : '#fca5a5')
const SORTS = [
  { v: 'total', l: 'Rendement total', f: r => -r.period.annual.total },
  { v: 'borrowed', l: 'Part empruntée', f: r => -(r.period.borrowed ?? -1) },
  { v: 'ratio', l: 'Rapport au plancher', f: r => -(r.ratio ?? 99) },
]

function Bars({ rows, sp, watch, onOpen }) {
  const W = 1000, RH = 24, L = 170, R0 = 640, top = 26
  const H = top + rows.length * RH + 8
  const vals = rows.flatMap(r => {
    const a = r.period.annual
    const pos = LAYERS.reduce((s, k) => s + Math.max(0, a[k] || 0), 0)
    const neg = LAYERS.reduce((s, k) => s + Math.min(0, a[k] || 0), 0)
    return [pos, neg, a.total]
  })
  const lo = Math.min(0, ...vals), hi = Math.max(0.05, ...vals, sp ?? 0)
  const x = v => L + ((v - lo) / (hi - lo)) * (R0 - L)
  const ticks = []
  const step = hi - lo > 0.8 ? 0.2 : 0.1
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) ticks.push(+t.toFixed(2))
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Décomposition annuelle de la hausse par titre">
      {ticks.map(t => <g key={t}><line x1={x(t)} x2={x(t)} y1={top - 6} y2={H - 8} stroke={t === 0 ? '#4b5563' : '#1f2937'} /><text x={x(t)} y={top - 10} fontSize="10" fill="#9ca3af" textAnchor="middle">{Math.round(t * 100)} %</text></g>)}
      {sp != null && <g><line x1={x(sp)} x2={x(sp)} y1={top - 6} y2={H - 8} stroke={C.sp} strokeDasharray="4 3" /><text x={x(sp) + 3} y={H - 10} fontSize="10" fill={C.sp}>S&amp;P 500 {pct(sp, 1)}/an</text></g>}
      <text x={R0 + 14} y={top - 10} fontSize="10" fill="#9ca3af">Total sur la période · par an · rapport au plancher</text>
      {rows.map((r, i) => {
        const a = r.period.annual, f = r.period.factor
        const y = top + i * RH
        let pb = 0, nb = 0
        const segs = LAYERS.map(k => {
          const v = a[k] || 0
          const s = v >= 0 ? [pb, pb + v] : [nb + v, nb]
          if (v >= 0) pb += v; else nb += v
          return <rect key={k} x={x(s[0])} y={y + 4} width={Math.max(0, x(s[1]) - x(s[0]))} height={RH - 8} fill={C[k]} opacity={v >= 0 ? 0.9 : 0.5}><title>{`${LABELS[k]} : ${pct(v)} par an`}</title></rect>
        })
        return (
          <g key={r.ticker} className="cursor-pointer" onClick={() => onOpen(r.ticker, 'valeur')}>
            <rect x={0} y={y} width={W} height={RH} fill="transparent" />
            <text x={L - 8} y={y + RH / 2 + 4} fontSize="12" fill={watch.has(r.ticker) ? '#fcd34d' : '#e5e7eb'} textAnchor="end">{watch.has(r.ticker) ? '★ ' : ''}{r.ticker}{r.period.shifted ? ' *' : ''}</text>
            {segs}
            <path d={`M${x(a.total)},${y + 3} l5,${RH / 2 - 3} l-5,${RH / 2 - 3} l-5,${-(RH / 2 - 3)} z`} fill="#38bdf8" stroke="#0c4a6e"><title>{`Total : ${pct(a.total)} par an`}</title></path>
            <text x={R0 + 14} y={y + RH / 2 + 4} fontSize="12" fill="#e5e7eb">{times(f.total)}</text>
            <text x={R0 + 80} y={y + RH / 2 + 4} fontSize="12" fill="#93c5fd">{pct(a.total)}</text>
            <text x={R0 + 160} y={y + RH / 2 + 4} fontSize="12" fill={ratioHex(r.ratio, r.degraded)}>{r.ratio ? `${times(r.ratio)} le plancher${r.degraded ? ' · caduc' : ''}` : 'pas de plancher'}</text>
            {r.period.borrowed != null && <text x={R0 + 300} y={y + RH / 2 + 4} fontSize="11" fill={r.period.borrowed > 0.05 ? C.mult : C.real}>{r.period.borrowed > 0.05 ? `${Math.round(100 * r.period.borrowed)} % emprunté` : 'méritée'}</text>}
          </g>
        )
      })}
    </svg>
  )
}

export default function NasdaqValeur() {
  const [period, setPeriod] = useState('10y')
  const [sum, setSum] = useState(null)
  const [snap, setSnap] = useState(null)
  const [watch, setWatch] = useState(new Set())
  const [onlyWatch, setOnlyWatch] = useState(false)
  const [sort, setSort] = useState('total')
  const [err, setErr] = useState(null)
  const [selected, openTicker, closeTicker] = useSelectedTicker()

  useEffect(() => {
    fetch(`${API}/nasdaq/snapshot`).then(r => r.json()).then(setSnap).catch(e => setErr(String(e)))
    fetch(`${API}/nasdaq/watchlist`).then(r => r.json()).then(j => setWatch(new Set(j.tickers))).catch(() => {})
  }, [])
  useEffect(() => {
    setSum(null)
    fetch(`${API}/nasdaq/valeur/summary?period=${period}`).then(r => r.json()).then(setSum).catch(e => setErr(String(e)))
  }, [period])

  const byTicker = useMemo(() => Object.fromEntries((snap?.rows || []).map(r => [r.ticker, r])), [snap])
  const all = (sum?.rows || []).filter(r => !onlyWatch || watch.has(r.ticker))
  const ok = all.filter(r => r.period?.ok).sort((a, b) => SORTS.find(s => s.v === sort).f(a) - SORTS.find(s => s.v === sort).f(b))
  const ko = all.filter(r => !r.period?.ok)
  const sp = ok[0]?.period?.annual?.sp ?? null

  const mainView = (
    <div className="pb-8 space-y-4">
      <Link href="/nasdaq" className="text-sm text-gray-500 hover:text-white">← Suivi NASDAQ</Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-white">Valeur du temps passé</h1>
        <div className="flex rounded border border-gray-700 overflow-hidden">
          {PERIODS.map(o => <button key={o.v} onClick={() => setPeriod(o.v)} className={`px-2.5 py-1 text-xs ${period === o.v ? 'bg-sky-900 text-white' : 'text-gray-400 hover:text-white'}`}>{o.l}</button>)}
        </div>
        <div className="flex rounded border border-gray-700 overflow-hidden">
          {[[false, 'Tous les titres'], [true, 'Ma liste']].map(([v, l]) => <button key={l} onClick={() => setOnlyWatch(v)} className={`px-2.5 py-1 text-xs ${onlyWatch === v ? 'bg-sky-900 text-white' : 'text-gray-400 hover:text-white'}`}>{l}</button>)}
        </div>
        <label className="text-xs text-gray-400">Trier par{' '}
          <select value={sort} onChange={e => setSort(e.target.value)} className="ml-1 rounded border border-gray-700 bg-gray-900 px-2 py-1 text-xs text-white">
            {SORTS.map(s => <option key={s.v} value={s.v}>{s.l}</option>)}
          </select>
        </label>
      </div>
      <p className="text-sm text-gray-400 max-w-3xl">
        D'où vient le rendement annuel de chaque titre : <span style={{ color: C.infl }}>l'inflation</span>, <span style={{ color: C.real }}>la croissance réelle des bénéfices</span> (méritée),{' '}
        <span style={{ color: C.mult }}>la variation du multiple</span> (empruntée) et <span style={{ color: C.div }}>les dividendes</span>. Le losange bleu est le total ; à droite, ce que la mise a été multipliée par sur la période.
        Les composantes se multiplient : leur somme approche le total sans l'égaler exactement. Un clic ouvre le titre.
      </p>
      {err && <div className="rounded border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">Erreur de chargement : {err}</div>}
      {!sum ? <p className="text-sm text-gray-500">Chargement…</p> : ok.length === 0
        ? <p className="text-sm text-gray-500">Aucun titre décomposable{sum.running ? ' — rafraîchissement en cours' : ''}.</p>
        : <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-3 overflow-x-auto"><div className="min-w-[760px]"><Bars rows={ok} sp={sp} watch={watch} onOpen={openTicker} /></div></div>}
      {ok.some(r => r.period.shifted) && <p className="text-xs text-gray-500">* départ décalé au premier bénéfice positif mesurable.</p>}
      {ko.length > 0 && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-3">
          <h2 className="text-sm font-semibold text-white mb-2">Non décomposables sur la période ({ko.length})</h2>
          <ul className="grid gap-1 sm:grid-cols-2 text-xs text-gray-400">
            {ko.map(r => (
              <li key={r.ticker}><button onClick={() => openTicker(r.ticker, 'valeur')} className="hover:text-white"><b className="text-gray-200">{r.ticker}</b> — {r.note || r.period?.reason || 'données insuffisantes'}</button></li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )

  return (
    <SlidePanes selected={selected} main={mainView}
      detail={(t) => (
        <section className="rounded-xl border border-gray-800 bg-gray-900/50 p-4 mb-8">
          {byTicker[t] ? <TickerSheet key={t} row={byTicker[t]} ticker={t} hot={6} onClose={closeTicker} /> : <p className="text-sm text-gray-500">Chargement…</p>}
        </section>
      )} />
  )
}
