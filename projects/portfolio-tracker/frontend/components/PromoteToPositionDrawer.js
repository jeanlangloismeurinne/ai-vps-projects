import { useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function PromoteToPositionDrawer({ item, onClose, onDone }) {
  const [form, setForm] = useState({
    entry_price: item?.entry_price_target || '',
    entry_date: new Date().toISOString().split('T')[0],
    quantity: '',
    allocation_pct: '',
    exchange: 'EURONEXT',
    triggerR1: false,
  })
  const [saving, setSaving] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [error, setError] = useState(null)

  const submit = async () => {
    setSaving(true)
    setError(null)
    try {
      const payload = {
        ticker: item.ticker,
        company_name: item.company_name,
        sector_schema: item.sector_schema || 'Unknown',
        exchange: form.exchange,
        entry_date: form.entry_date,
        entry_price: parseFloat(form.entry_price),
        entry_price_currency: 'EUR',
        allocation_pct: form.allocation_pct ? parseFloat(form.allocation_pct) : null,
        quantity: form.quantity ? parseFloat(form.quantity) : null,
      }
      const r = await fetch(`${API}/positions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error((await r.json()).detail || 'Erreur création position')
      const pos = await r.json()

      // Marquer watchlist invested
      await fetch(`${API}/watchlist/${item.id}/promote`, { method: 'POST' })

      if (form.triggerR1) {
        const tr = await fetch(`${API}/trigger/regime1/${item.ticker}`, { method: 'POST' })
        const td = await tr.json()
        setJobId(td.job_id)
      }

      onDone?.({ position: pos, jobId })
      onClose?.()
    } catch (e) {
      setError(e.message)
    }
    setSaving(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-full max-w-md bg-gray-900 border-l border-gray-700 p-6 overflow-y-auto space-y-5">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold text-white">Ouvrir position — {item?.ticker}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <div className="space-y-3">
          {[
            { label: "Prix d'entrée (€)", key: 'entry_price', type: 'number' },
            { label: "Date d'entrée", key: 'entry_date', type: 'date' },
            { label: "Quantité (titres)", key: 'quantity', type: 'number' },
            { label: "Allocation (%)", key: 'allocation_pct', type: 'number' },
            { label: "Exchange", key: 'exchange', type: 'text' },
          ].map(({ label, key, type }) => (
            <div key={key}>
              <label className="text-xs text-gray-400 block mb-1">{label}</label>
              <input type={type} value={form[key]}
                onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                className="w-full bg-gray-800 border border-gray-700 text-gray-100 text-sm rounded px-3 py-2" />
            </div>
          ))}

          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.triggerR1}
              onChange={e => setForm(f => ({ ...f, triggerR1: e.target.checked }))} />
            <span className="text-sm text-gray-300">Déclencher Régime 1 après création</span>
          </label>
        </div>

        <button onClick={submit} disabled={saving}
          className="w-full px-4 py-2 bg-emerald-700 hover:bg-emerald-600 text-white text-sm rounded font-medium disabled:opacity-50">
          {saving ? 'Création…' : 'Créer la position'}
        </button>
      </div>
    </div>
  )
}
