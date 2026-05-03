export default function DataSourcesPanel({ dataSources, dataQualityFlags, agentVersionResearch, agentVersionPortfolio, runDate }) {
  if (!dataSources) return null
  const sources = ['m1', 'm2', 'm3']
  const labels = { m1: 'M1 — Quantitatif', m2: 'M2 — Événementiel', m3: 'M3 — Qualitatif' }

  return (
    <div className="space-y-4">
      {runDate && (
        <div className="flex gap-4 text-xs text-gray-500">
          <span>Run : {new Date(runDate).toLocaleString('fr-FR')}</span>
          {agentVersionResearch && <span>Research v{agentVersionResearch}</span>}
          {agentVersionPortfolio && <span>Portfolio v{agentVersionPortfolio}</span>}
        </div>
      )}

      {sources.map(src => {
        const s = dataSources[src]
        if (!s) return null
        return (
          <div key={src} className="bg-gray-800 rounded-lg p-3 space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs font-medium text-gray-300">{labels[src]}</span>
              <span className="text-xs text-gray-500">{s.source}</span>
            </div>
            {s.missing_fields?.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {s.missing_fields.map(f => (
                  <span key={f} className="text-xs px-1.5 py-0.5 bg-amber-900/30 text-amber-400 border border-amber-800 rounded">
                    {f} manquant
                  </span>
                ))}
              </div>
            )}
          </div>
        )
      })}

      {dataQualityFlags?.length > 0 && (
        <div className="bg-amber-900/20 border border-amber-800 rounded p-3">
          <p className="text-xs text-amber-300 font-medium mb-1">Alertes qualité données</p>
          {dataQualityFlags.map((f, i) => (
            <p key={i} className="text-xs text-amber-200">{f}</p>
          ))}
        </div>
      )}
    </div>
  )
}
