import React, { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const CURRENCY_SYMBOLS = { EUR: '€', USD: '$', GBP: '£', JPY: '¥', HKD: 'HK$', CHF: 'CHF ' }
const fmtCurrency = (amount, currency) => {
  if (amount == null) return '—'
  const sym = CURRENCY_SYMBOLS[currency] || (currency ? `${currency} ` : '€')
  return `${sym}${Number(amount).toFixed(2)}`
}

const THESIS_STATUS_STYLES = {
  active: { cls: 'bg-emerald-900/50 text-emerald-300 border border-emerald-700', label: 'Active' },
  under_review: { cls: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700', label: 'Révision' },
  REVIEW_REQUIRED: { cls: 'bg-orange-900/50 text-orange-300 border border-orange-700', label: 'Révision requise' },
  CRITICAL: { cls: 'bg-red-900/50 text-red-300 border border-red-700', label: 'CRITIQUE' },
}

function ThesisStatusBadge({ status }) {
  const s = THESIS_STATUS_STYLES[status] || { cls: 'bg-gray-800 text-gray-400', label: status || '—' }
  return <span className={`text-xs px-2 py-0.5 rounded font-medium ${s.cls}`}>{s.label}</span>
}

function PnlCell({ pct }) {
  if (pct == null) return <span className="text-gray-600">—</span>
  return (
    <span className={`font-medium ${pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
      {pct > 0 ? '+' : ''}{pct.toFixed(2)}%
    </span>
  )
}

function EditPositionModal({ position, onClose, onSaved }) {
  const [priceEur, setPriceEur] = useState('')
  const [shares, setShares] = useState(String(Number(position.shares || 0)))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    const p = parseFloat(priceEur)
    const s = parseFloat(shares)
    if (isNaN(p) || p <= 0) { setError('Prix invalide'); return }
    if (isNaN(s) || s <= 0) { setError('Quantité invalide'); return }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/portfolio-v2/positions/${position.id}/edit`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ purchase_price_eur: p, shares: s }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Erreur ${res.status}`)
      }
      onSaved()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={() => !loading && onClose()} />
      <div className="relative bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-sm">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <h3 className="font-semibold text-white">Modifier — {position.ticker_id}</h3>
          <button onClick={() => !loading && onClose()} className="text-gray-400 hover:text-white text-xl">×</button>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">PRU en € — frais inclus, par action</label>
            <input
              type="number" step="0.01" min="0"
              value={priceEur}
              onChange={e => setPriceEur(e.target.value)}
              autoFocus
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Quantité (actions)</label>
            <input
              type="number" step="0.0001" min="0"
              value={shares}
              onChange={e => setShares(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          {error && <p className="text-red-400 text-sm bg-red-900/30 border border-red-800 rounded px-3 py-2">{error}</p>}
        </div>
        <div className="px-5 py-4 border-t border-gray-700 flex gap-3">
          <button onClick={submit} disabled={loading}
            className="flex-1 py-2 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm rounded font-medium">
            {loading ? 'Sauvegarde…' : 'Enregistrer'}
          </button>
          <button onClick={() => !loading && onClose()} className="px-4 text-gray-400 hover:text-gray-200 text-sm">Annuler</button>
        </div>
      </div>
    </div>
  )
}

function CashModal({ type, onClose, onConfirm }) {
  const [amount, setAmount] = useState('')
  const [label, setLabel] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!amount || isNaN(parseFloat(amount))) { setError('Montant invalide'); return }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/portfolio-v2/cash`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: parseFloat(amount),
          type,
          label: label.trim() || (type === 'deposit' ? 'Dépôt' : 'Retrait'),
        }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Erreur ${res.status}`)
      }
      onConfirm()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={() => !loading && onClose()} />
      <div className="relative bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-sm">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <h3 className="font-semibold text-white">{type === 'deposit' ? 'Déposer' : 'Retirer'} des fonds</h3>
          <button onClick={() => !loading && onClose()} className="text-gray-400 hover:text-white text-xl">×</button>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Montant (€)</label>
            <input
              type="number" min="0" step="0.01"
              value={amount}
              onChange={e => setAmount(e.target.value)}
              autoFocus
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Label</label>
            <input
              value={label}
              onChange={e => setLabel(e.target.value)}
              placeholder={type === 'deposit' ? 'Dépôt mensuel…' : 'Retrait…'}
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          {error && <p className="text-red-400 text-sm bg-red-900/30 border border-red-800 rounded px-3 py-2">{error}</p>}
        </div>
        <div className="px-5 py-4 border-t border-gray-700 flex gap-3">
          <button onClick={submit} disabled={loading}
            className={`flex-1 py-2 text-white text-sm rounded font-medium disabled:opacity-50 transition-colors ${
              type === 'deposit' ? 'bg-emerald-700 hover:bg-emerald-600' : 'bg-red-700 hover:bg-red-600'
            }`}>
            {loading ? 'En cours…' : type === 'deposit' ? 'Déposer' : 'Retirer'}
          </button>
          <button onClick={() => !loading && onClose()} className="px-4 text-gray-400 hover:text-gray-200 text-sm">Annuler</button>
        </div>
      </div>
    </div>
  )
}

function AddTickerModal({ onClose, onCreated }) {
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null) // { symbol, name, exchange }
  const [searching, setSearching] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const debounceRef = useRef(null)

  const onQueryChange = (val) => {
    setQuery(val)
    setSelected(null)
    setResults([])
    clearTimeout(debounceRef.current)
    if (val.trim().length < 2) return
    debounceRef.current = setTimeout(async () => {
      setSearching(true)
      try {
        const res = await fetch(`${API}/tickers/search?q=${encodeURIComponent(val.trim())}`)
        if (res.ok) setResults(await res.json())
      } catch {}
      setSearching(false)
    }, 400)
  }

  const submit = async (symbol, name, exchange) => {
    if (!symbol) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/tickers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: symbol, name: name || symbol, exchange: exchange || '' }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Erreur ${res.status}`)
      }
      const data = await res.json()
      router.push(`/ticker/${data.id || data.ticker_id || symbol}`)
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={() => !loading && onClose()} />
      <div className="relative bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-sm">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <h3 className="font-semibold text-white">Ajouter un titre</h3>
          <button onClick={() => !loading && onClose()} className="text-gray-400 hover:text-white text-xl">×</button>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div className="relative">
            <label className="text-xs text-gray-400 block mb-1">Nom ou ticker</label>
            <input
              value={query}
              onChange={e => onQueryChange(e.target.value)}
              placeholder="ex. Apple, MSFT, Capgemini…"
              autoFocus
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
            />
            {searching && <span className="absolute right-3 top-8 text-gray-500 text-xs">…</span>}
          </div>

          {selected ? (
            <div className="bg-indigo-900/30 border border-indigo-700 rounded-lg px-4 py-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-indigo-300 font-mono font-bold text-sm">{selected.symbol}</span>
                  <span className="text-gray-400 text-xs ml-2">{selected.exchange}</span>
                  <p className="text-gray-300 text-xs mt-0.5">{selected.name}</p>
                </div>
                <button onClick={() => { setSelected(null); setResults([]) }} className="text-gray-500 hover:text-gray-300 text-sm ml-3">×</button>
              </div>
            </div>
          ) : results.length > 0 ? (
            <div className="border border-gray-700 rounded-lg overflow-hidden divide-y divide-gray-700 max-h-52 overflow-y-auto">
              {results.map(r => (
                <button key={r.symbol} onClick={() => { setSelected(r); setQuery(r.symbol); setResults([]) }}
                  className="w-full text-left px-4 py-2.5 hover:bg-gray-700 transition-colors flex items-center justify-between">
                  <div>
                    <span className="text-indigo-400 font-mono font-bold text-sm">{r.symbol}</span>
                    <span className="text-gray-400 text-xs ml-2">{r.exchange}</span>
                    <p className="text-gray-300 text-xs mt-0.5 truncate max-w-xs">{r.name}</p>
                  </div>
                  {r.sector && <span className="text-gray-600 text-xs ml-2 flex-shrink-0">{r.sector}</span>}
                </button>
              ))}
            </div>
          ) : null}

          {error && <p className="text-red-400 text-sm bg-red-900/30 border border-red-800 rounded px-3 py-2">{error}</p>}
        </div>
        <div className="px-5 py-4 border-t border-gray-700 flex gap-3">
          <button
            onClick={() => submit(selected?.symbol || query.trim().toUpperCase(), selected?.name, selected?.exchange)}
            disabled={loading || (!selected && !query.trim())}
            className="flex-1 py-2 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors"
          >
            {loading ? 'Création…' : selected ? `Ajouter ${selected.symbol}` : 'Créer le ticker'}
          </button>
          <button onClick={() => !loading && onClose()} className="px-4 text-gray-400 hover:text-gray-200 text-sm">Annuler</button>
        </div>
      </div>
    </div>
  )
}

