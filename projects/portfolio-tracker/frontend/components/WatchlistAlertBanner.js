const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function WatchlistAlertBanner({ alerts, onAcknowledge }) {
  if (!alerts || alerts.length === 0) return null

  const acknowledge = async (id) => {
    await fetch(`${API}/watchlist/${id}/acknowledge-alert`, { method: 'PATCH' })
    onAcknowledge?.(id)
  }

  return (
    <div className="bg-red-950 border border-red-700 rounded-lg p-4 space-y-2">
      <p className="text-red-300 font-semibold text-sm">🚨 {alerts.length} alerte(s) watchlist</p>
      {alerts.map(a => (
        <div key={a.id} className="flex items-center justify-between bg-red-900/30 rounded p-2">
          <div className="flex items-center gap-3">
            <span className="font-mono font-bold text-white">{a.ticker}</span>
            <span className="text-red-200 text-sm">
              {a.current_price != null ? `€${Number(a.current_price).toFixed(2)}` : '—'}
              {' '}≤{' '}
              {a.trigger_alert_price != null ? `€${Number(a.trigger_alert_price).toFixed(2)}` : '—'}
            </span>
            {a.gap_to_entry != null && (
              <span className="text-xs text-red-300">Écart: {Number(a.gap_to_entry).toFixed(1)}%</span>
            )}
          </div>
          <div className="flex gap-2">
            <button onClick={() => acknowledge(a.id)}
              className="text-xs px-2 py-1 bg-red-800 hover:bg-red-700 text-red-200 rounded">
              Acquitter
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
