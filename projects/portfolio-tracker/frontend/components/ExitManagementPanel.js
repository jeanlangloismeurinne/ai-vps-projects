import { useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'
const EXIT_REASONS = [
  { value: 'thesis_invalidated', label: 'Thèse invalidée' },
  { value: 'target_reached', label: 'Objectif atteint' },
  { value: 'reallocation', label: 'Réallocation' },
  { value: 'stop_loss', label: 'Stop loss' },
]

export default function ExitManagementPanel({ positionId, thesis, onExit }) {
  const [mode, setMode] = useState(null) // 'partial' | 'close'
  const [form, setForm] = useState({ exit_price: '', exit_date: new Date().toISOString().split('T')[0], exit_reason: 'thesis_invalidated', exit_notes: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const thresholds = thesis?.price_thresholds_json || {}

  const submit = async () => {
    setSaving(true)
    setError(null)
    try {
      const payload = {
        exit_price: parseFloat(form.exit_price),
        exit_date: form.exit_date,
        exit_reason: form.exit_reason,
        exit_notes: form.exit_notes || null,
        status: 'closed',
      }
      const r = await fetch(`${API}/positions/${positionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error((await r.json()).detail || 'Erreur')
      onExit?.()
    } catch (e) { setError(e.message) }
    setSaving(false)
  }

  return (
    <div className="space-y-4">
      {thresholds.partial_exit_zone1 && (
        <div className="bg-gray-800 rounded p-3 text-sm">
          <p className="text-gray-400 text-xs mb-1">Seuils de sortie (thèse)</p>
          <div className="flex gap-4">
            {thresholds.partial_exit_zone1 && (
              <span className="text-amber-300">
                Sortie 25% : €{thresholds.partial_exit_zone1.from}–{thresholds.partial_exit_zone1.to}
              </span>
            )}
            {thresholds.partial_exit_zone2 && (
              <span className="text-orange-300">
                Sortie 50% : €{thresholds.partial_exit_zone2.from}–{thresholds.partial_exit_zone2.to}
              </span>
            )}
          </div>
        </div>
      )}

      {!mode && (
        <div className="flex gap-2">
          <button onClick={() => setMode('close')}
            className="px-3 py-1.5 text-xs bg-red-900 hover:bg-red-800 text-red-200 rounded">
            Clôturer la position
          </button>
        </div>
      )}

      {mode === 'close' && (
        <div className="bg-gray-800 border border-red-800 rounded-lg p-4 space-y-3">
          <h4 className="text-sm font-medium text-red-300">Clôture de position</h4>
          {error && <p className="text-red-400 text-xs">{error}</p>}
          {[
            { label: 'Prix de sortie (€)', key: 'exit_price', type: 'number' },
            { label: 'Date de sortie', key: 'exit_date', type: 'date' },
          ].map(({ label, key, type }) => (
            <div key={key}>
              <label className="text-xs text-gray-400 block mb-1">{label}</label>
              <input type={type} value={form[key]}
                onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                className="w-full bg-gray-700 border border-gray-600 text-gray-100 text-sm rounded px-3 py-2" />
            </div>
          ))}
          <div>
            <label className="text-xs text-gray-400 block mb-1">Raison</label>
            <select value={form.exit_reason} onChange={e => setForm(f => ({ ...f, exit_reason: e.target.value }))}
              className="w-full bg-gray-700 border border-gray-600 text-gray-100 text-sm rounded px-3 py-2">
              {EXIT_REASONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Notes</label>
            <textarea value={form.exit_notes} onChange={e => setForm(f => ({ ...f, exit_notes: e.target.value }))}
              rows={2} className="w-full bg-gray-700 border border-gray-600 text-gray-100 text-sm rounded px-3 py-2" />
          </div>
          <div className="flex gap-2">
            <button onClick={submit} disabled={saving}
              className="px-4 py-2 bg-red-800 hover:bg-red-700 text-white text-sm rounded disabled:opacity-50">
              {saving ? 'Enregistrement…' : 'Confirmer la clôture'}
            </button>
            <button onClick={() => setMode(null)} className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200">
              Annuler
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
