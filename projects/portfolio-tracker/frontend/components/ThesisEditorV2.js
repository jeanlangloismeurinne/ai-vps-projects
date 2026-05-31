const EVENT_TYPES = ['earnings', 'conference', 'product_launch', 'dividend', 'macro', 'other']

const REC_STYLES = {
  BUY:  'bg-emerald-900/60 text-emerald-300 border border-emerald-700',
  HOLD: 'bg-yellow-900/60 text-yellow-300 border border-yellow-700',
  SELL: 'bg-red-900/60 text-red-300 border border-red-700',
}

function ConvictionDots({ score }) {
  return (
    <div className="flex gap-1">
      {Array.from({ length: 10 }, (_, i) => (
        <div key={i} className={`w-2 h-2 rounded-full ${i < score ? 'bg-indigo-400' : 'bg-gray-700'}`} />
      ))}
    </div>
  )
}

export default function ThesisEditorV2({ thesisJson, onChange }) {
  if (!thesisJson) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-600 text-sm text-center px-8">
        <div>
          <p className="text-3xl mb-3">📊</p>
          <p>La thèse est vide</p>
          <p className="mt-1 text-gray-500">Cliquez sur <span className="text-indigo-400 font-medium">«Actualiser la thèse →»</span></p>
        </div>
      </div>
    )
  }

  const update = (key, value) => onChange({ ...thesisJson, [key]: value })

  const hypotheses   = thesisJson.hypotheses || []
  const scenarios    = thesisJson.scenarios || {}
  const price_thr    = thesisJson.price_thresholds || {}
  const pairs        = thesisJson.pairs || []
  const bear_sm      = thesisJson.bear_steel_man || ''
  const track_record = thesisJson.track_record_analysts || []
  const fa           = thesisJson.fundamental_analysis || {}

  const recommendation       = thesisJson.recommendation || ''
  const conviction_score     = thesisJson.conviction_score ?? null
  const conviction_rationale = thesisJson.conviction_rationale || ''
  const one_liner            = thesisJson.one_liner || ''
  const horizon_years        = thesisJson.thesis_horizon_years || ''
  const investor_profile     = thesisJson.ideal_investor_profile || ''
  const prob_weighted_target = thesisJson.probability_weighted_target ?? null

  return (
    <div className="space-y-6 p-4">

      {/* ── Header : conviction + recommandation + résumé ── */}
      {(recommendation || conviction_score != null || one_liner) && (
        <section className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-3 flex-wrap">
            {recommendation && (
              <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${REC_STYLES[recommendation] || REC_STYLES.HOLD}`}>
                {recommendation}
              </span>
            )}
            {conviction_score != null && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-white">{conviction_score}/10</span>
                <ConvictionDots score={conviction_score} />
              </div>
            )}
            {horizon_years && (
              <span className="text-xs text-gray-500">Horizon {horizon_years} ans</span>
            )}
          </div>
          {one_liner && (
            <p className="text-sm text-gray-300 leading-relaxed">{one_liner}</p>
          )}
          {conviction_rationale && (
            <p className="text-xs text-gray-500 italic border-t border-gray-700 pt-2">{conviction_rationale}</p>
          )}
          {investor_profile && (
            <p className="text-xs text-gray-500">
              <span className="text-gray-600">Profil : </span>{investor_profile}
            </p>
          )}
        </section>
      )}

      {/* ── Analyse fondamentale ── */}
      {Object.keys(fa).length > 0 && (
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Analyse fondamentale</h3>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 space-y-3">
            {fa.verdict && (
              <p className="text-sm font-medium text-white">{fa.verdict}</p>
            )}
            <div className="flex gap-2 flex-wrap">
              {fa.moat_status && (
                <span className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded">Moat : {fa.moat_status}</span>
              )}
              {fa.pricing_power_status && (
                <span className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded">Pricing power : {fa.pricing_power_status}</span>
              )}
            </div>
            {fa.moat_components?.length > 0 && (
              <div className="space-y-1">
                {fa.moat_components.map((c, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-gray-400">
                    <span className="text-indigo-400 flex-shrink-0 mt-0.5">•</span>
                    <span><span className="text-gray-300">{c.type}</span>{c.strength ? ` — ${c.strength}` : ''}{c.durability ? `, ${c.durability}` : ''}</span>
                  </div>
                ))}
              </div>
            )}
            {fa.pricing_power_sustainability && (
              <p className="text-xs text-gray-500 border-t border-gray-700 pt-2">Durabilité pricing : {fa.pricing_power_sustainability}</p>
            )}
            {fa.capital_allocation && (
              <div className="border-t border-gray-700 pt-2 space-y-1">
                {Object.entries(fa.capital_allocation).map(([k, v]) => (
                  <div key={k} className="flex gap-2 text-xs">
                    <span className="text-gray-500 flex-shrink-0">{k.replace(/_/g, ' ')} :</span>
                    <span className="text-gray-400">{String(v)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── Scénarios ── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">Scénarios 5 ans</h3>
          {prob_weighted_target != null && (
            <span className="text-xs text-gray-500">
              Cible pondérée : <span className="text-indigo-400 font-medium">${prob_weighted_target}</span>
            </span>
          )}
        </div>
        <div className="grid grid-cols-3 gap-3">
          {['bear', 'central', 'bull'].map(s => (
            <div key={s} className={`rounded-lg p-3 border ${
              s === 'bear'    ? 'border-red-800 bg-red-950/30' :
              s === 'bull'    ? 'border-emerald-800 bg-emerald-950/30' :
                                'border-indigo-800 bg-indigo-950/30'
            }`}>
              <p className={`text-xs font-semibold uppercase mb-2 ${
                s === 'bear' ? 'text-red-400' : s === 'bull' ? 'text-emerald-400' : 'text-indigo-400'
              }`}>{s}</p>
              <div className="space-y-1.5">
                <div>
                  <label className="text-xs text-gray-600">Proba. (%)</label>
                  <input type="number" min="0" max="100"
                    value={scenarios[s]?.probability ?? ''}
                    onChange={e => update('scenarios', { ...scenarios, [s]: { ...scenarios[s], probability: parseInt(e.target.value) } })}
                    className="w-full bg-gray-800 border border-gray-700 text-white text-xs rounded px-2 py-1 focus:border-indigo-500 focus:outline-none mt-0.5"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-600">CAGR (%/an)</label>
                  <input
                    value={scenarios[s]?.cagr ?? ''}
                    onChange={e => update('scenarios', { ...scenarios, [s]: { ...scenarios[s], cagr: e.target.value } })}
                    className="w-full bg-gray-800 border border-gray-700 text-white text-xs rounded px-2 py-1 focus:border-indigo-500 focus:outline-none mt-0.5"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-600">Description</label>
                  <textarea
                    value={scenarios[s]?.description ?? ''}
                    onChange={e => update('scenarios', { ...scenarios, [s]: { ...scenarios[s], description: e.target.value } })}
                    rows={3}
                    className="w-full bg-gray-800 border border-gray-700 text-white text-xs rounded px-2 py-1 focus:border-indigo-500 focus:outline-none resize-none mt-0.5"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Hypothèses H1-H7 ── */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Hypothèses H1-H7</h3>
        <div className="space-y-3">
          {(hypotheses.length > 0
            ? hypotheses
            : Array(7).fill(null).map((_, i) => ({ id: `H${i + 1}`, text: '', status: 'unverified', weight: '' }))
          ).map((h, i) => (
            <div key={i} className="bg-gray-800 border border-gray-700 rounded-lg p-3">
              <div className="flex items-start gap-3">
                <span className="text-indigo-400 font-bold text-sm w-8 flex-shrink-0 mt-0.5">{h.id || `H${i + 1}`}</span>
                <div className="flex-1 space-y-2">
                  <textarea
                    value={h.text || ''}
                    onChange={e => {
                      const next = [...hypotheses]; if (!next[i]) next[i] = {}
                      next[i] = { ...next[i], text: e.target.value }; update('hypotheses', next)
                    }}
                    placeholder="Texte de l'hypothèse…"
                    rows={2}
                    className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none resize-none"
                  />
                  <div className="flex gap-2 flex-wrap items-center">
                    <select
                      value={h.status || 'unverified'}
                      onChange={e => {
                        const next = [...hypotheses]; if (!next[i]) next[i] = {}
                        next[i] = { ...next[i], status: e.target.value }; update('hypotheses', next)
                      }}
                      className="bg-gray-700 border border-gray-600 text-sm rounded px-2 py-1 focus:border-indigo-500 focus:outline-none text-white"
                    >
                      <option value="unverified">Non vérifiée</option>
                      <option value="confirmed">Confirmée</option>
                      <option value="challenged">Challengée</option>
                      <option value="invalidated">Invalidée</option>
                    </select>
                    <input
                      value={h.weight || ''}
                      onChange={e => {
                        const next = [...hypotheses]; if (!next[i]) next[i] = {}
                        next[i] = { ...next[i], weight: e.target.value }; update('hypotheses', next)
                      }}
                      placeholder="Criticité…"
                      className="w-32 bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1 focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  {/* KPI + seuils */}
                  {(h.kpi_metric || h.alert_threshold?.value != null || h.invalidation_threshold?.value != null) && (
                    <div className="flex gap-1.5 flex-wrap mt-1">
                      {h.kpi_metric && (
                        <span className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded">
                          KPI : {h.kpi_metric}{h.kpi_target !== undefined && h.kpi_target !== '' ? ` (cible : ${h.kpi_target}${h.kpi_unit ? ' ' + h.kpi_unit : ''})` : ''}
                        </span>
                      )}
                      {h.alert_threshold?.value != null && (
                        <span className="text-xs bg-orange-950/50 text-orange-400 border border-orange-900/40 px-1.5 py-0.5 rounded">
                          ⚠ {h.alert_threshold.trigger_description || `Alerte < ${h.alert_threshold.value}`}
                        </span>
                      )}
                      {h.invalidation_threshold?.value != null && (
                        <span className="text-xs bg-red-950/50 text-red-400 border border-red-900/40 px-1.5 py-0.5 rounded">
                          ✕ Invalidation : {h.invalidation_threshold.value}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Seuils de cours ── */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Seuils de cours</h3>
        <div className="grid grid-cols-3 gap-3">
          {[
            { key: 'stop_loss',    label: 'Stop loss',   color: 'text-red-400' },
            { key: 'fair_value',   label: 'Juste valeur', color: 'text-indigo-400' },
            { key: 'target_price', label: 'Objectif',    color: 'text-emerald-400' },
          ].map(({ key, label, color }) => (
            <div key={key}>
              <label className={`text-xs block mb-1 ${color}`}>{label}</label>
              <input
                value={price_thr[key] ?? ''}
                onChange={e => update('price_thresholds', { ...price_thr, [key]: e.target.value })}
                placeholder="€ ou $"
                className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          ))}
        </div>
      </section>

      {/* ── Pairs comparables ── */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Pairs comparables</h3>
        <div className="space-y-2">
          {pairs.map((p, i) => (
            <div key={i} className="flex gap-2">
              <input value={p.ticker || ''}
                onChange={e => { const next = [...pairs]; next[i] = { ...next[i], ticker: e.target.value }; update('pairs', next) }}
                placeholder="Ticker"
                className="w-28 bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none font-mono"
              />
              <select value={p.tier || 'T1'}
                onChange={e => { const next = [...pairs]; next[i] = { ...next[i], tier: e.target.value }; update('pairs', next) }}
                className="bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
              >
                <option value="T1">T1</option>
                <option value="T2">T2</option>
                <option value="T3">T3</option>
              </select>
              <input value={p.note || ''}
                onChange={e => { const next = [...pairs]; next[i] = { ...next[i], note: e.target.value }; update('pairs', next) }}
                placeholder="Note…"
                className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
              />
              <button onClick={() => update('pairs', pairs.filter((_, j) => j !== i))}
                className="text-red-500 hover:text-red-400 text-sm px-1">✕</button>
            </div>
          ))}
          <button onClick={() => update('pairs', [...pairs, { ticker: '', tier: 'T1', note: '' }])}
            className="text-xs text-indigo-400 hover:text-indigo-300">+ Ajouter un pair</button>
        </div>
      </section>

      {/* ── Bear Steel Man ── */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Bear Steel Man</h3>
        <textarea
          value={bear_sm}
          onChange={e => update('bear_steel_man', e.target.value)}
          placeholder="Meilleur argument baissier possible…"
          rows={6}
          className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none resize-none"
        />
      </section>

      {/* ── Track Record Analystes ── */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Track record analystes</h3>
        <div className="space-y-2">
          {track_record.map((a, i) => (
            <div key={i} className="flex gap-2">
              <input value={a.analyst || ''}
                onChange={e => { const next = [...track_record]; next[i] = { ...next[i], analyst: e.target.value }; update('track_record_analysts', next) }}
                placeholder="Analyste / Firme"
                className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
              />
              <input value={a.accuracy || ''}
                onChange={e => { const next = [...track_record]; next[i] = { ...next[i], accuracy: e.target.value }; update('track_record_analysts', next) }}
                placeholder="Précision"
                className="w-72 bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
              />
              <button onClick={() => update('track_record_analysts', track_record.filter((_, j) => j !== i))}
                className="text-red-500 hover:text-red-400 text-sm px-1">✕</button>
            </div>
          ))}
          <button onClick={() => update('track_record_analysts', [...track_record, { analyst: '', accuracy: '' }])}
            className="text-xs text-indigo-400 hover:text-indigo-300">+ Ajouter</button>
        </div>
      </section>

    </div>
  )
}
