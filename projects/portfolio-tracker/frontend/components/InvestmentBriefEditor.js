import { useState } from 'react'

function ScreeningCriteria({ criteria = [], onChange }) {
  const CRITERIA_LABELS = [
    'Qualité du business',
    'Avantage compétitif durable',
    'Management aligné',
    'Valorisation raisonnable',
    'Catalyseur identifiable',
  ]
  const list = criteria.length > 0 ? criteria : CRITERIA_LABELS.map(label => ({ label, pass: null, note: '' }))

  return (
    <div className="space-y-2">
      {list.map((c, i) => (
        <div key={i} className="flex items-center gap-3">
          <button
            onClick={() => {
              const next = [...list]
              next[i] = { ...next[i], pass: next[i].pass === true ? null : true }
              onChange(next)
            }}
            className={`w-7 h-7 rounded-full text-sm font-bold flex-shrink-0 transition-colors ${
              c.pass === true ? 'bg-emerald-700 text-emerald-100' : 'bg-gray-700 text-gray-500'
            }`}
          >✓</button>
          <button
            onClick={() => {
              const next = [...list]
              next[i] = { ...next[i], pass: next[i].pass === false ? null : false }
              onChange(next)
            }}
            className={`w-7 h-7 rounded-full text-sm font-bold flex-shrink-0 transition-colors ${
              c.pass === false ? 'bg-red-700 text-red-100' : 'bg-gray-700 text-gray-500'
            }`}
          >✗</button>
          <span className="text-sm text-gray-300 flex-1">{c.label}</span>
          <input
            value={c.note || ''}
            onChange={e => {
              const next = [...list]
              next[i] = { ...next[i], note: e.target.value }
              onChange(next)
            }}
            placeholder="Note…"
            className="text-xs bg-gray-800 border border-gray-700 text-gray-400 rounded px-2 py-1 w-40 focus:border-indigo-500 focus:outline-none"
          />
        </div>
      ))}
    </div>
  )
}

