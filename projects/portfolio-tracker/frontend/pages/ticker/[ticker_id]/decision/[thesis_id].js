import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const DELAY_OPTIONS = [
  { label: '7 jours', days: 7 },
  { label: '14 jours', days: 14 },
]

const REEVALUATION_OPTIONS = [
  { label: '30 jours', days: 30 },
  { label: '60 jours', days: 60 },
  { label: '90 jours', days: 90 },
]

export default function DecisionPage() {
  const router = useRouter()
  const { ticker_id, thesis_id } = router.query

  const [thesis, setThesis] = useState(null)
  const [lastSession, setLastSession] = useState(null)
  const [position, setPosition] = useState(null)
  const [pageLoading, setPageLoading] = useState(true)
  const [error, setError] = useState('')

  // Option states
  const [selectedOption, setSelectedOption] = useState(null) // 'close' | 'reduce' | 'maintain' | 'delay'
  const [reducePercent, setReducePercent] = useState(50)
  const [maintainNote, setMaintainNote] = useState('')
  const [reevaluationDays, setReevaluationDays] = useState(30)
  const [delayDays, setDelayDays] = useState(7)
  const [delayUsed, setDelayUsed] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    if (!thesis_id || !ticker_id) return
    const init = async () => {
      setPageLoading(true)
      try {
        const [thRes, sesRes] = await Promise.all([
          fetch(`${API}/tickers/${ticker_id}/theses/${thesis_id}`),
          fetch(`${API}/tickers/${ticker_id}/monitoring?limit=10`),
        ])
        if (thRes.ok) {
          const th = await thRes.json()
          setThesis(th)
          // Check if delay was used
          setDelayUsed(th.decision_delay_used === true)
        }
        if (sesRes.ok) {
          const sessions = await sesRes.json()
          const mode3 = Array.isArray(sessions) ? sessions.find(s => s.mode === 3 || s.monitoring_mode === 3) : null
          setLastSession(mode3 || null)
        }
        // Load position
        const posRes = await fetch(`${API}/portfolio-v2/positions`)
        if (posRes.ok) {
          const positions = await posRes.json()
          const pos = positions.find(p => p.ticker_id === ticker_id || String(p.ticker_id) === String(ticker_id))
          setPosition(pos || null)
        }
      } catch (e) {
        setError('Erreur de chargement')
      }
      setPageLoading(false)
    }
    init()
  }, [thesis_id, ticker_id])

  const handleClose = async () => {
    if (!confirm('Confirmer la clôture de la position ?')) return
    setActionLoading(true)
    try {
      if (position?.id) {
        await fetch(`${API}/portfolio-v2/positions/${position.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'closed' }),
        })
      }
      router.push(`/ticker/${ticker_id}`)
    } catch (e) {
      setError(e.message)
    }
    setActionLoading(false)
  }

  const handleReduce = async () => {
    if (!position?.id) return
    setActionLoading(true)
    try {
      await fetch(`${API}/portfolio-v2/positions/${position.id}/reduce`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reduction_pct: reducePercent }),
      })
      router.push(`/ticker/${ticker_id}`)
    } catch (e) {
      setError(e.message)
    }
    setActionLoading(false)
  }

  const handleMaintainDebate = async () => {
    if (maintainNote.trim().split(/\s+/).length < 50) {
      setError('La note de conviction doit contenir au moins 50 mots')
      return
    }
    setActionLoading(true)
    try {
      const res = await fetch(`${API}/debates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thesis_id,
          ticker_id,
          conviction_note: maintainNote,
          reevaluation_days: reevaluationDays,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        router.push(`/ticker/${ticker_id}/debate/${data.id}`)
      } else {
        throw new Error((await res.json().catch(() => ({}))).detail || 'Erreur')
      }
    } catch (e) {
      setError(e.message)
    }
    setActionLoading(false)
  }

  const handleDelay = async () => {
    if (delayUsed) return
    setActionLoading(true)
    try {
      const reevalDate = new Date()
      reevalDate.setDate(reevalDate.getDate() + delayDays)
      await fetch(`${API}/tickers/${ticker_id}/theses/${thesis_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision_delay_used: true,
          reevaluation_date: reevalDate.toISOString().slice(0, 10),
        }),
      })
      setDelayUsed(true)
      router.push(`/ticker/${ticker_id}`)
    } catch (e) {
      setError(e.message)
    }
    setActionLoading(false)
  }

  if (pageLoading) return <div className="text-center py-16 text-gray-500">Chargement…</div>

  const hasMode3 = lastSession?.mode === 3 || lastSession?.monitoring_mode === 3
  const currentPrice = position?.current_price
  const resultJson = lastSession?.result_json || {}
  const wordCount = maintainNote.trim().split(/\s+/).filter(Boolean).length

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-4">
      {/* Header — non fermable */}
      <div className="bg-red-950/50 border border-red-700 rounded-xl p-6">
        <h1 className="text-2xl font-bold text-red-300 mb-4">DÉCISION REQUISE</h1>

        {hasMode3 ? (
          <div className="space-y-2">
            <p className="text-white font-semibold">
              Test de Munger : «Achèterais-tu {ticker_id} aujourd&apos;hui à {currentPrice ? `€${currentPrice}` : '—'} ?»
            </p>
            <p className="text-red-300 font-medium">
              → NON{resultJson.munger_test_rationale ? ` — ${resultJson.munger_test_rationale}` : ''}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-white font-semibold">
              Analyse fresh — Opportunity Agent : «Achèterais-tu {ticker_id} aujourd&apos;hui ?»
            </p>
            <p className="text-red-300 font-medium">
              → NON{thesis?.conviction_score != null ? ` (conviction ${thesis.conviction_score}/10)` : ''}
              {resultJson.top_risks?.length > 0 && ` — ${resultJson.top_risks.slice(0, 2).join(', ')}`}
            </p>
          </div>
        )}

        {/* Position summary */}
        {position && (
          <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
            <div className="bg-red-900/30 rounded-lg px-3 py-2 text-center">
              <p className="text-xs text-red-400">Quantité</p>
              <p className="text-white font-medium">{position.quantity || position.shares || '—'} actions</p>
            </div>
            <div className="bg-red-900/30 rounded-lg px-3 py-2 text-center">
              <p className="text-xs text-red-400">Prix achat</p>
              <p className="text-white font-medium">€{position.avg_buy_price?.toFixed(2) || '—'}</p>
            </div>
            <div className="bg-red-900/30 rounded-lg px-3 py-2 text-center">
              <p className="text-xs text-red-400">P&L</p>
              <p className={`font-medium ${(position.unrealized_pnl_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {position.unrealized_pnl_pct != null ? `${position.unrealized_pnl_pct >= 0 ? '+' : ''}${position.unrealized_pnl_pct.toFixed(1)}%` : '—'}
              </p>
            </div>
          </div>
        )}
      </div>

      {error && <div className="bg-red-900/30 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">{error}</div>}

      {/* Option A — Clôturer */}
      <div className={`border rounded-xl p-5 transition-colors ${selectedOption === 'close' ? 'border-red-700 bg-red-950/20' : 'border-gray-800 bg-gray-900'}`}>
        <button onClick={() => setSelectedOption(o => o === 'close' ? null : 'close')}
          className="w-full flex items-center justify-between text-left">
          <div>
            <h3 className="font-semibold text-white">Option A — Clôturer la position</h3>
            <p className="text-sm text-gray-500 mt-0.5">Vendre l&apos;intégralité de la position</p>
          </div>
          <span className="text-gray-600">{selectedOption === 'close' ? '▲' : '▼'}</span>
        </button>
        {selectedOption === 'close' && (
          <div className="mt-4">
            <p className="text-sm text-gray-400 mb-4">
              Confirmer la clôture de la position {ticker_id} ?
              {position && ` (${position.quantity || position.shares} actions à prix moyen €${position.avg_buy_price?.toFixed(2)})`}
            </p>
            <button onClick={handleClose} disabled={actionLoading}
              className="px-5 py-2 bg-red-700 hover:bg-red-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors">
              {actionLoading ? 'Clôture…' : 'Confirmer la clôture'}
            </button>
          </div>
        )}
      </div>

      {/* Option B — Réduire */}
      <div className={`border rounded-xl p-5 transition-colors ${selectedOption === 'reduce' ? 'border-orange-700 bg-orange-950/20' : 'border-gray-800 bg-gray-900'}`}>
        <button onClick={() => setSelectedOption(o => o === 'reduce' ? null : 'reduce')}
          className="w-full flex items-center justify-between text-left">
          <div>
            <h3 className="font-semibold text-white">Option B — Réduire la position</h3>
            <p className="text-sm text-gray-500 mt-0.5">Vendre une partie des actions</p>
          </div>
          <span className="text-gray-600">{selectedOption === 'reduce' ? '▲' : '▼'}</span>
        </button>
        {selectedOption === 'reduce' && (
          <div className="mt-4 space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm text-gray-400">Pourcentage à vendre</label>
                <span className="text-white font-medium">{reducePercent}%</span>
              </div>
              <input
                type="range" min="10" max="90" step="5"
                value={reducePercent}
                onChange={e => setReducePercent(Number(e.target.value))}
                className="w-full accent-orange-500"
              />
              <div className="flex justify-between text-xs text-gray-600 mt-1">
                <span>10%</span><span>50%</span><span>90%</span>
              </div>
            </div>
            <button onClick={handleReduce} disabled={actionLoading}
              className="px-5 py-2 bg-orange-700 hover:bg-orange-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors">
              {actionLoading ? 'Réduction…' : `Réduire de ${reducePercent}%`}
            </button>
          </div>
        )}
      </div>

      {/* Option C — Maintenir (débat) */}
      <div className={`border rounded-xl p-5 transition-colors ${selectedOption === 'maintain' ? 'border-yellow-700 bg-yellow-950/20' : 'border-gray-800 bg-gray-900'}`}>
        <button onClick={() => setSelectedOption(o => o === 'maintain' ? null : 'maintain')}
          className="w-full flex items-center justify-between text-left">
          <div>
            <h3 className="font-semibold text-white">Option C — Maintenir (débat de conviction)</h3>
            <p className="text-sm text-gray-500 mt-0.5">Argumenter pour maintenir la position malgré le signal négatif</p>
          </div>
          <span className="text-gray-600">{selectedOption === 'maintain' ? '▲' : '▼'}</span>
        </button>
        {selectedOption === 'maintain' && (
          <div className="mt-4 space-y-4">
            <div>
              <label className="text-xs text-gray-400 block mb-1">
                Argumentation pour le maintien
                <span className={`ml-2 ${wordCount >= 50 ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {wordCount}/50 mots min.
                </span>
              </label>
              <textarea
                value={maintainNote}
                onChange={e => setMaintainNote(e.target.value)}
                placeholder="Expliquez pourquoi vous maintenez la conviction sur ce titre malgré le signal négatif de l'agent…"
                rows={5}
                className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 placeholder-gray-600 focus:border-indigo-500 focus:outline-none resize-none"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-2">Date de réévaluation</label>
              <div className="flex gap-2">
                {REEVALUATION_OPTIONS.map(opt => (
                  <button key={opt.days} onClick={() => setReevaluationDays(opt.days)}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      reevaluationDays === opt.days
                        ? 'bg-indigo-700 text-white'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}>
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <button
              onClick={handleMaintainDebate}
              disabled={actionLoading || wordCount < 50}
              className="px-5 py-2 bg-yellow-700 hover:bg-yellow-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors"
            >
              {actionLoading ? 'Ouverture…' : 'Ouvrir le débat de conviction'}
            </button>
          </div>
        )}
      </div>

      {/* Option D — Reporter */}
      <div className={`border rounded-xl p-5 transition-colors ${selectedOption === 'delay' ? 'border-gray-600 bg-gray-800/50' : 'border-gray-800 bg-gray-900'} ${delayUsed ? 'opacity-50' : ''}`}>
        <button onClick={() => !delayUsed && setSelectedOption(o => o === 'delay' ? null : 'delay')}
          disabled={delayUsed}
          className="w-full flex items-center justify-between text-left disabled:cursor-not-allowed">
          <div>
            <h3 className="font-semibold text-white">
              Option D — Reporter
              {delayUsed && <span className="ml-2 text-xs text-gray-600 font-normal">(déjà utilisé)</span>}
            </h3>
            <p className="text-sm text-gray-500 mt-0.5">Reporter la décision (usage unique)</p>
          </div>
          <span className="text-gray-600">{selectedOption === 'delay' ? '▲' : '▼'}</span>
        </button>
        {selectedOption === 'delay' && !delayUsed && (
          <div className="mt-4 space-y-4">
            <div>
              <label className="text-xs text-gray-400 block mb-2">Reporter de</label>
              <div className="flex gap-2">
                {DELAY_OPTIONS.map(opt => (
                  <button key={opt.days} onClick={() => setDelayDays(opt.days)}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      delayDays === opt.days
                        ? 'bg-indigo-700 text-white'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}>
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <button onClick={handleDelay} disabled={actionLoading}
              className="px-5 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors">
              {actionLoading ? 'Report…' : `Reporter de ${delayDays} jours`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
