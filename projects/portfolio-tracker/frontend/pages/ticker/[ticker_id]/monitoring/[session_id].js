import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import AgentChat from '../../../../components/AgentChat'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const IMPACT_STATUS_STYLES = {
  REVIEW_REQUIRED: 'bg-orange-900/30 border-orange-700 text-orange-300',
  CRITICAL: 'bg-red-900/30 border-red-700 text-red-300',
  OK: 'bg-gray-900 border-gray-800 text-gray-400',
}

export default function MonitoringSessionPage() {
  const router = useRouter()
  const { ticker_id, session_id } = router.query

  const [session, setSession] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [error, setError] = useState('')
  const [calendarUpdates, setCalendarUpdates] = useState([])
  const [validatedUpdates, setValidatedUpdates] = useState(new Set())
  const [ignoredUpdates, setIgnoredUpdates] = useState(new Set())

  useEffect(() => {
    if (!session_id || !ticker_id) return
    const init = async () => {
      setPageLoading(true)
      try {
        const [sRes, mRes] = await Promise.all([
          fetch(`${API}/tickers/${ticker_id}/monitoring/${session_id}`),
          fetch(`${API}/tickers/${ticker_id}/monitoring/${session_id}/messages`),
        ])
        if (sRes.ok) {
          const s = await sRes.json()
          setSession(s)
          const calUpdates = s.result_json?.calendar_events_update || []
          setCalendarUpdates(Array.isArray(calUpdates) ? calUpdates : [])
        }
        if (mRes.ok) setMessages(await mRes.json())
      } catch (e) {
        setError('Erreur de chargement')
      }
      setPageLoading(false)
    }
    init()
  }, [session_id, ticker_id])

  const sendMessage = async (text) => {
    if (!session?.id) return
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setIsLoading(true)
    try {
      const res = await fetch(`${API}/tickers/${ticker_id}/monitoring/${session.id}/messages`, {
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

  const archiveSession = async () => {
    try {
      await fetch(`${API}/tickers/${ticker_id}/monitoring/${session.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'archived' }),
      })
      router.push(`/ticker/${ticker_id}`)
    } catch {}
  }

  const validateCalendarUpdate = async (update, idx) => {
    try {
      if (update.id) {
        await fetch(`${API}/calendar-v2/${update.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(update),
        })
      } else {
        await fetch(`${API}/calendar-v2`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...update, ticker_id }),
        })
      }
      setValidatedUpdates(prev => new Set([...prev, idx]))
    } catch {}
  }

  if (pageLoading) return <div className="text-center py-16 text-gray-500">Chargement…</div>
  if (!session) return <div className="text-center py-16 text-red-400">Session introuvable</div>

  const mode = session.mode || session.monitoring_mode || 2
  const resultJson = session.result_json || {}

  const impactStatus = resultJson.impact_status || resultJson.status
  const impactBannerClass = IMPACT_STATUS_STYLES[impactStatus] || ''

  return (
    <div className="space-y-4">
      {/* Breadcrumb + title */}
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <Link href="/portfolio" className="hover:text-gray-400">Portefeuille</Link>
        <span>/</span>
        <Link href={`/ticker/${ticker_id}`} className="hover:text-gray-400">{ticker_id}</Link>
        <span>/</span>
        <span className="text-gray-400">Monitoring</span>
      </div>

      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">
          {session.trigger_label || session.label || `Session #${session_id}`}
          <span className="ml-3 text-sm font-normal text-gray-500">Mode {mode}</span>
        </h1>
        <span className="text-xs text-gray-600">
          {session.created_at ? new Date(session.created_at).toLocaleDateString('fr-FR') : ''}
        </span>
      </div>

      {/* Impact banner */}
      {(impactStatus === 'REVIEW_REQUIRED' || impactStatus === 'CRITICAL') && (
        <div className={`border rounded-xl px-5 py-3 flex items-center justify-between ${impactBannerClass}`}>
          <span className="font-semibold">
            {impactStatus === 'CRITICAL' ? '🔴 ALERTE CRITIQUE' : '⚠️ RÉVISION REQUISE'}
            {resultJson.summary && <span className="font-normal ml-2">{resultJson.summary}</span>}
          </span>
          <Link href={`/ticker/${ticker_id}`} className="text-sm hover:opacity-80">
            Voir la fiche →
          </Link>
        </div>
      )}

      {error && <div className="bg-red-900/30 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">{error}</div>}

      {/* MODE 1 — Checklist */}
      {mode === 1 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-white mb-4">
            Checklist de lecture — {session.trigger_label}
          </h2>
          {(resultJson.checklist_items || []).length === 0 ? (
            <p className="text-gray-600 text-sm">Aucune checklist disponible — générez-en une via l&apos;agent</p>
          ) : (
            <div className="space-y-3">
              {(resultJson.checklist_items || []).map((item, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className="text-indigo-400 font-bold w-6 flex-shrink-0">{i + 1}</span>
                  <div className="flex-1">
                    <p className="text-gray-300 text-sm">{item.text || item}</p>
                    {item.signal && (
                      <p className={`text-xs mt-1 ${item.signal === 'confirmation' ? 'text-emerald-400' : 'text-red-400'}`}>
                        {item.signal === 'confirmation' ? '✓ Signal confirmation' : '✗ Signal alerte'} — {item.detail || ''}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
          <button onClick={archiveSession}
            className="mt-5 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm rounded-lg font-medium transition-colors">
            Archiver
          </button>
        </div>
      )}

      {/* MODE 5 — Routing */}
      {mode === 5 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-white mb-4">Suggestion de routage</h2>
          {resultJson.alert_summary && (
            <p className="text-gray-300 mb-3">{resultJson.alert_summary}</p>
          )}
          {resultJson.suggested_routing && (
            <p className="text-sm text-gray-400 mb-5">
              Recommandation : <span className="text-white font-medium">{resultJson.suggested_routing}</span>
            </p>
          )}
          <div className="flex gap-3">
            <Link href={`/ticker/${ticker_id}/monitoring/new?mode=3`}
              className="px-4 py-2 bg-orange-700 hover:bg-orange-600 text-white text-sm rounded-lg font-medium transition-colors">
              Ouvrir en Régime 3
            </Link>
            <Link href={`/ticker/${ticker_id}/opportunity/new?source=monitoring_reroute`}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm rounded-lg font-medium transition-colors">
              Relancer analyse fresh
            </Link>
          </div>
        </div>
      )}

      {/* MODES 2, 3, 4 — Two columns */}
      {[2, 3, 4].includes(mode) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" style={{ minHeight: '60vh' }}>
          {/* Col 1 — Chat */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl flex flex-col" style={{ minHeight: '500px' }}>
            <div className="px-4 py-3 border-b border-gray-800">
              <h2 className="font-semibold text-white text-sm">Chat — Monitoring Agent</h2>
            </div>
            <div className="flex-1 min-h-0">
              <AgentChat
                messages={messages}
                onSend={sendMessage}
                isLoading={isLoading}
              />
            </div>
          </div>

          {/* Col 2 — Impact thèse */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="font-semibold text-white mb-4">Impact sur la thèse</h2>
            {!resultJson.hypotheses_status ? (
              <p className="text-gray-600 text-sm">Envoyez un message à l&apos;agent pour analyser l&apos;impact</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(resultJson.hypotheses_status).map(([hId, status]) => (
                  <div key={hId} className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2">
                    <span className="text-sm font-medium text-indigo-400">{hId}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      status === 'confirmed' ? 'bg-emerald-900/50 text-emerald-300' :
                      status === 'challenged' ? 'bg-amber-900/50 text-amber-300' :
                      status === 'invalidated' ? 'bg-red-900/50 text-red-300' :
                      'bg-gray-700 text-gray-400'
                    }`}>{status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Calendar updates (Modes 2, 3, 4) */}
      {[2, 3, 4].includes(mode) && calendarUpdates.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="font-semibold text-white mb-4">Mises à jour calendrier proposées</h3>
          <div className="space-y-2">
            {calendarUpdates.map((update, i) => (
              <div key={i} className={`flex items-center justify-between border rounded-lg px-4 py-3 ${
                validatedUpdates.has(i) ? 'bg-emerald-950/20 border-emerald-800' :
                ignoredUpdates.has(i) ? 'bg-gray-800/50 border-gray-700 opacity-50' :
                'bg-gray-800 border-gray-700'
              }`}>
                <div className="text-sm">
                  <span className="text-white">{update.label || update.event_type}</span>
                  {update.event_date && (
                    <span className="text-gray-500 ml-2 text-xs">
                      {new Date(update.event_date).toLocaleDateString('fr-FR')}
                    </span>
                  )}
                  {update.action && (
                    <span className="ml-2 text-xs text-indigo-400">[{update.action}]</span>
                  )}
                </div>
                {!validatedUpdates.has(i) && !ignoredUpdates.has(i) && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => validateCalendarUpdate(update, i)}
                      className="text-xs bg-emerald-700 hover:bg-emerald-600 text-white px-3 py-1 rounded transition-colors"
                    >✓ Valider</button>
                    <button
                      onClick={() => setIgnoredUpdates(prev => new Set([...prev, i]))}
                      className="text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 px-3 py-1 rounded transition-colors"
                    >✗ Ignorer</button>
                  </div>
                )}
                {validatedUpdates.has(i) && <span className="text-emerald-400 text-xs">Validé</span>}
                {ignoredUpdates.has(i) && <span className="text-gray-600 text-xs">Ignoré</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