function ProtoHypotheses({ items = [], onChange }) {
  const [newH, setNewH] = useState('')
  const add = () => {
    if (!newH.trim()) return
    onChange([...items, { text: newH.trim(), confidence: 'medium' }])
    setNewH('')
  }
  return (
    <div className="space-y-2">
      {items.map((h, i) => (
        <div key={i} className="flex items-start gap-2">
          <span className="text-indigo-400 text-sm mt-2">H{i + 1}</span>
          <textarea
            value={h.text}
            onChange={e => {
              const next = [...items]
              next[i] = { ...next[i], text: e.target.value }
              onChange(next)
            }}
            rows={3}
            className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none resize-none"
          />
          <select
            value={h.confidence || 'medium'}
            onChange={e => {
              const next = [...items]
              next[i] = { ...next[i], confidence: e.target.value }
              onChange(next)
            }}
            className="bg-gray-800 border border-gray-700 text-gray-400 text-xs rounded px-1 py-1.5 focus:border-indigo-500 focus:outline-none"
          >
            <option value="high">Haute</option>
            <option value="medium">Moyenne</option>
            <option value="low">Faible</option>
          </select>
          <button onClick={() => onChange(items.filter((_, j) => j !== i))}
            className="text-red-500 hover:text-red-400 text-sm px-1">✕</button>
        </div>
      ))}
      <div className="flex gap-2">
        <input
          value={newH}
          onChange={e => setNewH(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="Nouvelle hypothèse…"
          className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
        />
        <button onClick={add} disabled={!newH.trim()}
          className="text-xs bg-indigo-700 hover:bg-indigo-600 disabled:opacity-40 text-white px-3 py-1.5 rounded">
          Ajouter
        </button>
      </div>
    </div>
  )
}

export default function InvestmentBriefEditor({ briefJson, onChange }) {
  if (!briefJson) {
    return (
      <div className="flex items-center justify-center h-full text-gray-600 text-sm text-center px-8">
        <div>
          <p className="text-3xl mb-3">📋</p>
          <p>Cliquez sur <span className="text-indigo-400 font-medium">«Actualiser le brief →»</span></p>
          <p className="mt-1">pour générer le brief d&apos;investissement</p>
        </div>
      </div>
    )
  }

  const update = (key, value) => onChange({ ...briefJson, [key]: value })

  const rec = briefJson.verdict?.recommendation
  const screeningFailed = briefJson.screening?.criteria?.filter(c => c.pass === false).length >= 3

  return (
    <div className="space-y-5 overflow-y-auto p-4">
      {/* Screening Failed State */}
      {screeningFailed && (
        <div className="bg-gray-800 border border-red-700 rounded-lg p-4">
          <p className="text-red-300 font-semibold mb-2">⛔ Screening échoué</p>
          {briefJson.screening?.criteria?.filter(c => c.pass === false).map((c, i) => (
            <p key={i} className="text-red-400 text-sm">• {c.label || c.reason}</p>
          ))}
          <button
            onClick={() => update('screening', { ...briefJson.screening, override: true })}
            className="mt-3 text-xs text-amber-400 hover:text-amber-300 border border-amber-700 rounded px-3 py-1.5 transition-colors"
          >
            Passer outre et analyser quand même
          </button>
        </div>
      )}

      {/* Monitor State */}
      {rec === 'MONITOR' && (
        <div className="bg-indigo-950/60 border border-indigo-700 rounded-lg p-4">
          <p className="text-indigo-300 font-semibold mb-3">📌 Recommandation : MONITOR</p>
          <div className="flex gap-2">
            <button className="text-sm bg-indigo-700 hover:bg-indigo-600 text-white px-3 py-1.5 rounded">
              Définir un seuil d&apos;entrée →
            </button>
          </div>
        </div>
      )}

      {/* Section: Screening */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Screening</h3>
        <ScreeningCriteria
          criteria={briefJson.screening?.criteria || []}
          onChange={val => update('screening', { ...briefJson.screening, criteria: val })}
        />
      </section>

      {/* Section: Anomalie */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Anomalie détectée</h3>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Score /10</label>
            <input
              type="number" min="0" max="10" step="0.1"
              value={briefJson.anomalie?.score || ''}
              onChange={e => update('anomalie', { ...briefJson.anomalie, score: parseFloat(e.target.value) })}
              className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-500 block mb-1">Facteurs</label>
            <textarea
              value={briefJson.anomalie?.facteurs || ''}
              onChange={e => update('anomalie', { ...briefJson.anomalie, facteurs: e.target.value })}
              placeholder="Facteurs clés de l'anomalie…"
              rows={4}
              className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none resize-none"
            />
          </div>
        </div>
      </section>

      {/* Section: Analogie */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Analogie historique</h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Société de référence</label>
            <input
              value={briefJson.analogie?.societe || ''}
              onChange={e => update('analogie', { ...briefJson.analogie, societe: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Confiance (%)</label>
            <input
              type="number" min="0" max="100"
              value={briefJson.analogie?.confiance || ''}
              onChange={e => update('analogie', { ...briefJson.analogie, confiance: parseInt(e.target.value) })}
              className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
            />
          </div>
        </div>
        <textarea
          value={briefJson.analogie?.description || ''}
          onChange={e => update('analogie', { ...briefJson.analogie, description: e.target.value })}
          placeholder="Description de l'analogie…"
          rows={4}
          className="mt-2 w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none resize-none"
        />
      </section>

      {/* Section: Catalyseurs */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Catalyseurs</h3>
        <div className="space-y-1">
          {(briefJson.catalyseurs || []).map((c, i) => (
            <div key={i} className="flex gap-2">
              <input
                value={c}
                onChange={e => {
                  const next = [...(briefJson.catalyseurs || [])]
                  next[i] = e.target.value
                  update('catalyseurs', next)
                }}
                className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
              />
              <button onClick={() => update('catalyseurs', briefJson.catalyseurs.filter((_, j) => j !== i))}
                className="text-red-500 hover:text-red-400 text-sm">✕</button>
            </div>
          ))}
          <button
            onClick={() => update('catalyseurs', [...(briefJson.catalyseurs || []), ''])}
            className="text-xs text-indigo-400 hover:text-indigo-300"
          >+ Ajouter un catalyseur</button>
        </div>
      </section>

      {/* Section: Proto-hypothèses */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Proto-hypothèses</h3>
        <ProtoHypotheses
          items={briefJson.proto_hypotheses || []}
          onChange={val => update('proto_hypotheses', val)}
        />
      </section>

      {/* Section: Verdict */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Verdict</h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Conviction /10</label>
            <input
              type="number" min="0" max="10" step="0.5"
              value={briefJson.verdict?.conviction || ''}
              onChange={e => update('verdict', { ...briefJson.verdict, conviction: parseFloat(e.target.value) })}
              className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Recommandation</label>
            <select
              value={briefJson.verdict?.recommendation || ''}
              onChange={e => update('verdict', { ...briefJson.verdict, recommendation: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">—</option>
              <option value="PROCEED">PROCEED</option>
              <option value="MONITOR">MONITOR</option>
              <option value="PASS">PASS</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Downside floor</label>
            <input
              value={briefJson.verdict?.downside_floor || ''}
              onChange={e => update('verdict', { ...briefJson.verdict, downside_floor: e.target.value })}
              placeholder="ex. -20%"
              className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-500 block mb-1">Top risques</label>
            <div className="space-y-1">
              {(briefJson.verdict?.top_risques || []).map((r, i) => (
                <div key={i} className="flex gap-2">
                  <textarea
                    value={r}
                    onChange={e => {
                      const next = [...(briefJson.verdict?.top_risques || [])]
                      next[i] = e.target.value
                      update('verdict', { ...briefJson.verdict, top_risques: next })
                    }}
                    rows={2}
                    className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1.5 focus:border-indigo-500 focus:outline-none resize-none"
                  />
                  <button
                    onClick={() => update('verdict', { ...briefJson.verdict, top_risques: (briefJson.verdict?.top_risques || []).filter((_, j) => j !== i) })}
                    className="text-red-500 hover:text-red-400 text-sm self-start pt-1.5"
                  >✕</button>
                </div>
              ))}
              <button
                onClick={() => update('verdict', { ...briefJson.verdict, top_risques: [...(briefJson.verdict?.top_risques || []), ''] })}
                className="text-xs text-indigo-400 hover:text-indigo-300"
              >+ Ajouter un risque</button>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
