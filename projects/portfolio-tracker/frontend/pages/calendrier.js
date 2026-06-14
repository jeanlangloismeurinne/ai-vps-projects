import { useState, useEffect } from 'react'
import Link from 'next/link'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const EVENT_TYPE_META = {
  quarterly_results: { label: 'Résultats trimestriels', cls: 'bg-blue-900/60 text-blue-300 border-blue-700' },
  cmd:               { label: 'Capital Markets Day',    cls: 'bg-purple-900/60 text-purple-300 border-purple-700' },
  agm:               { label: 'Assemblée générale',     cls: 'bg-gray-800 text-gray-300 border-gray-600' },
  sector_pulse_peer: { label: 'Sector Pulse (pair)',    cls: 'bg-teal-900/60 text-teal-300 border-teal-700' },
  conviction_review: { label: 'Révision conviction',   cls: 'bg-orange-900/60 text-orange-300 border-orange-700' },
  prochain_tour:     { label: 'Prochain tour',          cls: 'bg-violet-900/60 text-violet-300 border-violet-700' },
  ipo:               { label: 'IPO',                    cls: 'bg-amber-900/60 text-amber-300 border-amber-700' },
  ma:                { label: 'M&A',                    cls: 'bg-red-900/60 text-red-300 border-red-700' },
  milestone:         { label: 'Milestone',              cls: 'bg-emerald-900/60 text-emerald-300 border-emerald-700' },
}

const SOURCE_LABELS = {
  thesis_agent:        'Thèse',
  monitoring_agent:    'Monitoring',
  manual:              'Manuel',
  conviction_override: 'Décision',
}

const MODE_LABELS = {
  1: 'Mode 1 — Pré-event',
  2: 'Mode 2 — Revue trimestrielle',
  3: 'Mode 3 — Décision Review',
  4: 'Mode 4 — Sector Pulse',
  5: 'Mode 5 — Routage alerte',
}

function daysUntil(dateStr) {
  if (!dateStr) return null
  const target = new Date(dateStr)
  target.setHours(0, 0, 0, 0)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((target - today) / 86400000)
}

function CountdownBadge({ days }) {
  if (days == null) return null
  if (days === 0) return <span className="text-xs font-bold text-yellow-300 bg-yellow-900/40 border border-yellow-700 px-2 py-0.5 rounded">Aujourd'hui</span>
  if (days < 0)  return <span className="text-xs text-gray-500">J+{Math.abs(days)}</span>
  if (days <= 3) return <span className="text-xs font-bold text-red-300 bg-red-900/40 border border-red-800 px-2 py-0.5 rounded">J-{days}</span>
  if (days <= 14) return <span className="text-xs font-medium text-amber-300 bg-amber-900/30 border border-amber-800 px-2 py-0.5 rounded">J-{days}</span>
  return <span className="text-xs text-gray-500">J-{days}</span>
}

