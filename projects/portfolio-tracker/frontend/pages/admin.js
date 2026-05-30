import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

function AgentCard({ agent, onSync, onUpdate }) {
  const [editingId, setEditingId] = useState(false)
  const [dustId, setDustId] = useState(agent.dust_agent_id || '')
  const [copied, setCopied] = useState(false)

  const copyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(agent.prompt || '')
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }

  const saveId = async () => {
    await onUpdate(agent.name, { dust_agent_id: dustId })
    setEditingId(false)
  }

  return (
    <div className={`bg-gray-900 border rounded-xl p-5 ${agent.synced ? 'border-gray-800' : 'border-amber-700'}`}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-white">{agent.name}</h3>
          {agent.description && <p className="text-xs text-gray-500 mt-0.5">{agent.description}</p>}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded border font-medium ${
            agent.synced
              ? 'bg-emerald-900/50 text-emerald-300 border-emerald-700'
              : 'bg-amber-900/50 text-amber-300 border-amber-700'
          }`}>
            {agent.synced ? '✓ Synchronisé' : '⚠️ Hors sync'}
          </span>
        </div>
      </div>

      {/* Prompt */}
      {agent.prompt && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs text-gray-500">Prompt</label>
            <button onClick={copyPrompt}
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
              {copied ? '✓ Copié !' : 'Copier le prompt'}
            </button>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-auto max-h-48">
            <pre className="font-mono text-xs text-gray-400 p-3 whitespace-pre-wrap">
              {agent.prompt.split('\n').map((line, i) => (
                <span key={i} className="flex">
                  <span className="text-gray-700 select-none mr-3 min-w-[2rem] text-right">{i + 1}</span>
                  <span>{line}</span>
                </span>
              ))}
            </pre>
          </div>
        </div>
      )}

      {/* Dust Agent ID */}
      <div className="mb-4">
        <label className="text-xs text-gray-500 block mb-1">Dust Agent ID</label>
        {editingId ? (
          <div className="flex gap-2">
            <input
              value={dustId}
              onChange={e => setDustId(e.target.value)}
              className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded px-3 py-1.5 font-mono focus:border-indigo-500 focus:outline-none"
            />
            <button onClick={saveId} className="text-xs bg-indigo-700 hover:bg-indigo-600 text-white px-3 py-1.5 rounded transition-colors">Sauvegarder</button>
            <button onClick={() => setEditingId(false)} className="text-xs text-gray-500 hover:text-gray-300 px-2">Annuler</button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-gray-400">{agent.dust_agent_id || '—'}</span>
            <button onClick={() => setEditingId(true)} className="text-xs text-gray-600 hover:text-gray-400 transition-colors">Éditer</button>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        {!agent.synced && (
          <button onClick={() => onSync(agent.name)}
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

  const load = async () => {
    setLoading(true)
    try {
      const [agRes, stRes] = await Promise.all([
        fetch(`${API}/admin/agents`),
        fetch(`${API}/admin/status`),
      ])
      if (agRes.ok) setAgents(await agRes.json())
      if (stRes.ok) setStatus(await stRes.json())
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
          {loading ? (
            <div className="text-center py-8 text-gray-500">Chargement…</div>
          ) : agents.length === 0 ? (
            <div className="text-center py-12 text-gray-600">Aucun agent configuré</div>
          ) : (
            <div className="space-y-4">
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
