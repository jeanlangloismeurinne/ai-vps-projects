import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { fmtAge, fmtCap } from '../../components/nasdaq/BubbleChart'
import ProbaChart, { Legend } from '../../components/nasdaq/ProbaChart'
import { Explain, useProba } from '../../components/nasdaq/ProbaPanel'
import SlidePanes, { useSelectedTicker } from '../../components/nasdaq/SlidePanes'
import TickerSheet from '../../components/nasdaq/TickerSheet'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

function Card({ row, onOpen, onRemove }) {
  const { data, err } = useProba(row.ticker, 5)
  const p = data ? data.p[data.p.length - 1] : null
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-3 hover:border-sky-800 cursor-pointer" onClick={() => onOpen(row.ticker)}>
      <div className="flex items-start gap-2">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-white">{row.ticker} <span className="font-normal text-gray-400 truncate">{row.name.replace(/ - .*$/, '')}</span></div>
          <div className="text-xs text-gray-500">
            {row.price != null ? `${row.price.toFixed(2)} $` : ''} · ancienneté du cours : {row.age_months == null ? '—' : fmtAge(row)} · {fmtCap(row.market_cap)}
          </div>
        </div>
        <button onClick={e => { e.stopPropagation(); onRemove(row.ticker) }} title="Retirer de ma liste"
          className="ml-auto text-amber-300 hover:text-white text-sm">★</button>
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-xl font-bold text-sky-300">{p === null ? '—' : `${Math.round(p * 100)} %`}</span>
        <span className="text-xs text-gray-500">chance d'un nouveau plus haut à 12 mois</span>
      </div>
      {data ? <ProbaChart curve={data} compact h={90} w={400} /> : <p className="text-xs text-gray-600 py-6">{err ? 'Courbe indisponible' : 'Chargement…'}</p>}
    </div>
  )
}

function Search({ onOpen }) {
  const [q, setQ] = useState('')
  const [res, setRes] = useState([])
  useEffect(() => {
    if (!q.trim()) { setRes([]); return }
    const h = setTimeout(() => {
      fetch(`${API}/nasdaq/search?q=${encodeURIComponent(q.trim())}`).then(r => r.json()).then(setRes).catch(() => setRes([]))
    }, 200)
    return () => clearTimeout(h)
  }, [q])
  return (
    <div className="relative flex-1 min-w-[220px] max-w-md">
      <input value={q} onChange={e => setQ(e.target.value)} placeholder="Rechercher une entreprise ou un symbole…"
        className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white placeholder-gray-500" />
      {res.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full rounded border border-gray-700 bg-gray-900 shadow-lg max-h-72 overflow-y-auto">
          {res.map(r => (
            <li key={r.ticker}>
              <button className="w-full text-left px-3 py-2 text-sm text-gray-200 hover:bg-gray-800"
                onClick={() => { setQ(''); setRes([]); onOpen(r.ticker) }}>
                <b className="text-white">{r.ticker}</b> <span className="text-gray-400">{r.name.replace(/ - .*$/, '')}</span>
                <span className="float-right text-xs text-gray-500">{fmtCap(r.market_cap)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function NasdaqHome() {
  const [snap, setSnap] = useState(null)
  const [watch, setWatch] = useState(null)
  const [calib, setCalib] = useState(null)
  const [err, setErr] = useState(null)
  const [selected, openTicker, closeTicker] = useSelectedTicker()

  const loadWatch = useCallback(() => {
    fetch(`${API}/nasdaq/watchlist`).then(r => r.json()).then(j => setWatch(j.tickers)).catch(e => setErr(String(e)))
  }, [])
  useEffect(() => {
    loadWatch()
    fetch(`${API}/nasdaq/snapshot`).then(r => r.json()).then(setSnap).catch(e => setErr(String(e)))
    fetch(`${API}/nasdaq/proba-calib`).then(r => r.json()).then(setCalib).catch(() => {})
  }, [loadWatch])
  // revient de la fiche : la liste a pu changer (étoile)
  useEffect(() => { if (!selected) loadWatch() }, [selected, loadWatch])

  const byTicker = useMemo(() => Object.fromEntries((snap?.rows || []).map(r => [r.ticker, r])), [snap])
  const remove = (t) => {
    setWatch(w => w.filter(x => x !== t))
    fetch(`${API}/nasdaq/watchlist/${encodeURIComponent(t)}`, { method: 'DELETE' }).catch(loadWatch)
  }
  const cards = (watch || []).map(t => byTicker[t]).filter(Boolean)

  const mainView = (
    <div className="pb-8">
      <Link href="/" className="text-sm text-gray-500 hover:text-white">← Choix de l'espace</Link>
      <div className="mt-4 mb-5 flex flex-wrap items-center gap-3">
        <span className="text-3xl">🫧</span>
        <h1 className="text-2xl font-bold text-white">Suivi NASDAQ</h1>
        <Search onOpen={openTicker} />
        <Link href="/nasdaq/explorer" className="ml-auto px-4 py-2 rounded bg-sky-800 hover:bg-sky-700 text-sm text-white">Explorer →</Link>
      </div>
      {err && <div className="mb-4 rounded border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">Erreur de chargement : {err}</div>}
      {watch && watch.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-700 p-8 text-center text-sm text-gray-400">
          Votre liste est vide. Cherchez une entreprise ci-dessus ou lancez l'exploration, ouvrez une fiche et cliquez sur « ☆ Suivre ».
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {cards.map(r => <Card key={r.ticker} row={r} onOpen={openTicker} onRemove={remove} />)}
      </div>
      <p className="mt-2 text-xs text-gray-600">La recherche couvre les {snap?.rows?.length ?? '…'} entreprises publiées (capitalisation ≥ 50 Md$).</p>
      <div className="mt-6 rounded-xl border border-gray-800 bg-gray-900/50 p-4 space-y-2">
        <Legend />
        <Explain calib={calib} />
      </div>
    </div>
  )

  return (
    <SlidePanes selected={selected} main={mainView}
      detail={(t) => (
        <section className="rounded-xl border border-gray-800 bg-gray-900/50 p-4 mb-8">
          <TickerSheet key={t} row={byTicker[t]} ticker={t} hot={6} onClose={closeTicker} />
        </section>
      )} />
  )
}