function AllocateModal({ thesis, onClose, onConfirm }) {
  const today = new Date().toISOString().split('T')[0]
  const [form, setForm] = useState({ shares: '', purchase_price: '', purchase_date: today })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!form.shares || isNaN(parseFloat(form.shares)) || parseFloat(form.shares) <= 0) { setError('Nombre d\'actions invalide'); return }
    if (!form.purchase_price || isNaN(parseFloat(form.purchase_price)) || parseFloat(form.purchase_price) <= 0) { setError('Prix d\'achat invalide'); return }
    if (!form.purchase_date) { setError('Date requise'); return }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/theses/${thesis.id}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          shares: parseFloat(form.shares),
          purchase_price: parseFloat(form.purchase_price),
          purchase_date: form.purchase_date,
          calendar_events: [],
        }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Erreur ${res.status}`)
      }
      onConfirm()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={() => !loading && onClose()} />
      <div className="relative bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-sm">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <div>
            <h3 className="font-semibold text-white">Allouer le capital</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              <span className="font-mono text-indigo-400">{thesis.ticker_id}</span>
              {thesis.ticker_name ? ` · ${thesis.ticker_name}` : ''}
            </p>
          </div>
          <button onClick={() => !loading && onClose()} className="text-gray-400 hover:text-white text-xl">×</button>
        </div>
        {thesis.one_liner && (
          <div className="px-5 pt-4">
            <p className="text-xs text-gray-500 italic">&ldquo;{thesis.one_liner}&rdquo;</p>
          </div>
        )}
        <div className="px-5 py-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Nombre d&apos;actions</label>
              <input
                type="number" min="0" step="1"
                value={form.shares}
                onChange={e => setForm(f => ({ ...f, shares: e.target.value }))}
                autoFocus
                className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">PRU en € — frais inclus</label>
              <input
                type="number" min="0" step="0.01"
                value={form.purchase_price}
                onChange={e => setForm(f => ({ ...f, purchase_price: e.target.value }))}
                className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Date d&apos;achat</label>
            <input
              type="date"
              value={form.purchase_date}
              onChange={e => setForm(f => ({ ...f, purchase_date: e.target.value }))}
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          {form.shares && form.purchase_price && (
            <p className="text-xs text-gray-500">
              Total : <span className="text-gray-300 font-medium">
                €{(parseFloat(form.shares || 0) * parseFloat(form.purchase_price || 0)).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </p>
          )}
          {error && <p className="text-red-400 text-sm bg-red-900/30 border border-red-800 rounded px-3 py-2">{error}</p>}
        </div>
        <div className="px-5 py-4 border-t border-gray-700 flex gap-3">
          <button onClick={submit} disabled={loading}
            className="flex-1 py-2 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors">
            {loading ? 'Validation…' : 'Valider et créer la position'}
          </button>
          <button onClick={() => !loading && onClose()} className="px-4 text-gray-400 hover:text-gray-200 text-sm">Annuler</button>
        </div>
      </div>
    </div>
  )
}

const STAGE_LABELS = {
  'pre-seed': 'Pre-Seed',
  'seed': 'Seed',
  'series-a': 'Série A',
  'series-b': 'Série B',
  'series-c': 'Série C',
  'growth': 'Growth',
  'pre-ipo': 'Pré-IPO',
  'mature': 'Mature',
}

function IrrCell({ pct }) {
  if (pct == null) return <span className="text-gray-600">—</span>
  return (
    <span className={`font-medium ${pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
      {pct > 0 ? '+' : ''}{pct.toFixed(1)}%
    </span>
  )
}

