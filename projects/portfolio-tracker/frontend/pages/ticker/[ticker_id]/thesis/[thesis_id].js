import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import AgentChat from '../../../../components/AgentChat'
import ThesisEditorV2 from '../../../../components/ThesisEditorV2'
import AgentSyncOverlay from '../../../../components/AgentSyncOverlay'
import CalendarEditor from '../../../../components/CalendarEditor'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'
const STREAMING = process.env.NEXT_PUBLIC_DUST_STREAMING === 'true'

const _TICKER_MAP = {
  amazon: 'AMZN', aws: 'AMZN', google: 'GOOGL', alphabet: 'GOOGL', gcp: 'GOOGL',
  apple: 'AAPL', meta: 'META', facebook: 'META', nvidia: 'NVDA',
  salesforce: 'CRM', oracle: 'ORCL', ibm: 'IBM', servicenow: 'NOW',
  sap: 'SAP', workday: 'WDAY',
}
function _guessTicker(name) {
  const first = (name.split(/[\s,(]/)[0] || '').toLowerCase().replace(/[,()]/g, '')
  return _TICKER_MAP[first] || (name.split(/[\s,(]/)[0] || '').slice(0, 8).toUpperCase()
}

function normalizeAgentThesis(raw) {
  // Déjà normalisé (format frontend) → pass-through
  if (raw.hypotheses || raw.scenarios) return raw

  const out = { ...raw }

  // ── Metadata ──────────────────────────────────────────────────────────────
  const meta = raw.thesis_metadata || {}
  if (meta.investment_thesis_summary) out.one_liner = meta.investment_thesis_summary
  if (meta.analyst_conviction_score != null) out.conviction_score = meta.analyst_conviction_score
  if (meta.analyst_conviction_rationale) out.conviction_rationale = meta.analyst_conviction_rationale
  if (meta.investment_recommendation) out.recommendation = meta.investment_recommendation
  if (meta.thesis_horizon_years) out.thesis_horizon_years = meta.thesis_horizon_years
  if (meta.ideal_investor_profile) out.ideal_investor_profile = meta.ideal_investor_profile

  // ── Scénarios ─────────────────────────────────────────────────────────────
  const rawStep4 = raw.step_4_scenarios_5yr || {}
  const scenariosList = Array.isArray(rawStep4.scenarios) ? rawStep4.scenarios
    : Array.isArray(rawStep4) ? rawStep4 : []
  const basePrice = typeof rawStep4 === 'object' && !Array.isArray(rawStep4) ? (rawStep4.base_price || 0) : 0
  if (rawStep4.probability_weighted_target) out.probability_weighted_target = rawStep4.probability_weighted_target

  const scenarios = {}
  for (const s of scenariosList) {
    const name = (s.scenario_name || '').toLowerCase()
    if (!name) continue
    const midpoint = (s.price_target_5yr || {}).midpoint || 0
    let cagr = ''
    if (basePrice && midpoint) {
      try { cagr = Math.round((Math.pow(midpoint / basePrice, 0.2) - 1) * 1000) / 10 } catch {}
    }
    scenarios[name] = { probability: s.probability_pct || 0, cagr, description: s.hypothesis_directrice || s.description || '' }
  }
  if (Object.keys(scenarios).length) out.scenarios = scenarios

  // ── Hypothèses ────────────────────────────────────────────────────────────
  const hypsList = Array.isArray(raw.step_5_falsifiable_hypotheses) ? raw.step_5_falsifiable_hypotheses : []
  if (hypsList.length) {
    out.hypotheses = hypsList.map((h, i) => ({
      id: `H${h.hypothesis_id || i + 1}`,
      text: h.statement || '',
      status: 'unverified',
      weight: h.criticality_level || '',
      kpi_metric: (h.kpi_tracking || {}).metric_name || '',
      kpi_target: (h.kpi_tracking || {}).baseline_target || '',
      kpi_unit: (h.kpi_tracking || {}).unit || '',
      alert_threshold: h.alert_threshold || {},
      invalidation_threshold: h.invalidation_threshold || {},
    }))
  }

  // ── Seuils de cours (dérivés des scénarios) ────────────────────────────────
  const getScenario = n => scenariosList.find(s => (s.scenario_name || '').toUpperCase() === n) || {}
  const bearPt = getScenario('BEAR').price_target_5yr || {}
  const centralPt = getScenario('CENTRAL').price_target_5yr || {}
  const bullPt = getScenario('BULL').price_target_5yr || {}
  const price_thresholds = {}
  if (bearPt.low || bearPt.midpoint) price_thresholds.stop_loss = bearPt.low || bearPt.midpoint
  if (centralPt.midpoint) price_thresholds.fair_value = centralPt.midpoint
  if (bullPt.midpoint) price_thresholds.target_price = bullPt.midpoint
  if (Object.keys(price_thresholds).length) out.price_thresholds = price_thresholds

  // ── Analyse fondamentale ───────────────────────────────────────────────────
  const rawStep1 = raw.step_1_fundamental_analysis || {}
  if (typeof rawStep1 === 'object') {
    const fa = {}
    if (rawStep1.verdict) fa.verdict = rawStep1.verdict
    const moat = rawStep1.moat_assessment || {}
    if (moat.status) fa.moat_status = moat.status
    if (moat.components?.length) {
      fa.moat_components = moat.components.map(c => ({ type: c.moat_type || '', strength: c.strength || '', durability: c.durability || '' }))
    }
    const pricing = rawStep1.pricing_power || {}
    if (pricing.status) fa.pricing_power_status = pricing.status
    if (pricing.sustainability) fa.pricing_power_sustainability = pricing.sustainability
    const capalloc = rawStep1.capital_allocation || {}
    if (Object.keys(capalloc).length) fa.capital_allocation = capalloc
    if (Object.keys(fa).length) out.fundamental_analysis = fa
  }

  // ── Pairs comparables ──────────────────────────────────────────────────────
  const competitors = (raw.step_2_competitive_analysis || {}).key_competitors_analysis || []
  if (competitors.length) {
    out.pairs = competitors.map((c, i) => ({
      ticker: _guessTicker(c.competitor || ''),
      tier: ['T1', 'T2', 'T3'][Math.min(i, 2)],
      note: c.competitive_position || c.competitor || '',
    }))
  }

  // ── Bear Steel Man ─────────────────────────────────────────────────────────
  const rawStep7 = raw.step_7_devil_advocate_risks || []
  const risks = Array.isArray(rawStep7) ? rawStep7 : (rawStep7.bear_steel_man || [])
  if (risks.length) {
    out.bear_steel_man = risks.slice(0, 4).map(r =>
      typeof r === 'string' ? r : (r.risk_category ? `${r.risk_category} : ${r.description || ''}` : r.description || '')
    ).join('\n\n')
  }

  // ── Track Record Analystes ─────────────────────────────────────────────────
  const rawStep6 = raw.step_6_analyst_track_record || {}
  if (typeof rawStep6 === 'object') {
    const consensus = rawStep6.consensus_current || {}
    const hist = rawStep6.historical_reliability || {}
    const label = consensus.analyst_count ? `Consensus (${consensus.analyst_count} analystes)` : 'Consensus Wall Street'
    const parts = [
      hist.eps_beat_ratio_pct ? `EPS beat ${hist.eps_beat_ratio_pct}%` : '',
      hist.revenue_beat_ratio_pct ? `Rev beat ${hist.revenue_beat_ratio_pct}%` : '',
      consensus.price_target_median ? `PT $${consensus.price_target_low}-$${consensus.price_target_high} (médian $${consensus.price_target_median})` : '',
      consensus.recommendation_buy_pct ? `Buy ${consensus.recommendation_buy_pct}%` : '',
    ].filter(Boolean)
    out.track_record_analysts = [{ analyst: label, accuracy: parts.join(' | ') }]
  }

  return out
}

function _detectEventType(name = '') {
  const n = name.toLowerCase()
  if (n.includes('earning')) return 'earnings'
  if (n.includes('conference') || n.includes('investor day')) return 'conference'
  if (n.includes('product') || n.includes('launch') || n.includes('release')) return 'product_launch'
  if (n.includes('dividend')) return 'dividend'
  if (n.includes('macro') || n.includes('regulatory') || n.includes('fed')) return 'macro'
  return 'other'
}

function _criticalityToMode(criticality = '') {
  const c = criticality.toLowerCase()
  if (c === 'critical') return 3
  if (c === 'high') return 2
  return 1
}

function normalizeCalendarEvents(events = []) {
  return events.map((ev, i) => ({
    ...ev,
    _tempId: ev._tempId || `agent_${i}_${Date.now()}`,
    label: ev.label || ev.event_name || '',
    event_date: ev.event_date || ev.scheduled_date || ev.date_estimated || '',
    event_type: ev.event_type || _detectEventType(ev.event_name),
    monitoring_mode: ev.monitoring_mode || _criticalityToMode(ev.criticality),
  }))
}

export default function ThesisPage() {
  const router = useRouter()
  const { ticker_id, thesis_id } = router.query

  const [thesis, setThesis] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [agentSynced, setAgentSynced] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshChars, setRefreshChars] = useState(0)
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
  const jsonImportRef = useRef(null)

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
            setCalendarEvents(normalizeCalendarEvents(th.calendar_events_suggested))
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

  const _readStream = async (res, onEvent) => {
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try { onEvent(JSON.parse(line.slice(6))) } catch {}
      }
    }
  }

  const _sendStreaming = async (url, body, initialMessages) => {
    setIsLoading(true)
    setMessages(prev => [...prev, ...initialMessages])
    setMessages(prev => [...prev, { role: 'streaming', content: '', chainOfThought: '' }])
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        setMessages(prev => { const n = [...prev]; n[n.length - 1] = { role: 'error', content: err.detail || `Erreur ${res.status}` }; return n })
        return
      }
      await _readStream(res, (event) => {
        if (event.type === 'chain_of_thought') {
          setMessages(prev => { const n = [...prev]; const l = n[n.length - 1]; if (l?.role === 'streaming') n[n.length - 1] = { ...l, chainOfThought: (l.chainOfThought || '') + event.text }; return n })
        } else if (event.type === 'tokens') {
          setMessages(prev => { const n = [...prev]; const l = n[n.length - 1]; if (l?.role === 'streaming') n[n.length - 1] = { ...l, content: (l.content || '') + event.text }; return n })
        } else if (event.type === 'done') {
          setMessages(prev => { const n = [...prev]; n[n.length - 1] = { role: 'assistant', content: event.content, chainOfThought: event.chain_of_thought }; return n })
        } else if (event.type === 'error') {
          setMessages(prev => { const n = [...prev]; n[n.length - 1] = { role: 'error', content: event.message }; return n })
        }
      })
    } catch (e) {
      setMessages(prev => { const n = [...prev]; if (n[n.length - 1]?.role === 'streaming') n[n.length - 1] = { role: 'error', content: 'Impossible de joindre le serveur.' }; return n })
    } finally {
      setIsLoading(false)
    }
  }

  const handleImportJson = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !thesis?.id) return
    e.target.value = ''
    try {
      const parsed = normalizeAgentThesis(JSON.parse(await file.text()))
      setThesis(prev => ({ ...prev, thesis_json: parsed }))
      if (parsed.calendar_events_suggested) {
        setCalendarEvents(normalizeCalendarEvents(parsed.calendar_events_suggested))
      }
      setSaving(true)
      await fetch(`${API}/tickers/${ticker_id}/theses/${thesis.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thesis_json: parsed }),
      })
    } catch {
      setError('Fichier JSON invalide')
    }
    setSaving(false)
  }

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

      if (STREAMING) {
        await _sendStreaming(
          `${API}/theses/${thesis.id}/chat/stream`,
          { role: 'user', content: handoffContent },
          [{ role: 'user', content: '(Handoff automatique depuis le brief d\'opportunité)' }]
        )
        return
      }

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
    if (STREAMING) {
      await _sendStreaming(
        `${API}/theses/${thesis.id}/chat/stream`,
        { role: 'user', content: text },
        [{ role: 'user', content: text }]
      )
      return
    }
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
      } else {
        const err = await res.json().catch(() => ({}))
        const detail = err.detail || `Erreur ${res.status}`
        setMessages(prev => [...prev, { role: 'error', content: detail }])
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'error', content: 'Impossible de joindre le serveur.' }])
    }
    setIsLoading(false)
  }

  const refreshThesis = async () => {
    if (!thesis?.id) return
    setRefreshing(true)
    setRefreshChars(0)
    setError('')

    if (STREAMING) {
      try {
        const res = await fetch(`${API}/theses/${thesis.id}/refresh-json/stream`, { method: 'POST' })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          setError(err.detail || `Erreur actualisation (${res.status})`)
          setRefreshing(false)
          return
        }
        await _readStream(res, (event) => {
          if (event.type === 'tokens') {
            setRefreshChars(prev => prev + (event.text?.length || 0))
          } else if (event.type === 'done_refresh') {
            setThesis(prev => ({ ...prev, thesis_json: event.parsed_json }))
            if (event.calendar_events_suggested) setCalendarEvents(normalizeCalendarEvents(event.calendar_events_suggested))
          } else if (event.type === 'error') {
            setError(event.message)
          }
        })
      } catch {
        setError('Impossible de joindre le serveur.')
      }
      setRefreshing(false)
      setRefreshChars(0)
      return
    }

    try {
      const res = await fetch(`${API}/theses/${thesis.id}/refresh-json`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        const newThesis = { ...thesis, thesis_json: data.parsed_json || data.thesis?.thesis_json }
        setThesis(newThesis)
        if (data.calendar_events_suggested) {
          setCalendarEvents(normalizeCalendarEvents(data.calendar_events_suggested))
        }
      } else {
        const err = await res.json().catch(() => ({}))
        setError(err.detail || `Erreur actualisation (${res.status})`)
      }
    } catch {
      setError('Impossible de joindre le serveur.')
    }
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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        {/* Col 1 — Chat — fixed height, sticky so it stays visible while scrolling thesis */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl relative flex flex-col sticky top-4" style={{ height: '75vh' }}>
          <div className="px-4 py-3 border-b border-gray-800">
            <h2 className="font-semibold text-white text-sm">Chat — Thesis Agent</h2>
          </div>
          {!agentSynced && <AgentSyncOverlay agentName="thesis-agent" />}
          {messages.length === 0 && !isLoading && thesis?.id && (
            <div className="flex flex-col items-center justify-center gap-3 py-8 px-6 border-b border-gray-800">
              <p className="text-gray-500 text-sm text-center">L&apos;analyse n&apos;a pas encore démarré.</p>
              <button
                onClick={sendHandoff}
                disabled={!agentSynced}
                className="px-4 py-2 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors"
              >
                Lancer l&apos;analyse
              </button>
            </div>
          )}
          <div className="flex-1 min-h-0">
            <AgentChat
              messages={messages}
              onSend={sendMessage}
              isLoading={isLoading}
              disabled={!agentSynced}
            />
          </div>
        </div>

        {/* Col 2 — Thesis Editor — expands naturally, not capped to 75vh */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl" style={{ minHeight: '75vh' }}>
          <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
            <h2 className="font-semibold text-white text-sm">Thèse en cours</h2>
            <div className="flex items-center gap-2">
              <input
                ref={jsonImportRef}
                type="file"
                accept=".json,application/json"
                className="hidden"
                onChange={handleImportJson}
              />
              <button
                onClick={() => jsonImportRef.current?.click()}
                disabled={!thesis?.id}
                className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-200 text-xs rounded-lg font-medium transition-colors"
              >
                Importer JSON
              </button>
              <button
                onClick={refreshThesis}
                disabled={refreshing || !thesis?.id}
                className="px-3 py-1.5 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-xs rounded-lg font-medium transition-colors"
              >
                {refreshing
                  ? STREAMING
                    ? `⟳ Génération… ${refreshChars > 0 ? `(${refreshChars} car.)` : ''}`
                    : '⟳ Actualisation…'
                  : 'Actualiser la thèse →'}
              </button>
            </div>
          </div>
          {refreshing && STREAMING && (
            <div className="h-1 bg-gray-800 overflow-hidden rounded-b">
              <div
                className="h-full bg-indigo-500 transition-all duration-500"
                style={{ width: `${Math.min(95, (refreshChars / 4000) * 100)}%` }}
              />
            </div>
          )}
          <div>
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
