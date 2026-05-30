import { useState } from 'react'

const EVENT_TYPES = ['earnings', 'conference', 'product_launch', 'dividend', 'macro', 'other']

function EventRow({ event, onDelete, onUpdate }) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ ...event })

  const save = () => {
    onUpdate(form)
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="bg-gray-750 border border-indigo-700/50 rounded-lg p-3 space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <input
            value={form.label || ''}
            onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
            placeholder="Label"
            className="bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
          />
          <input
            type="date"
            value={form.event_date ? form.event_date.slice(0, 10) : ''}
            onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))}
            className="bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
          />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <select
            value={form.event_type || 'other'}
            onChange={e => setForm(f => ({ ...f, event_type: e.target.value }))}
            className="bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
          >
            {EVENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <select
            value={form.monitoring_mode || 2}
            onChange={e => setForm(f => ({ ...f, monitoring_mode: Number(e.target.value) }))}
            className="bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
          >
            {[1, 2, 3, 4, 5].map(m => <option key={m} value={m}>Mode {m}</option>)}
          </select>
        </div>
        <div className="flex gap-2 justify-end">
          <button onClick={() => setEditing(false)} className="text-xs text-gray-400 hover:text-gray-200 px-2 py-1">Annuler</button>
          <button onClick={save} className="text-xs bg-indigo-700 hover:bg-indigo-600 text-white px-3 py-1 rounded">Sauvegarder</button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-between bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 group">
      <div className="flex items-center gap-3">
        <span className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded">{event.event_type || 'other'}</span>
        <span className="text-sm text-white">{event.label || '—'}</span>
        {event.event_date && (
          <span className="text-xs text-gray-500">{new Date(event.event_date).toLocaleDateString('fr-FR')}</span>
        )}
        {event.monitoring_mode && (
          <span className="text-xs text-indigo-400">Mode {event.monitoring_mode}</span>
        )}
      </div>
      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={() => setEditing(true)} className="text-xs text-gray-400 hover:text-gray-200">Éditer</button>
        <button onClick={() => onDelete(event.id || event._tempId)} className="text-xs text-red-500 hover:text-red-400">✕</button>
      </div>
    </div>
  )
}

export default function CalendarEditor({ events = [], onAdd, onDelete, onUpdate }) {
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ label: '', event_date: '', event_type: 'earnings', monitoring_mode: 2 })

  const submit = () => {
    if (!form.label.trim() || !form.event_date) return
    onAdd({ ...form })
    setForm({ label: '', event_date: '', event_type: 'earnings', monitoring_mode: 2 })
    setShowForm(false)
  }

  return (
    <div className="space-y-2">
      {events.length === 0 && (
        <p className="text-gray-600 text-sm text-center py-3">
          Aucun événement calendrier — ajoutez-en un ci-dessous
        </p>
      )}
      {events.map((ev, i) => (
        <EventRow
          key={ev.id || ev._tempId || i}
          event={ev}
          onDelete={onDelete}
          onUpdate={onUpdate}
        />
      ))}

      {showForm ? (
        <div className="bg-gray-800 border border-indigo-700/50 rounded-lg p-3 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <input
              value={form.label}
              onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
              placeholder="Label de l'événement"
              autoFocus
              className="bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
            />
            <input
              type="date"
              value={form.event_date}
              onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))}
              className="bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <select
              value={form.event_type}
              onChange={e => setForm(f => ({ ...f, event_type: e.target.value }))}
              className="bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
            >
              {EVENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <select
              value={form.monitoring_mode}
              onChange={e => setForm(f => ({ ...f, monitoring_mode: Number(e.target.value) }))}
              className="bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
            >
              {[1, 2, 3, 4, 5].map(m => <option key={m} value={m}>Mode {m}</option>)}
            </select>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="text-xs text-gray-400 hover:text-gray-200 px-2 py-1">Annuler</button>
            <button onClick={submit} disabled={!form.label.trim() || !form.event_date}
              className="text-xs bg-indigo-700 hover:bg-indigo-600 disabled:opacity-40 text-white px-3 py-1 rounded">
              Ajouter
            </button>
          </div>
        </div>
      ) : (
        <button onClick={() => setShowForm(true)}
          className="w-full text-sm text-indigo-400 hover:text-indigo-300 border border-dashed border-gray-700 hover:border-indigo-700 rounded-lg py-2 transition-colors">
          + Ajouter un événement
        </button>
      )}
    </div>
  )
}
