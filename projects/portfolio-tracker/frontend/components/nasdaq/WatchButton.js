import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function WatchButton({ ticker, onChange }) {
  const [on, setOn] = useState(null)
  useEffect(() => {
    let live = true
    setOn(null)
    fetch(`${API}/nasdaq/watchlist`).then(r => r.json()).then(j => live && setOn(j.tickers.includes(ticker))).catch(() => live && setOn(false))
    return () => { live = false }
  }, [ticker])
  const toggle = () => {
    const next = !on
    setOn(next)
    fetch(`${API}/nasdaq/watchlist/${encodeURIComponent(ticker)}`, { method: next ? 'PUT' : 'DELETE' })
      .then(r => { if (!r.ok) throw new Error(); onChange && onChange(ticker, next) })
      .catch(() => setOn(!next))
  }
  if (on === null) return null
  return (
    <button onClick={toggle} title={on ? 'Retirer de ma liste' : 'Ajouter à ma liste'}
      className={`text-xs px-2 py-1 rounded border ${on ? 'border-amber-600 text-amber-300' : 'border-gray-700 text-gray-300 hover:text-white'}`}>
      {on ? '★ Dans ma liste' : '☆ Suivre'}
    </button>
  )
}
