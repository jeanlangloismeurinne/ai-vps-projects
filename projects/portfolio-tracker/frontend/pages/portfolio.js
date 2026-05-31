import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

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
  const [ticker, setTicker] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!ticker.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/tickers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: ticker.trim().toUpperCase(), name: ticker.trim().toUpperCase() }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Erreur ${res.status}`)
      }
      const data = await res.json()
      router.push(`/ticker/${data.id || data.ticker_id || ticker.trim().toUpperCase()}`)
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
          <div>
            <label className="text-xs text-gray-400 block mb-1">Ticker</label>
            <input
              value={ticker}
              onChange={e => setTicker(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === 'Enter' && submit()}
              placeholder="ex. CAP.PA, MSFT, TSLA"
              autoFocus
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-indigo-500 focus:outline-none font-mono uppercase"
            />
          </div>
          {error && <p className="text-red-400 text-sm bg-red-900/30 border border-red-800 rounded px-3 py-2">{error}</p>}
        </div>
        <div className="px-5 py-4 border-t border-gray-700 flex gap-3">
          <button onClick={submit} disabled={loading || !ticker.trim()}
            className="flex-1 py-2 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors">
            {loading ? 'Création…' : 'Créer le ticker'}
          </button>
          <button onClick={() => !loading && onClose()} className="px-4 text-gray-400 hover:text-gray-200 text-sm">Annuler</button>
        </div>
      </div>
    </div>
  )
}

export default function PortfolioV1() {
  const [summary, setSummary] = useState(null)
  const [positions, setPositions] = useState([])
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [cashModal, setCashModal] = useState(null) // 'deposit' | 'withdraw'
  const [addTicker, setAddTicker] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [sumRes, posRes] = await Promise.all([
        fetch(`${API}/portfolio-v2/summary`),
        fetch(`${API}/portfolio-v2/positions`),
      ])
      if (sumRes.ok) setSummary(await sumRes.json())
      if (posRes.ok) setPositions(await posRes.json())
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
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Module Cash</p>
            <div className="flex items-center gap-6">
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
          </div>
          <div className="flex gap-2">
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

      {/* Positions Table */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Positions</h2>
        {loading ? (
          <div className="text-center py-12 text-gray-500">Chargement…</div>
        ) : positions.length === 0 ? (
          <div className="text-center py-16 bg-gray-900 border border-gray-800 rounded-xl">
            <p className="text-gray-500 text-lg">Aucune position active</p>
            <button onClick={() => setAddTicker(true)}
              className="mt-4 px-4 py-2 bg-indigo-700 hover:bg-indigo-600 text-white text-sm rounded-lg">
              + Ajouter un premier titre
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-gray-800">
            <table className="w-full text-sm">
              <thead className="bg-gray-900">
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Ticker / Nom</th>
                  <th className="px-4 py-3 text-right">Qté</th>
                  <th className="px-4 py-3 text-right">P. Achat</th>
                  <th className="px-4 py-3 text-right">P. Actuel</th>
                  <th className="px-4 py-3 text-right">Valeur</th>
                  <th className="px-4 py-3 text-right">Perf. %</th>
                  <th className="px-4 py-3 text-right">Perf. ann.</th>
                  <th className="px-4 py-3">Statut thèse</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {positions.map(p => (
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
                      <td className="px-4 py-3 text-right text-gray-300">
                        {p.purchase_price != null ? `€${Number(p.purchase_price).toFixed(2)}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-300">
                        {p.current_price != null ? `€${Number(p.current_price).toFixed(2)}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-300">
                        {p.market_value != null ? fmt(p.market_value) : '—'}
                      </td>
                      <td className="px-4 py-3 text-right"><PnlCell pct={p.perf_pct} /></td>
                      <td className="px-4 py-3 text-right"><PnlCell pct={p.perf_annualized} /></td>
                      <td className="px-4 py-3">
                        <ThesisStatusBadge status={p.thesis_status} />
                      </td>
                    </tr>
                    {p.thesis_status === 'under_review' && (
                      <tr className="bg-orange-950/20">
                        <td colSpan={8} className="px-4 py-2">
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
        )}
      </div>

      {/* Footer Summary */}
      {!loading && summary && (
        <div className="border-t border-gray-800 pt-4 flex gap-8 text-sm text-gray-500">
          <span>{positions.length} position{positions.length > 1 ? 's' : ''}</span>
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
    </div>
  )
}
