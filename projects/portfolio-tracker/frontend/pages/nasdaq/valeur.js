import Link from 'next/link'
import { useRouter } from 'next/router'
import { useEffect, useMemo, useState } from 'react'
import SlidePanes, { useSelectedTicker } from '../../components/nasdaq/SlidePanes'
import TickerSheet from '../../components/nasdaq/TickerSheet'
import ValeurPanel, { C, FLOOR_CAVEAT, LABELS, NASDAQ_LABELS, PERIODS, pct, times } from '../../components/nasdaq/ValeurPanel'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'
const LAYERS = ['infl', 'real', 'mult', 'div']
const ratioHex = (r, degraded) => (degraded || r == null ? '#f87171' : r <= 2 ? '#6ee7b7' : r <= 3 ? '#fcd34d' : '#fca5a5')
const MARKETS = [['nasdaq', 'Nasdaq'], ['cac40', 'CAC 40']]
const short = (s, n = 18) => (s && s.length > n ? `${s.slice(0, n - 1)}…` : s)
const SORTS = [
  { v: 'total', l: 'Rendement total', f: r => -r.period.annual.total },
  { v: 'borrowed', l: 'Part empruntée', f: r => -(r.period.borrowed ?? -1) },
  { v: 'ratio', l: 'Rapport au plancher', f: r => -(r.ratio ?? 99) },
]

// Échelle logarithmique : les composantes se multiplient, donc leurs logarithmes s'additionnent
// exactement jusqu'au total ; une échelle en % linéaire empilerait des taux qui ne s'additionnent pas.
const lg = r => Math.log1p(r || 0)
const TICKS = [-0.75, -0.5, -0.25, 0, 0.25, 0.5, 1, 2, 3, 5]

function Bars({ rows, sp, watch, onOpen, refLabel }) {
  const named = rows.some(r => r.name)
  const W = 1000, RH = 24, L = named ? 150 : 90, R0 = 560, top = 26
  const COL = { total: R0 + 14, an: R0 + 66, ratio: R0 + 140, part: R0 + 320 }
  const H = top + rows.length * RH + 26
  const vals = rows.flatMap(r => {
    const a = r.period.annual
    const pos = LAYERS.reduce((s, k) => s + Math.max(0, lg(a[k])), 0)
    const neg = LAYERS.reduce((s, k) => s + Math.min(0, lg(a[k])), 0)
    return [pos, neg, lg(a.total)]
  })
  const lo = Math.min(0, ...vals), hi = Math.max(lg(0.05), ...vals, lg(sp))
  const x = v => L + ((v - lo) / (hi - lo)) * (R0 - L)
  const ticks = TICKS.filter(t => lg(t) >= lo - 1e-9 && lg(t) <= hi + 1e-9)
  const mid = (y) => y + RH / 2 + 4
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Décomposition annuelle de la hausse par titre">
      {ticks.map(t => <g key={t}><line x1={x(lg(t))} x2={x(lg(t))} y1={top - 6} y2={H - 26} stroke={t === 0 ? '#4b5563' : '#1f2937'} /><text x={x(lg(t))} y={top - 10} fontSize="10" fill="#9ca3af" textAnchor="middle">{t > 0 ? '+' : ''}{Math.round(t * 100)} %</text></g>)}
      {sp != null && <g><line x1={x(lg(sp))} x2={x(lg(sp))} y1={top - 6} y2={H - 20} stroke={C.sp} strokeDasharray="4 3" /><text x={x(lg(sp))} y={H - 6} fontSize="10" fill={C.sp} textAnchor="middle">{refLabel} {pct(sp, 1)}/an</text></g>}
      <text x={COL.total} y={top - 10} fontSize="10" fill="#9ca3af">Mise ×</text>
      <text x={COL.an} y={top - 10} fontSize="10" fill="#9ca3af">Par an</text>
      <text x={COL.ratio} y={top - 10} fontSize="10" fill="#9ca3af">Cours / plancher</text>
      <text x={COL.part} y={top - 10} fontSize="10" fill="#9ca3af">Hausse</text>
      {rows.map((r, i) => {
        const a = r.period.annual, f = r.period.factor
        const y = top + i * RH
        let pb = 0, nb = 0
        const segs = LAYERS.map(k => {
          const v = lg(a[k])
          const s = v >= 0 ? [pb, pb + v] : [nb + v, nb]
          if (v >= 0) pb += v; else nb += v
          return <rect key={k} x={x(s[0])} y={y + 4} width={Math.max(0, x(s[1]) - x(s[0]))} height={RH - 8} fill={C[k]} opacity={v >= 0 ? 0.9 : 0.5}><title>{`${LABELS[k]} : ${pct(a[k])} par an`}</title></rect>
        })
        const xt = x(lg(a.total))
        return (
          <g key={r.ticker} className="cursor-pointer" onClick={() => onOpen(r.ticker, 'valeur')}>
            <rect x={0} y={y} width={W} height={RH} fill="transparent" />
            <text x={L - 8} y={mid(y)} fontSize="12" fill={watch.has(r.ticker) ? '#fcd34d' : '#e5e7eb'} textAnchor="end">{watch.has(r.ticker) ? '★ ' : ''}{r.name ? short(r.name) : r.ticker}{r.period.shifted ? ' *' : ''}{r.name && <title>{`${r.name} (${r.ticker})`}</title>}</text>
            {segs}
            <path d={`M${xt},${y + 3} l5,${RH / 2 - 3} l-5,${RH / 2 - 3} l-5,${-(RH / 2 - 3)} z`} fill="#38bdf8" stroke="#0c4a6e"><title>{`Total : ${pct(a.total)} par an`}</title></path>
            <text x={COL.total} y={mid(y)} fontSize="12" fill="#e5e7eb">{times(f.total)}</text>
            <text x={COL.an} y={mid(y)} fontSize="12" fill="#93c5fd">{pct(a.total)}</text>
            <text x={COL.ratio} y={mid(y)} fontSize="12" fill={ratioHex(r.ratio, r.degraded)}>{r.ratio ? `${times(r.ratio)}${r.degraded ? ' · caduc' : ''}` : 'pas de plancher'}</text>
            {r.period.borrowed != null && <text x={COL.part} y={mid(y)} fontSize="12" fill={r.period.borrowed > 0.05 ? C.mult : C.real}>{r.period.borrowed > 0.05 ? `${Math.round(100 * r.period.borrowed)} % empruntée` : 'méritée'}</text>}
          </g>
        )
      })}
    </svg>
  )
}

