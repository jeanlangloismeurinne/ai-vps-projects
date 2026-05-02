import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050/api'

function GapBadge({ gap }) {
  if (gap == null) return <span className="text-gray-600">—</span>
  const color = gap <= 0 ? 'text-emerald-400' : gap <= 5 ? 'text-amber-400' : 'text-gray-400'
  return <span className={`font-medium ${color}`}>{gap > 0 ? '+' : ''}{gap.toFixed(1)}%</span>
}

export default function Watchlist() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/watchlist`)
      .then(r => r.json())
      .then(data => { setItems(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const promote = async (item) => {
    if (!confirm(`Promouvoir ${item.ticker} en position active ?`)) return
    try {
      const r = await fetch(`${API}/watchlist/${item.id}/promote`, { method: 'POST' })
      const data = await r.json()
      alert(`Payload suggéré :\n${JSON.stringify(data.suggested_payload, null, 2)}\n\nCréez la position via POST /api/positions`)
    } catch (e) {
      alert('Erreur lors de la promotion')
    }
  }

  if (loading) return <div className="text-gray-400 py-12 text-center">Chargement…</div>

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Watchlist</h1>
        <span className="text-sm text-gray-500">{items.length} valeur(s)</span>
      </div>

      {items.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p>Watchlist vide</p>
          <p className="text-sm mt-1">POST /api/watchlist pour ajouter des valeurs</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-800">
          <table className="w-full text-sm">
            <thead className="bg-gray-900">
              <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                <th className="px-4 py-3">Ticker</th>
                <th className="px-4 py-3">Société</th>
                <th className="px-4 py-3">Secteur</th>
                <th className="px-4 py-3 text-right">Prix actuel</th>
                <th className="px-4 py-3 text-right">Cible entrée</th>
                <th className="px-4 py-3 text-right">Écart</th>
                <th className="px-4 py-3 text-right">Alerte</th>
                <th className="px-4 py-3">Statut</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {items.map(item => (
                <tr key={item.id} className="hover:bg-gray-800/50">
                  <td className="px-4 py-3 font-mono font-bold text-blue-400">{item.ticker}</td>
                  <td className="px-4 py-3 text-gray-300">{item.company_name || '—'}</td>
                  <td className="px-4 py-3">
                    {item.sector_schema
                      ? <span className="text-xs bg-gray-800 px-1.5 py-0.5 rounded text-gray-400">{item.sector_schema}</span>
                      : <span className="text-gray-600">—</span>}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {item.current_price != null ? `€${Number(item.current_price).toFixed(2)}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {item.entry_price_target != null ? `€${Number(item.entry_price_target).toFixed(2)}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <GapBadge gap={item.gap_to_entry} />
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {item.trigger_alert_price != null ? `€${Number(item.trigger_alert_price).toFixed(2)}` : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      item.status === 'promoted' ? 'bg-emerald-900 text-emerald-300' :
                      item.status === 'watching' ? 'bg-blue-900 text-blue-300' :
                      'bg-gray-800 text-gray-400'}`}>
                      {item.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {item.status === 'watching' && (
                      <button
                        onClick={() => promote(item)}
                        className="text-xs px-2 py-1 bg-emerald-900 hover:bg-emerald-800 text-emerald-300 rounded">
                        Promouvoir
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
