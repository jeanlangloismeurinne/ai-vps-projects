import { useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function ThesisValidationPanel({ entityType, entityId, item, onValidated }) {
  const [entryPrice, setEntryPrice] = useState(item?.entry_price_target || '')
  const [alertPrice, setAlertPrice] = useState(item?.trigger_alert_price || '')
  const [decision, setDecision] = useState('watch')
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState(null)

  if (entityType === 'watchlist' && item?.thesis_status === 'validated' && item?.validated_at) {
    return (
      <div className="bg-emerald-900/20 border border-emerald-700 rounded-lg p-4">
        <p className="text-emerald-300 font-medium">✅ Thèse validée le {new Date(item.validated_at).toLocaleDateString('fr-FR')}</p>
        <p className="text-emerald-200 text-sm mt-1">Prix cible : {item.entry_price_target != null ? `€${Number(item.entry_price_target).toFixed(2)}` : '—'}</p>
        {item.trigger_alert_price && (
          <p className="text-emerald-200 text-sm">Trigger alerte : €{Number(item.trigger_alert_price).toFixed(2)}</p>
        )}
      </div>
    )
  }

  const validate = async () => {
    setSaving(true)
    const url = entityType === 'watchlist'
      ? `${API}/watchlist/${entityId}/validate-thesis`
      : `${API}/positions/${entityId}/validate-thesis`
    const body = entityType === 'watchlist'
      ? { entry_price_target: entryPrice ? parseFloat(entryPrice) : null, trigger_alert_price: alertPrice ? parseFloat(alertPrice) : null, decision }
      : {}
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      const data = await r.json()
      setResult(data)
      onValidated?.(data)
    } catch (e) {}
    setSaving(false)
  }

  if (result?.validated) {
    return (
      <div className="bg-emerald-900/20 border border-emerald-700 rounded-lg p-4 space-y-2">
        <p className="text-emerald-300 font-medium">✅ Thèse validée</p>
        {result.open_promote_drawer && (
          <p className="text-amber-300 text-sm">→ Ouvrez le drawer de promotion pour créer la position</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {entityType === 'watchlist' && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Prix d&apos;entrée cible (€)</label>
              <input value={entryPrice} onChange={e => setEntryPrice(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 text-gray-100 text-sm rounded px-3 py-2" />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Trigger alerte (€)</label>
              <input value={alertPrice} onChange={e => setAlertPrice(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 text-gray-100 text-sm rounded px-3 py-2" />
            </div>
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="radio" value="watch" checked={decision === 'watch'} onChange={() => setDecision('watch')} />
              <span className="text-sm text-gray-300">Attendre le prix cible</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="radio" value="invest_now" checked={decision === 'invest_now'} onChange={() => setDecision('invest_now')} />
              <span className="text-sm text-gray-300">Ouvrir une position maintenant</span>
            </label>
          </div>
        </>
      )}
      <button onClick={validate} disabled={saving}
        className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 text-white text-sm rounded font-medium disabled:opacity-50">
        {saving ? 'Validation…' : '✓ Valider la thèse'}
      </button>
    </div>
  )
}
