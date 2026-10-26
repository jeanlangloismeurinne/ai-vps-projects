import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import BubbleChart, { fmtAge, fmtCap, fmtMult } from '../components/nasdaq/BubbleChart'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'
const CAP_OPTIONS = [
  { v: 0, l: 'Toutes' }, { v: 1e8, l: '≥ 100 M$' }, { v: 3e8, l: '≥ 300 M$' },
  { v: 1e9, l: '≥ 1 Md$' }, { v: 5e9, l: '≥ 5 Md$' }, { v: 1e10, l: '≥ 10 Md$' }, { v: 5.8e10, l: '≥ 50 Md€ (≈ 58 Md$)' },
]
const ATL_AGE = 1e6 // tri : un plus bas historique passe avant toute ancienneté chiffrée
const ageKey = (r) => (r.is_atl ? ATL_AGE : r.age_months ?? -1)

const COLS = [
  { k: 'ticker', l: 'Ticker', get: r => r.ticker },
  { k: 'name', l: 'Nom', get: r => r.name.replace(/ - .*$/, '') },
  { k: 'price', l: 'Cours ($)', get: r => r.price, num: true },
  { k: 'age', l: 'Ancienneté (mois)', get: ageKey, num: true },
  { k: 'mult', l: 'Multiple 10 ans', get: r => r.multiple_10y ?? -1, num: true },
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
  const [minCap, setMinCap] = useState(5.8e10)
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
    if (!status?.running) return
    const t = setInterval(() => { loadStatus() }, 4000)
    return () => clearInterval(t)
  }, [status?.running, loadStatus])
  useEffect(() => { if (status && !status.running) load() }, [status?.running]) // eslint-disable-line

  const lancer = async () => {
    const r = await fetch(`${API}/nasdaq/run`, { method: 'POST' })
    if (r.ok || r.status === 409) loadStatus()
  }

  const rows = snap?.rows ?? []
  const filtered = useMemo(() => {
    const q = query.trim().toUpperCase()
    return rows.filter(r => (minCap === 0 || (r.market_cap ?? 0) >= minCap)
      && (!q || r.ticker.includes(q) || r.name.toUpperCase().includes(q)))
  }, [rows, minCap, query])
  const shown = useMemo(() => (onlyAlerts ? filtered.filter(r => r.alert) : filtered), [filtered, onlyAlerts])

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
    const head = ['ticker', 'nom', 'cours', 'anciennete_mois', 'plus_bas_historique', 'multiple_10_ans', 'moins_de_10_ans', 'capitalisation', 'alerte', 'nouvelle_alerte']
    const lines = [head.join(';')].concat(sorted.map(r => [
      r.ticker, r.name, r.price, r.is_atl ? '' : r.age_months, r.is_atl ? 'oui' : '', r.multiple_10y?.toFixed(3) ?? '',
      r.lt_10y ? 'oui' : '', r.market_cap ?? '', r.alert ? 'oui' : '', r.alert_new ? 'oui' : ''].map(csvCell).join(';')))
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
          {dateFr ? `Clôture du ${dateFr} · ${rows.length} entreprises` : 'Aucune donnée publiée'}
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
        <label className="text-xs text-gray-400">Capitalisation minimale
          <select value={minCap} onChange={e => { setMinCap(Number(e.target.value)); setLimit(100) }}
            className="mt-1 block rounded bg-gray-800 border border-gray-700 px-2 py-1.5 text-sm text-white">
            {CAP_OPTIONS.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
          </select>
        </label>
        <label className="text-xs text-gray-400">Recherche (ticker ou nom)
          <input value={query} onChange={e => { setQuery(e.target.value); setLimit(100) }} placeholder="ex. NVDA"
            className="mt-1 block rounded bg-gray-800 border border-gray-700 px-2 py-1.5 text-sm text-white w-44" />
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-300 pb-1.5">
          <input type="checkbox" checked={onlyAlerts} onChange={e => setOnlyAlerts(e.target.checked)} />
          Alertes uniquement
        </label>
        <span className="ml-auto text-xs text-gray-500 pb-2">{shown.length} titres affichés sur {rows.length}</span>
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

      <section className="mb-6 rounded-xl border border-gray-800 bg-gray-900/50 p-4">
        <div className="flex flex-wrap items-center gap-4 mb-2 text-xs text-gray-400">
          <span className="text-sm font-semibold text-white">Ancienneté du cours × multiple 10 ans</span>
          <span><i className="inline-block w-3 h-3 rounded-full align-[-2px] mr-1" style={{ background: 'rgba(239,68,68,.5)' }} />alerte (≥ 12 mois ou ATL)</span>
          <span><i className="inline-block w-3 h-3 rounded-full align-[-2px] mr-1" style={{ background: 'rgba(156,163,175,.4)' }} />autres</span>
          <span>Surface ∝ capitalisation · molette = zoom · glisser = déplacer · pointillé = 1×</span>
        </div>
        {shown.length ? <BubbleChart rows={shown} /> : <p className="text-sm text-gray-500 py-12 text-center">Rien à afficher.</p>}
      </section>

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
                <tr key={r.ticker} className="border-b border-gray-900 text-gray-200">
                  <td className="py-1.5 pr-4 font-semibold text-white">{r.ticker}</td>
                  <td className="py-1.5 pr-4 text-gray-400 max-w-[280px] truncate">{r.name.replace(/ - .*$/, '')}</td>
                  <td className="py-1.5 pr-4 text-right tabular-nums">{r.price.toFixed(2)}</td>
                  <td className="py-1.5 pr-4 text-right tabular-nums">
                    {r.is_atl ? <span className="rounded bg-red-900/60 text-red-200 px-1.5 text-xs">ATL</span> : r.age_months}
                    {r.short_history && <span title="Historique de moins d'un an" className="ml-1 text-amber-400">•</span>}
                  </td>
                  <td className="py-1.5 pr-4 text-right tabular-nums">{fmtMult(r)}</td>
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
