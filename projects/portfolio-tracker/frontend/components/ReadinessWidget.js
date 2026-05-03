import { useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function ReadinessWidget({ itemId, score = 0, cashReady = false, onUpdate }) {
  const [toggling, setToggling] = useState(false)

  const color = score >= 75 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-500'

  const toggleCash = async () => {
    setToggling(true)
    try {
      await fetch(`${API}/watchlist/${itemId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cash_ready: !cashReady }),
      })
      onUpdate?.()
    } catch (e) {}
    setToggling(false)
  }

  return (
    <div className="flex items-center gap-2">
      <div className="relative w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`absolute left-0 top-0 h-full rounded-full transition-all ${color}`}
          style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
      <span className="text-xs text-gray-400 w-6 text-right">{score}</span>
      <button
        onClick={toggleCash}
        disabled={toggling}
        title={cashReady ? 'Cash disponible' : 'Marquer cash prêt'}
        className={`text-xs px-1.5 py-0.5 rounded border transition-colors ${
          cashReady ? 'border-emerald-600 text-emerald-400 bg-emerald-900/30' : 'border-gray-600 text-gray-500 hover:border-gray-400'
        }`}>
        💰
      </button>
    </div>
  )
}
