import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const TIER = {
  'ingestion-agent': 'ouvrier', 'search-worker': 'ouvrier', 'gap-intake': 'ouvrier',
  'groundedness-checker': 'ouvrier', 'postmortem-agent': 'ouvrier',
  'knowledge-curator': 'métier léger', 'research-agent': 'métier', 'bull-agent': 'métier',
  'bear-agent': 'métier', 'thesis-agent': 'métier', 'debate-agent': 'métier',
  'monitoring-agent': 'mixte',
}

function AgentRow({ a }) {
  const tier = TIER[a.agent_name] || '—'
  return (
    <tr className="border-t border-gray-800">
      <td className="py-2 px-3 font-medium text-white">{a.agent_name}</td>
      <td className="py-2 px-3 text-gray-400">{tier}</td>
      <td className="py-2 px-3 text-gray-400">{a.provider}</td>
      <td className="py-2 px-3 text-gray-500 font-mono text-xs">{a.model || '—'}</td>
      <td className="py-2 px-3">
        {a.tools_json
          ? <span className="text-emerald-300 text-xs">tools</span>
          : <span className="text-gray-600 text-xs">—</span>}
      </td>
    </tr>
  )
}

export default function V2Dashboard() {
  const [agents, setAgents] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    fetch(`${API}/admin/agents?flow_version=v2`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(d => setAgents(Array.isArray(d) ? d : []))
      .catch(e => setErr(String(e)))
  }, [])

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">Espace V2 — tableau de bord</h1>
        <p className="text-sm text-gray-500 mt-1">
          Architecture V2 en construction. Les pages fonctionnelles (watchlist, curator, analyse
          bull/bear/synthèse) arrivent au fil des prochains lots. Ci-dessous, l'état des agents V2.
        </p>
      </div>

      <div className="rounded-xl border border-gray-800 bg-gray-900/50 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-200">Agents V2</h2>
          {agents && <span className="text-xs text-gray-500">{agents.length} agents · provider DeepInfra</span>}
        </div>
        {err && <div className="px-4 py-6 text-sm text-red-400">Erreur de chargement des agents ({err}).</div>}
        {!err && !agents && <div className="px-4 py-6 text-sm text-gray-500">Chargement…</div>}
        {agents && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500">
                <th className="py-2 px-3 font-medium">Agent</th>
                <th className="py-2 px-3 font-medium">Tier</th>
                <th className="py-2 px-3 font-medium">Provider</th>
                <th className="py-2 px-3 font-medium">Modèle</th>
                <th className="py-2 px-3 font-medium">Outils</th>
              </tr>
            </thead>
            <tbody>
              {agents.map(a => <AgentRow key={a.agent_name} a={a} />)}
            </tbody>
          </table>
        )}
      </div>

      <div className="mt-6 rounded-xl border border-amber-900/40 bg-amber-950/20 px-4 py-3">
        <p className="text-xs text-amber-300/90">
          🧪 Espace expérimental. Les données V2 (base de connaissance, analyses) sont disjointes de la
          V1 : rien de ce qui est fait ici n'affecte le portefeuille de production.
        </p>
      </div>
    </div>
  )
}
