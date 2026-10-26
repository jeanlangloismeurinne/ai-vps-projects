import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import BubbleChart, { BASES_LIST, fmtAge, fmtCap, fmtJump, fmtMult } from '../components/nasdaq/BubbleChart'
import TickerSheet from '../components/nasdaq/TickerSheet'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'
const DPM = 30.4375
const SPLITS = [{ v: 'none', l: 'Un seul graphique' }, { v: 'mult', l: 'Par multiple sur 10 ans' }, { v: 'cap', l: 'Par capitalisation' }]
const TRAILS = [{ v: 0, l: 'Aucune' }, { v: 5, l: '1 semaine' }, { v: 20, l: '1 mois' }, { v: 60, l: '3 mois' }]
const CAP_BANDS = [
  { key: 'c500', label: '≥ 500 Md$', min: 5e11 }, { key: 'c200', label: '200 à 500 Md$', min: 2e11 },
  { key: 'c100', label: '100 à 200 Md$', min: 1e11 }, { key: 'c0', label: '< 100 Md$', min: 0 },
]
const num = (v) => parseFloat(String(v).replace(',', '.'))
const ATL_AGE = 1e6 // tri : un plus bas historique passe avant toute ancienneté chiffrée
const ageKey = (r) => (r.is_atl ? ATL_AGE : r.age_months ?? -1)

const COLS = [
  { k: 'ticker', l: 'Ticker', get: r => r.ticker },
  { k: 'name', l: 'Nom', get: r => r.name.replace(/ - .*$/, '') },
  { k: 'price', l: 'Cours ($)', get: r => r.price, num: true },
  { k: 'age', l: 'Ancienneté (mois)', get: ageKey, num: true },
  { k: 'mult', l: 'Multiple 10 ans', get: r => r.multiple_10y ?? -1, num: true },
  { k: 'jump5', l: 'Saut 5 j (mois)', get: r => r.jump5 ?? -999, num: true },
  { k: 'jump20', l: 'Saut 20 j (mois)', get: r => r.jump20 ?? -999, num: true },
  { k: 'cap', l: 'Capitalisation', get: r => r.market_cap ?? -1, num: true },
  { k: 'alert', l: 'Alerte', get: r => (r.alert_new ? 2 : r.alert ? 1 : 0), num: true },
]

