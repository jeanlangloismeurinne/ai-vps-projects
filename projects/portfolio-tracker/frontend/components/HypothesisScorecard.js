const STATUS_STYLE = {
  confirmed:   'bg-emerald-900/50 border-emerald-700 text-emerald-300',
  neutral:     'bg-gray-800 border-gray-600 text-gray-300',
  alert:       'bg-amber-900/50 border-amber-700 text-amber-300',
  invalidated: 'bg-red-900/50 border-red-700 text-red-300',
}

const CRIT_BADGE = {
  critical:   'bg-red-900 text-red-300',
  important:  'bg-amber-900 text-amber-300',
  secondary:  'bg-gray-800 text-gray-400',
}

export default function HypothesisScorecard({ hypotheses = [] }) {
  if (!hypotheses.length) return <p className="text-gray-500 text-sm">Aucune hypothèse.</p>
  return (
    <div className="space-y-2">
      {hypotheses.map(h => (
        <div key={h.id || h.code}
          className={`border rounded-lg p-3 ${STATUS_STYLE[h.current_status] || STATUS_STYLE.neutral}`}>
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold">{h.code}</span>
              <span className="font-medium text-sm">{h.label}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${CRIT_BADGE[h.criticality] || CRIT_BADGE.secondary}`}>
                {h.criticality}
              </span>
            </div>
            <span className="text-xs font-semibold uppercase shrink-0">
              {h.current_status || 'neutral'}
            </span>
          </div>
          {h.description && (
            <p className="text-xs text-gray-400 mt-1">{h.description}</p>
          )}
          <div className="flex gap-4 mt-1 text-xs text-gray-500">
            {h.verification_horizon && <span>⏱ {h.verification_horizon}</span>}
            {h.kpi_to_watch && <span>📊 {h.kpi_to_watch}</span>}
          </div>
        </div>
      ))}
    </div>
  )
}
