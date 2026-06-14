import { useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function AddPrivateCompanyModal({ onClose, onCreated }) {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!name.trim()) { setError('Nom requis'); return }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/tickers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), company_type: 'private' }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Erreur ${res.status}`)
      }
      onCreated()
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={() => !loading && onClose()} />
      <div className="relative bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-sm">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <div>
            <h3 className="font-semibold text-white">Ajouter une société non cotée</h3>
            <p className="text-xs text-violet-400 mt-0.5">Les détails seront renseignés via les JSON d&apos;opportunité et de thèse</p>
          </div>
          <button onClick={() => !loading && onClose()} className="text-gray-400 hover:text-white text-xl">×</button>
        </div>

        <div className="px-5 py-5">
          <label className="text-xs text-gray-400 block mb-1">Nom de la société <span className="text-violet-400">*</span></label>
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            placeholder="ex. Mistral AI, Contentsquare…"
            autoFocus
            className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-violet-500 focus:outline-none"
          />
          {error && (
            <p className="mt-3 text-red-400 text-sm bg-red-900/30 border border-red-800 rounded px-3 py-2">{error}</p>
          )}
        </div>

        <div className="px-5 py-4 border-t border-gray-700 flex gap-3">
          <button
            onClick={submit}
            disabled={loading || !name.trim()}
            className="flex-1 py-2 bg-violet-700 hover:bg-violet-600 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors"
          >
            {loading ? 'Création…' : 'Ajouter'}
          </button>
          <button onClick={() => !loading && onClose()} className="px-4 text-gray-400 hover:text-gray-200 text-sm">
            Annuler
          </button>
        </div>
      </div>
    </div>
  )
}
