import { useState } from 'react'

export default function PrivateMetricsModal({ company, onClose, onConfirm }) {
  const today = new Date()
  const quarter = `Q${Math.ceil((today.getMonth() + 1) / 3)} ${today.getFullYear()}`

  const [form, setForm] = useState({
    arr_ca_m: company?.arr_m != null ? String(company.arr_m) : '',
    growth_pct: '',
    nrr_pct: '',
    burn_rate_m: '',
    runway_months: '',
    ebitda_m: company?.ebitda_m != null ? String(company.ebitda_m) : '',
    gross_margin_pct: '',
    headcount: '',
    last_valuation_m: company?.last_valuation_m != null ? String(company.last_valuation_m) : '',
    last_board_date: '',
    context: '',
  })

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const handleConfirm = () => {
    // Build a formatted text block summarising the metrics
    const lines = []
    if (form.arr_ca_m) lines.push(`ARR / CA : ${form.arr_ca_m} M€`)
    if (form.growth_pct) lines.push(`Croissance : ${form.growth_pct}%`)
    if (form.nrr_pct) lines.push(`NRR / rétention : ${form.nrr_pct}%`)
    if (form.burn_rate_m) lines.push(`Burn rate mensuel : ${form.burn_rate_m} M€`)
    if (form.runway_months) lines.push(`Runway : ${form.runway_months} mois`)
    if (form.ebitda_m) lines.push(`EBITDA : ${form.ebitda_m} M€`)
    if (form.gross_margin_pct) lines.push(`Marge brute : ${form.gross_margin_pct}%`)
    if (form.headcount) lines.push(`Effectif : ${form.headcount}`)
    if (form.last_valuation_m) lines.push(`Dernière valo : ${form.last_valuation_m} M€`)
    if (form.last_board_date) lines.push(`Dernier board : ${form.last_board_date}`)
    if (form.context) lines.push(`\nContexte : ${form.context}`)

    const metricsText = lines.length > 0
      ? `--- Métriques opérationnelles ${quarter} ---\n${lines.join('\n')}\n---`
      : null

    onConfirm({
      private_metrics: {
        quarter,
        arr_ca_m: form.arr_ca_m ? parseFloat(form.arr_ca_m) : null,
        growth_pct: form.growth_pct ? parseFloat(form.growth_pct) : null,
        nrr_pct: form.nrr_pct ? parseFloat(form.nrr_pct) : null,
        burn_rate_m: form.burn_rate_m ? parseFloat(form.burn_rate_m) : null,
        runway_months: form.runway_months ? parseFloat(form.runway_months) : null,
        ebitda_m: form.ebitda_m ? parseFloat(form.ebitda_m) : null,
        gross_margin_pct: form.gross_margin_pct ? parseFloat(form.gross_margin_pct) : null,
        headcount: form.headcount ? parseInt(form.headcount, 10) : null,
        last_valuation_m: form.last_valuation_m ? parseFloat(form.last_valuation_m) : null,
        last_board_date: form.last_board_date || null,
        context: form.context.trim() || null,
      },
      metricsText,
    })
  }

  const fieldClass = "w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-violet-500 focus:outline-none"
  const labelClass = "text-xs text-gray-400 block mb-1"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700 sticky top-0 bg-gray-800 z-10">
          <div>
            <h3 className="font-semibold text-white">
              Métriques opérationnelles
              {company?.name ? ` — ${company.name}` : ''}
            </h3>
            <p className="text-xs text-violet-400 mt-0.5">{quarter} · Revue trimestrielle (Mode 2)</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">×</button>
        </div>

        <div className="px-5 py-4 space-y-4">
          <p className="text-xs text-gray-500">
            Renseignez les métriques disponibles. Seuls les champs pertinents sont nécessaires — laissez les autres vides.
          </p>

          {/* Revenus + Croissance */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>ARR ou CA (M€)</label>
              <input
                type="number" step="0.1"
                value={form.arr_ca_m}
                onChange={e => set('arr_ca_m', e.target.value)}
                placeholder="ex. 12.5"
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Croissance MoM ou YoY (%)</label>
              <input
                type="number" step="0.1"
                value={form.growth_pct}
                onChange={e => set('growth_pct', e.target.value)}
                placeholder="ex. 85"
                className={fieldClass}
              />
            </div>
          </div>

          {/* NRR + Burn */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>NRR / rétention (%)</label>
              <input
                type="number" step="0.1"
                value={form.nrr_pct}
                onChange={e => set('nrr_pct', e.target.value)}
                placeholder="ex. 120"
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Burn rate mensuel (M€)</label>
              <input
                type="number" step="0.1"
                value={form.burn_rate_m}
                onChange={e => set('burn_rate_m', e.target.value)}
                placeholder="ex. 1.2"
                className={fieldClass}
              />
            </div>
          </div>

          {/* Runway + EBITDA */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Runway (mois)</label>
              <input
                type="number" step="1"
                value={form.runway_months}
                onChange={e => set('runway_months', e.target.value)}
                placeholder="ex. 18"
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>EBITDA (M€)</label>
              <input
                type="number" step="0.1"
                value={form.ebitda_m}
                onChange={e => set('ebitda_m', e.target.value)}
                placeholder="ex. -2.0"
                className={fieldClass}
              />
            </div>
          </div>

          {/* Marge brute + Effectif */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Marge brute (%)</label>
              <input
                type="number" step="0.1"
                value={form.gross_margin_pct}
                onChange={e => set('gross_margin_pct', e.target.value)}
                placeholder="ex. 72"
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Effectif</label>
              <input
                type="number" step="1"
                value={form.headcount}
                onChange={e => set('headcount', e.target.value)}
                placeholder="ex. 450"
                className={fieldClass}
              />
            </div>
          </div>

          {/* Valorisation + Board */}
          <div className="border-t border-gray-700 pt-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Contexte investisseur</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Dernière valo connue (M€)</label>
                <input
                  type="number" step="0.1"
                  value={form.last_valuation_m}
                  onChange={e => set('last_valuation_m', e.target.value)}
                  placeholder="ex. 250"
                  className={fieldClass}
                />
                {company?.last_valuation_m && (
                  <p className="text-xs text-gray-600 mt-1">Pré-rempli depuis la fiche</p>
                )}
              </div>
              <div>
                <label className={labelClass}>Date du dernier board</label>
                <input
                  type="date"
                  value={form.last_board_date}
                  onChange={e => set('last_board_date', e.target.value)}
                  className={fieldClass}
                />
              </div>
            </div>
          </div>

          {/* Contexte libre */}
          <div>
            <label className={labelClass}>Contexte libre</label>
            <textarea
              value={form.context}
              onChange={e => set('context', e.target.value)}
              rows={3}
              placeholder="Actualités, événements récents, signaux, rumeurs de levée, changements d'équipe…"
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-violet-500 focus:outline-none resize-none"
            />
          </div>
        </div>

        <div className="px-5 py-4 border-t border-gray-700 flex gap-3 sticky bottom-0 bg-gray-800">
          <button
            onClick={handleConfirm}
            className="flex-1 py-2 bg-violet-700 hover:bg-violet-600 text-white text-sm rounded font-medium transition-colors"
          >
            Lancer la revue →
          </button>
          <button onClick={onClose} className="px-4 text-gray-400 hover:text-gray-200 text-sm">
            Annuler
          </button>
        </div>
      </div>
    </div>
  )
}
