const STATUS_ARROW = { confirming: '↑', confirmed: '↑', alert: '↓', invalidated: '↓', neutral: '=' }
const STATUS_COLOR = { confirming: 'text-emerald-400', confirmed: 'text-emerald-400', alert: 'text-red-400', invalidated: 'text-red-500', neutral: 'text-gray-400' }
const CRIT_COLOR = { critical: 'text-red-300', important: 'text-amber-300', secondary: 'text-gray-400' }

export default function HypothesisDiff({ currentScores, previousScores, hypotheses }) {
  if (!currentScores || !hypotheses) return null
  const prevMap = {}
  if (previousScores) previousScores.forEach(s => { prevMap[s.code] = s })

  return (
    <div className="space-y-1">
      {hypotheses.map(h => {
        const curr = currentScores.find(s => s.code === h.code)
        const prev = prevMap[h.code]
        if (!curr) return null
        const changed = prev && prev.status !== curr.status
        return (
          <div key={h.code} className={`flex items-center justify-between px-3 py-1.5 rounded text-xs ${changed ? 'bg-gray-800' : ''}`}>
            <div className="flex items-center gap-2">
              <span className="font-mono text-gray-400 w-6">{h.code}</span>
              <span className={`text-xs ${CRIT_COLOR[h.criticality] || 'text-gray-400'}`}>({h.criticality})</span>
              <span className="text-gray-300 truncate max-w-32">{h.label}</span>
            </div>
            <div className="flex items-center gap-2">
              {prev && prev.status !== curr.status && (
                <span className="text-gray-500">{prev.status} →</span>
              )}
              <span className={`font-medium ${STATUS_COLOR[curr.status] || 'text-gray-400'}`}>
                {curr.status} {STATUS_ARROW[curr.status] || ''}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
