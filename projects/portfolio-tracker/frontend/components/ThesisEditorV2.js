export default function ThesisEditorV2({ thesisJson, onChange }) {
  if (!thesisJson) {
    return (
      <div className="flex items-center justify-center h-full text-gray-600 text-sm text-center px-8">
        <div>
          <p className="text-3xl mb-3">📊</p>
          <p>La thèse est vide</p>
          <p className="mt-1 text-gray-500">Cliquez sur <span className="text-indigo-400 font-medium">«Actualiser la thèse →»</span></p>
        </div>
      </div>
    )
  }

  const update = (key, value) => onChange({ ...thesisJson, [key]: value })

  const hypotheses = thesisJson.hypotheses || []
  const scenarios = thesisJson.scenarios || {}
  const price_thresholds = thesisJson.price_thresholds || {}
  const pairs = thesisJson.pairs || []
  const bear_steel_man = thesisJson.bear_steel_man || ''
  const track_record = thesisJson.track_record_analysts || []

  return (
    <div className="space-y-6 overflow-y-auto p-4">
      {/* Scenarios */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Scénarios</h3>
        <div className="grid grid-cols-3 gap-3">
          {['bear', 'central', 'bull'].map(s => (
            <div key={s} className={`rounded-lg p-3 border ${
              s === 'bear' ? 'border-red-800 bg-red-950/30' :
              s === 'bull' ? 'border-emerald-800 bg-emerald-950/30' :
              'border-indigo-800 bg-indigo-950/30'
            }`}>
              <p className={`text-xs font-semibold uppercase mb-2 ${
                s === 'bear' ? 'text-red-400' : s === 'bull' ? 'text-emerald-400' : 'text-indigo-400'
              }`}>{s}</p>
              <div className="space-y-1.5">
                <div>
                  <label className="text-xs text-gray-600">Proba. (%)</label>
                  <input
                    type="number" min="0" max="100"
                    value={scenarios[s]?.probability || ''}
                    onChange={e => update('scenarios', { ...scenarios, [s]: { ...scenarios[s], probability: parseInt(e.target.value) } })}
                    className="w-full bg-gray-800 border border-gray-700 text-white text-xs rounded px-2 py-1 focus:border-indigo-500 focus:outline-none mt-0.5"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-600">CAGR (%/an)</label>
                  <input
                    value={scenarios[s]?.cagr || ''}
                    onChange={e => update('scenarios', { ...scenarios, [s]: { ...scenarios[s], cagr: e.target.value } })}
                    className="w-full bg-gray-800 border border-gray-700 text-white text-xs rounded px-2 py-1 focus:border-indigo-500 focus:outline-none mt-0.5"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-600">Description</label>
                  <textarea
                    value={scenarios[s]?.description || ''}
                    onChange={e => update('scenarios', { ...scenarios, [s]: { ...scenarios[s], description: e.target.value } })}
                    rows={2}
                    className="w-full bg-gray-800 border border-gray-700 text-white text-xs rounded px-2 py-1 focus:border-indigo-500 focus:outline-none resize-none mt-0.5"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Hypotheses H1-H7 */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Hypothèses H1-H7</h3>
        <div className="space-y-3">
          {(hypotheses.length > 0 ? hypotheses : Array(7).fill(null).map((_, i) => ({ id: `H${i + 1}`, text: '', status: 'unverified', weight: '' }))).map((h, i) => (
            <div key={i} className="bg-gray-800 border border-gray-700 rounded-lg p-3">
              <div className="flex items-start gap-3">
                <span className="text-indigo-400 font-bold text-sm w-8 flex-shrink-0">{h.id || `H${i + 1}`}</span>
                <div className="flex-1 space-y-2">
                  <textarea
                    value={h.text || ''}
                    onChange={e => {
                      const next = [...hypotheses]
                      if (!next[i]) next[i] = {}
                      next[i] = { ...next[i], text: e.target.value }
                      update('hypotheses', next)
                    }}
                    placeholder="Texte de l'hypothèse…"
                    rows={2}
                    className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none resize-none"
                  />
                  <div className="flex gap-2">
                    <select
                      value={h.status || 'unverified'}
                      onChange={e => {
                        const next = [...hypotheses]
                        if (!next[i]) next[i] = {}
                        next[i] = { ...next[i], status: e.target.value }
                        update('hypotheses', next)
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
                        const next = [...hypotheses]
                        if (!next[i]) next[i] = {}
                        next[i] = { ...next[i], weight: e.target.value }
                        update('hypotheses', next)
                      }}
                      placeholder="Poids…"
                      className="w-24 bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1 focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Price Thresholds */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Seuils de cours</h3>
        <div className="grid grid-cols-3 gap-3">
          {['stop_loss', 'fair_value', 'target_price'].map(key => (
            <div key={key}>
              <label className="text-xs text-gray-500 block mb-1">{key.replace(/_/g, ' ')}</label>
              <input
                value={price_thresholds[key] || ''}
                onChange={e => update('price_thresholds', { ...price_thresholds, [key]: e.target.value })}
                placeholder="€ ou %"
                className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          ))}
        </div>
      </section>

      {/* Pairs */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Pairs comparables</h3>
        <div className="space-y-2">
          {pairs.map((p, i) => (
            <div key={i} className="flex gap-2">
              <input
                value={p.ticker || ''}
                onChange={e => {
                  const next = [...pairs]; next[i] = { ...next[i], ticker: e.target.value }; update('pairs', next)
                }}
                placeholder="Ticker"
                className="w-28 bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none font-mono"
              />
              <select
                value={p.tier || 'T1'}
                onChange={e => {
                  const next = [...pairs]; next[i] = { ...next[i], tier: e.target.value }; update('pairs', next)
                }}
                className="bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
              >
                <option value="T1">T1</option>
                <option value="T2">T2</option>
                <option value="T3">T3</option>
              </select>
              <input
                value={p.note || ''}
                onChange={e => {
                  const next = [...pairs]; next[i] = { ...next[i], note: e.target.value }; update('pairs', next)
                }}
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

      {/* Bear Steel Man */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Bear Steel Man</h3>
        <textarea
          value={bear_steel_man}
          onChange={e => update('bear_steel_man', e.target.value)}
          placeholder="Meilleur argument baissier possible…"
          rows={4}
          className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-3 py-2 focus:border-indigo-500 focus:outline-none resize-none"
        />
      </section>

      {/* Track Record Analystes */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Track record analystes</h3>
        <div className="space-y-2">
          {track_record.map((a, i) => (
            <div key={i} className="flex gap-2">
              <input
                value={a.analyst || ''}
                onChange={e => {
                  const next = [...track_record]; next[i] = { ...next[i], analyst: e.target.value }; update('track_record_analysts', next)
                }}
                placeholder="Analyste / Firme"
                className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
              />
              <input
                value={a.accuracy || ''}
                onChange={e => {
                  const next = [...track_record]; next[i] = { ...next[i], accuracy: e.target.value }; update('track_record_analysts', next)
                }}
                placeholder="Précision"
                className="w-24 bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
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