function EventCard({ event, onValidated }) {
  const [validating, setValidating] = useState(false)
  const typeMeta = EVENT_TYPE_META[event.event_type] || { label: event.event_type, cls: 'bg-gray-800 text-gray-400 border-gray-700' }
  const days = daysUntil(event.scheduled_date)
  const dateLabel = event.scheduled_date
    ? new Date(event.scheduled_date).toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'long' })
    : '—'

  const handleValidate = async () => {
    setValidating(true)
    try {
      const res = await fetch(`${API}/calendar-v2/${event.id}/validate`, { method: 'POST' })
      if (res.ok) onValidated()
    } catch {}
    setValidating(false)
  }

  const tickerHref = `/ticker/${event.ticker_id}`
  const thesisHref = event.thesis_id ? `/ticker/${event.ticker_id}/thesis/${event.thesis_id}` : null

  return (
    <div className={`bg-gray-900 border rounded-xl px-4 py-3.5 flex flex-col gap-2.5 ${
      event.pending_validation ? 'border-amber-700/60' : 'border-gray-800'
    }`}>
      {/* Header row */}
      <div className="flex items-start gap-3">
        {/* Date column */}
        <div className="flex-shrink-0 w-20 text-right">
          <p className="text-xs text-gray-500 capitalize leading-tight">
            {new Date(event.scheduled_date).toLocaleDateString('fr-FR', { weekday: 'short' })}
          </p>
          <p className="text-white font-semibold text-sm leading-tight">
            {new Date(event.scheduled_date).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Link href={tickerHref} className="font-mono font-bold text-indigo-400 hover:text-indigo-300 text-sm">
              {event.ticker_id}
            </Link>
            {event.ticker_name && event.ticker_name !== event.ticker_id && (
              <span className="text-xs text-gray-500 truncate">{event.ticker_name}</span>
            )}
            {event.ticker_status === 'portfolio' && (
              <span className="text-xs bg-emerald-900/40 border border-emerald-800 text-emerald-400 px-1.5 py-0.5 rounded">Portefeuille</span>
            )}
            {event.ticker_company_type === 'private' && (
              <span className="text-xs bg-violet-900/40 border border-violet-800 text-violet-400 px-1.5 py-0.5 rounded">Non côté</span>
            )}
          </div>

          <p className="text-sm text-white mt-0.5 font-medium">{event.label}</p>

          {event.thesis_one_liner && (
            <p className="text-xs text-gray-500 mt-0.5 truncate">{event.thesis_one_liner}</p>
          )}

          {event.peer_ticker && (
            <p className="text-xs text-gray-600 mt-0.5">Pair : {event.peer_ticker}</p>
          )}
        </div>

        {/* Right column */}
        <div className="flex-shrink-0 flex flex-col items-end gap-1.5">
          <CountdownBadge days={days} />
          <span className={`text-xs border px-2 py-0.5 rounded ${typeMeta.cls}`}>{typeMeta.label}</span>
        </div>
      </div>

      {/* Footer row */}
      <div className="flex items-center gap-2 flex-wrap border-t border-gray-800 pt-2">
        <span className="text-xs text-gray-600">{MODE_LABELS[event.monitoring_mode] || `Mode ${event.monitoring_mode}`}</span>
        {event.source && (
          <span className="text-xs text-gray-700">· {SOURCE_LABELS[event.source] || event.source}</span>
        )}

        <div className="ml-auto flex items-center gap-2">
          {event.pending_validation && (
            <button
              onClick={handleValidate}
              disabled={validating}
              className="text-xs px-2.5 py-1 bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-white rounded font-medium transition-colors"
            >
              {validating ? '…' : '✓ Valider'}
            </button>
          )}
          {thesisHref && (
            <Link href={thesisHref} className="text-xs text-indigo-500 hover:text-indigo-400 transition-colors">
              Thèse →
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}

function groupByMonth(events) {
  const groups = {}
  for (const ev of events) {
    const d = new Date(ev.scheduled_date)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const label = d.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })
    if (!groups[key]) groups[key] = { label, events: [] }
    groups[key].events.push(ev)
  }
  return Object.values(groups)
}

const FILTERS = [
  { id: 'all',        label: 'Tout' },
  { id: 'portfolio',  label: 'Portefeuille' },
  { id: 'watchlist',  label: 'Watchlist' },
  { id: 'pending',    label: 'À valider' },
]

export default function Calendrier() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/calendar-v2`)
      if (!res.ok) throw new Error(`Erreur ${res.status}`)
      setEvents(await res.json())
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const filtered = events.filter(ev => {
    if (filter === 'portfolio') return ev.ticker_status === 'portfolio'
    if (filter === 'watchlist') return ev.ticker_status === 'watchlist'
    if (filter === 'pending')   return ev.pending_validation === true
    return true
  })

  const pendingCount = events.filter(e => e.pending_validation).length
  const groups = groupByMonth(filtered)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Calendrier</h1>
        <span className="text-xs text-gray-600">{filtered.length} événement{filtered.length > 1 ? 's' : ''}</span>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {FILTERS.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              filter === f.id
                ? 'bg-indigo-700 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {f.label}
            {f.id === 'pending' && pendingCount > 0 && (
              <span className="ml-1.5 bg-amber-600 text-white text-xs rounded-full px-1.5 py-0.5">{pendingCount}</span>
            )}
          </button>
        ))}
      </div>

      {error && (
        <p className="text-red-400 text-sm bg-red-900/30 border border-red-800 rounded-lg px-3 py-2">{error}</p>
      )}

      {loading ? (
        <div className="text-center py-20 text-gray-500">Chargement…</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 bg-gray-900 border border-gray-800 rounded-xl">
          <p className="text-gray-500 text-lg mb-2">Aucun événement</p>
          <p className="text-gray-600 text-sm">
            {filter === 'pending'
              ? 'Aucun événement en attente de validation'
              : 'Les événements sont créés lors de la validation des thèses'}
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {groups.map(group => (
            <div key={group.label}>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 capitalize">
                {group.label}
              </h2>
              <div className="space-y-2">
                {group.events.map(ev => (
                  <EventCard key={ev.id} event={ev} onValidated={load} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