export default function PortfolioV1() {
  const [summary, setSummary] = useState(null)
  const [positions, setPositions] = useState([])
  const [pendingTheses, setPendingTheses] = useState([])
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [cashModal, setCashModal] = useState(null) // 'deposit' | 'withdraw'
  const [addTicker, setAddTicker] = useState(false)
  const [allocateThesis, setAllocateThesis] = useState(null)
  const [editPosition, setEditPosition] = useState(null)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [sumRes, posRes, pendRes] = await Promise.all([
        fetch(`${API}/portfolio-v2/summary`),
        fetch(`${API}/portfolio-v2/positions`),
        fetch(`${API}/portfolio-v2/pending-allocation`),
      ])
      if (sumRes.ok) setSummary(await sumRes.json())
      if (posRes.ok) setPositions(await posRes.json())
      if (pendRes.ok) setPendingTheses(await pendRes.json())
    } catch (e) {
      setError('Erreur de chargement')
    } finally {
      setLoading(false)
    }
  }

  const loadHistory = async () => {
    if (history.length > 0) { setHistoryOpen(o => !o); return }
    setHistoryLoading(true)
    try {
      const res = await fetch(`${API}/portfolio-v2/cash/history`)
      if (res.ok) setHistory(await res.json())
    } catch {}
    setHistoryLoading(false)
    setHistoryOpen(true)
  }

  useEffect(() => { load() }, [])

  const fmt = v => v != null ? `€${Number(v).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'

  const listedPositions = positions.filter(p => p.company_type !== 'private')
  const privatePositions = positions.filter(p => p.company_type === 'private')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Portefeuille</h1>
        <button onClick={() => setAddTicker(true)}
          className="px-4 py-2 bg-indigo-700 hover:bg-indigo-600 text-white text-sm rounded-lg font-medium transition-colors">
          + Ajouter un titre
        </button>
      </div>

      {error && <div className="bg-red-900/30 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">{error}</div>}

      {/* Cash Module */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Module Cash</p>
          <div className="flex gap-2 shrink-0">
            <button onClick={() => setCashModal('deposit')}
              className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 text-white text-sm rounded-lg font-medium transition-colors">
              Déposer
            </button>
            <button onClick={() => setCashModal('withdraw')}
              className="px-3 py-1.5 bg-red-700/80 hover:bg-red-700 text-white text-sm rounded-lg font-medium transition-colors">
              Retirer
            </button>
          </div>
        </div>
        <div className="flex items-end gap-4 flex-wrap mb-4">
          <div>
            <p className="text-xs text-gray-500">Liquidités</p>
            <p className="text-2xl font-bold text-white">{loading ? '…' : fmt(summary?.cash_balance)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Positions</p>
            <p className="text-xl font-semibold text-gray-300">{loading ? '…' : fmt(summary?.positions_value)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Total</p>
            <p className="text-xl font-semibold text-indigo-300">{loading ? '…' : fmt(summary?.total)}</p>
          </div>
        </div>

        {/* Historique accordéon */}
        <button onClick={loadHistory}
          className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-300 transition-colors">
          <span className={`transition-transform ${historyOpen ? 'rotate-90' : ''}`}>▶</span>
          Historique des mouvements
          {historyLoading && <span className="text-gray-600">…</span>}
        </button>
        {historyOpen && (
          <div className="mt-3 space-y-1.5 max-h-48 overflow-y-auto">
            {history.length === 0 ? (
              <p className="text-gray-600 text-xs">Aucun mouvement</p>
            ) : history.slice(0, 10).map((h, i) => (
              <div key={i} className="flex items-center justify-between text-sm bg-gray-800 rounded px-3 py-2">
                <span className="text-gray-400 text-xs">{h.label || h.type}</span>
                <span className={`font-medium ${h.amount >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {h.amount >= 0 ? '+' : ''}{fmt(h.amount)}
                </span>
                <span className="text-xs text-gray-600">
                  {h.created_at ? new Date(h.created_at).toLocaleDateString('fr-FR') : ''}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Positions Table — Listed */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Positions</h2>
        {loading ? (
          <div className="text-center py-12 text-gray-500">Chargement…</div>
        ) : listedPositions.length === 0 && privatePositions.length === 0 ? (
          <div className="text-center py-16 bg-gray-900 border border-gray-800 rounded-xl">
            <p className="text-gray-500 text-lg">Aucune position active</p>
            <button onClick={() => setAddTicker(true)}
              className="mt-4 px-4 py-2 bg-indigo-700 hover:bg-indigo-600 text-white text-sm rounded-lg">
              + Ajouter un premier titre
            </button>
          </div>
        ) : listedPositions.length > 0 ? (
          <div className="overflow-x-auto rounded-xl border border-gray-800">
            <table className="w-full text-sm">
              <thead className="bg-gray-900">
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Ticker / Nom</th>
                  <th className="px-4 py-3 text-right">Qté</th>
                  <th className="px-4 py-3 text-right">PRU €</th>
                  <th className="px-4 py-3 text-right">P. Actuel</th>
                  <th className="px-4 py-3 text-right">Valeur</th>
                  <th className="px-4 py-3 text-right">Perf. %</th>
                  <th className="px-4 py-3 text-right">Perf. ann.</th>
                  <th className="px-4 py-3">Statut thèse</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {listedPositions.map(p => (
                  <React.Fragment key={p.ticker_id || p.id}>
                    <tr onClick={() => { if (typeof window !== 'undefined') window.location.href = `/ticker/${p.ticker_id || p.id}` }}
                      className="hover:bg-gray-800/50 cursor-pointer transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className="font-mono font-bold text-indigo-400">{p.ticker_id}</span>
                          <span className="text-xs text-gray-500">{p.ticker_name || ''}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-300">{p.shares ?? '—'}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex flex-col items-end">
                          <span className="text-gray-300">{fmtCurrency(p.purchase_price_eur ?? p.purchase_price, 'EUR')}</span>
                          {p.purchase_price_native_today != null && p.currency && p.currency !== 'EUR' && (
                            <span className="text-xs text-gray-500">= {fmtCurrency(p.purchase_price_native_today, p.currency)} J</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-300">
                        {fmtCurrency(p.current_price, p.currency)}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-300">
                        {p.market_value != null ? fmt(p.market_value) : '—'}
                      </td>
                      <td className="px-4 py-3 text-right"><PnlCell pct={p.perf_pct} /></td>
                      <td className="px-4 py-3 text-right"><PnlCell pct={p.perf_annualized} /></td>
                      <td className="px-4 py-3">
                        <ThesisStatusBadge status={p.thesis_status} />
                      </td>
                      <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                        <button
                          onClick={() => setEditPosition(p)}
                          className="text-xs text-gray-500 hover:text-gray-300 px-2 py-1 rounded hover:bg-gray-700 transition-colors"
                          title="Modifier prix / quantité"
                        >
                          ✎
                        </button>
                      </td>
                    </tr>
                    {p.thesis_status === 'under_review' && (
                      <tr className="bg-orange-950/20">
                        <td colSpan={9} className="px-4 py-2">
                          <div className="flex items-center gap-3 text-sm">
                            <span className="text-orange-300 font-medium">Décision requise</span>
                            {p.thesis_id && (
                              <Link href={`/ticker/${p.ticker_id}/decision/${p.thesis_id}`}
                                className="text-orange-400 hover:text-orange-300 underline text-xs">
                                Accéder à la page de décision →
                              </Link>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      {/* Private / Non côté positions */}
      {!loading && privatePositions.length > 0 && (
        <div className="mt-8">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-violet-400 inline-block"></span>
            Private / Non côté ({privatePositions.length})
          </h2>
          <div className="overflow-x-auto rounded-xl border border-violet-900/30">
            <table className="w-full text-sm">
              <thead className="bg-gray-900">
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Société</th>
                  <th className="px-4 py-3">Stade</th>
                  <th className="px-4 py-3 text-right">Parts</th>
                  <th className="px-4 py-3 text-right">Prix entrée</th>
                  <th className="px-4 py-3 text-right">Investi</th>
                  <th className="px-4 py-3 text-right">Derni. Valo</th>
                  <th className="px-4 py-3 text-right">IRR actuel</th>
                  <th className="px-4 py-3 text-right">IRR projeté</th>
                  <th className="px-4 py-3 text-right">Particip.</th>
                  <th className="px-4 py-3">Prochain événement</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {privatePositions.map(p => {
                  const invested = p.shares && p.purchase_price
                    ? p.shares * p.purchase_price
                    : null
                  const stageLbl = STAGE_LABELS[p.stage] || p.stage || '—'
                  return (
                    <tr key={p.ticker_id || p.id}
                      onClick={() => { if (typeof window !== 'undefined') window.location.href = `/ticker/${p.ticker_id || p.id}` }}
                      className="hover:bg-gray-800/50 cursor-pointer transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className="font-bold text-violet-400">{p.ticker_name || p.ticker_id}</span>
                          <span className="text-xs text-gray-500">{p.ticker_id}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {p.stage ? (
                          <span className="text-xs bg-violet-900/50 border border-violet-700 text-violet-300 px-2 py-0.5 rounded-full">
                            {stageLbl}
                          </span>
                        ) : <span className="text-gray-600">—</span>}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-300">{p.shares ?? '—'}</td>
                      <td className="px-4 py-3 text-right text-gray-300">
                        {fmtCurrency(p.purchase_price, p.purchase_currency || p.currency || 'EUR')}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-300">
                        {invested != null ? fmt(invested) : '—'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex flex-col items-end">
                          <span className="text-gray-300">
                            {p.last_valuation_m != null ? `${p.last_valuation_m}M€` : '—'}
                          </span>
                          {p.last_valuation_date && (
                            <span className="text-xs text-gray-600">
                              {new Date(p.last_valuation_date).toLocaleDateString('fr-FR', { month: 'short', year: 'numeric' })}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <IrrCell pct={p.irr_current_pct} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex flex-col items-end">
                          <IrrCell pct={p.irr_projected_pct} />
                          {p.next_event_date && (
                            <span className="text-xs text-gray-600">
                              {new Date(p.next_event_date).toLocaleDateString('fr-FR', { month: 'short', year: 'numeric' })}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-300">
                        {p.current_ownership_pct != null
                          ? `${Number(p.current_ownership_pct).toFixed(2)}%`
                          : '—'}
                      </td>
                      <td className="px-4 py-3">
                        {p.next_event_type ? (
                          <div className="flex flex-col">
                            <span className="text-xs text-gray-400">{p.next_event_type}</span>
                            {p.next_event_date && (
                              <span className="text-xs text-gray-600">
                                {new Date(p.next_event_date).toLocaleDateString('fr-FR')}
                              </span>
                            )}
                          </div>
                        ) : <span className="text-gray-600">—</span>}
                      </td>
                      <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => setEditPosition(p)}
                            className="text-xs text-gray-500 hover:text-gray-300 px-2 py-1 rounded hover:bg-gray-700 transition-colors"
                            title="Modifier"
                          >
                            ✎
                          </button>
                          <Link
                            href={`/ticker/${p.ticker_id || p.id}`}
                            className="text-xs text-violet-500 hover:text-violet-300 px-2 py-1 rounded hover:bg-gray-700 transition-colors"
                            onClick={e => e.stopPropagation()}
                          >
                            Fiche
                          </Link>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* En attente d'allocation */}
      {pendingTheses.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            En attente d&apos;allocation de capital
            <span className="text-xs bg-amber-800/50 text-amber-300 border border-amber-700 px-2 py-0.5 rounded-full font-normal">
              {pendingTheses.length}
            </span>
          </h2>
          <div className="overflow-x-auto rounded-xl border border-amber-900/50">
            <table className="w-full text-sm">
              <thead className="bg-gray-900">
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Ticker / Nom</th>
                  <th className="px-4 py-3">Thèse</th>
                  <th className="px-4 py-3">Statut</th>
                  <th className="px-4 py-3">Mis à jour</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {pendingTheses.map(th => (
                  <tr key={th.id}
                    onClick={() => { if (typeof window !== 'undefined') window.location.href = `/ticker/${th.ticker_id}` }}
                    className="bg-amber-950/10 hover:bg-gray-800/50 cursor-pointer transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="font-mono font-bold text-amber-400">{th.ticker_id}</span>
                        <span className="text-xs text-gray-500">{th.ticker_name || ''}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs max-w-xs">
                      <span className="line-clamp-2">{th.one_liner || '—'}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs px-2 py-0.5 rounded border bg-gray-800 text-gray-400 border-gray-600">
                        {th.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">
                      {th.updated_at ? new Date(th.updated_at).toLocaleDateString('fr-FR') : '—'}
                    </td>
                    <td className="px-4 py-3 text-right" onClick={e => e.stopPropagation()}>
                      <button
                        onClick={() => setAllocateThesis(th)}
                        className="px-3 py-1.5 bg-amber-700 hover:bg-amber-600 text-white text-xs rounded-lg font-medium transition-colors"
                      >
                        Allouer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Footer Summary */}
      {!loading && summary && (
        <div className="border-t border-gray-800 pt-4 flex gap-8 text-sm text-gray-500 flex-wrap">
          <span>{listedPositions.length} position{listedPositions.length !== 1 ? 's' : ''} cotée{listedPositions.length !== 1 ? 's' : ''}</span>
          {privatePositions.length > 0 && (
            <span>{privatePositions.length} non coté{privatePositions.length !== 1 ? 'es' : 'e'}</span>
          )}
          <span>Cash : {fmt(summary.cash_balance)}</span>
          <span>Portefeuille total : <span className="text-gray-300 font-medium">{fmt(summary.total_value)}</span></span>
        </div>
      )}

      {cashModal && (
        <CashModal
          type={cashModal}
          onClose={() => setCashModal(null)}
          onConfirm={() => { setCashModal(null); load() }}
        />
      )}
      {addTicker && <AddTickerModal onClose={() => setAddTicker(false)} onCreated={() => setAddTicker(false)} />}
      {editPosition && (
        <EditPositionModal
          position={editPosition}
          onClose={() => setEditPosition(null)}
          onSaved={() => { setEditPosition(null); load() }}
        />
      )}
      {allocateThesis && (
        <AllocateModal
          thesis={allocateThesis}
          onClose={() => setAllocateThesis(null)}
          onConfirm={() => { setAllocateThesis(null); load() }}
        />
      )}
    </div>
  )
}