function csvCell(v) {
  const s = String(v ?? '')
  return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export default function Nasdaq() {
  const [snap, setSnap] = useState(null)
  const [err, setErr] = useState(null)
  const [status, setStatus] = useState(null)
  const [minCap, setMinCap] = useState('')
  const [maxCap, setMaxCap] = useState('')
  const [series, setSeries] = useState(null)
  const [jumpWin, setJumpWin] = useState(20)
  const [minJump, setMinJump] = useState('')
  const [trailWin, setTrailWin] = useState(20)
  const [split, setSplit] = useState('none')
  const [selected, setSelected] = useState(null)
  const [base, setBase] = useState(2)
  const [minMult, setMinMult] = useState('')
  const [minAge, setMinAge] = useState('')
  const [query, setQuery] = useState('')
  const [onlyAlerts, setOnlyAlerts] = useState(false)
  const [sort, setSort] = useState({ k: 'cap', dir: -1 })
  const [limit, setLimit] = useState(100)
  const [openCats, setOpenCats] = useState({})

  const load = useCallback(() => {
    fetch(`${API}/nasdaq/snapshot`).then(r => r.json()).then(setSnap).catch(e => setErr(String(e)))
  }, [])
  const loadStatus = useCallback(() => {
    fetch(`${API}/nasdaq/status`).then(r => r.json()).then(setStatus).catch(() => {})
  }, [])
  useEffect(() => { load(); loadStatus() }, [load, loadStatus])
  useEffect(() => {
    if (!snap?.run_date) return
    fetch(`${API}/nasdaq/series`).then(r => r.json()).then(setSeries).catch(() => setSeries(null))
  }, [snap?.run_date])
  useEffect(() => {
    if (!status?.running) return
    const t = setInterval(() => { loadStatus() }, 4000)
    return () => clearInterval(t)
  }, [status?.running, loadStatus])
  useEffect(() => { if (status && !status.running) load() }, [status?.running]) // eslint-disable-line

  const lancer = async () => {
    const r = await fetch(`${API}/nasdaq/run`, { method: 'POST' })
    if (r.ok || r.status === 409) loadStatus()
  }

  const rawRows = snap?.rows ?? []
  const rows = useMemo(() => {
    const S = series?.series ?? {}
    return rawRows.map(r => {
      const q = S[r.ticker]
      if (!q) return r
      const L = q.d.length - 1
      const at = (N) => (L - N >= 0 ? L - N : null)
      const jump = (N) => { const i = at(N); return i == null ? null : ((q.a[L] - q.a[i]) - (q.d[L] - q.d[i])) / DPM }
      const pi = trailWin ? at(trailWin) : null
      return {
        ...r, jump5: jump(5), jump20: jump(20),
        fact20: at(20) == null ? null : (1 + q.a[L] / DPM) / (1 + (q.a[at(20)] + q.d[L] - q.d[at(20)]) / DPM),
        prev: pi == null ? null : { age: Math.round(q.a[pi] / DPM), atl: !!q.l[pi], mult: q.m[pi] },
      }
    })
  }, [rawRows, series, trailWin])
  const filtered = useMemo(() => {
    const q = query.trim().toUpperCase()
    const lo = num(minCap) * 1e9, hi = num(maxCap) * 1e9
    return rows.filter(r => (isNaN(lo) || (r.market_cap ?? 0) >= lo) && (isNaN(hi) || (r.market_cap ?? 0) <= hi)
      && (!q || r.ticker.includes(q) || r.name.toUpperCase().includes(q)))
  }, [rows, minCap, maxCap, query])
  const shown = useMemo(() => {
    const m = num(minMult), a = num(minAge), j = num(minJump)
    return filtered.filter(r => (!onlyAlerts || r.alert)
      && (isNaN(m) || (r.multiple_10y ?? 0) >= m) && (isNaN(a) || r.is_atl || (r.age_months ?? 0) >= a)
      && (isNaN(j) || (r['jump' + jumpWin] ?? -Infinity) >= j))
  }, [filtered, onlyAlerts, minMult, minAge, minJump, jumpWin])
  const ranking = useMemo(() => filtered.filter(r => (r['jump' + jumpWin] ?? 0) > 0)
    .sort((a, b) => b['jump' + jumpWin] - a['jump' + jumpWin]).slice(0, 10), [filtered, jumpWin])
  const jumpHot = isNaN(num(minJump)) ? 6 : num(minJump)
  const maxCapShown = Math.max(1, ...shown.map(r => r.market_cap || 0))
  const panels = useMemo(() => {
    if (split === 'none') return [{ key: 'all', label: null, rows: shown }]
    const defs = split === 'mult' ? (snap?.categories ?? []) : CAP_BANDS
    const out = defs.map(d => ({ key: d.key, label: d.label, rows: [] }))
    for (const r of shown) {
      const v = split === 'mult' ? (r.multiple_10y ?? 0) : (r.market_cap ?? 0)
      const i = defs.findIndex(d => v >= d.min)
      out[i < 0 ? out.length - 1 : i].rows.push(r)
    }
    return out.filter(p => p.rows.length)
  }, [shown, split, snap])

  const groups = useMemo(() => {
    const cats = snap?.categories ?? []
    const out = cats.map(c => ({ ...c, items: [] }))
    for (const r of filtered) {
      if (!r.alert) continue
      const m = r.multiple_10y ?? 0
      const g = out.find(c => m >= c.min) ?? out[out.length - 1]
      g.items.push(r)
    }
    for (const g of out) g.items.sort((a, b) => ageKey(b) - ageKey(a) || (b.market_cap ?? 0) - (a.market_cap ?? 0))
    return out.filter(g => g.items.length)
  }, [filtered, snap])
  const nbAlerts = groups.reduce((n, g) => n + g.items.length, 0)
  const nbNew = filtered.filter(r => r.alert_new).length

  const sorted = useMemo(() => {
    const col = COLS.find(c => c.k === sort.k)
    return [...shown].sort((a, b) => {
      const x = col.get(a), y = col.get(b)
      const c = col.num ? x - y : String(x).localeCompare(String(y))
      return c * sort.dir || a.ticker.localeCompare(b.ticker)
    })
  }, [shown, sort])

  const exportCsv = () => {
    const head = ['ticker', 'nom', 'cours', 'anciennete_mois', 'plus_bas_historique', 'multiple_10_ans', 'moins_de_10_ans', 'saut_5j_mois', 'saut_20j_mois', 'capitalisation', 'alerte', 'nouvelle_alerte']
    const lines = [head.join(';')].concat(sorted.map(r => [
      r.ticker, r.name, r.price, r.is_atl ? '' : r.age_months, r.is_atl ? 'oui' : '', r.multiple_10y?.toFixed(3) ?? '',
      r.lt_10y ? 'oui' : '', r.jump5?.toFixed(1) ?? '', r.jump20?.toFixed(1) ?? '', r.market_cap ?? '', r.alert ? 'oui' : '', r.alert_new ? 'oui' : ''].map(csvCell).join(';')))
    const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `nasdaq_${snap.run_date}.csv`
    a.click()
  }

  const dateFr = snap?.run_date ? new Date(snap.run_date + 'T12:00:00').toLocaleDateString('fr-FR') : null
  const lastRun = status?.runs?.[0]

  return (
    <div className="min-h-screen px-4 md:px-8 py-8 max-w-[1400px] mx-auto">
      <Link href="/" className="text-sm text-gray-500 hover:text-white">← Choix de l'espace</Link>
      <div className="mt-4 mb-5 flex flex-wrap items-center gap-3">
        <span className="text-3xl">🫧</span>
        <h1 className="text-2xl font-bold text-white">Suivi NASDAQ</h1>
        <span className="text-sm text-gray-400">
          {dateFr ? `Clôture du ${dateFr} · ${rawRows.length} entreprises` : 'Aucune donnée publiée'}
        </span>
        <div className="ml-auto flex items-center gap-2">
          {status?.running && (
            <span className="text-xs text-sky-300">
              Calcul en cours — {status.step}{status.total ? ` (${status.done}/${status.total})` : ''}
            </span>
          )}
          <button onClick={lancer} disabled={status?.running}
            className="text-xs px-3 py-1.5 rounded border border-gray-700 text-gray-300 hover:text-white disabled:opacity-40">
            Recalculer maintenant
          </button>
        </div>
      </div>

      {err && <div className="mb-4 rounded border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">Erreur de chargement : {err}</div>}
      {snap?.warning && (
        <div className="mb-4 rounded border border-amber-700 bg-amber-950/40 p-3 text-sm text-amber-200">⚠️ {snap.warning}</div>
      )}
      {lastRun && lastRun.status !== 'ok' && !snap?.warning && (
        <div className="mb-4 rounded border border-amber-700 bg-amber-950/40 p-3 text-sm text-amber-200">⚠️ {lastRun.warning}</div>
      )}

      <section className="mb-4 flex flex-wrap items-end gap-4 rounded-xl border border-gray-800 bg-gray-900/50 p-4">
        <label className="text-xs text-gray-400">Capitalisation ≥ (Md$)
          <input value={minCap} onChange={e => { setMinCap(e.target.value); setLimit(100) }} placeholder="ex. 200" inputMode="decimal"
            className="mt-1 block rounded bg-gray-800 border border-gray-700 px-2 py-1.5 text-sm text-white w-28" />
        </label>
        <label className="text-xs text-gray-400">Capitalisation ≤ (Md$)
          <input value={maxCap} onChange={e => { setMaxCap(e.target.value); setLimit(100) }} placeholder="ex. 500" inputMode="decimal"
            className="mt-1 block rounded bg-gray-800 border border-gray-700 px-2 py-1.5 text-sm text-white w-28" />
        </label>
        <label className="text-xs text-gray-400">Recherche (ticker ou nom)
          <input value={query} onChange={e => { setQuery(e.target.value); setLimit(100) }} placeholder="ex. NVDA"
            className="mt-1 block rounded bg-gray-800 border border-gray-700 px-2 py-1.5 text-sm text-white w-44" />
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-300 pb-1.5">
          <input type="checkbox" checked={onlyAlerts} onChange={e => setOnlyAlerts(e.target.checked)} />
          Alertes uniquement
        </label>
        <span className="ml-auto text-xs text-gray-500 pb-2">{shown.length} titres affichés sur {rawRows.length} · filtres d'affichage seulement (l'analyse porte toujours sur ≥ 50 Md$)</span>
      </section>

      <section className="mb-6 rounded-xl border border-red-900/60 bg-gray-900/50 p-4">
        <h2 className="text-sm font-semibold text-white mb-1">
          Alertes — cours observé pour la dernière fois il y a 12 mois ou plus
          <span className="ml-2 font-normal text-gray-400">{nbAlerts} actives{nbNew ? ` · ${nbNew} nouvelles aujourd'hui` : ''}</span>
        </h2>
        <p className="text-xs text-gray-500 mb-3">Groupées par multiple sur 10 ans ; dans chaque groupe : ancienneté décroissante, puis capitalisation décroissante.</p>
        {groups.length === 0 && <p className="text-sm text-gray-500">Aucune alerte avec ces filtres.</p>}
        {groups.map(g => {
          const open = openCats[g.key] ?? false
          const items = open ? g.items : g.items.slice(0, 8)
          return (
            <div key={g.key} className="mb-3">
              <div className="text-xs font-semibold text-gray-300 mb-1">{g.label} <span className="text-gray-500 font-normal">· {g.items.length}</span></div>
              <div className="flex flex-wrap gap-1.5">
                {items.map(r => (
                  <button key={r.ticker} onClick={() => setQuery(r.ticker)}
                    title={`${r.name} — ${fmtAge(r)} · ${fmtMult(r)} · ${fmtCap(r.market_cap)}`}
                    className={`rounded border px-2 py-1 text-xs ${r.alert_new ? 'border-red-500 bg-red-950/60 text-red-200' : 'border-gray-700 bg-gray-800/60 text-gray-300'} hover:text-white`}>
                    <b>{r.ticker}</b> <span className="text-gray-400">{r.is_atl ? 'ATL' : `${r.age_months} m`} · {r.multiple_10y == null ? '–' : `${r.multiple_10y.toFixed(1)}×`}</span>
                  </button>
                ))}
                {g.items.length > 8 && (
                  <button onClick={() => setOpenCats({ ...openCats, [g.key]: !open })}
                    className="text-xs px-2 py-1 text-sky-300 hover:text-sky-200">
                    {open ? 'Réduire' : `+ ${g.items.length - 8} autres`}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </section>

      <section className="mb-6 rounded-xl border border-amber-900/60 bg-gray-900/50 p-4">
        <div className="flex flex-wrap items-center gap-3 mb-1">
          <h2 className="text-sm font-semibold text-white">Plus fortes hausses d'ancienneté</h2>
          <select value={jumpWin} onChange={e => setJumpWin(Number(e.target.value))}
            className="rounded bg-gray-800 border border-gray-700 px-2 py-1 text-xs text-white">
            <option value={5}>sur 5 séances</option><option value={20}>sur 20 séances</option>
          </select>
        </div>
        <p className="text-xs text-gray-500 mb-3">Saut = ancienneté d'aujourd'hui moins celle d'il y a N séances, temps écoulé retiré : un titre stable fait 0, un titre qui retombe à un niveau absent depuis longtemps fait un grand saut. Le facteur ×N compare la durée avant/après (3 → 20 mois = ×4).</p>
        {!series && <p className="text-sm text-gray-500">Chargement des séries…</p>}
        {series && ranking.length === 0 && <p className="text-sm text-gray-500">Aucune hausse avec ces filtres.</p>}
        <div className="flex flex-wrap gap-1.5">
          {ranking.map(r => (
            <button key={r.ticker} onClick={() => setSelected(r.ticker)}
              title={`${r.name} — ancienneté ${fmtAge(r)} · multiple ${fmtMult(r)} · ${fmtCap(r.market_cap)}`}
              className={`rounded border px-2 py-1 text-xs ${r['jump' + jumpWin] >= jumpHot ? 'border-red-500 bg-red-950/60 text-red-200' : 'border-gray-700 bg-gray-800/60 text-gray-300'} hover:text-white`}>
              <b>{r.ticker}</b> <span className="text-gray-400">{fmtJump(r['jump' + jumpWin])} m{jumpWin === 20 && r.fact20 ? ` · ×${r.fact20.toFixed(1)}` : ''} · {r.is_atl ? 'ATL' : `${r.age_months} m`}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="mb-6 rounded-xl border border-gray-800 bg-gray-900/50 p-4">
        <div className="flex flex-wrap items-center gap-4 mb-2 text-xs text-gray-400">
          <span className="text-sm font-semibold text-white">Ancienneté du cours × multiple 10 ans</span>
          <span><i className="inline-block w-3 h-3 rounded-full align-[-2px] mr-1" style={{ background: 'rgba(239,68,68,.5)' }} />alerte (≥ 12 mois ou ATL)</span>
          <span><i className="inline-block w-3 h-3 rounded-full align-[-2px] mr-1" style={{ background: 'rgba(156,163,175,.4)' }} />autres</span>
          <span>Surface ∝ capitalisation · molette = zoom · glisser = déplacer · clic = fiche du titre · pointillé = 1×</span>
          {trailWin > 0 && <span><i className="inline-block w-4 h-0.5 align-middle mr-1" style={{ background: 'rgba(125,211,252,.8)' }} />traînée = position d'il y a {TRAILS.find(t => t.v === trailWin)?.l}, <i className="inline-block w-4 h-0.5 align-middle mx-1" style={{ background: 'rgb(248,113,113)' }} />rouge = saut ≥ {jumpHot} mois</span>}
        </div>
        <div className="mb-3 flex flex-wrap items-end gap-4 text-xs text-gray-400">
          <label>Échelle horizontale
            <select value={base} onChange={e => setBase(e.target.value === 'lin' ? 'lin' : Number(e.target.value))}
              className="mt-1 block rounded bg-gray-800 border border-gray-700 px-2 py-1.5 text-sm text-white">
              {BASES_LIST.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
            </select>
          </label>
          <label>Multiple 10 ans ≥
            <input value={minMult} onChange={e => setMinMult(e.target.value)} placeholder="ex. 2" inputMode="decimal"
              className="mt-1 block rounded bg-gray-800 border border-gray-700 px-2 py-1.5 text-sm text-white w-24" />
          </label>
          <label>Ancienneté ≥ (mois)
            <input value={minAge} onChange={e => setMinAge(e.target.value)} placeholder="ex. 12" inputMode="decimal"
              className="mt-1 block rounded bg-gray-800 border border-gray-700 px-2 py-1.5 text-sm text-white w-24" />
          </label>
          <label>Saut ≥ (mois, sur {jumpWin} séances)
            <input value={minJump} onChange={e => setMinJump(e.target.value)} placeholder="ex. 6" inputMode="decimal"
              className="mt-1 block rounded bg-gray-800 border border-gray-700 px-2 py-1.5 text-sm text-white w-24" />
          </label>
          <label>Traînée
            <select value={trailWin} onChange={e => setTrailWin(Number(e.target.value))}
              className="mt-1 block rounded bg-gray-800 border border-gray-700 px-2 py-1.5 text-sm text-white">
              {TRAILS.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
            </select>
          </label>
          <label>Découpage
            <select value={split} onChange={e => setSplit(e.target.value)}
              className="mt-1 block rounded bg-gray-800 border border-gray-700 px-2 py-1.5 text-sm text-white">
              {SPLITS.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
            </select>
          </label>
          <span className="pb-2 text-gray-500">{shown.length} titres · échelles recalculées automatiquement par graphique (plus bas historiques toujours inclus)</span>
        </div>
        <div className={split === 'none' ? '' : 'grid grid-cols-1 xl:grid-cols-2 gap-4'}>
          {panels.map(p => (
            <div key={p.key} className={split === 'none' ? '' : 'rounded-lg border border-gray-800 p-2'}>
              {p.label && <div className="text-xs font-semibold text-gray-300 mb-1">{p.label} <span className="font-normal text-gray-500">· {p.rows.length} titres</span></div>}
              <BubbleChart rows={p.rows} base={base} trail={trailWin > 0} maxCap={maxCapShown} selected={selected}
                onSelect={setSelected} jumpWin={jumpWin} jumpHot={jumpHot} compact={split !== 'none'} />
            </div>
          ))}
          {panels.length === 0 && <p className="text-sm text-gray-500">Aucun titre avec ces filtres.</p>}
        </div>
      </section>

      {selected && (
        <section className="mb-6 rounded-xl border border-gray-800 bg-gray-900/50 p-4">
          <TickerSheet row={rows.find(r => r.ticker === selected)} s={series?.series?.[selected]} hot={jumpHot}
            onClose={() => setSelected(null)} />
        </section>
      )}

      <section className="rounded-xl border border-gray-800 bg-gray-900/50 p-4">
        <div className="flex items-center mb-3">
          <h2 className="text-sm font-semibold text-white">Tableau</h2>
          <button onClick={exportCsv} disabled={!sorted.length}
            className="ml-auto text-xs px-3 py-1.5 rounded border border-gray-700 text-gray-300 hover:text-white disabled:opacity-40">
            Exporter en CSV ({sorted.length})
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-800">
                {COLS.map(c => (
                  <th key={c.k} onClick={() => setSort(s => ({ k: c.k, dir: s.k === c.k ? -s.dir : (c.num ? -1 : 1) }))}
                    className={`py-2 pr-4 cursor-pointer hover:text-white whitespace-nowrap ${c.num ? 'text-right' : ''}`}>
                    {c.l}{sort.k === c.k ? (sort.dir > 0 ? ' ▲' : ' ▼') : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.slice(0, limit).map(r => (
                <tr key={r.ticker} onClick={() => setSelected(r.ticker)} className="border-b border-gray-900 text-gray-200 cursor-pointer hover:bg-gray-800/40">
                  <td className="py-1.5 pr-4 font-semibold text-white">{r.ticker}</td>
                  <td className="py-1.5 pr-4 text-gray-400 max-w-[280px] truncate">{r.name.replace(/ - .*$/, '')}</td>
                  <td className="py-1.5 pr-4 text-right tabular-nums">{r.price.toFixed(2)}</td>
                  <td className="py-1.5 pr-4 text-right tabular-nums">
                    {r.is_atl ? <span className="rounded bg-red-900/60 text-red-200 px-1.5 text-xs">ATL</span> : r.age_months}
                    {r.short_history && <span title="Historique de moins d'un an" className="ml-1 text-amber-400">•</span>}
                  </td>
                  <td className="py-1.5 pr-4 text-right tabular-nums">{fmtMult(r)}</td>
                  <td className={`py-1.5 pr-4 text-right tabular-nums ${r.jump5 >= jumpHot ? 'text-red-300 font-semibold' : ''}`}>{fmtJump(r.jump5)}</td>
                  <td className={`py-1.5 pr-4 text-right tabular-nums ${r.jump20 >= jumpHot ? 'text-red-300 font-semibold' : ''}`}>{fmtJump(r.jump20)}</td>
                  <td className="py-1.5 pr-4 text-right tabular-nums">{fmtCap(r.market_cap)}</td>
                  <td className="py-1.5 pr-4 text-right">
                    {r.alert_new ? <span className="text-red-300 font-semibold">NOUVELLE</span> : r.alert ? <span className="text-red-400">active</span> : <span className="text-gray-600">–</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {limit < sorted.length && (
          <button onClick={() => setLimit(limit + 200)} className="mt-3 text-xs text-sky-300 hover:text-sky-200">
            Afficher 200 lignes de plus ({sorted.length - limit} restantes)
          </button>
        )}
        <p className="mt-3 text-[11px] text-gray-600">• historique de moins d'un an (introduction récente) · « &lt;10 ans » : multiple calculé depuis l'introduction en bourse.</p>
      </section>

      {status?.runs?.length > 0 && (
        <details className="mt-6 text-xs text-gray-500">
          <summary className="cursor-pointer hover:text-gray-300">Journal d'exécution ({status.runs.length} derniers passages)</summary>
          {status.runs.map(r => (
            <details key={r.id} className="mt-2 ml-3">
              <summary className="cursor-pointer">
                {new Date(r.started_at).toLocaleString('fr-FR')} — <b className={r.status === 'ok' ? 'text-emerald-400' : 'text-amber-400'}>{r.status}</b>
                {' '}· séance {r.run_date} · {r.n_shown ?? '–'} publiés{r.warning ? ` · ${r.warning}` : ''}
              </summary>
              <pre className="mt-1 whitespace-pre-wrap text-[11px] text-gray-500">{r.log}</pre>
            </details>
          ))}
        </details>
      )}
    </div>
  )
}
