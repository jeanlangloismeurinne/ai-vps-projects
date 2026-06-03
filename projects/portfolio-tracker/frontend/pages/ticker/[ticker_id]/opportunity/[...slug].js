import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import AgentChat from '../../../../components/AgentChat'
import InvestmentBriefEditor from '../../../../components/InvestmentBriefEditor'
import AgentSyncOverlay from '../../../../components/AgentSyncOverlay'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

function normalizeAgentBrief(raw) {
  // Déjà normalisé (format frontend) → pass-through
  if (raw.screening || raw.verdict) return raw

  const details = raw.step_1_screening?.details || []
  const criteria = details.map(d => ({
    label: d.criterion || '',
    pass: d.status === 'pass' ? true : d.status === 'fail' ? false : null,
    note: d.comment || '',
  }))

  const diag = raw.step_2_diagnostic || {}
  const anomalie = {
    score: null,
    facteurs: diag.main_finding || diag.root_cause || '',
  }

  const step3 = raw.step_3_analogies || {}
  const analogies = step3.analogies || []
  const analogie = analogies.length > 0 ? {
    societe: analogies[0].comparable || '',
    confiance: step3.confidence_score ?? null,
    description: analogies[0].parallel || analogies[0].notes || '',
  } : {}

  const cats = raw.step_4_catalysts?.catalysts || []
  const catalyseurs = cats.map(c => c.event || '').filter(Boolean)

  const hyps = raw.step_5_proto_hypotheses?.hypotheses || []
  const proto_hypotheses = hyps.map(h => ({
    text: h.belief || '',
    confidence: h.criticality === 'MUST_BE_TRUE' ? 'high' : 'medium',
  }))

  const v = raw.step_6_verdict || {}
  const top_risques = (v.top_3_risks || []).map(r => r.risk || '').filter(Boolean)
  const verdict = {
    conviction: v.conviction_score ?? null,
    conviction_score: v.conviction_score ?? null,
    recommendation: v.recommendation || '',
    downside_floor: v.downside_floor ?? null,
    top_risques,
  }

  return {
    screening: { criteria },
    anomalie,
    analogie,
    catalyseurs,
    proto_hypotheses,
    verdict,
    _raw: raw,
  }
}

