import { useState, useEffect } from 'react'
import CalendarView from '../components/CalendarView'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050/api'

export default function CalendarPage() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('upcoming')
  const [refreshing, setRefreshing] = useState(false)

  const load = (upcomingOnly = true) => {
    setLoading(true)
    fetch(`${API}/calendar?upcoming_only=${upcomingOnly}&limit=100`)
      .then(r => r.json())
      .then(data => { setEvents(data); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { load(filter === 'upcoming') }, [filter])

  const refresh = async () => {
    setRefreshing(true)
    try {
      await fetch(`${API}/calendar/refresh`, { method: 'POST' })
      load(filter === 'upcoming')
    } catch (e) {
      alert('Erreur refresh calendrier')
    }
    setRefreshing(false)
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Calendrier Événementiel</h1>
        <div className="flex gap-2">
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded px-3 py-1.5">
            <option value="upcoming">À venir</option>
            <option value="all">Tous</option>
          </select>
          <button
            onClick={refresh}
            disabled={refreshing}
            className="px-3 py-1.5 text-sm bg-blue-800 hover:bg-blue-700 text-blue-200 rounded font-medium disabled:opacity-50">
            {refreshing ? 'Refresh…' : '↻ Refresh'}
          </button>
        </div>
      </div>

      {loading
        ? <div className="text-gray-400 py-8 text-center">Chargement…</div>
        : <CalendarView events={events} />
      }
    </div>
  )
}
