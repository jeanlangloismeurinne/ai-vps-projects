import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function DustRunViewer({ dustConversationId, label = 'Raisonnement agent', defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const [turns, setTurns] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (open && turns === null && dustConversationId) {
      setLoading(true)
      fetch(`${API}/dust-runs/conversation/${dustConversationId}`)
        .then(r => r.json())
        .then(d => { setTurns(d.turns || []); setLoading(false) })
        .catch(() => setLoading(false))
    }
  }, [open, dustConversationId, turns])

  if (!dustConversationId) return null

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-800 hover:bg-gray-750 text-sm font-medium text-gray-300">
        <span>🧠 {label}</span>
        <span className="text-gray-500">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="p-4 space-y-4 bg-gray-900">
          {loading && <p className="text-gray-500 text-sm">Chargement…</p>}
          {turns?.map((turn, i) => (
            <div key={i}>
              {turn.role === 'human' && (
                <div className="text-xs text-gray-500 bg-gray-800 rounded p-2">
                  <span className="font-medium text-gray-400">Vous :</span> {turn.content}
                </div>
              )}
              {turn.role === 'agent' && (
                <div className="space-y-2">
                  {turn.chain_of_thought && (
                    <details className="text-xs text-gray-500 bg-gray-850 rounded p-2 border border-gray-700">
                      <summary className="cursor-pointer font-medium text-gray-400">Pensée intermédiaire</summary>
                      <p className="mt-1 whitespace-pre-wrap">{turn.chain_of_thought}</p>
                    </details>
                  )}
                  {turn.tools_used?.length > 0 && (
                    <div className="text-xs text-gray-500">
                      <span className="font-medium">Outils :</span> {turn.tools_used.join(', ')}
                    </div>
                  )}
                  <div className="text-sm text-gray-200 bg-gray-800 rounded p-3 whitespace-pre-wrap">
                    {turn.content}
                  </div>
                  {turn.agent_version && (
                    <span className="text-xs text-gray-600">v{turn.agent_version}</span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
