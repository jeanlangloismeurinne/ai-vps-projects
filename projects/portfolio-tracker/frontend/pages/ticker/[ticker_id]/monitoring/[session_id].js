import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import AgentChat from '../../../../components/AgentChat'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const STATUS_STYLES = {
  confirmed:  'bg-emerald-900/50 text-emerald-300',
  neutral:    'bg-gray-700 text-gray-400',
  alert:      'bg-amber-900/50 text-amber-300',
  invalidated:'bg-red-900/50 text-red-300',
  unverified: 'bg-gray-800 text-gray-500',
}

const DECISION_STYLES = {
  reinforce:  'bg-emerald-700 text-white',
  maintain:   'bg-gray-600 text-white',
  reduce_25:  'bg-amber-700 text-white',
  reduce_50:  'bg-orange-700 text-white',
  exit:       'bg-red-700 text-white',
}

export default function MonitoringSessionPage() {
  const router = useRouter()
  const { ticker_id, session_id } = router.query

  const [session, setSession] = useState(null)
  const [messages, setMessages] = useState([])
  const [linkedSessions, setLinkedSessions] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [error, setError] = useState('')
  const [calendarUpdates, setCalendarUpdates] = useState([])
  const [validatedUpdates, setValidatedUpdates] = useState(new Set())
  const [ignoredUpdates, setIgnoredUpdates] = useState(new Set())
  const [launchingMode, setLaunchingMode] = useState(null)

  useEffect(() => {
    if (!session_id || !ticker_id) return
    const init = async () => {
      setPageLoading(true)
      try {
        const [sRes, mRes] = await Promise.all([
          fetch(`${API}/tickers/${ticker_id}/monitoring/${session_id}`),
          fetch(`${API}/monitoring/${session_id}/messages`),
        ])
        if (sRes.ok) {
          const s = await sRes.json()
          setSession(s)
          setCalendarUpdates(
            Array.isArray(s.result_json?.calendar_events_update)
              ? s.result_json.calendar_events_update
              : []
          )
          if (s.calendar_event_id) {
            const lRes = await fetch(`${API}/calendar-v2/${s.calendar_event_id}/sessions`)
            if (lRes.ok) setLinkedSessions(await lRes.json())
          }
        }
        if (mRes.ok) setMessages(await mRes.json())
      } catch {
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
      const res = await fetch(`${API}/tickers/${ticker_id}/monitoring/${session.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content: text }),
      })
      if (res.ok) {
        const data = await res.json()
        setMessages(prev => [...prev, { role: 'assistant', content: data.content || '' }])
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

  const launchMode = async (mode) => {
    setLaunchingMode(mode)
    try {
      const res = await fetch(`${API}/tickers/${ticker_id}/monitoring`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trigger_type: 'manual',
          trigger_label: `Mode ${mode} — ${session.trigger_label || ''}`,
          mode,
          thesis_id: session.thesis_id || null,
          calendar_event_id: session.calendar_event_id || null,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        router.push(`/ticker/${ticker_id}/monitoring/${data.session.id}`)
      }
    } catch {}
    setLaunchingMode(null)
  }

  const validateCalendarUpdate = async (update, idx) => {
    try {
      if (update.id) {
        await fetch(`${API}/calendar-v2/${update.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            label: update.label,
            scheduled_date: update.scheduled_date,
            monitoring_mode: update.monitoring_mode,
          }),
        })
      } else {
        await fetch(`${API}/calendar-v2`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ticker_id,
            event_type: update.event_type,
            label: update.label,
            scheduled_date: update.scheduled_date,
            monitoring_mode: update.monitoring_mode,
            thesis_id: session?.thesis_id || null,
          }),
        })
      }
      setValidatedUpdates(prev => new Set([...prev, idx]))
    } catch {}
  }

  if (pageLoading) return <div className="text-center py-16 text-gray-500">Chargement…</div>
  if (!session) return <div className="text-center py-16 text-red-400">Session introuvable</div>

  const mode = session.mode || session.monitoring_mode || 2
  const result = session.result_json || {}
  const alertLevel = session.alert_level || result.alert_level || result.flag
  const linkedMode1 = linkedSessions.find(s => s.mode === 1)

  return (
    <div className="space-y-4">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <Link href="/portfolio" className="hover:text-gray-400">Portefeuille</Link>
        <span>/</span>
        <Link href={`/ticker/${ticker_id}`} className="hover:text-gray-400">{ticker_id}</Link>
        <span>/</span>
        <span className="text-gray-400">Monitoring</span>
      </div>

      {/* Title */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h1 className="text-xl font-bold text-white truncate">{session.trigger_label || `Session #${session_id}`}</h1>
          <span className="text-sm text-gray-500">Mode {mode}</span>
        </div>
        <span className="text-xs text-gray-600 flex-shrink-0">
          {session.created_at ? new Date(session.created_at).toLocaleDateString('fr-FR') : ''}
        </span>
      </div>

      {/* Pending manual upload banner */}
      {session.status === 'pending_manual' && (
        <PendingManualUpload
          tickerId={ticker_id}
          sessionId={session_id}
          onSuccess={(updatedSession) => {
            setSession(updatedSession)
            setCalendarUpdates(
              Array.isArray(updatedSession.result_json?.calendar_events_update)
                ? updatedSession.result_json.calendar_events_update
                : []
            )
          }}
        />
      )}

      {/* Alert banner */}
      {(alertLevel === 'REVIEW_REQUIRED' || alertLevel === 'CRITICAL') && (
        <div className={`border rounded-xl px-5 py-3 flex items-center justify-between ${
          alertLevel === 'CRITICAL'
            ? 'bg-red-900/30 border-red-700 text-red-300'
            : 'bg-orange-900/30 border-orange-700 text-orange-300'
        }`}>
          <span className="font-semibold">
            {alertLevel === 'CRITICAL' ? '🔴 ALERTE CRITIQUE' : '⚠️ RÉVISION REQUISE'}
          </span>
        </div>
      )}

      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* ── MODE 1 — Checklist pré-event ─────────────────────────────────── */}
      {mode === 1 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-white mb-4">
            Checklist de lecture — {session.trigger_label}
          </h2>
          {(result.checklist_items || []).length === 0 ? (
            <p className="text-gray-600 text-sm">Aucune checklist disponible</p>
          ) : (
            <div className="space-y-3">
              {result.checklist_items.map((item, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className="text-indigo-400 font-bold w-6 flex-shrink-0">{i + 1}</span>
                  <div className="flex-1">
                    <p className="text-gray-300 text-sm">{item.text || item}</p>
                    {item.signal && (
                      <p className={`text-xs mt-1 ${
                        item.signal === 'confirmation' ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {item.signal === 'confirmation' ? '✓ Signal confirmation' : '✗ Signal alerte'}
                        {item.detail ? ` — ${item.detail}` : ''}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
          <button
            onClick={archiveSession}
            className="mt-5 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm rounded-lg font-medium transition-colors"
          >
            Archiver
          </button>
        </div>
      )}

      {/* ── MODE 2 — Revue trimestrielle ─────────────────────────────────── */}
      {mode === 2 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Col gauche — Checklist J-2 liée */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="font-semibold text-white mb-4 text-sm">Checklist J-2 liée</h2>
            {linkedMode1 ? (
              (linkedMode1.result_json?.checklist_items || []).length === 0 ? (
                <p className="text-gray-600 text-sm">Aucun item dans le pré-event brief</p>
              ) : (
                <div className="space-y-3">
                  {linkedMode1.result_json.checklist_items.map((item, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <span className="text-indigo-400 font-bold w-5 flex-shrink-0 text-sm">{i + 1}</span>
                      <div className="flex-1">
                        <p className="text-gray-300 text-sm">{item.text || item}</p>
                        {item.signal && (
                          <p className={`text-xs mt-0.5 ${
                            item.signal === 'confirmation' ? 'text-emerald-400' : 'text-red-400'
                          }`}>
                            {item.signal === 'confirmation' ? '✓' : '✗'} {item.detail || ''}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : (
              <p className="text-gray-600 text-sm">Aucun pré-event brief lié à cet événement</p>
            )}
          </div>

          {/* Col droite — Hypothèses */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="font-semibold text-white mb-4 text-sm">Hypothèses post-monitoring</h2>
            <HypothesesReviewed hypotheses={result.hypotheses_reviewed} />
            <HypothesesSummary hypotheses={result.hypotheses_reviewed} alertLevel={alertLevel} />
            <div className="mt-4 flex gap-3">
              {alertLevel === 'REVIEW_REQUIRED' && (
                <button
                  onClick={() => launchMode(5)}
                  disabled={launchingMode === 5}
                  className="px-4 py-2 bg-orange-700 hover:bg-orange-600 text-white text-sm rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  {launchingMode === 5 ? 'Lancement…' : 'Lancer Mode 5 — Routing'}
                </button>
              )}
              {alertLevel === 'CRITICAL' && (
                <button
                  onClick={() => launchMode(3)}
                  disabled={launchingMode === 3}
                  className="px-4 py-2 bg-red-700 hover:bg-red-600 text-white text-sm rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  {launchingMode === 3 ? 'Lancement…' : 'Lancer Mode 3 — Décision Review'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Valorisation non cotée mise à jour (Mode 2 / company private) ── */}
      {result.private_valuation_update && (
        <div className="bg-gray-900 border border-indigo-800 rounded-xl p-5">
          <h2 className="font-semibold text-indigo-300 text-sm mb-4">Mise à jour valorisation — Société non cotée</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
            {result.private_valuation_update.last_valuation_m != null && (
              <div>
                <p className="text-gray-500 text-xs mb-1">Valorisation</p>
                <p className="text-white font-semibold">{result.private_valuation_update.last_valuation_m} M€</p>
                {result.private_valuation_update.last_valuation_basis && (
                  <p className="text-gray-500 text-xs">{result.private_valuation_update.last_valuation_basis}</p>
                )}
              </div>
            )}
            {result.private_valuation_update.last_valuation_date && (
              <div>
                <p className="text-gray-500 text-xs mb-1">Date valorisation</p>
                <p className="text-white">{new Date(result.private_valuation_update.last_valuation_date).toLocaleDateString('fr-FR')}</p>
              </div>
            )}
            {result.private_valuation_update.current_ownership_pct != null && (
              <div>
                <p className="text-gray-500 text-xs mb-1">Participation actuelle</p>
                <p className="text-white font-semibold">{result.private_valuation_update.current_ownership_pct}%</p>
              </div>
            )}
            {result.private_valuation_update.projected_valuation_next_event_m != null && (
              <div>
                <p className="text-gray-500 text-xs mb-1">Val. projetée prochain event</p>
                <p className="text-white font-semibold">{result.private_valuation_update.projected_valuation_next_event_m} M€</p>
              </div>
            )}
            {result.private_valuation_update.next_event_date && (
              <div>
                <p className="text-gray-500 text-xs mb-1">Prochain événement</p>
                <p className="text-white">{new Date(result.private_valuation_update.next_event_date).toLocaleDateString('fr-FR')}</p>
                {result.private_valuation_update.next_event_type && (
                  <p className="text-gray-500 text-xs">{result.private_valuation_update.next_event_type}</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── MODE 3 — Décision Review ──────────────────────────────────────── */}
      {mode === 3 && (
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl divide-y divide-gray-800">
            {/* Diagnostic */}
            <div className="p-5">
              <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Diagnostic</h2>
              {result.diagnostic && (
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-bold mb-2 ${
                  result.diagnostic === 'structural'
                    ? 'bg-red-900/40 text-red-300'
                    : 'bg-amber-900/40 text-amber-300'
                }`}>
                  {result.diagnostic === 'structural' ? 'STRUCTUREL' : 'CONJONCTUREL'}
                </span>
              )}
              {result.diagnostic_detail && (
                <p className="text-gray-300 text-sm mt-1">{result.diagnostic_detail}</p>
              )}
            </div>

            {/* Conviction */}
            <div className="p-5">
              <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Conviction révisée</h2>
              <span className="text-2xl font-bold text-white">
                {result.revised_conviction ?? '—'}
                <span className="text-sm font-normal text-gray-500">/10</span>
              </span>
            </div>

            {/* Munger test */}
            {result.munger_test_conclusion && (
              <div className="p-5">
                <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Test de Munger</h2>
                <p className="text-gray-300 text-sm">{result.munger_test_conclusion}</p>
              </div>
            )}

            {/* Décision */}
            {result.decision && (
              <div className="p-5">
                <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Décision</h2>
                <span className={`inline-block px-4 py-1.5 rounded-lg text-sm font-bold uppercase ${
                  DECISION_STYLES[result.decision] || 'bg-gray-700 text-white'
                }`}>
                  {result.decision.replace('_', ' ')}
                </span>
              </div>
            )}
          </div>

          {/* Hypothèses */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="font-semibold text-white mb-4 text-sm">Hypothèses</h2>
            <HypothesesReviewed hypotheses={result.hypotheses_reviewed} />
            <HypothesesSummary hypotheses={result.hypotheses_reviewed} alertLevel={alertLevel} />
          </div>
        </div>
      )}

      {/* ── MODE 4 — Sector Pulse ─────────────────────────────────────────── */}
      {mode === 4 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-5">
          {/* Score */}
          <div>
            <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Score sectoriel</h2>
            {session.trigger_label && (
              <p className="text-xs text-gray-500 mb-2">Pair : {result.peer_ticker || ''}</p>
            )}
            <SectorScoreGauge score={result.sector_health_score} />
            {result.sector_observations && (
              <p className="text-gray-300 text-sm mt-3">{result.sector_observations}</p>
            )}
          </div>

          {/* Impact par hypothèse */}
          {(result.hypothesis_impacts || []).length > 0 && (
            <div>
              <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Impact par hypothèse</h2>
              <div className="space-y-2">
                {result.hypothesis_impacts.map((hi, i) => (
                  <div key={i} className="flex items-start gap-3 bg-gray-800 rounded-lg px-3 py-2">
                    <span className="text-indigo-400 font-bold text-sm w-8 flex-shrink-0">
                      {hi.hypothesis_id || hi.id}
                    </span>
                    <span className={`text-sm flex-shrink-0 ${
                      hi.impact_direction === 'positive' ? 'text-emerald-400' :
                      hi.impact_direction === 'negative' ? 'text-red-400' : 'text-gray-400'
                    }`}>
                      {hi.impact_direction === 'positive' ? '↑' : hi.impact_direction === 'negative' ? '↓' : '→'}
                    </span>
                    <p className="text-gray-300 text-sm">{hi.observation}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action */}
          <div>
            <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Action</h2>
            {result.action === 'escalate_to_regime3' ? (
              <div className="flex items-center gap-4">
                <span className="text-orange-400 font-semibold text-sm">ESCALADE → RÉGIME 3</span>
                <button
                  onClick={() => launchMode(3)}
                  disabled={launchingMode === 3}
                  className="px-4 py-2 bg-orange-700 hover:bg-orange-600 text-white text-sm rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  {launchingMode === 3 ? 'Lancement…' : 'Lancer Mode 3'}
                </button>
              </div>
            ) : (
              <span className="text-gray-400 text-sm">STORE — Score en mémoire</span>
            )}
          </div>
        </div>
      )}

      {/* ── MODE 5 — Routing d'alerte ─────────────────────────────────────── */}
      {mode === 5 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-white mb-4">Suggestion de routage</h2>
          {result.alert_summary && (
            <p className="text-gray-300 mb-3">{result.alert_summary}</p>
          )}
          {result.rationale && (
            <p className="text-sm text-gray-400 mb-5">{result.rationale}</p>
          )}
          {result.routing_suggestion && (
            <p className="text-xs text-gray-500 mb-5">
              Recommandation :{' '}
              <span className="text-white font-medium">{result.routing_suggestion}</span>
            </p>
          )}
          <div className="flex gap-3">
            <button
              onClick={() => launchMode(3)}
              disabled={launchingMode === 3}
              className="px-4 py-2 bg-orange-700 hover:bg-orange-600 text-white text-sm rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              {launchingMode === 3 ? 'Lancement…' : 'Décision Review — Mode 3'}
            </button>
            <Link
              href={`/ticker/${ticker_id}/opportunity/new?source=monitoring_reroute`}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm rounded-lg font-medium transition-colors"
            >
              Relancer analyse fresh
            </Link>
          </div>
        </div>
      )}

      {/* ── Calendar updates (Modes 2/3/4) ───────────────────────────────── */}
      {[2, 3, 4].includes(mode) && calendarUpdates.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="font-semibold text-white mb-4 text-sm">Mises à jour calendrier proposées</h3>
          <div className="space-y-2">
            {calendarUpdates.map((update, i) => (
              <div key={i} className={`flex items-start gap-3 border rounded-lg px-4 py-3 ${
                validatedUpdates.has(i) ? 'bg-emerald-950/20 border-emerald-800' :
                ignoredUpdates.has(i) ? 'bg-gray-800/50 border-gray-700 opacity-50' :
                'bg-gray-800 border-gray-700'
              }`}>
                <div className="text-sm min-w-0 flex-1">
                  <span className="text-white break-words">{update.label || update.event_type}</span>
                  {(update.scheduled_date || update.event_date) && (
                    <span className="text-gray-500 ml-2 text-xs">
                      {new Date(update.scheduled_date || update.event_date).toLocaleDateString('fr-FR')}
                    </span>
                  )}
                  {update.action && (
                    <span className="ml-1 text-xs text-indigo-400 whitespace-nowrap">[{update.action}]</span>
                  )}
                </div>
                <div className="flex-shrink-0 flex items-center gap-2 mt-0.5">
                  {!validatedUpdates.has(i) && !ignoredUpdates.has(i) && (
                    <>
                      <button
                        onClick={() => validateCalendarUpdate(update, i)}
                        className="text-xs bg-emerald-700 hover:bg-emerald-600 text-white px-3 py-1 rounded transition-colors"
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => setIgnoredUpdates(prev => new Set([...prev, i]))}
                        className="text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 px-3 py-1 rounded transition-colors"
                      >
                        ✗
                      </button>
                    </>
                  )}
                  {validatedUpdates.has(i) && <span className="text-emerald-400 text-xs">✓</span>}
                  {ignoredUpdates.has(i) && <span className="text-gray-600 text-xs">✗</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Chat agent (tous modes) ───────────────────────────────────────── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl" style={{ minHeight: '400px' }}>
        <div className="px-4 py-3 border-b border-gray-800">
          <h2 className="font-semibold text-white text-sm">Chat — Monitoring Agent</h2>
        </div>
        <div style={{ minHeight: '350px' }}>
          <AgentChat messages={messages} onSend={sendMessage} isLoading={isLoading} />
        </div>
      </div>
    </div>
  )
}

// ── Composants internes ──────────────────────────────────────────────────────

function HypothesesReviewed({ hypotheses }) {
  if (!hypotheses || hypotheses.length === 0) {
    return <p className="text-gray-600 text-sm">Aucune hypothèse analysée</p>
  }
  return (
    <div className="space-y-3">
      {hypotheses.map((h, i) => (
        <div key={i} className="bg-gray-800 rounded-lg px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-indigo-400 font-bold text-sm">{h.id}</span>
            {h.weight && <span className="text-gray-500 text-xs uppercase">{h.weight}</span>}
            <span className={`ml-auto text-xs px-2 py-0.5 rounded font-medium ${
              STATUS_STYLES[h.status] || STATUS_STYLES.unverified
            }`}>
              {(h.status || 'unverified').toUpperCase()}
            </span>
          </div>
          {h.text && <p className="text-gray-300 text-sm mb-1">Énoncé : {h.text}</p>}
          <p className="text-xs text-gray-500">
            {h.kpi_metric && `KPI : ${h.kpi_metric}`}
            {h.alert_threshold && typeof h.alert_threshold === 'object' && Object.keys(h.alert_threshold).length > 0
              ? ` | Seuil alerte : ${JSON.stringify(h.alert_threshold)}`
              : ''}
          </p>
          {h.observation && (
            <p className="text-gray-400 text-sm mt-1 italic">{h.observation}</p>
          )}
        </div>
      ))}
    </div>
  )
}

function HypothesesSummary({ hypotheses, alertLevel }) {
  if (!hypotheses || hypotheses.length === 0) return null
  const counts = { confirmed: 0, neutral: 0, alert: 0, invalidated: 0 }
  for (const h of hypotheses) {
    if (h.status in counts) counts[h.status]++
  }
  return (
    <div className="mt-3 flex items-center gap-3 text-xs flex-wrap">
      {counts.confirmed > 0 && <span className="text-emerald-400">{counts.confirmed} confirmée{counts.confirmed > 1 ? 's' : ''}</span>}
      {counts.neutral > 0 && <span className="text-gray-400">{counts.neutral} neutre{counts.neutral > 1 ? 's' : ''}</span>}
      {counts.alert > 0 && <span className="text-amber-400">{counts.alert} en alerte</span>}
      {counts.invalidated > 0 && <span className="text-red-400">{counts.invalidated} invalidée{counts.invalidated > 1 ? 's' : ''}</span>}
      {alertLevel && (
        <span className={`ml-auto px-2 py-0.5 rounded font-bold ${
          alertLevel === 'CRITICAL' ? 'bg-red-900/50 text-red-300' :
          alertLevel === 'REVIEW_REQUIRED' ? 'bg-orange-900/50 text-orange-300' :
          'bg-emerald-900/50 text-emerald-300'
        }`}>
          {alertLevel}
        </span>
      )}
    </div>
  )
}

function PendingManualUpload({ tickerId, sessionId, onSuccess }) {
  const [jsonText, setJsonText] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef(null)

  const submitParsed = async (parsed) => {
    setUploading(true)
    try {
      const res = await fetch(
        `${API}/tickers/${tickerId}/monitoring/${sessionId}/upload-result`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ result_json: parsed }),
        }
      )
      if (res.ok) {
        const data = await res.json()
        onSuccess(data.session)
      } else {
        const err = await res.json().catch(() => ({}))
        setError(err.detail || 'Erreur lors de l\'upload')
      }
    } catch {
      setError('Erreur réseau')
    }
    setUploading(false)
  }

  const parseJsonText = (text) => {
    const match = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/)
    return JSON.parse(match ? match[1] : text)
  }

  const handleFileImport = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setError('')
    try {
      const parsed = parseJsonText(await file.text())
      await submitParsed(parsed)
    } catch {
      setError('Fichier JSON invalide')
    }
  }

  const handleSubmitText = async () => {
    setError('')
    try {
      const parsed = parseJsonText(jsonText)
      await submitParsed(parsed)
    } catch {
      setError('JSON invalide — vérifiez le format')
    }
  }

  return (
    <div className="bg-amber-950/20 border border-amber-700/50 rounded-xl p-5">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-start gap-3">
          <span className="text-amber-400 text-lg flex-shrink-0">⏳</span>
          <div>
            <h2 className="font-semibold text-amber-300 text-sm">Session en attente — résultat Dust à uploader</h2>
            <p className="text-xs text-amber-700/80 mt-0.5">
              Lancez l&apos;analyse dans Dust avec le contexte reçu par Slack, puis importez le JSON résultat.
            </p>
          </div>
        </div>
        <div className="flex-shrink-0">
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={handleFileImport}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="px-3 py-1.5 bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-white text-xs rounded-lg font-medium transition-colors"
          >
            Importer JSON
          </button>
        </div>
      </div>
      <textarea
        value={jsonText}
        onChange={e => setJsonText(e.target.value)}
        placeholder={'Ou collez directement le JSON renvoyé par Dust…\n\nAccepte les deux formats :\n  ```json\n  { … }\n  ```\nou le JSON brut.'}
        rows={8}
        className="w-full bg-gray-900 border border-gray-700 text-gray-300 text-xs font-mono rounded-lg px-3 py-2.5 focus:border-amber-600 focus:outline-none resize-y"
      />
      {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
      <button
        onClick={handleSubmitText}
        disabled={uploading || !jsonText.trim()}
        className="mt-3 px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-200 text-sm rounded-lg font-medium transition-colors"
      >
        {uploading ? 'Upload en cours…' : 'Soumettre le texte collé'}
      </button>
    </div>
  )
}

function SectorScoreGauge({ score }) {
  const s = typeof score === 'number' ? score : 0
  const pct = ((s + 5) / 10) * 100
  const color = s >= 3 ? '#10b981' : s >= 0 ? '#6b7280' : s >= -2 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-white font-bold text-sm w-12 text-right">
        {score !== null && score !== undefined ? `${score > 0 ? '+' : ''}${score}` : '—'}
        <span className="text-gray-500 font-normal">/5</span>
      </span>
    </div>
  )
}
