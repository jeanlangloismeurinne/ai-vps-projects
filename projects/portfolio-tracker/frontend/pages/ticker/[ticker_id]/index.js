import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import PriceChart from '../../../components/PriceChart'
import PrivateMetricsModal from '../../../components/PrivateMetricsModal'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const STATUS_STYLES = {
  active: 'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  under_review: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700',
  REVIEW_REQUIRED: 'bg-orange-900/50 text-orange-300 border border-orange-700',
  CRITICAL: 'bg-red-900/50 text-red-300 border border-red-700',
}

const HYPOTHESIS_STATUS = {
  confirmed: 'text-emerald-400',
  challenged: 'text-amber-400',
  invalidated: 'text-red-400',
  unverified: 'text-gray-500',
}

const PERIODS = ['1Y', '5Y', 'MAX']

const CURRENCY_SYMBOLS = { EUR: '€', USD: '$', GBP: '£', JPY: '¥', HKD: 'HK$', CHF: 'CHF ' }
const fmtPrice = (amount, currency) => {
  if (amount == null) return '—'
  const sym = CURRENCY_SYMBOLS[currency] || (currency ? `${currency} ` : '')
  return `${sym}${Number(amount).toFixed(2)}`
}

// onNeedMetrics(form) is called when private company + mode 2 is selected
function MonitoringModal({ tickerId, isPrivate, onClose, onNeedMetrics }) {
  const router = useRouter()
  const [form, setForm] = useState({ label: '', mode: 2 })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!form.label.trim()) { setError('Label requis'); return }
    // Private + mode 2 → hand off to PrivateMetricsModal via parent
    if (isPrivate && form.mode === 2) {
      onNeedMetrics(form)
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`${API}/tickers/${tickerId}/monitoring`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Erreur')
      const data = await res.json()
      router.push(`/ticker/${tickerId}/monitoring/${data.id || data.session_id}`)
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
          <h3 className="font-semibold text-white">Monitoring ad hoc</h3>
          <button onClick={() => !loading && onClose()} className="text-gray-400 hover:text-white text-xl">×</button>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Label / Déclencheur</label>
            <input
              value={form.label}
              onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
              placeholder="ex. Publication résultats Q1…"
              autoFocus
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Mode (1-5)</label>
            <select
              value={form.mode}
              onChange={e => setForm(f => ({ ...f, mode: Number(e.target.value) }))}
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
            >
              <option value={1}>Mode 1 — Checklist lecture</option>
              <option value={2}>Mode 2 — Revue trimestrielle{isPrivate ? ' (+ métriques)' : ''}</option>
              <option value={3}>Mode 3 — Analyse approfondie</option>
              <option value={4}>Mode 4 — Analyse complète</option>
              <option value={5}>Mode 5 — Routing</option>
            </select>
          </div>
          {isPrivate && form.mode === 2 && (
            <p className="text-xs text-violet-400 bg-violet-950/30 border border-violet-900/50 rounded px-3 py-2">
              Les métriques opérationnelles seront demandées à l&apos;étape suivante.
            </p>
          )}
          {error && <p className="text-red-400 text-sm bg-red-900/30 border border-red-800 rounded px-3 py-2">{error}</p>}
        </div>
        <div className="px-5 py-4 border-t border-gray-700 flex gap-3">
          <button onClick={handleSubmit} disabled={loading}
            className="flex-1 py-2 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm rounded font-medium">
            {loading ? 'Création…' : isPrivate && form.mode === 2 ? 'Suivant →' : 'Lancer le monitoring'}
          </button>
          <button onClick={() => !loading && onClose()} className="px-4 text-gray-400 hover:text-gray-200 text-sm">Annuler</button>
        </div>
      </div>
    </div>
  )
}

