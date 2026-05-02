const EVENT_TYPE_STYLE = {
  earnings:     'bg-blue-900 text-blue-300 border-blue-700',
  cmd:          'bg-purple-900 text-purple-300 border-purple-700',
  agm:          'bg-gray-800 text-gray-300 border-gray-600',
  ma:           'bg-amber-900 text-amber-300 border-amber-700',
}

function daysUntil(dateStr) {
  if (!dateStr) return null
  const diff = Math.ceil((new Date(dateStr) - new Date()) / 86400000)
  return diff
}

export default function CalendarView({ events = [] }) {
  if (!events.length) return <p className="text-gray-500 text-sm">Aucun événement calendrier.</p>
  return (
    <div className="space-y-2">
      {events.map(e => {
        const days = daysUntil(e.event_date)
        const style = EVENT_TYPE_STYLE[e.event_type] || EVENT_TYPE_STYLE.agm
        return (
          <div key={e.id}
            className={`flex items-center justify-between border rounded-lg px-4 py-3 ${style}`}>
            <div className="flex items-center gap-3">
              <span className="font-mono font-bold text-sm">{e.ticker}</span>
              <span className="text-sm capitalize">{e.event_type}</span>
              {e.processed && (
                <span className="text-xs bg-black/30 px-1.5 py-0.5 rounded">Traité</span>
              )}
            </div>
            <div className="flex items-center gap-4 text-sm">
              <span>{new Date(e.event_date).toLocaleDateString('fr-FR')}</span>
              {days != null && !e.processed && (
                <span className={`text-xs font-medium ${days <= 2 ? 'text-red-300' : days <= 7 ? 'text-amber-300' : 'text-gray-400'}`}>
                  {days === 0 ? "Aujourd'hui" : days < 0 ? `J+${Math.abs(days)}` : `J-${days}`}
                </span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
