import RecommendationBadge from './RecommendationBadge'

const REGIME_LABEL = { 1: 'Thesis', 2: 'Routine', 3: 'Decision' }

export default function ThesisTimeline({ reviews = [] }) {
  if (!reviews.length) return <p className="text-gray-500 text-sm">Aucune revue.</p>
  return (
    <div className="relative">
      <div className="absolute left-3 top-0 bottom-0 w-px bg-gray-700" />
      <div className="space-y-4">
        {reviews.map(r => (
          <div key={r.id} className="relative pl-8">
            <div className="absolute left-0.5 top-1.5 w-5 h-5 rounded-full bg-gray-700 border-2 border-gray-500 flex items-center justify-center">
              <span className="text-xs text-gray-300">{r.regime}</span>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div className="flex items-center justify-between gap-2 mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">
                    {r.review_date ? new Date(r.review_date).toLocaleDateString('fr-FR') : '—'}
                  </span>
                  <span className="text-xs bg-gray-700 px-1.5 py-0.5 rounded text-gray-300">
                    Régime {r.regime} — {REGIME_LABEL[r.regime]}
                  </span>
                </div>
                <RecommendationBadge recommendation={r.recommendation} alertLevel={r.alert_level} />
              </div>
              {r.rationale && <p className="text-sm text-gray-300">{r.rationale}</p>}
              {r.triggered_by && (
                <p className="text-xs text-gray-500 mt-1">Déclencheur : {r.triggered_by}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
