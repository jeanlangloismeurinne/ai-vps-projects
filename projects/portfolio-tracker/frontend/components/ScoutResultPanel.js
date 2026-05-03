import { useState } from 'react'
import DustRunViewer from './DustRunViewer'

const CONVICTION_COLORS = {
  strong: 'bg-emerald-900 text-emerald-300 border-emerald-600',
  moderate: 'bg-blue-900 text-blue-300 border-blue-600',
  weak: 'bg-amber-900 text-amber-300 border-amber-600',
  avoid: 'bg-red-900 text-red-300 border-red-600',
}

function Accordion({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <button onClick={() => setOpen(!open)}
        className="w-full flex justify-between px-4 py-2.5 bg-gray-800 text-sm font-medium text-gray-300">
        <span>{title}</span><span>{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="p-4 bg-gray-900">{children}</div>}
    </div>
  )
}

export default function ScoutResultPanel({ item, onRelance }) {
  if (!item || !item.scout_run_at) {
    return (
      <div className="text-center py-8 text-gray-500 space-y-3">
        <p>Aucune analyse disponible</p>
        <button onClick={onRelance}
          className="px-4 py-2 bg-blue-800 hover:bg-blue-700 text-blue-200 text-sm rounded">
          Lancer l&apos;analyse Scout
        </button>
      </div>
    )
  }

  const signal = item.conviction_signal
  const schema = item.schema_json_draft || {}
  const peers = item.peer_snapshot_json || {}

  return (
    <div className="space-y-3">
      {item.scout_agent_version && (
        <div className="flex justify-end">
          <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">Agent v{item.scout_agent_version}</span>
        </div>
      )}

      {signal && (
        <div className={`flex items-center gap-2 px-3 py-2 rounded border ${CONVICTION_COLORS[signal] || CONVICTION_COLORS.weak}`}>
          <span className="font-semibold capitalize">{signal}</span>
        </div>
      )}

      {item.scout_brief && (
        <Accordion title="📝 Thèse préliminaire" defaultOpen>
          <p className="text-gray-200 text-sm whitespace-pre-wrap">{item.scout_brief}</p>
        </Accordion>
      )}

      {schema.raw_section && (
        <Accordion title="🔍 Schéma analytique">
          <pre className="text-gray-300 text-xs whitespace-pre-wrap">{schema.raw_section}</pre>
        </Accordion>
      )}

      {peers.raw_section && (
        <Accordion title="📊 Comparaison peers">
          <pre className="text-gray-300 text-xs whitespace-pre-wrap">{peers.raw_section}</pre>
        </Accordion>
      )}

      {item.entry_price_target != null && (
        <Accordion title="💰 Prix d'entrée cible">
          <p className="text-2xl font-bold text-emerald-400">€{Number(item.entry_price_target).toFixed(2)}</p>
        </Accordion>
      )}

      {item.dust_conversation_id && (
        <Accordion title="🧠 Raisonnement agent">
          <DustRunViewer dustConversationId={item.dust_conversation_id} defaultOpen />
        </Accordion>
      )}

      <div className="flex justify-between items-center pt-2">
        <span className="text-xs text-gray-500">
          Analysé le {item.scout_run_at ? new Date(item.scout_run_at).toLocaleDateString('fr-FR') : '—'}
        </span>
        <button onClick={onRelance}
          className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded border border-gray-700">
          ↺ Relancer le Scout
        </button>
      </div>
    </div>
  )
}
