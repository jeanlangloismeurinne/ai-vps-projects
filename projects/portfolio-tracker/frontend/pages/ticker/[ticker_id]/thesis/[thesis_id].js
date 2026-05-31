import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import AgentChat from '../../../../components/AgentChat'
import ThesisEditorV2 from '../../../../components/ThesisEditorV2'
import AgentSyncOverlay from '../../../../components/AgentSyncOverlay'
import CalendarEditor from '../../../../components/CalendarEditor'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function ThesisPage() {
  const router = useRouter()
  const { ticker_id, thesis_id } = router.query

  const [thesis, setThesis] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [agentSynced, setAgentSynced] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [error, setError] = useState('')
  const [calendarEvents, setCalendarEvents] = useState([])
  const [cashAvailable, setCashAvailable] = useState(null)
  const [currentPrice, setCurrentPrice] = useState(null)

  // Validation form
  const [valForm, setValForm] = useState({ shares: '', buy_price: '', date: '' })

  const debounceRef = useRef(null)
  const initialHandoffSent = useRef(false)

  // Check agent sync
  useEffect(() => {
    fetch(`${API}/admin/agents`)
      .then(r => r.json())
      .then(agents => {
        const agent = Array.isArray(agents) ? agents.find(a => a.agent_name === 'thesis-agent') : null
        if (agent) setAgentSynced(agent.synced !== false)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!thesis_id || !ticker_id) return

    const init = async () => {
      setPageLoading(true)
      try {
        const [thRes, mRes, sumRes] = await Promise.all([
          fetch(`${API}/tickers/${ticker_id}/theses/${thesis_id}`),
          fetch(`${API}/theses/${thesis_id}/messages`),
          fetch(`${API}/portfolio-v2/summary`),
        ])
        if (thRes.ok) {
          const th = await thRes.json()
          setThesis(th)
          if (th.calendar_events_suggested) {
            setCalendarEvents(th.calendar_events_suggested)
          }
        }
        if (mRes.ok) setMessages(await mRes.json())
        if (sumRes.ok) {
          const sum = await sumRes.json()
          setCashAvailable(sum.cash_balance)
        }
        // Get current price
        const mktRes = await fetch(`${API}/tickers/${ticker_id}/metrics`)
        if (mktRes.ok) {
          const m = await mktRes.json()
          setCurrentPrice(m.current_price)
          setValForm(f => ({ ...f, buy_price: m.current_price?.toFixed(2) || '' }))
        }
      } catch (e) {
        setError('Erreur de chargement')
      }
      setPageLoading(false)
    }
    init()
  }, [thesis_id, ticker_id])

  // Send handoff when thesis loaded (new thesis, no messages)
  useEffect(() => {
    if (!thesis?.id || initialHandoffSent.current || messages.length > 0 || !agentSynced) return
    if (!thesis.opportunity_id) return
    initialHandoffSent.current = true
    sendHandoff()
  }, [thesis?.id, messages.length, agentSynced])

  const sendHandoff = async () => {
    if (!thesis?.opportunity_id) return
    setIsLoading(true)
    try {
      const briefRes = await fetch(`${API}/opportunities/${thesis.opportunity_id}`)
      const brief = briefRes.ok ? await briefRes.json() : null
      const handoffContent = JSON.stringify({
        type: 'thesis_handoff',
        ticker: ticker_id,
        opportunity_id: thesis.opportunity_id,
        brief_summary: brief?.brief_json?.verdict || null,
        proto_hypotheses: brief?.brief_json?.proto_hypotheses || [],
        instruction: 'Construis la thèse d\'investissement complète H1-H7 avec les scénarios Bear/Central/Bull, les seuils de cours, et le calendrier de monitoring suggéré.',
      })

      const res = await fetch(`${API}/theses/${thesis.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content: handoffContent }),
      })
      if (res.ok) {
        const data = await res.json()
        setMessages([
          { role: 'user', content: '(Handoff automatique depuis le brief d\'opportunité)' },
          { role: 'assistant', content: data.content || data.message || '' },
        ])
      }
    } catch {}
    setIsLoading(false)
  }

  const sendMessage = async (text) => {
    if (!thesis?.id) return
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setIsLoading(true)
    try {
      const res = await fetch(`${API}/theses/${thesis.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content: text }),
      })
      if (res.ok) {
        const data = await res.json()
        setMessages(prev => [...prev, { role: 'assistant', content: data.content || data.message || '' }])
      }
    } catch {}
    setIsLoading(false)
  }

  const refreshThesis = async () => {
    if (!thesis?.id) return
    setRefreshing(true)
    try {
      const res = await fetch(`${API}/theses/${thesis.id}/refresh-json`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        const newThesis = { ...thesis, thesis_json: data.thesis_json || data }
        setThesis(newThesis)
        if (data.calendar_events_suggested) {
          setCalendarEvents(data.calendar_events_suggested)
        }
      }
    } catch {}
    setRefreshing(false)
  }

  const handleThesisChange = useCallback((newJson) => {
    if (!thesis?.id) return
    setThesis(prev => ({ ...prev, thesis_json: newJson }))
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      setSaving(true)
      try {
        await fetch(`${API}/tickers/${ticker_id}/theses/${thesis.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ thesis_json: newJson }),
        })
      } catch {}
      setSaving(false)
    }, 1000)
  }, [thesis?.id])

  const handleValidate = async () => {
    if (!thesis?.id || !thesis?.thesis_json) return
    const amount = parseFloat(valForm.shares) * parseFloat(valForm.buy_price)
    if (cashAvailable != null && amount > cashAvailable) {
      if (!confirm(`Montant (€${amount.toFixed(2)}) supérieur au cash disponible (€${cashAvailable.toFixed(2)}). Continuer ?`)) return
    }
    setValidating(true)
    try {
      const res = await fetch(`${API}/theses/${thesis.id}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          shares: parseFloat(valForm.shares),
          purchase_price: parseFloat(valForm.buy_price),
          purchase_date: valForm.date || new Date().toISOString().slice(0, 10),
        }),
      })
      if (res.ok) {
        router.push(`/ticker/${ticker_id}`)
      } else {
        const e = await res.json().catch(() => ({}))
        setError(e.detail || 'Erreur de validation')
      }
    } catch (e) {
      setError(e.message)
    }
    setValidating(false)
  }

  const validationAmount = parseFloat(valForm.shares || 0) * parseFloat(valForm.buy_price || 0)
  const overCash = cashAvailable != null && validationAmount > cashAvailable && validationAmount > 0

  if (pageLoading) return <div className="text-center py-16 text-gray-500">Chargement…</div>

  return (
    <div className="space-y-4">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <Link href="/portfolio" className="hover:text-gray-400">Portefeuille</Link>
        <span>/</span>
        <Link href={`/ticker/${ticker_id}`} className="hover:text-gray-400">{ticker_id}</Link>
        <span>/</span>
        <span className="text-gray-400">Thèse #{thesis_id}</span>
        {saving && <span className="ml-2 text-xs text-gray-600">Sauvegarde…</span>}
        {error && <span className="ml-2 text-xs text-red-400">{error}</span>}
      </div>

      {/* Main layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Col 1 — Chat */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl relative flex flex-col" style={{ height: '75vh' }}>
          <div className="px-4 py-3 border-b border-gray-800">
            <h2 className="font-semibold text-white text-sm">Chat — Thesis Agent</h2>
          </div>
          {!agentSynced && <AgentSyncOverlay agentName="thesis-agent" />}
          <div className="flex-1 min-h-0">
            <AgentChat
              messages={messages}
              onSend={sendMessage}
              isLoading={isLoading}
              disabled={!agentSynced}
            />
          </div>
        </div>

        {/* Col 2 — Thesis Editor */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl flex flex-col" style={{ height: '75vh' }}>
          <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
            <h2 className="font-semibold text-white text-sm">Thèse en cours</h2>
            <button
              onClick={refreshThesis}
              disabled={refreshing || !thesis?.id}
              className="px-3 py-1.5 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-xs rounded-lg font-medium transition-colors"
            >
              {refreshing ? '⟳ Actualisation…' : 'Actualiser la thèse →'}
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <ThesisEditorV2
              thesisJson={thesis?.thesis_json}
              onChange={handleThesisChange}
            />
          </div>
        </div>
      </div>

      {/* Calendar de monitoring */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="font-semibold text-white mb-4">Calendrier de monitoring</h3>
        {calendarEvents.length === 0 && !thesis?.thesis_json ? (
          <p className="text-gray-600 text-sm">Actualisez la thèse pour générer des événements calendrier suggérés</p>
        ) : (
          <CalendarEditor
            events={calendarEvents}
            onAdd={ev => setCalendarEvents(prev => [...prev, { ...ev, _tempId: Date.now() }])}
            onDelete={id => setCalendarEvents(prev => prev.filter(e => (e.id || e._tempId) !== id))}
            onUpdate={updated => setCalendarEvents(prev => prev.map(e => (e.id || e._tempId) === (updated.id || updated._tempId) ? updated : e))}
          />
        )}
      </div>

      {/* Validation */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="font-semibold text-white mb-4">Valider la thèse et enregistrer la position</h3>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Nombre d&apos;actions</label>
            <input
              type="number" min="1"
              value={valForm.shares}
              onChange={e => setValForm(f => ({ ...f, shares: e.target.value }))}
              placeholder="ex. 10"
              className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">
              Prix d&apos;achat (€)
              {currentPrice && <span className="text-gray-600 ml-1">— actuel : €{currentPrice.toFixed(2)}</span>}
            </label>
            <input
              type="number" step="0.01"
              value={valForm.buy_price}
              onChange={e => setValForm(f => ({ ...f, buy_price: e.target.value }))}
              className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Date</label>
            <input
              type="date"
              value={valForm.date}
              onChange={e => setValForm(f => ({ ...f, date: e.target.value }))}
              className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none"
            />
          </div>
        </div>

        {validationAmount > 0 && (
          <div className="mb-3 text-sm text-gray-400">
            Montant total : <span className="text-white font-medium">
              €{validationAmount.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            {cashAvailable != null && (
              <span className="ml-2 text-gray-500">
                (cash disponible : €{cashAvailable.toLocaleString('fr-FR', { minimumFractionDigits: 2 })})
              </span>
            )}
          </div>
        )}

        {overCash && (
          <div className="mb-3 bg-orange-900/30 border border-orange-700 text-orange-300 text-sm rounded-lg px-4 py-2">
            Attention : le montant dépasse le cash disponible (€{cashAvailable?.toFixed(2)})
          </div>
        )}

        {error && (
          <div className="mb-3 bg-red-900/30 border border-red-700 text-red-300 text-sm rounded-lg px-4 py-2">{error}</div>
        )}

        <button
          onClick={handleValidate}
          disabled={validating || !thesis?.thesis_json || !valForm.shares || !valForm.buy_price}
          title={!thesis?.thesis_json ? "Cliquez d'abord sur 'Actualiser la thèse'" : ''}
          className="px-5 py-2 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg font-medium transition-colors"
        >
          {validating ? 'Validation…' : 'Valider la thèse et enregistrer la position'}
        </button>
        {!thesis?.thesis_json && (
          <p className="mt-2 text-xs text-gray-600">Actualisez d&apos;abord la thèse pour activer la validation</p>
        )}
      </div>
    </div>
  )
}
