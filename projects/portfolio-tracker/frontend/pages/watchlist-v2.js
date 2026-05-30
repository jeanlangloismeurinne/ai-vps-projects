import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import PriceChart from '../components/PriceChart'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

function AlertModal({ ticker, onClose, onSaved }) {
  const [form, setForm] = useState({ price: '', direction: 'below', label: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!form.price) { setError('Prix requis'); return }
    setLoading(true)
    try {
      const res = await fetch(`${API}/tickers/${ticker.id}/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          price: parseFloat(form.price),
          direction: form.direction,
          label: form.label || `${form.direction === 'below' ? 'Sous' : 'Au-dessus de'} ${form.price}`,
        }),
      })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Erreur')
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
          <h3 className="font-semibold text-white">Créer une alerte — {ticker.ticker_symbol}</h3>
          <button onClick={() => !loading && onClose()} className="text-gray-400 hover:text-white text-xl">×</button>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Prix</label>
              <input
                type="number" step="0.01"
                value={form.price}
                onChange={e => setForm(f => ({ ...f, price: e.target.value }))}
                autoFocus
                className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Direction</label>
              <select
                value={form.direction}
                onChange={e => setForm(f => ({ ...f, direction: e.target.value }))}
                className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
              >
                <option value="below">En dessous</option>
                <option value="above">Au-dessus</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Label</label>
            <input
              value={form.label}
              onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
              placeholder="Description de l'alerte…"
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          {error && <p className="text-red-400 text-sm bg-red-900/30 border border-red-800 rounded px-3 py-2">{error}</p>}
        </div>
        <div className="px-5 py-4 border-t border-gray-700 flex gap-3">
          <button onClick={submit} disabled={loading}
            className="flex-1 py-2 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm rounded font-medium">
            {loading ? 'Création…' : 'Créer l\'alerte'}
          </button>
          <button onClick={() => !loading && onClose()} className="px-4 text-gray-400 hover:text-gray-200 text-sm">Annuler</button>
        </div>
      </div>
    </div>
  )
}

function TickerCard({ ticker, opportunityAgentSynced, onAlertCreated }) {
  const [priceHistory, setPriceHistory] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [showAlertModal, setShowAlertModal] = useState(false)

  useEffect(() => {
    fetch(`${API}/tickers/${ticker.id}/price-history?period=1mo`)
      .then(r => r.json())
      .then(data => setPriceHistory(Array.isArray(data) ? data : data.prices || []))
      .catch(() => {})
    fetch(`${API}/tickers/${ticker.id}/metrics`)
      .then(r => r.json())
      .then(setMetrics)
      .catch(() => {})
  }, [ticker.id])

  const currentPrice = metrics?.current_price ?? ticker.current_price
  const priceChange = metrics?.price_change_1d_pct

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <Link href={`/ticker/${ticker.id}`} className="font-mono font-bold text-indigo-400 hover:text-indigo-300 text-lg">
            {ticker.id}
          </Link>
          <p className="text-xs text-gray-500">{ticker.name || ''} {ticker.exchange ? `· ${ticker.exchange}` : ''}</p>
        </div>
        <div className="text-right">
          <p className="text-white font-semibold">
            {currentPrice != null ? `€${Number(currentPrice).toFixed(2)}` : '—'}
          </p>
          {priceChange != null && (
            <p className={`text-xs font-medium ${priceChange >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
            </p>
          )}
        </div>
      </div>

      {/* Sparkline */}
      <div className="h-16 -mx-1">
        <PriceChart data={priceHistory} height={64} color="auto" />
      </div>

      {/* Alerts */}
      {ticker.alerts && ticker.alerts.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {ticker.alerts.map((alert, i) => (
            <button key={i}
              className="text-xs bg-amber-900/50 border border-amber-700 text-amber-300 px-2 py-0.5 rounded hover:bg-amber-900/70 transition-colors"
              title="Cliquer pour éditer">
              {alert.direction === 'below' ? '↓' : '↑'} {alert.price} — {alert.label || alert.direction}
            </button>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        {/* Analyser */}
        <div className="relative flex-1">
          <Link
            href={opportunityAgentSynced === false ? '#' : `/ticker/${ticker.id}/opportunity/new`}
            className={`block text-center text-sm py-1.5 rounded-lg font-medium transition-colors ${
              opportunityAgentSynced === false
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-indigo-700 hover:bg-indigo-600 text-white'
            }`}
            onClick={e => opportunityAgentSynced === false && e.preventDefault()}
          >
            Analyser
          </Link>
          {opportunityAgentSynced === false && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-800/90 rounded-lg z-10">
              <div className="text-center px-2">
                <p className="text-xs text-red-300">⛔ Opportunity Agent hors sync</p>
                <Link href="/admin" className="text-xs text-indigo-400 hover:text-indigo-300">
                  Mettre à jour →
                </Link>
              </div>
            </div>
          )}
        </div>
        <Link href={`/ticker/${ticker.id}`}
          className="flex-1 text-center text-sm py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-200 font-medium transition-colors">
          Fiche
        </Link>
        <button onClick={() => setShowAlertModal(true)}
          className="px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-200 font-medium transition-colors text-sm">
          +
        </button>
      </div>

      {showAlertModal && (
        <AlertModal
          ticker={ticker}
          onClose={() => setShowAlertModal(false)}
          onSaved={() => { setShowAlertModal(false); onAlertCreated() }}
        />
      )}
    </div>
  )
}

export default function WatchlistV2() {
  const router = useRouter()
  const [tickers, setTickers] = useState([])
  const [loading, setLoading] = useState(true)
  const [opportunityAgentSynced, setOpportunityAgentSynced] = useState(null)
  const [addTicker, setAddTicker] = useState('')
  const [addLoading, setAddLoading] = useState(false)
  const [addError, setAddError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [tickRes, agentRes] = await Promise.all([
        fetch(`${API}/tickers?status=watchlist`),
        fetch(`${API}/admin/agents`),
      ])
      if (tickRes.ok) setTickers(await tickRes.json())
      if (agentRes.ok) {
        const agents = await agentRes.json()
        const opp = Array.isArray(agents) ? agents.find(a => a.name === 'opportunity-agent') : null
        if (opp) setOpportunityAgentSynced(opp.synced)
      }
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleAddTicker = async () => {
    if (!addTicker.trim()) return
    setAddLoading(true)
    setAddError('')
    try {
      const res = await fetch(`${API}/tickers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: addTicker.trim().toUpperCase(), name: addTicker.trim().toUpperCase() }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Erreur ${res.status}`)
      }
      const data = await res.json()
      router.push(`/ticker/${data.id || data.ticker_id}`)
    } catch (e) {
      setAddError(e.message)
      setAddLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Watchlist V1</h1>
        <span className="text-xs text-gray-600">{tickers.length} titre{tickers.length > 1 ? 's' : ''}</span>
      </div>

      {/* Add ticker bar */}
      <div className="flex gap-3">
        <input
          value={addTicker}
          onChange={e => setAddTicker(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && handleAddTicker()}
          placeholder="Ajouter un ticker… ex. CAP.PA, MSFT"
          className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-4 py-2.5 placeholder-gray-600 focus:border-indigo-500 focus:outline-none font-mono"
        />
        <button
          onClick={handleAddTicker}
          disabled={addLoading || !addTicker.trim()}
          className="px-4 py-2.5 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors"
        >
          {addLoading ? '…' : 'Ajouter'}
        </button>
      </div>
      {addError && <p className="text-red-400 text-sm bg-red-900/30 border border-red-800 rounded-lg px-3 py-2">{addError}</p>}

      {loading ? (
        <div className="text-center py-16 text-gray-500">Chargement…</div>
      ) : tickers.length === 0 ? (
        <div className="text-center py-20 bg-gray-900 border border-gray-800 rounded-xl">
          <p className="text-gray-500 text-lg mb-2">Watchlist vide</p>
          <p className="text-gray-600 text-sm">Ajoutez un ticker ci-dessus pour commencer</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {tickers.map(t => (
            <TickerCard
              key={t.id}
              ticker={t}
              opportunityAgentSynced={opportunityAgentSynced}
              onAlertCreated={load}
            />
          ))}
        </div>
      )}
    </div>
  )
}
