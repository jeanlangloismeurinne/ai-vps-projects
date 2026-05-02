const STYLES = {
  reinforce:  'bg-emerald-900 text-emerald-300 border border-emerald-700',
  maintain:   'bg-blue-900 text-blue-300 border border-blue-700',
  reduce_25:  'bg-amber-900 text-amber-300 border border-amber-700',
  reduce_50:  'bg-orange-900 text-orange-300 border border-orange-700',
  exit:       'bg-red-900 text-red-300 border border-red-700',
}

const ALERT_DOT = {
  green:  'bg-emerald-400',
  orange: 'bg-amber-400',
  red:    'bg-red-400',
}

export default function RecommendationBadge({ recommendation, alertLevel }) {
  const style = STYLES[recommendation] || 'bg-gray-800 text-gray-400 border border-gray-600'
  const dot = alertLevel ? ALERT_DOT[alertLevel] : null
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium ${style}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />}
      {recommendation?.toUpperCase() || '—'}
    </span>
  )
}
