import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'
const COLORS = {
  cold: 'bg-blue-900 text-blue-200 border-blue-700',
  neutral: 'bg-gray-800 text-gray-200 border-gray-600',
  warm: 'bg-amber-900 text-amber-200 border-amber-700',
  hot: 'bg-red-900 text-red-200 border-red-700',
}
const LABELS = { cold: '❄️ Cold', neutral: '😐 Neutral', warm: '🌡️ Warm', hot: '🔥 Hot' }

export default function MarketTemperatureBadge({ showCash = false }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    const cached = sessionStorage.getItem('market_temp')
    if (cached) {
      const { data: d, ts } = JSON.parse(cached)
      if (Date.now() - ts < 3600000) { setData(d); return }
    }
    fetch(`${API}/market/temperature`)
      .then(r => r.json())
      .then(d => {
        setData(d)
        sessionStorage.setItem('market_temp', JSON.stringify({ data: d, ts: Date.now() }))
      })
      .catch(() => {})
  }, [])

  if (!data || !data.temperature) return null
  const temp = data.temperature
  return (
    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-medium ${COLORS[temp] || COLORS.neutral}`}>
      <span>{LABELS[temp] || temp}</span>
      {showCash && data.cash_target_pct && (
        <span className="opacity-70">· Cash cible {data.cash_target_pct}%</span>
      )}
    </div>
  )
}