export default function NasdaqValeur() {
  const router = useRouter()
  const market = router.query.m === 'cac40' ? 'cac40' : 'nasdaq'
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
  // Le CAC 40 n'a de comptes ESEF que depuis 2020 : ni 10 ans ni « depuis 2010 » (l'API le dit, `labels.periods`).
  const per = market === 'cac40' && !['3y', '5y'].includes(period) ? '5y' : period
  useEffect(() => {
    if (!router.isReady) return
    setSum(null)
    fetch(`${API}/nasdaq/valeur/summary?period=${per}&market=${market}`).then(r => r.json()).then(setSum).catch(e => setErr(String(e)))
  }, [per, market, router.isReady])
  const L = sum?.labels || NASDAQ_LABELS
  const setMarket = (m) => {
    const { m: _m, t: _t, v: _v, ...q } = router.query
    router.replace({ pathname: router.pathname, query: m === 'nasdaq' ? q : { ...q, m } }, undefined, { shallow: true, scroll: false })
  }

  const byTicker = useMemo(() => Object.fromEntries((snap?.rows || []).map(r => [r.ticker, r])), [snap])
  const eu = market === 'cac40'
  const all = (sum?.rows || []).filter(r => eu || !onlyWatch || watch.has(r.ticker))
  const ok = all.filter(r => r.period?.ok).sort((a, b) => SORTS.find(s => s.v === sort).f(a) - SORTS.find(s => s.v === sort).f(b))
  const ko = all.filter(r => !r.period?.ok)
  // Un départ décalé a son propre S&P 500 : la référence commune se lit sur un titre au départ de la période.
  const sp = ok.find(r => !r.period.shifted)?.period?.annual?.sp ?? null

  const mainView = (
    <div className="pb-8 space-y-4">
      <Link href="/nasdaq" className="text-sm text-gray-500 hover:text-white">← Suivi NASDAQ</Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-white">Valeur du temps passé</h1>
        <div className="flex rounded border border-gray-700 overflow-hidden">
          {MARKETS.map(([v, l]) => <button key={v} onClick={() => setMarket(v)} className={`px-2.5 py-1 text-xs ${market === v ? 'bg-emerald-900 text-white' : 'text-gray-400 hover:text-white'}`}>{l}</button>)}
        </div>
        <div className="flex rounded border border-gray-700 overflow-hidden">
          {PERIODS.filter(o => L.periods.includes(o.v)).map(o => <button key={o.v} onClick={() => setPeriod(o.v)} className={`px-2.5 py-1 text-xs ${per === o.v ? 'bg-sky-900 text-white' : 'text-gray-400 hover:text-white'}`}>{o.l}</button>)}
        </div>
        {!eu && <div className="flex rounded border border-gray-700 overflow-hidden">
          {[[false, 'Tous les titres'], [true, 'Ma liste']].map(([v, l]) => <button key={l} onClick={() => setOnlyWatch(v)} className={`px-2.5 py-1 text-xs ${onlyWatch === v ? 'bg-sky-900 text-white' : 'text-gray-400 hover:text-white'}`}>{l}</button>)}
        </div>}
        <label className="text-xs text-gray-400">Trier par{' '}
          <select value={sort} onChange={e => setSort(e.target.value)} className="ml-1 rounded border border-gray-700 bg-gray-900 px-2 py-1 text-xs text-white">
            {SORTS.map(s => <option key={s.v} value={s.v}>{s.l}</option>)}
          </select>
        </label>
      </div>
      <p className="text-sm text-gray-400 max-w-3xl">
        D'où vient le rendement annuel de chaque titre : <span style={{ color: C.infl }}>l'inflation</span>, <span style={{ color: C.real }}>la croissance réelle des bénéfices</span> (méritée),{' '}
        <span style={{ color: C.mult }}>la variation du multiple</span> (empruntée) et <span style={{ color: C.div }}>les dividendes</span>. Le losange bleu est le total ; à droite, par combien la mise a été multipliée sur la période et le rapport du cours à son plancher.
        Les composantes se multiplient : l'échelle est logarithmique pour que leurs longueurs s'ajoutent exactement jusqu'au losange. Un clic ouvre le titre.
        {eu && <> Pour le CAC 40 : bénéfice du dernier exercice publié ({L.source}), connu 4 mois après la clôture ; {L.infl} ; référence {L.ref}, dividendes réinvestis.</>}
      </p>
      {eu && <p className="text-xs text-amber-200/80 max-w-3xl">{FLOOR_CAVEAT}</p>}
      {err && <div className="rounded border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">Erreur de chargement : {err}</div>}
      {!sum ? <p className="text-sm text-gray-500">Chargement…</p> : ok.length === 0
        ? <p className="text-sm text-gray-500">Aucun titre décomposable{sum.running ? ' — rafraîchissement en cours' : ''}.</p>
        : <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-3 overflow-x-auto"><div className="min-w-[760px]"><Bars rows={ok} sp={sp} watch={eu ? new Set() : watch} onOpen={openTicker} refLabel={L.ref} /></div></div>}
      {ok.some(r => r.period.shifted) && <p className="text-xs text-gray-500">* départ décalé au premier bénéfice positif mesurable.</p>}
      {ko.length > 0 && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-3">
          <h2 className="text-sm font-semibold text-white mb-2">Non décomposables sur la période ({ko.length})</h2>
          <ul className="grid gap-1 sm:grid-cols-2 text-xs text-gray-400">
            {ko.map(r => (
              <li key={r.ticker}><button onClick={() => openTicker(r.ticker, 'valeur')} className="hover:text-white"><b className="text-gray-200">{r.name || r.ticker}</b> — {[r.period?.reason, r.note].filter(Boolean).join(' ; ') || 'données insuffisantes'}</button></li>
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
          {eu ? (
            // La fiche Nasdaq (`TickerSheet`) dépend du suivi des cours du Nasdaq : en CAC 40, la valeur seule.
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-white">{(sum?.rows || []).find(r => r.ticker === t)?.name || t} <span className="text-sm text-gray-500">{t}</span></h2>
                <button onClick={closeTicker} className="text-sm text-gray-400 hover:text-white">✕ Fermer</button>
              </div>
              <ValeurPanel key={t} ticker={t} market="cac40" name={(sum?.rows || []).find(r => r.ticker === t)?.name} />
            </div>
          ) : byTicker[t] ? <TickerSheet key={t} row={byTicker[t]} ticker={t} hot={6} onClose={closeTicker} /> : <p className="text-sm text-gray-500">Chargement…</p>}
        </section>
      )} />
  )
}
