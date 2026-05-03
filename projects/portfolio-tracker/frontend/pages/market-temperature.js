import { useState, useEffect } from 'react'
import MarketTemperatureBadge from '../components/MarketTemperatureBadge'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const BUFFETT_ZONES = [
  { max: 100, color: '#10b981', label: 'Sous-évalué' },
  { max: 120, color: '#f59e0b', label: 'Neutre' },
  { max: 150, color: '#f97316', label: 'Surévalué' },
  { max: Infinity, color: '#ef4444', label: 'Extrême' },
]

function ZoneBar({ value, zones, maxDisplay = 200, label }) {
  if (value == null) return <div className="text-gray-500 text-sm">Données indisponibles</div>
  const pct = Math.min((value / maxDisplay) * 100, 100)
  const zone = zones.find(z => value <= z.max) || zones[zones.length - 1]
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{label}</span>
        <span className="font-bold text-white">{value.toFixed(1)}</span>
      </div>
      <div className="h-3 bg-gray-700 rounded-full overflow-hidden relative">
        {zones.filter(z => z.max !== Infinity).map((z, i) => {
          const prevMax = i === 0 ? 0 : zones[i - 1].max
          const w = ((Math.min(z.max, maxDisplay) - prevMax) / maxDisplay) * 100
          return <div key={i} style={{ width: `${w}%`, backgroundColor: z.color, opacity: 0.3 }} className="absolute h-full" />
        })}
        <div className="absolute h-full w-1 bg-white rounded-full transition-all"
          style={{ left: `${pct}%`, transform: 'translateX(-50%)' }} />
      </div>
      <p className="text-xs" style={{ color: zone.color }}>{zone.label}</p>
    </div>
  )
}

export default function MarketTemperaturePage() {
  const [current, setCurrent] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = () => {
    fetch(`${API}/market/temperature`).then(r => r.json()).then(setCurrent).catch(() => {})
    fetch(`${API}/market/temperature/history?limit=52`).then(r => r.json()).then(setHistory).catch(() => {})
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const refresh = async () => {
    setRefreshing(true)
    await fetch(`${API}/market/temperature`)
    load()
    setRefreshing(false)
  }

  const CAPE_ZONES = [
    { max: 20, color: '#10b981', label: 'Bon marché' },
    { max: 25, color: '#f59e0b', label: 'Neutre' },
    { max: 35, color: '#f97316', label: 'Cher' },
    { max: Infinity, color: '#ef4444', label: 'Très cher' },
  ]

  if (loading) return <div className="text-gray-400 py-12 text-center">Chargement…</div>

  const TEMP_COLORS = { cold: 'text-blue-400', neutral: 'text-gray-300', warm: 'text-amber-400', hot: 'text-red-400' }
  const temp = current?.temperature

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Température des marchés</h1>
        <button onClick={refresh} disabled={refreshing}
          className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 text-gray-200 rounded disabled:opacity-50">
          {refreshing ? '↻…' : '↻ Refresh'}
        </button>
      </div>

      {current && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 text-center">
            <p className="text-xs text-gray-500 mb-2">Température</p>
            <p className={`text-4xl font-bold capitalize ${TEMP_COLORS[temp] || 'text-white'}`}>
              {temp || '—'}
            </p>
            <p className="text-sm text-gray-400 mt-2">Cash cible : {current.cash_target_pct}%</p>
            <p className="text-xs text-gray-500 mt-1">
              Buffett : {current.buffett_ratio_pct?.toFixed(0)}% | CAPE : {current.cape_ratio?.toFixed(1)}
            </p>
          </div>

          <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 space-y-4 col-span-2">
            <ZoneBar
              value={current.buffett_ratio_pct}
              zones={BUFFETT_ZONES}
              maxDisplay={200}
              label="Buffett Indicator (Wilshire / GDP %)"
            />
            <ZoneBar
              value={current.cape_ratio}
              zones={CAPE_ZONES}
              maxDisplay={50}
              label="CAPE Shiller"
            />
          </div>
        </div>
      )}

      {history.length > 1 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Historique ({history.length} points)</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-gray-400">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-1 pr-4">Date</th>
                  <th className="text-right pr-4">Buffett %</th>
                  <th className="text-right pr-4">CAPE</th>
                  <th className="text-left">Temp.</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 20).map((h, i) => (
                  <tr key={i} className="border-b border-gray-800">
                    <td className="py-1 pr-4">{h.fetched_at ? new Date(h.fetched_at).toLocaleDateString('fr-FR') : '—'}</td>
                    <td className="text-right pr-4">{h.buffett_ratio != null ? Number(h.buffett_ratio).toFixed(0) : '—'}</td>
                    <td className="text-right pr-4">{h.cape_ratio != null ? Number(h.cape_ratio).toFixed(1) : '—'}</td>
                    <td className={`capitalize ${TEMP_COLORS[h.temperature] || ''}`}>{h.temperature || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
