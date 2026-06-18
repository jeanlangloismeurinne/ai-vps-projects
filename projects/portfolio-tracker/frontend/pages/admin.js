import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const AGENT_LABELS = {
  'opportunity-agent': { label: 'Opportunity Agent', desc: 'Analyse d\'opportunité — Pages 3 & Débat', modes: 'freeform · json_generation · conviction_challenge' },
  'thesis-agent':      { label: 'Thesis Agent',      desc: 'Construction de thèse — Page 4',         modes: 'freeform · json_generation' },
  'monitoring-agent':  { label: 'Monitoring Agent',  desc: 'Suivi de thèse — Page 5',                modes: 'modes 1→5' },
}

function AgentCard({ agent, onSync, onUpdate }) {
  // L'API retourne agent_name et prompt_text — on normalise ici
  const name = agent.agent_name
  const promptText = agent.prompt_text || ''
  const meta = AGENT_LABELS[name] || { label: name, desc: '', modes: '' }

  const [showPrompt, setShowPrompt] = useState(false)
  const [dustId, setDustId] = useState(agent.dust_agent_id || '')
  const [editingId, setEditingId] = useState(false)
  const [copied, setCopied] = useState(false)

  const copyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(promptText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }

  const saveId = async () => {
    await onUpdate(name, { dust_agent_id: dustId })
    setEditingId(false)
  }

  const needsDustId = !agent.dust_agent_id

  return (
    <div className={`bg-gray-900 border rounded-xl overflow-hidden ${agent.synced ? 'border-gray-800' : 'border-amber-700'}`}>

      {/* Header */}
      <div className="flex items-start justify-between p-5">
        <div>
          <h3 className="font-semibold text-white">{meta.label}</h3>
          <p className="text-xs text-gray-500 mt-0.5">{meta.desc}</p>
          <p className="text-xs text-gray-700 mt-0.5 font-mono">{meta.modes}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-4">
          <span className="text-xs text-gray-600 font-mono">v{agent.version}</span>
          <span className={`text-xs px-2 py-0.5 rounded border font-medium ${
            agent.synced
              ? 'bg-emerald-900/50 text-emerald-300 border-emerald-700'
              : 'bg-amber-900/50 text-amber-300 border-amber-700'
          }`}>
            {agent.synced ? '✓ Synchronisé' : '⚠️ Hors sync'}
          </span>
        </div>
      </div>

      {/* Dust Agent ID — zone principale */}
      <div className={`mx-5 mb-4 rounded-lg border p-4 ${needsDustId ? 'border-amber-700/50 bg-amber-950/20' : 'border-gray-800 bg-gray-800/50'}`}>
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-medium text-gray-400">
            ID de l&apos;agent Dust
            {needsDustId && <span className="ml-2 text-amber-400">— à renseigner</span>}
          </label>
          {agent.last_synced_at && (
            <span className="text-xs text-gray-600">
              Sync {new Date(agent.last_synced_at).toLocaleDateString('fr-FR')}
            </span>
          )}
        </div>
        {editingId ? (
          <div className="flex gap-2">
            <input
              value={dustId}
              onChange={e => setDustId(e.target.value)}
              placeholder="ex: eAYsKqZ1D2"
              autoFocus
              className="flex-1 bg-gray-900 border border-gray-600 text-white text-sm rounded px-3 py-1.5 font-mono focus:border-indigo-500 focus:outline-none placeholder-gray-700"
            />
            <button onClick={saveId}
              className="text-xs bg-indigo-700 hover:bg-indigo-600 text-white px-3 py-1.5 rounded transition-colors font-medium">
              Sauvegarder
            </button>
            <button onClick={() => { setDustId(agent.dust_agent_id || ''); setEditingId(false) }}
              className="text-xs text-gray-500 hover:text-gray-300 px-2">
              Annuler
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            {agent.dust_agent_id
              ? <span className="text-sm font-mono text-indigo-400">{agent.dust_agent_id}</span>
              : <span className="text-sm font-mono text-gray-700 italic">non configuré</span>
            }
            <button onClick={() => setEditingId(true)}
              className="text-xs text-gray-600 hover:text-gray-400 transition-colors underline underline-offset-2">
              Éditer
            </button>
          </div>
        )}
      </div>

      {/* Prompt — dropdown */}
      <div className="mx-5 mb-4">
        <button
          onClick={() => setShowPrompt(v => !v)}
          className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-300 transition-colors w-full text-left"
        >
          <span className={`transition-transform duration-200 ${showPrompt ? 'rotate-90' : ''}`}>▶</span>
          <span>Prompt système ({promptText.split('\n').length} lignes)</span>
          {showPrompt && (
            <button
              onClick={e => { e.stopPropagation(); copyPrompt() }}
              className="ml-auto text-xs text-gray-600 hover:text-gray-400 transition-colors"
            >
              {copied ? '✓ Copié !' : 'Copier'}
            </button>
          )}
        </button>
        {showPrompt && (
          <div className="mt-2 bg-gray-800 border border-gray-700 rounded-lg overflow-auto max-h-96">
            <pre className="font-mono text-xs text-gray-400 p-3 whitespace-pre-wrap leading-relaxed">
              {promptText.split('\n').map((line, i) => (
                <span key={i} className="flex">
                  <span className="text-gray-700 select-none mr-3 min-w-[2.5rem] text-right flex-shrink-0">{i + 1}</span>
                  <span>{line}</span>
                </span>
              ))}
            </pre>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 px-5 pb-5">
        {!agent.synced && (
          <button onClick={() => onSync(name)}
            className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 text-white text-xs rounded-lg font-medium transition-colors">
            ✓ Marquer synchronisé
          </button>
        )}
        {agent.dust_agent_url && (
          <a href={agent.dust_agent_url} target="_blank" rel="noopener noreferrer"
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs rounded-lg font-medium transition-colors">
            Ouvrir dans Dust →
          </a>
        )}
      </div>
    </div>
  )
}

function DustAutoToggle({ enabled, onChange }) {
  const [loading, setLoading] = useState(false)

  const toggle = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API}/admin/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dust_auto_enabled: !enabled }),
      })
      if (res.ok) onChange(!enabled)
    } catch {}
    setLoading(false)
  }

  return (
    <div className={`border rounded-xl p-5 flex items-center justify-between ${
      enabled ? 'bg-gray-900 border-gray-800' : 'bg-amber-950/20 border-amber-700/50'
    }`}>
      <div>
        <h3 className="font-semibold text-white text-sm">Mode automatique Dust</h3>
        <p className="text-xs text-gray-500 mt-0.5 max-w-lg">
          {enabled
            ? 'Les agents Dust sont appelés automatiquement lors des événements de monitoring.'
            : 'Mode manuel — les événements envoient 2 notifications Slack : le lien vers la session et le contexte à coller dans Dust.'}
        </p>
      </div>
      <button
        onClick={toggle}
        disabled={loading}
        className={`relative ml-6 flex-shrink-0 w-12 h-6 rounded-full transition-colors duration-200 ${
          enabled ? 'bg-emerald-600' : 'bg-gray-600'
        } ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200 ${
          enabled ? 'translate-x-6' : 'translate-x-0'
        }`} />
      </button>
    </div>
  )
}

