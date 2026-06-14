import { useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const STAGE_OPTIONS = [
  { value: 'pre-seed', label: 'Pre-Seed' },
  { value: 'seed', label: 'Seed' },
  { value: 'series-a', label: 'Série A' },
  { value: 'series-b', label: 'Série B' },
  { value: 'series-c', label: 'Série C' },
  { value: 'growth', label: 'Growth' },
  { value: 'pre-ipo', label: 'Pré-IPO' },
  { value: 'mature', label: 'Mature' },
]

const BASIS_OPTIONS = [
  { value: 'funding_round', label: 'Tour de financement' },
  { value: 'revenue_multiple', label: 'Multiple de revenus' },
  { value: 'transaction_comparable', label: 'Comparable transactionnel' },
  { value: 'book_value', label: 'Valeur comptable' },
  { value: 'manual', label: 'Manuel' },
]

export default function AddPrivateCompanyModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '',
    sector: '',
    country: 'FR',
    stage: 'series-b',
    currency: 'EUR',
    last_valuation_m: '',
    last_valuation_date: '',
    valuation_basis: '',
    arr_m: '',
    ebitda_m: '',
    notable_investors: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const submit = async () => {
    if (!form.name.trim()) { setError('Nom requis'); return }
    setLoading(true)
    setError('')
    try {
      // L'ID PRIV-XXXXXXXX est généré côté backend — on n'envoie pas de champ id
      const payload = {
        name: form.name.trim(),
        company_type: 'private',
        sector: form.sector.trim() || null,
        country: form.country.trim() || 'FR',
        stage: form.stage || null,
        reporting_currency: form.currency || 'EUR',
        last_valuation_m: form.last_valuation_m ? parseFloat(form.last_valuation_m) : null,
        last_valuation_date: form.last_valuation_date || null,
        last_valuation_basis: form.valuation_basis || null,
        arr_or_revenue_m: form.arr_m ? parseFloat(form.arr_m) : null,
        ebitda_m: form.ebitda_m ? parseFloat(form.ebitda_m) : null,
        notable_investors: form.notable_investors
          ? form.notable_investors.split(',').map(s => s.trim()).filter(Boolean)
          : [],
        status: 'watchlist',
      }

      const res = await fetch(`${API}/tickers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
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
      <div className="relative bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700 sticky top-0 bg-gray-800 z-10">
          <div>
            <h3 className="font-semibold text-white">Ajouter une société non cotée</h3>
            <p className="text-xs text-violet-400 mt-0.5">PE / VC — sans symbole boursier</p>
          </div>
          <button onClick={() => !loading && onClose()} className="text-gray-400 hover:text-white text-xl">×</button>
        </div>

        <div className="px-5 py-4 space-y-4">
          {/* Nom */}
          <div>
            <label className="text-xs text-gray-400 block mb-1">Nom <span className="text-violet-400">*</span></label>
            <input
              value={form.name}
              onChange={e => set('name', e.target.value)}
              placeholder="ex. Mistral AI, Contentsquare…"
              autoFocus
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-violet-500 focus:outline-none"
            />
          </div>

          {/* Secteur + Pays */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Secteur</label>
              <input
                value={form.sector}
                onChange={e => set('sector', e.target.value)}
                placeholder="ex. SaaS B2B, Fintech…"
                className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-violet-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Pays</label>
              <input
                value={form.country}
                onChange={e => set('country', e.target.value)}
                placeholder="FR"
                className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-violet-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Stade + Devise */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Stade</label>
              <select
                value={form.stage}
                onChange={e => set('stage', e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-violet-500 focus:outline-none"
              >
                {STAGE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Devise</label>
              <select
                value={form.currency}
                onChange={e => set('currency', e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-violet-500 focus:outline-none"
              >
                <option value="EUR">EUR €</option>
                <option value="USD">USD $</option>
                <option value="GBP">GBP £</option>
              </select>
            </div>
          </div>

          {/* Valorisation */}
          <div className="border-t border-gray-700 pt-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Valorisation</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Dernière valo (M€)</label>
                <input
                  type="number" min="0" step="0.1"
                  value={form.last_valuation_m}
                  onChange={e => set('last_valuation_m', e.target.value)}
                  placeholder="ex. 250"
                  className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-violet-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Date de valorisation</label>
                <input
                  type="date"
                  value={form.last_valuation_date}
                  onChange={e => set('last_valuation_date', e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-violet-500 focus:outline-none"
                />
              </div>
            </div>
            <div className="mt-3">
              <label className="text-xs text-gray-400 block mb-1">Base de valorisation</label>
              <select
                value={form.valuation_basis}
                onChange={e => set('valuation_basis', e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 focus:border-violet-500 focus:outline-none"
              >
                <option value="">— Non renseigné</option>
                {BASIS_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Financières */}
          <div className="border-t border-gray-700 pt-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Métriques financières</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">ARR / CA (M€)</label>
                <input
                  type="number" min="0" step="0.1"
                  value={form.arr_m}
                  onChange={e => set('arr_m', e.target.value)}
                  placeholder="ex. 12"
                  className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-violet-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">EBITDA (M€)</label>
                <input
                  type="number" step="0.1"
                  value={form.ebitda_m}
                  onChange={e => set('ebitda_m', e.target.value)}
                  placeholder="ex. -2"
                  className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-violet-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Investisseurs */}
          <div className="border-t border-gray-700 pt-4">
            <label className="text-xs text-gray-400 block mb-1">Investisseurs notables</label>
            <input
              value={form.notable_investors}
              onChange={e => set('notable_investors', e.target.value)}
              placeholder="Andreessen Horowitz, Sequoia, …  (séparés par virgule)"
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-violet-500 focus:outline-none"
            />
            <p className="text-xs text-gray-600 mt-1">Séparer les investisseurs par des virgules</p>
          </div>

          {error && (
            <p className="text-red-400 text-sm bg-red-900/30 border border-red-800 rounded px-3 py-2">{error}</p>
          )}
        </div>

        <div className="px-5 py-4 border-t border-gray-700 flex gap-3 sticky bottom-0 bg-gray-800">
          <button
            onClick={submit}
            disabled={loading || !form.name.trim()}
            className="flex-1 py-2 bg-violet-700 hover:bg-violet-600 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors"
          >
            {loading ? 'Création…' : 'Ajouter la société'}
          </button>
          <button onClick={() => !loading && onClose()} className="px-4 text-gray-400 hover:text-gray-200 text-sm">
            Annuler
          </button>
        </div>
      </div>
    </div>
  )
}
