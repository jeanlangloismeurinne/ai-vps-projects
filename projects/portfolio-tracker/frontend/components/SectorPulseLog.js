function ScoreBar({ score }) {
  const clamped = Math.max(-5, Math.min(5, score || 0))
  const pct = ((clamped + 5) / 10) * 100
  const color = clamped < -2 ? 'bg-red-500' : clamped > 2 ? 'bg-emerald-500' : 'bg-gray-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-mono ${clamped < 0 ? 'text-red-400' : clamped > 0 ? 'text-emerald-400' : 'text-gray-400'}`}>
        {clamped > 0 ? '+' : ''}{clamped}
      </span>
    </div>
  )
}

export default function SectorPulseLog({ pulses = [] }) {
  if (!pulses.length) return <p className="text-gray-500 text-sm">Aucun sector pulse.</p>
  return (
    <div className="space-y-2">
      {pulses.map(p => (
        <div key={p.id} className="bg-gray-800 border border-gray-700 rounded-lg p-3">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-blue-400">{p.peer_ticker}</span>
              <span className="text-xs text-gray-500">
                {p.pulse_date ? new Date(p.pulse_date).toLocaleDateString('fr-FR') : '—'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <ScoreBar score={p.pulse_score} />
              {p.action === 'escalate_to_regime3' && (
                <span className="text-xs bg-red-900 text-red-300 px-1.5 py-0.5 rounded">Escalade</span>
              )}
            </div>
          </div>
          {p.peer_result_summary && (
            <p className="text-sm text-gray-300">{p.peer_result_summary}</p>
          )}
        </div>
      ))}
    </div>
  )
}