function PingButton({ label, endpoint }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  const ping = async () => {
    setLoading(true)
    setStatus(null)
    try {
      const start = Date.now()
      const res = await fetch(`${API}/admin/ping/${endpoint}`)
      const elapsed = Date.now() - start
      setStatus(res.ok ? `✓ OK (${elapsed}ms)` : `✗ Erreur ${res.status}`)
    } catch {
      setStatus('✗ Connexion échouée')
    }
    setLoading(false)
  }

  return (
    <div className="flex items-center justify-between bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
      <span className="text-sm text-gray-300">{label}</span>
      <div className="flex items-center gap-3">
        {status && <span className={`text-xs ${status.startsWith('✓') ? 'text-emerald-400' : 'text-red-400'}`}>{status}</span>}
        <button onClick={ping} disabled={loading}
          className="text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-300 px-3 py-1 rounded transition-colors">
          {loading ? '…' : 'Test ping'}
        </button>
      </div>
    </div>
  )
}

export default function AdminPage() {
  const [agents, setAgents] = useState([])
  const [status, setStatus] = useState(null)
  const [calendarEvents, setCalendarEvents] = useState([])
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeSection, setActiveSection] = useState('agents')
  const [error, setError] = useState('')
  const [dustAutoEnabled, setDustAutoEnabled] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const [agRes, stRes, settingsRes] = await Promise.all([
        fetch(`${API}/admin/agents`),
        fetch(`${API}/admin/status`),
        fetch(`${API}/admin/settings`),
      ])
      if (agRes.ok) setAgents(await agRes.json())
      if (stRes.ok) setStatus(await stRes.json())
      if (settingsRes.ok) {
        const s = await settingsRes.json()
        setDustAutoEnabled(s.dust_auto_enabled ?? true)
      }
    } catch {
      setError('Erreur de chargement')
    }
    setLoading(false)
  }

  const loadCalendar = async () => {
    const res = await fetch(`${API}/admin/calendar`)
    if (res.ok) setCalendarEvents(await res.json())
  }

  const loadLogs = async () => {
    const res = await fetch(`${API}/admin/logs`)
    if (res.ok) setLogs(await res.json())
  }

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    if (activeSection === 'calendar') loadCalendar()
    if (activeSection === 'logs') loadLogs()
  }, [activeSection])

  const syncAgent = async (name) => {
    try {
      await fetch(`${API}/admin/agents/${name}/sync`, { method: 'POST' })
      load()
    } catch {}
  }

  const updateAgent = async (name, data) => {
    try {
      await fetch(`${API}/admin/agents/${name}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      load()
    } catch {}
  }

  const SECTIONS = [
    { id: 'agents', label: 'Agents Dust' },
    { id: 'env', label: 'Variables d\'env.' },
    { id: 'calendar', label: 'Calendrier global' },
    { id: 'logs', label: 'Logs système' },
  ]

  const outOfSync = agents.filter(a => !a.synced).length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Administration</h1>
          {outOfSync > 0 && (
            <p className="text-amber-400 text-sm mt-1">⚠️ {outOfSync} agent{outOfSync > 1 ? 's' : ''} hors sync</p>
          )}
        </div>
      </div>

      {error && <div className="bg-red-900/30 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">{error}</div>}

      {/* Section tabs */}
      <div className="flex gap-2 border-b border-gray-800 pb-0">
        {SECTIONS.map(s => (
          <button key={s.id} onClick={() => setActiveSection(s.id)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors -mb-px ${
              activeSection === s.id
                ? 'bg-gray-900 border border-gray-700 border-b-gray-900 text-white'
                : 'text-gray-500 hover:text-gray-300'
            }`}>
            {s.label}
            {s.id === 'agents' && outOfSync > 0 && (
              <span className="ml-1.5 bg-amber-700 text-amber-200 text-xs px-1.5 py-0.5 rounded-full">
                {outOfSync}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Section 1 — Agents */}
      {activeSection === 'agents' && (
        <div>
          <DustAutoToggle enabled={dustAutoEnabled} onChange={setDustAutoEnabled} />
          {loading ? (
            <div className="text-center py-8 text-gray-500">Chargement…</div>
          ) : agents.length === 0 ? (
            <div className="text-center py-12 text-gray-600">Aucun agent configuré</div>
          ) : (
            <div className="space-y-4 mt-4">
              {agents.map(agent => (
                <AgentCard
                  key={agent.name}
                  agent={agent}
                  onSync={syncAgent}
                  onUpdate={updateAgent}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Section 2 — Env */}
      {activeSection === 'env' && (
        <div className="space-y-4">
          {status ? (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h3 className="font-semibold text-white mb-4">Variables d&apos;environnement</h3>
              <div className="space-y-2 font-mono text-sm">
                {Object.entries(status.env || {}).map(([key, val]) => (
                  <div key={key} className="flex items-center gap-4">
                    <span className="text-gray-500 w-48 flex-shrink-0">{key}</span>
                    <span className="text-gray-300">{val}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">Chargement…</div>
          )}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h3 className="font-semibold text-white mb-4">Tests de connectivité</h3>
            <div className="space-y-2">
              <PingButton label="Dust API" endpoint="dust" />
              <PingButton label="Slack" endpoint="slack" />
              <PingButton label="MarketData (FMP)" endpoint="market" />
            </div>
          </div>
        </div>
      )}

      {/* Section 3 — Calendar */}
      {activeSection === 'calendar' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="font-semibold text-white mb-4">Calendrier global</h3>
          {calendarEvents.length === 0 ? (
            <p className="text-gray-600 text-sm">Aucun événement à venir</p>
          ) : (
            <div className="space-y-2">
              {calendarEvents.map((ev, i) => (
                <div key={i} className="flex items-center justify-between bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
                  <div>
                    <span className="text-sm text-white">{ev.label || ev.event_type}</span>
                    {ev.ticker_symbol && (
                      <span className="ml-2 text-xs font-mono text-indigo-400">{ev.ticker_symbol}</span>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">
                      {ev.event_date ? new Date(ev.event_date).toLocaleDateString('fr-FR') : '—'}
                    </p>
                    {ev.monitoring_mode && (
                      <p className="text-xs text-gray-600">Mode {ev.monitoring_mode}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Section 4 — Logs */}
      {activeSection === 'logs' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="font-semibold text-white mb-4">Logs système</h3>
          {logs.length === 0 ? (
            <p className="text-gray-600 text-sm">Aucun log disponible</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto font-mono text-xs">
              {logs.map((log, i) => (
                <div key={i} className={`px-3 py-2 rounded ${
                  log.level === 'error' ? 'bg-red-950/30 text-red-400' :
                  log.level === 'warning' ? 'bg-amber-950/30 text-amber-400' :
                  'bg-gray-800 text-gray-400'
                }`}>
                  <span className="text-gray-600 mr-3">
                    {log.timestamp ? new Date(log.timestamp).toLocaleTimeString('fr-FR') : ''}
                  </span>
                  {log.message || JSON.stringify(log)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