function AssignSymbolSection({ tickerId, onAssigned }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
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

  const assign = async () => {
    if (!selected) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/tickers/${tickerId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker_symbol: selected.symbol, exchange: selected.exchange || '' }),
      })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Erreur')
      onAssigned()
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  return (
    <div className="bg-amber-950/30 border border-amber-700/50 rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-amber-400 font-medium text-sm">Symbole boursier non renseigné</span>
        <span className="text-xs text-amber-600">— Les données de marché ne sont pas disponibles</span>
      </div>
      <div className="flex gap-2 flex-wrap">
        <div className="flex-1 min-w-0 relative">
          <input
            value={query}
            onChange={e => onQueryChange(e.target.value)}
            placeholder="Rechercher le symbole… ex. MC.PA, LVMH"
            className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 placeholder-gray-600 focus:border-amber-500 focus:outline-none"
          />
          {searching && <span className="absolute right-3 top-2.5 text-gray-500 text-xs">…</span>}
          {results.length > 0 && !selected && (
            <div className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-xl overflow-hidden divide-y divide-gray-700 max-h-48 overflow-y-auto">
              {results.map(r => (
                <button key={r.symbol}
                  onClick={() => { setSelected(r); setQuery(r.symbol); setResults([]) }}
                  className="w-full text-left px-3 py-2 hover:bg-gray-700 transition-colors flex items-center justify-between">
                  <div>
                    <span className="text-indigo-400 font-mono font-bold text-sm">{r.symbol}</span>
                    <span className="text-gray-400 text-xs ml-2">{r.exchange}</span>
                    <p className="text-gray-300 text-xs mt-0.5 truncate max-w-xs">{r.name}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          onClick={assign}
          disabled={loading || !selected}
          className="px-4 py-2 bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors shrink-0"
        >
          {loading ? '…' : selected ? `Assigner ${selected.symbol}` : 'Rechercher'}
        </button>
      </div>
      {selected && (
        <div className="flex items-center gap-2 text-sm">
          <span className="inline-flex items-center gap-2 bg-indigo-900/30 border border-indigo-700 rounded px-3 py-1.5">
            <span className="text-indigo-300 font-mono font-bold">{selected.symbol}</span>
            <span className="text-gray-400 text-xs">{selected.name}</span>
            <button onClick={() => { setSelected(null); setQuery('') }} className="text-gray-500 hover:text-gray-300 ml-1">×</button>
          </span>
        </div>
      )}
      {error && <p className="text-red-400 text-sm">{error}</p>}
    </div>
  )
}

export default function TickerPage() {
  const router = useRouter()
  const { ticker_id } = router.query

  const [ticker, setTicker] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [opportunity, setOpportunity] = useState(null)
  const [thesis, setThesis] = useState(null)
  const [monitoring, setMonitoring] = useState([])
  const [calendar, setCalendar] = useState([])
  const [priceHistory, setPriceHistory] = useState([])
  const [period, setPeriod] = useState('1Y')
  const [loading, setLoading] = useState(true)
  const [alerts, setAlerts] = useState([])
  const [showMonitoringModal, setShowMonitoringModal] = useState(false)
  const [pendingMonitoringForm, setPendingMonitoringForm] = useState(null) // { label, mode } awaiting private metrics
  const [showAlertForm, setShowAlertForm] = useState(false)
  const [alertForm, setAlertForm] = useState({ price: '', direction: 'below', label: '' })
  const [alertLoading, setAlertLoading] = useState(false)
  const [alertError, setAlertError] = useState('')
  const [debugOpen, setDebugOpen] = useState(false)

  useEffect(() => {
    if (!ticker_id) return
    setLoading(true)
    Promise.all([
      fetch(`${API}/tickers/${ticker_id}`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/tickers/${ticker_id}/metrics`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/tickers/${ticker_id}/opportunities`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/tickers/${ticker_id}/theses`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/tickers/${ticker_id}/monitoring`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/calendar-v2?ticker_id=${ticker_id}`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/tickers/${ticker_id}/price-history?period=${period}`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/tickers/${ticker_id}/alerts`).then(r => r.ok ? r.json() : []),
    ]).then(([t, m, opp, th, mon, cal, ph, al]) => {
      setTicker(t)
      setMetrics(m)
      const oppData = opp ? (Array.isArray(opp) ? opp[0] : opp) : null
      setOpportunity(oppData)
      const thData = th ? (Array.isArray(th) ? th[0] : th) : null
      setThesis(thData)
      setMonitoring(Array.isArray(mon) ? mon : [])
      setCalendar(Array.isArray(cal) ? cal.slice(0, 3) : [])
      const phArr = ph ? (Array.isArray(ph) ? ph : ph.data || []) : []
      setPriceHistory(phArr)
      setAlerts(Array.isArray(al) ? al : [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [ticker_id])

  useEffect(() => {
    if (!ticker_id) return
    fetch(`${API}/tickers/${ticker_id}/price-history?period=${period}`)
      .then(r => r.ok ? r.json() : null)
      .then(ph => {
        const phArr = ph ? (Array.isArray(ph) ? ph : ph.data || []) : []
        setPriceHistory(phArr)
      })
      .catch(() => {})
  }, [period, ticker_id])

  if (loading) return <div className="text-center py-16 text-gray-500">Chargement…</div>
  if (!ticker) return <div className="text-center py-16 text-red-400">Ticker introuvable</div>

  const currentPrice = metrics?.current_price ?? ticker.current_price
  const priceChange = metrics?.price_change_1d_pct

  const thesisJson = thesis?.thesis_json || {}
  const hypotheses = thesisJson.hypotheses || []

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <Link href="/portfolio" className="hover:text-gray-400">Portefeuille</Link>
        <span>/</span>
        <span className="text-gray-400">{ticker.ticker_symbol}</span>
      </div>

      {/* Assigner symbole boursier — PUB- sans ticker_symbol */}
      {ticker.company_type !== 'private' && !ticker.ticker_symbol && (
        <AssignSymbolSection
          tickerId={ticker_id}
          onAssigned={() => window.location.reload()}
        />
      )}

      {/* Bannière DÉCISION REQUISE */}
      {thesis?.status === 'under_review' && (
        <div className="bg-red-950/50 border border-red-700 rounded-xl px-5 py-4 flex items-center justify-between">
          <span className="text-red-300 font-semibold">DÉCISION REQUISE — thèse sous révision</span>
          <Link href={`/ticker/${ticker_id}/decision/${thesis.id}`}
            className="text-red-400 hover:text-red-300 font-medium text-sm">
            Accéder →
          </Link>
        </div>
      )}

      {/* Section 1 — Carte d'identité */}
      <div className={`bg-gray-900 border rounded-xl p-5 ${ticker.company_type === 'private' ? 'border-violet-900/40' : 'border-gray-800'}`}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-3xl font-bold text-white">{ticker.ticker_symbol || ticker.name}</h1>
              {ticker.company_type === 'private' && (
                <span className="text-xs bg-violet-950/60 border border-violet-800/50 text-violet-400 px-2 py-0.5 rounded font-medium">
                  Non côté
                </span>
              )}
            </div>
            <p className="text-gray-400">{ticker.company_name || ticker.name} {ticker.exchange ? `· ${ticker.exchange}` : ''}</p>
          </div>
          {ticker.company_type !== 'private' ? (
            <div className="text-right">
              <p className="text-2xl font-bold text-white">
                {fmtPrice(currentPrice, ticker.currency || metrics?.currency)}
              </p>
              {priceChange != null && (
                <p className={`text-sm font-medium ${priceChange >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}% J-1
                </p>
              )}
            </div>
          ) : (
            <div className="text-right">
              {ticker.last_valuation_m != null && (
                <>
                  <p className="text-xs text-gray-500">Dernière valorisation</p>
                  <p className="text-2xl font-bold text-violet-300">{ticker.last_valuation_m}M€</p>
                  {ticker.last_valuation_date && (
                    <p className="text-xs text-gray-500">
                      {new Date(ticker.last_valuation_date).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}
                    </p>
                  )}
                </>
              )}
              {ticker.stage && (
                <span className="inline-block mt-1 text-xs bg-violet-900/50 border border-violet-700 text-violet-300 px-2 py-0.5 rounded-full">
                  {ticker.stage}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Private company metrics panel */}
        {ticker.company_type === 'private' && (ticker.arr_m != null || ticker.ebitda_m != null || ticker.sector || ticker.notable_investors?.length > 0) && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
            {ticker.sector && (
              <div className="bg-gray-800 rounded-lg px-3 py-2">
                <p className="text-xs text-gray-500 mb-0.5">Secteur</p>
                <p className="text-white font-medium text-sm">{ticker.sector}</p>
              </div>
            )}
            {ticker.arr_m != null && (
              <div className="bg-gray-800 rounded-lg px-3 py-2">
                <p className="text-xs text-gray-500 mb-0.5">ARR / CA</p>
                <p className="text-white font-semibold">{ticker.arr_m}M€</p>
              </div>
            )}
            {ticker.ebitda_m != null && (
              <div className="bg-gray-800 rounded-lg px-3 py-2">
                <p className="text-xs text-gray-500 mb-0.5">EBITDA</p>
                <p className={`font-semibold ${ticker.ebitda_m >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{ticker.ebitda_m}M€</p>
              </div>
            )}
            {ticker.notable_investors?.length > 0 && (
              <div className="bg-gray-800 rounded-lg px-3 py-2">
                <p className="text-xs text-gray-500 mb-0.5">Investisseurs</p>
                <p className="text-white font-medium text-sm truncate">{ticker.notable_investors.slice(0, 2).join(', ')}</p>
              </div>
            )}
          </div>
        )}

        {/* Price Chart with period selector — listed only */}
        {ticker.company_type !== 'private' && (
          <div className="mb-4">
            <div className="flex gap-2 mb-2">
              {PERIODS.map(p => (
                <button key={p} onClick={() => setPeriod(p)}
                  className={`text-xs px-3 py-1 rounded transition-colors ${
                    period === p ? 'bg-indigo-700 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}>
                  {p}
                </button>
              ))}
            </div>
            <PriceChart data={priceHistory} height={180} color="auto" showAxes showDates />
          </div>
        )}

        {/* Financial Metrics — listed only */}
        {ticker.company_type !== 'private' && metrics && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
            {[
              { label: 'Capitalisation', value: metrics.market_cap ? `€${(metrics.market_cap / 1e9).toFixed(1)}Md` : '—' },
              { label: 'PER NTM', value: metrics.pe_ntm ? `${metrics.pe_ntm.toFixed(1)}x` : '—' },
              { label: 'FCF Yield', value: metrics.fcf_yield ? `${metrics.fcf_yield.toFixed(1)}%` : '—' },
              { label: 'Dette/EBITDA', value: metrics.net_debt_ebitda ? `${metrics.net_debt_ebitda.toFixed(1)}x` : '—' },
            ].map(m => (
              <div key={m.label} className="bg-gray-800 rounded-lg px-3 py-2">
                <p className="text-xs text-gray-500 mb-0.5">{m.label}</p>
                <p className="text-white font-semibold">{m.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex flex-wrap gap-3">
          <Link href={`/ticker/${ticker_id}/opportunity/new`}
            className="px-4 py-2 bg-indigo-700 hover:bg-indigo-600 text-white text-sm rounded-lg font-medium transition-colors">
            Analyse d&apos;opportunité
          </Link>
          {thesis?.id ? (
            <Link href={`/ticker/${ticker_id}/thesis/${thesis.id}`}
              className="px-4 py-2 bg-purple-700 hover:bg-purple-600 text-white text-sm rounded-lg font-medium transition-colors">
              Analyse approfondie
            </Link>
          ) : (
            <button disabled
              title="Aucun brief validé — lancez d'abord une analyse d'opportunité"
              className="px-4 py-2 bg-gray-700 text-gray-500 text-sm rounded-lg font-medium cursor-not-allowed">
              Analyse approfondie
            </button>
          )}
          <button onClick={() => setShowMonitoringModal(true)}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm rounded-lg font-medium transition-colors">
            Monitoring ad hoc
          </button>
        </div>
      </div>

      {/* Section 2 — Étude d'opportunité */}
      {opportunity && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-start justify-between mb-3">
            <h2 className="text-lg font-semibold text-white">Étude d&apos;opportunité</h2>
            <span className={`text-xs px-2 py-0.5 rounded border ${
              opportunity.status === 'draft' ? 'bg-gray-800 text-gray-400 border-gray-600' :
              opportunity.status === 'active' ? 'bg-indigo-900/50 text-indigo-300 border-indigo-700' :
              'bg-gray-800 text-gray-400 border-gray-600'
            }`}>{opportunity.status || 'draft'}</span>
          </div>
          {opportunity.brief_json?.verdict && (
            <div className="mb-3 text-sm text-gray-400">
              Conviction : <span className="text-white font-medium">{opportunity.brief_json.verdict.conviction}/10</span>
              {' · '}
              Reco. : <span className="text-white font-medium">{opportunity.brief_json.verdict.recommendation || '—'}</span>
            </div>
          )}
          <p className="text-sm text-gray-400 line-clamp-2">{opportunity.summary || opportunity.brief_json?.summary || '—'}</p>
          <Link href={`/ticker/${ticker_id}/opportunity/${opportunity.id}`}
            className="mt-3 inline-block text-sm text-indigo-400 hover:text-indigo-300">
            Voir le brief →
          </Link>
        </div>
      )}

      {/* Section 3 — Thèse d'investissement */}
      {thesis && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-start justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Thèse d&apos;investissement</h2>
            <span className={`text-xs px-2 py-0.5 rounded border ${STATUS_STYLES[thesis.status] || 'bg-gray-800 text-gray-400 border-gray-600'}`}>
              {thesis.status || '—'}
            </span>
          </div>

          {thesis.one_liner && (
            <p className="text-gray-300 italic mb-4">&ldquo;{thesis.one_liner}&rdquo;</p>
          )}

          {thesis.conviction_override_note && (
            <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg px-4 py-2 mb-4 text-sm text-yellow-300">
              Maintien par conviction : {thesis.conviction_override_note}
            </div>
          )}

          {thesis.needs_revision && (
            <div className="bg-orange-900/20 border border-orange-700 rounded-lg px-4 py-2 mb-4 text-sm text-orange-300">
              Cette thèse nécessite une révision
            </div>
          )}

          {/* H1-H7 table */}
          {hypotheses.length > 0 && (
            <div className="mb-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">Hypothèses</h3>
              <div className="space-y-1.5">
                {hypotheses.map((h, i) => (
                  <div key={i} className="flex items-start gap-3 text-sm">
                    <span className="text-indigo-400 font-bold w-8 flex-shrink-0">{h.id || `H${i + 1}`}</span>
                    <span className="text-gray-300 flex-1">{h.text || h.statement || '—'}</span>
                    <span className={`text-xs font-medium ${HYPOTHESIS_STATUS[h.status] || 'text-gray-500'}`}>
                      {h.status || '—'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Price thresholds */}
          {thesisJson.price_thresholds && (
            <div className="grid grid-cols-3 gap-3 text-center text-sm mb-4">
              {[
                { k: 'stop_loss', label: 'Stop loss', cls: 'text-red-400' },
                { k: 'fair_value', label: 'Juste valeur', cls: 'text-gray-300' },
                { k: 'target_price', label: 'Objectif', cls: 'text-emerald-400' },
              ].map(({ k, label, cls }) => (
                <div key={k} className="bg-gray-800 rounded-lg px-3 py-2">
                  <p className="text-xs text-gray-500 mb-0.5">{label}</p>
                  <p className={`font-semibold ${cls}`}>{thesisJson.price_thresholds[k] || '—'}</p>
                </div>
              ))}
            </div>
          )}

          <Link href={`/ticker/${ticker_id}/thesis/${thesis.id}`}
            className="text-sm text-indigo-400 hover:text-indigo-300">
            Voir la thèse complète →
          </Link>
        </div>
      )}

      {/* Section 4 — Monitoring */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Monitoring</h2>
        {monitoring.length === 0 ? (
          <p className="text-gray-600 text-sm">Aucune session de monitoring</p>
        ) : (
          <div className="space-y-2">
            {monitoring.map(s => (
              <Link key={s.id} href={`/ticker/${ticker_id}/monitoring/${s.id}`}
                className="flex items-center justify-between bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg px-4 py-3 transition-colors">
                <div>
                  <span className="text-sm text-white">{s.trigger_label || s.label || `Session #${s.id}`}</span>
                  <span className="ml-3 text-xs text-gray-500">Mode {s.mode || '—'}</span>
                </div>
                <span className="text-xs text-gray-600">
                  {s.created_at ? new Date(s.created_at).toLocaleDateString('fr-FR') : ''}
                </span>
              </Link>
            ))}
          </div>
        )}

        {/* Upcoming calendar events */}
        {calendar.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-800">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Prochains événements</p>
            <div className="space-y-1.5">
              {calendar.map((ev, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">{ev.label || ev.event_type}</span>
                  <span className="text-gray-600 text-xs">
                    {ev.event_date ? new Date(ev.event_date).toLocaleDateString('fr-FR') : '—'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Section 5 — Alertes de prix */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Alertes de prix</h2>
          <button onClick={() => { setShowAlertForm(v => !v); setAlertError('') }}
            className="text-xs bg-indigo-700 hover:bg-indigo-600 text-white px-3 py-1.5 rounded-lg font-medium transition-colors">
            {showAlertForm ? 'Annuler' : '+ Nouvelle alerte'}
          </button>
        </div>

        {showAlertForm && (
          <div className="mb-4 bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Prix cible</label>
                <input
                  type="number" step="0.01" min="0"
                  value={alertForm.price}
                  onChange={e => setAlertForm(f => ({ ...f, price: e.target.value }))}
                  placeholder="ex. 380.00"
                  className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Direction</label>
                <select
                  value={alertForm.direction}
                  onChange={e => setAlertForm(f => ({ ...f, direction: e.target.value }))}
                  className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
                >
                  <option value="below">En dessous de</option>
                  <option value="above">Au dessus de</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Label (optionnel)</label>
              <input
                value={alertForm.label}
                onChange={e => setAlertForm(f => ({ ...f, label: e.target.value }))}
                placeholder="ex. Stop loss, Take profit…"
                className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>
            {alertError && <p className="text-red-400 text-sm">{alertError}</p>}
            <button
              disabled={alertLoading || !alertForm.price}
              onClick={async () => {
                if (!alertForm.price || isNaN(parseFloat(alertForm.price))) { setAlertError('Prix invalide'); return }
                setAlertLoading(true); setAlertError('')
                try {
                  const res = await fetch(`${API}/tickers/${ticker_id}/alerts`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      price: parseFloat(alertForm.price),
                      direction: alertForm.direction,
                      label: alertForm.label.trim() || null,
                    }),
                  })
                  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `Erreur ${res.status}`)
                  const newAlert = await res.json()
                  setAlerts(prev => [...prev, newAlert])
                  setAlertForm({ price: '', direction: 'below', label: '' })
                  setShowAlertForm(false)
                } catch (e) { setAlertError(e.message) }
                setAlertLoading(false)
              }}
              className="w-full py-2 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors"
            >
              {alertLoading ? 'Création…' : 'Créer l\'alerte'}
            </button>
          </div>
        )}

        {alerts.length === 0 ? (
          <p className="text-gray-600 text-sm">Aucune alerte active</p>
        ) : (
          <div className="space-y-2">
            {alerts.map(a => (
              <div key={a.id} className="flex items-center justify-between bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-0.5 rounded border font-medium ${
                    a.direction === 'above'
                      ? 'bg-emerald-900/40 text-emerald-300 border-emerald-700'
                      : 'bg-red-900/40 text-red-300 border-red-700'
                  }`}>
                    {a.direction === 'above' ? '↑' : '↓'} {a.direction === 'above' ? 'Au-dessus de' : 'En dessous de'}
                  </span>
                  <span className="text-white font-semibold text-sm">
                    {a.price != null ? `${Number(a.price).toFixed(2)}` : '—'}
                  </span>
                  {a.label && <span className="text-gray-400 text-xs">{a.label}</span>}
                </div>
                <button
                  onClick={async () => {
                    try {
                      await fetch(`${API}/tickers/${ticker_id}/alerts/${a.id}`, { method: 'DELETE' })
                      setAlerts(prev => prev.filter(x => x.id !== a.id))
                    } catch {}
                  }}
                  className="text-gray-600 hover:text-red-400 transition-colors text-sm px-2"
                  title="Supprimer"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section 6 — Debug (accordéon fermé) */}
      <div className="border border-gray-800 rounded-xl">
        <button onClick={() => setDebugOpen(o => !o)}
          className="w-full flex items-center justify-between px-5 py-3 text-sm text-gray-600 hover:text-gray-400 transition-colors">
          <span>Debug — Derniers appels API marché</span>
          <span className={`transition-transform ${debugOpen ? 'rotate-90' : ''}`}>▶</span>
        </button>
        {debugOpen && (
          <div className="px-5 pb-4 border-t border-gray-800">
            <pre className="text-xs text-gray-500 overflow-x-auto mt-3">
              {JSON.stringify({ ticker, metrics, lastRefresh: new Date().toISOString() }, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {showMonitoringModal && (
        <MonitoringModal
          tickerId={ticker_id}
          isPrivate={ticker?.company_type === 'private'}
          onClose={() => setShowMonitoringModal(false)}
          onNeedMetrics={(form) => {
            setShowMonitoringModal(false)
            setPendingMonitoringForm(form)
          }}
        />
      )}

      {pendingMonitoringForm && (
        <PrivateMetricsModal
          company={ticker}
          onClose={() => setPendingMonitoringForm(null)}
          onConfirm={async (metricsData) => {
            setPendingMonitoringForm(null)
            try {
              const body = {
                ...pendingMonitoringForm,
                private_metrics: metricsData.private_metrics,
                private_metrics_text: metricsData.metricsText,
              }
              const res = await fetch(`${API}/tickers/${ticker_id}/monitoring`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
              })
              if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Erreur')
              const data = await res.json()
              window.location.href = `/ticker/${ticker_id}/monitoring/${data.id || data.session_id}`
            } catch (e) {
              // silently fail — user stays on page
              console.error(e)
            }
          }}
        />
      )}
    </div>
  )
}
