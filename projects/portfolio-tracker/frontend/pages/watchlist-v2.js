import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import PriceChart from '../components/PriceChart'
import AddPrivateCompanyModal from '../components/AddPrivateCompanyModal'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const CURRENCY_SYMBOLS = { EUR: '€', USD: '$', GBP: '£', JPY: '¥', HKD: 'HK$', CHF: 'CHF ' }
const fmtPrice = (amount, currency) => {
  if (amount == null) return '—'
  const sym = CURRENCY_SYMBOLS[currency] || (currency ? `${currency} ` : '')
  return `${sym}${Number(amount).toFixed(2)}`
}

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

const PERIODS = ['1Y', '5Y', 'MAX']

function TickerCard({ ticker, opportunityAgentSynced, onAlertCreated }) {
  const hasSymbol = !!ticker.ticker_symbol
  const [priceHistory, setPriceHistory] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [showAlertModal, setShowAlertModal] = useState(false)
  const [period, setPeriod] = useState('1Y')

  useEffect(() => {
    if (!hasSymbol) return
    fetch(`${API}/tickers/${ticker.id}/price-history?period=${period}`)
      .then(r => r.json())
      .then(data => setPriceHistory(Array.isArray(data) ? data : data.data || []))
      .catch(() => {})
  }, [ticker.id, hasSymbol, period])

  useEffect(() => {
    if (!hasSymbol) return
    fetch(`${API}/tickers/${ticker.id}/metrics`)
      .then(r => r.json())
      .then(setMetrics)
      .catch(() => {})
  }, [ticker.id, hasSymbol])

  const currentPrice = metrics?.current_price ?? ticker.current_price
  const priceChange = metrics?.price_change_1d_pct

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1 mr-3">
          {hasSymbol ? (
            <>
              <Link href={`/ticker/${ticker.id}`} className="font-mono font-bold text-indigo-400 hover:text-indigo-300 text-lg block">
                {ticker.ticker_symbol}
              </Link>
              {ticker.name && ticker.name !== ticker.ticker_symbol && (
                <p className="text-xs text-gray-500 truncate">
                  {ticker.name}{ticker.exchange ? ` · ${ticker.exchange}` : ''}
                </p>
              )}
              {ticker.exchange && (!ticker.name || ticker.name === ticker.ticker_symbol) && (
                <p className="text-xs text-gray-600">{ticker.exchange}</p>
              )}
            </>
          ) : (
            <>
              <Link href={`/ticker/${ticker.id}`} className="font-bold text-indigo-400 hover:text-indigo-300 text-base leading-tight block truncate">
                {ticker.name || ticker.id}
              </Link>
              <p className="text-xs text-amber-500/80 mt-0.5">Symbole à renseigner</p>
            </>
          )}
        </div>
        {hasSymbol && (
          <div className="text-right flex-shrink-0">
            <p className="text-white font-semibold">
              {fmtPrice(currentPrice, metrics?.currency)}
            </p>
            {priceChange != null && (
              <p className={`text-xs font-medium ${priceChange >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
              </p>
            )}
          </div>
        )}
      </div>

      {/* Chart — uniquement si le symbole boursier est connu */}
      {hasSymbol && (
        <div>
          <div className="flex gap-1.5 mb-1.5">
            {PERIODS.map(p => (
              <button key={p} onClick={() => setPeriod(p)}
                className={`text-xs px-2 py-0.5 rounded transition-colors ${
                  period === p ? 'bg-indigo-700 text-white' : 'bg-gray-800 text-gray-500 hover:bg-gray-700'
                }`}>
                {p}
              </button>
            ))}
          </div>
          <div className="-mx-1">
            <PriceChart data={priceHistory} height={100} color="auto" showAxes showDates />
          </div>
        </div>
      )}

      {/* Placeholder quand pas de symbole */}
      {!hasSymbol && (
        <div className="bg-amber-950/30 border border-amber-800/40 rounded-lg px-3 py-2.5 text-xs text-amber-400/80">
          Le symbole boursier sera renseigné lors de l&apos;analyse d&apos;opportunité.
        </div>
      )}

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
        {hasSymbol && (
          <button onClick={() => setShowAlertModal(true)}
            className="px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-200 font-medium transition-colors text-sm">
            +
          </button>
        )}
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

function PrivateTickerCard({ ticker, opportunityAgentSynced }) {
  const stageLabel = STAGE_LABELS[ticker.stage] || ticker.stage || '—'
  const investors = Array.isArray(ticker.notable_investors) ? ticker.notable_investors : []
  const topInvestors = investors.slice(0, 2)

  return (
    <div className="bg-gray-900 border border-violet-900/40 rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <Link href={`/ticker/${ticker.id}`} className="font-bold text-violet-400 hover:text-violet-300 text-base leading-tight">
            {ticker.name || ticker.id}
          </Link>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs bg-violet-900/50 border border-violet-700 text-violet-300 px-2 py-0.5 rounded-full">
              {stageLabel}
            </span>
            {ticker.sector && (
              <span className="text-xs text-gray-500">{ticker.sector}</span>
            )}
          </div>
        </div>
        <span className="text-xs bg-violet-950/60 border border-violet-800/50 text-violet-400 px-2 py-0.5 rounded font-medium flex-shrink-0">
          Non côté
        </span>
      </div>

      {/* Valorisation */}
      <div className="bg-gray-800/60 rounded-lg px-3 py-2">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-500">Dernière valorisation</p>
            <p className="text-white font-semibold">
              {ticker.last_valuation_m != null ? `${ticker.last_valuation_m}M€` : '—'}
            </p>
          </div>
          <div className="text-right">
            {ticker.last_valuation_date && (
              <p className="text-xs text-gray-500">
                {new Date(ticker.last_valuation_date).toLocaleDateString('fr-FR', { month: 'short', year: 'numeric' })}
              </p>
            )}
            {ticker.valuation_basis && (
              <p className="text-xs text-gray-600 capitalize">{ticker.valuation_basis?.replace(/_/g, ' ')}</p>
            )}
          </div>
        </div>
      </div>

      {/* Investisseurs */}
      {topInvestors.length > 0 && (
        <p className="text-xs text-gray-500">
          {topInvestors.join(' · ')}
          {investors.length > 2 && <span className="text-gray-600"> +{investors.length - 2}</span>}
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <Link
          href={opportunityAgentSynced === false ? '#' : `/ticker/${ticker.id}/opportunity/new`}
          className={`flex-1 text-center text-sm py-1.5 rounded-lg font-medium transition-colors ${
            opportunityAgentSynced === false
              ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
              : 'bg-violet-700 hover:bg-violet-600 text-white'
          }`}
          onClick={e => opportunityAgentSynced === false && e.preventDefault()}
        >
          Analyser
        </Link>
        <Link href={`/ticker/${ticker.id}`}
          className="flex-1 text-center text-sm py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-200 font-medium transition-colors">
          Fiche
        </Link>
      </div>
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
  const [showAddPrivate, setShowAddPrivate] = useState(false)

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
        body: JSON.stringify({ name: addTicker.trim() }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Erreur ${res.status}`)
      }
      const data = await res.json()
      router.push(`/ticker/${data.id}`)
    } catch (e) {
      setAddError(e.message)
      setAddLoading(false)
    }
  }

  const listedTickers = tickers.filter(t => t.company_type !== 'private')
  const privateTickers = tickers.filter(t => t.company_type === 'private')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Watchlist V1</h1>
        <span className="text-xs text-gray-600">{tickers.length} titre{tickers.length > 1 ? 's' : ''}</span>
      </div>

      {/* Add ticker bar */}
      <div className="flex gap-3 flex-wrap">
        <input
          value={addTicker}
          onChange={e => setAddTicker(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAddTicker()}
          placeholder="Nom de la société cotée… ex. LVMH, Hermès, Capgemini"
          className="flex-1 min-w-0 bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-4 py-2.5 placeholder-gray-600 focus:border-indigo-500 focus:outline-none"
        />
        <button
          onClick={handleAddTicker}
          disabled={addLoading || !addTicker.trim()}
          className="px-4 py-2.5 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors"
        >
          {addLoading ? '…' : 'Ajouter'}
        </button>
        <button
          onClick={() => setShowAddPrivate(true)}
          className="px-4 py-2.5 bg-violet-700 hover:bg-violet-600 text-white text-sm rounded-lg font-medium transition-colors"
        >
          + Non coté
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
        <>
          {/* Listed tickers */}
          {listedTickers.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {listedTickers.map(t => (
                <TickerCard
                  key={t.id}
                  ticker={t}
                  opportunityAgentSynced={opportunityAgentSynced}
                  onAlertCreated={load}
                />
              ))}
            </div>
          )}

          {/* Private tickers — Non côté section */}
          {privateTickers.length > 0 && (
            <div className="mt-8">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-violet-400 inline-block"></span>
                Non coté — PE / VC ({privateTickers.length})
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {privateTickers.map(ticker => (
                  <PrivateTickerCard
                    key={ticker.id}
                    ticker={ticker}
                    opportunityAgentSynced={opportunityAgentSynced}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {showAddPrivate && (
        <AddPrivateCompanyModal
          onClose={() => setShowAddPrivate(false)}
          onCreated={() => { setShowAddPrivate(false); load() }}
        />
      )}
    </div>
  )
}