function ExistingBriefModal({ brief, onResume, onRestart }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70" />
      <div className="relative bg-gray-800 border border-amber-700 rounded-xl shadow-2xl w-full max-w-md">
        <div className="px-6 py-5">
          <h3 className="font-semibold text-white text-lg mb-2">Un brief existe déjà pour ce titre</h3>
          <div className="text-sm text-gray-400 space-y-1 mb-5">
            <p>Créé le {brief.created_at ? new Date(brief.created_at).toLocaleDateString('fr-FR') : '—'}</p>
            {brief.brief_json?.verdict?.conviction != null && (
              <p>Conviction {brief.brief_json.verdict.conviction}/10</p>
            )}
            {brief.brief_json?.verdict?.recommendation && (
              <p>Recommandation : <span className="text-white font-medium">{brief.brief_json.verdict.recommendation}</span></p>
            )}
          </div>
          <div className="flex gap-3">
            <button onClick={onResume}
              className="flex-1 py-2 bg-indigo-700 hover:bg-indigo-600 text-white text-sm rounded-lg font-medium transition-colors">
              Reprendre l&apos;analyse
            </button>
            <button onClick={onRestart}
              className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm rounded-lg font-medium transition-colors">
              Recommencer depuis zéro
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function OpportunityPage() {
  const router = useRouter()
  const { ticker_id, slug } = router.query
  const slugArr = Array.isArray(slug) ? slug : []
  const isNew = slugArr[0] === 'new'
  const briefIdFromUrl = isNew ? null : slugArr[0]

  const [brief, setBrief] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [agentSynced, setAgentSynced] = useState(true)
  const [existingBrief, setExistingBrief] = useState(null)
  const [showExistingModal, setShowExistingModal] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const debounceRef = useRef(null)
  const jsonImportRef = useRef(null)

  // Check agent sync status
  useEffect(() => {
    fetch(`${API}/admin/agents`)
      .then(r => r.json())
      .then(agents => {
        const opp = Array.isArray(agents) ? agents.find(a => a.name === 'opportunity-agent') : null
        if (opp) setAgentSynced(opp.synced !== false)
      })
      .catch(() => {})
  }, [])

  // Load or create brief
  useEffect(() => {
    if (!ticker_id || !slugArr.length) return

    const init = async () => {
      setPageLoading(true)
      try {
        if (briefIdFromUrl) {
          // Load existing brief
          const [bRes, mRes] = await Promise.all([
            fetch(`${API}/tickers/${ticker_id}/opportunities/${briefIdFromUrl}`),
            fetch(`${API}/opportunities/${briefIdFromUrl}/messages`),
          ])
          if (bRes.ok) setBrief(await bRes.json())
          if (mRes.ok) setMessages(await mRes.json())
        } else if (isNew) {
          // Check for existing draft brief
          const existingRes = await fetch(`${API}/tickers/${ticker_id}/opportunities?status=draft&limit=1`)
          if (existingRes.ok) {
            const existing = await existingRes.json()
            const existingList = Array.isArray(existing) ? existing : existing.items || []
            if (existingList.length > 0) {
              setExistingBrief(existingList[0])
              setShowExistingModal(true)
              setPageLoading(false)
              return
            }
          }
          // Create new brief
          await createNewBrief()
        }
      } catch (e) {
        setError('Erreur d\'initialisation')
      }
      setPageLoading(false)
    }

    init()
  }, [ticker_id, briefIdFromUrl, isNew])

  const createNewBrief = async () => {
    const res = await fetch(`${API}/tickers/${ticker_id}/opportunities`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'draft' }),
    })
    if (!res.ok) throw new Error('Impossible de créer le brief')
    const newBrief = await res.json()
    setBrief(newBrief)
    router.replace(`/ticker/${ticker_id}/opportunity/${newBrief.id}`, undefined, { shallow: true })
    return newBrief
  }

  const sendInitialMessage = async (briefId) => {
    setIsLoading(true)
    try {
      const ticker = ticker_id
      const content = `[mode: freeform]\n\nAnalyse ${ticker} — commence par un screening rapide puis identifie l'anomalie principale si elle existe.`
      const res = await fetch(`${API}/opportunities/${briefId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content, mode: 'freeform' }),
      })
      if (res.ok) {
        const data = await res.json()
        setMessages(prev => [...prev,
          { role: 'user', content },
          { role: 'assistant', content: data.content || data.message || '' }
        ])
      } else {
        const e = await res.json().catch(() => ({}))
        const msg = e.detail || `Erreur agent ${res.status}`
        setError(msg)
        setMessages(prev => [...prev, { role: 'error', content: msg }])
      }
    } catch (e) {
      const msg = e.message || 'Erreur réseau'
      setError(msg)
      setMessages(prev => [...prev, { role: 'error', content: msg }])
    }
    setIsLoading(false)
  }

  const handleImportJson = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !brief?.id) return
    e.target.value = ''
    try {
      const parsed = normalizeAgentBrief(JSON.parse(await file.text()))
      setBrief(prev => ({ ...prev, brief_json: parsed }))
      setSaving(true)
      await fetch(`${API}/tickers/${ticker_id}/opportunities/${brief.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief_json: parsed }),
      })
    } catch {
      setError('Fichier JSON invalide')
    }
    setSaving(false)
  }

  const sendMessage = async (text) => {
    if (!brief?.id) return
    const userMsg = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/opportunities/${brief.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content: text }),
      })
      if (res.ok) {
        const data = await res.json()
        setMessages(prev => [...prev, { role: 'assistant', content: data.content || data.message || '' }])
      } else {
        const e = await res.json().catch(() => ({}))
        const msg = e.detail || `Erreur agent ${res.status}`
        setError(msg)
        setMessages(prev => [...prev, { role: 'error', content: msg }])
      }
    } catch (e) {
      const msg = e.message || 'Erreur réseau'
      setError(msg)
      setMessages(prev => [...prev, { role: 'error', content: msg }])
    }
    setIsLoading(false)
  }

  const refreshBrief = async () => {
    if (!brief?.id) return
    setRefreshing(true)
    setError('')
    try {
      const res = await fetch(`${API}/opportunities/${brief.id}/refresh-json`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        const newJson = data.parsed_json || data.brief?.brief_json
        if (newJson) setBrief(prev => ({ ...prev, ...data.brief, brief_json: newJson }))
      } else {
        const e = await res.json().catch(() => ({}))
        setError(e.detail || `Erreur ${res.status}`)
      }
    } catch (e) {
      setError(e.message || 'Erreur réseau')
    }
    setRefreshing(false)
  }

  const handleBriefChange = useCallback((newJson) => {
    if (!brief?.id) return
    setBrief(prev => ({ ...prev, brief_json: newJson }))
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      setSaving(true)
      try {
        await fetch(`${API}/tickers/${ticker_id}/opportunities/${brief.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ brief_json: newJson }),
        })
      } catch {}
      setSaving(false)
    }, 1000)
  }, [brief?.id, ticker_id])

  const handleResume = async () => {
    const b = existingBrief
    setBrief(b)
    router.replace(`/ticker/${ticker_id}/opportunity/${b.id}`, undefined, { shallow: true })
    // Load messages
    const mRes = await fetch(`${API}/opportunities/${b.id}/messages`)
    if (mRes.ok) setMessages(await mRes.json())
    setShowExistingModal(false)
    setPageLoading(false)
  }

  const handleRestart = async () => {
    // Dismiss existing brief
    await fetch(`${API}/tickers/${ticker_id}/opportunities/${existingBrief.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'dismissed' }),
    }).catch(() => {})
    setShowExistingModal(false)
    setExistingBrief(null)
    setMessages([])
    setPageLoading(true)
    await createNewBrief()
    setPageLoading(false)
  }

  const launchThesis = async () => {
    if (!brief?.id) return
    try {
      const res = await fetch(`${API}/tickers/${ticker_id}/theses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ opportunity_id: brief.id }),
      })
      if (res.ok) {
        const data = await res.json()
        router.push(`/ticker/${ticker_id}/thesis/${data.id}`)
      }
    } catch {}
  }

  if (pageLoading) return <div className="text-center py-16 text-gray-500">Chargement…</div>

  const recommendation = brief?.brief_json?.verdict?.recommendation

  return (
    <div className="space-y-4">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <Link href="/portfolio" className="hover:text-gray-400">Portefeuille</Link>
        <span>/</span>
        <Link href={`/ticker/${ticker_id}`} className="hover:text-gray-400">{ticker_id}</Link>
        <span>/</span>
        <span className="text-gray-400">Opportunité</span>
        {saving && <span className="ml-2 text-xs text-gray-600">Sauvegarde…</span>}
        {error && <span className="ml-2 text-xs text-red-400">{error}</span>}
      </div>

      {showExistingModal && existingBrief && (
        <ExistingBriefModal
          brief={existingBrief}
          onResume={handleResume}
          onRestart={handleRestart}
        />
      )}

      {/* Main layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Col 1 — Chat */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl relative flex flex-col" style={{ height: '75vh' }}>
          <div className="px-4 py-3 border-b border-gray-800">
            <h2 className="font-semibold text-white text-sm">Chat — Opportunity Agent</h2>
          </div>
          {!agentSynced && <AgentSyncOverlay agentName="opportunity-agent" />}
          {messages.length === 0 && !isLoading && brief?.id && (
            <div className="flex flex-col items-center justify-center gap-3 py-8 px-6 border-b border-gray-800">
              <p className="text-gray-500 text-sm text-center">L&apos;analyse n&apos;a pas encore démarré.</p>
              <button
                onClick={() => sendInitialMessage(brief.id)}
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

        {/* Center button */}
        <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
          {/* Handled inline below on small screens */}
        </div>

        {/* Col 2 — Brief Editor */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl flex flex-col" style={{ height: '75vh' }}>
          <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
            <h2 className="font-semibold text-white text-sm">Investment Brief</h2>
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
                disabled={!brief?.id}
                className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-200 text-xs rounded-lg font-medium transition-colors"
              >
                Importer JSON
              </button>
              <button
                onClick={refreshBrief}
                disabled={refreshing || !brief?.id}
                className="px-3 py-1.5 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-xs rounded-lg font-medium transition-colors"
              >
                {refreshing ? '⟳ Actualisation…' : 'Actualiser le brief →'}
              </button>
            </div>
          </div>
          <div className="flex-1 min-h-0">
            <InvestmentBriefEditor
              briefJson={brief?.brief_json}
              onChange={handleBriefChange}
            />
          </div>
        </div>
      </div>

      {/* Bottom banner */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl px-5 py-4 flex items-center justify-between flex-wrap gap-3">
        <div>
          {recommendation === 'PROCEED' ? (
            <p className="text-emerald-300 text-sm font-medium">Recommandation PROCEED — la thèse approfondie peut être lancée</p>
          ) : recommendation === 'MONITOR' ? (
            <p className="text-indigo-300 text-sm font-medium">Recommandation MONITOR — définissez un seuil d&apos;entrée</p>
          ) : recommendation === 'PASS' ? (
            <p className="text-gray-500 text-sm">Recommandation PASS — analyse terminée</p>
          ) : (
            <p className="text-gray-600 text-sm">Actualisez le brief pour voir la recommandation</p>
          )}
        </div>
        <div className="flex gap-3">
          {recommendation === 'PROCEED' && (
            <button onClick={launchThesis}
              className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 text-white text-sm rounded-lg font-medium transition-colors">
              Lancer la thèse approfondie
            </button>
          )}
          <Link href={`/ticker/${ticker_id}`}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm rounded-lg font-medium transition-colors">
            Sauvegarder et revenir
          </Link>
        </div>
      </div>
    </div>
  )
}
