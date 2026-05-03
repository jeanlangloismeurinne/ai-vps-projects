import { useState } from 'react'
import HypothesisDiff from './HypothesisDiff'
import DataSourcesPanel from './DataSourcesPanel'
import DustRunViewer from './DustRunViewer'
import RecommendationBadge from './RecommendationBadge'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'
const ALERT_COLORS = { green: 'border-emerald-800', orange: 'border-amber-700', red: 'border-red-700' }

export default function MonitoringFeed({ reviews, hypotheses, positionId }) {
  const [openRun, setOpenRun] = useState(null)
  const [subTab, setSubTab] = useState({})
  const [acknowledging, setAcknowledging] = useState(null)

  const acknowledge = async (runId) => {
    setAcknowledging(runId)
    await fetch(`${API}/positions/${positionId}/monitoring/${runId}/acknowledge`, { method: 'PATCH' })
    setAcknowledging(null)
  }

  if (!reviews || reviews.length === 0) {
    return <p className="text-gray-500 text-sm py-4">Aucune revue disponible</p>
  }

  return (
    <div className="space-y-3">
      {reviews.map((rev, i) => {
        const open = openRun === rev.id
        const tab = subTab[rev.id] || 'scores'
        const prevRev = reviews[i + 1]
        const alertColor = ALERT_COLORS[rev.alert_level] || ALERT_COLORS.green

        return (
          <div key={rev.id} className={`border rounded-lg overflow-hidden ${alertColor}`}>
            <button onClick={() => setOpenRun(open ? null : rev.id)}
              className="w-full flex items-center justify-between px-4 py-3 bg-gray-800 text-sm">
              <div className="flex items-center gap-3">
                <span className={`px-1.5 py-0.5 rounded text-xs font-mono ${
                  rev.regime === 1 ? 'bg-purple-900 text-purple-300' :
                  rev.regime === 2 ? 'bg-blue-900 text-blue-300' :
                  'bg-amber-900 text-amber-300'
                }`}>R{rev.regime}</span>
                <span className="text-gray-400 text-xs">
                  {rev.review_date ? new Date(rev.review_date).toLocaleDateString('fr-FR') : '—'}
                </span>
                {rev.recommendation && <RecommendationBadge recommendation={rev.recommendation} alertLevel={rev.alert_level} />}
                {!rev.acknowledged && <span className="text-xs bg-red-900 text-red-300 px-1.5 py-0.5 rounded">Non acquitté</span>}
              </div>
              <span className="text-gray-500">{open ? '▲' : '▼'}</span>
            </button>

            {open && (
              <div className="bg-gray-900 p-4 space-y-3">
                <div className="flex gap-2 border-b border-gray-700 pb-2">
                  {['scores', 'données', 'raisonnement'].map(t => (
                    <button key={t} onClick={() => setSubTab(s => ({ ...s, [rev.id]: t }))}
                      className={`text-xs px-3 py-1 rounded capitalize ${
                        tab === t ? 'bg-blue-800 text-white' : 'text-gray-400 hover:text-gray-200'
                      }`}>{t}</button>
                  ))}
                  {!rev.acknowledged && (
                    <button onClick={() => acknowledge(rev.id)} disabled={acknowledging === rev.id}
                      className="ml-auto text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded">
                      {acknowledging === rev.id ? '…' : 'Acquitter'}
                    </button>
                  )}
                </div>

                {tab === 'scores' && (
                  <HypothesisDiff
                    currentScores={rev.hypotheses_scores_json}
                    previousScores={prevRev?.hypotheses_scores_json}
                    hypotheses={hypotheses}
                  />
                )}
                {tab === 'données' && (
                  <DataSourcesPanel
                    dataSources={rev.data_brief_json?.data_sources}
                    dataQualityFlags={rev.data_quality_flags}
                    agentVersionResearch={rev.agent_version_research}
                    agentVersionPortfolio={rev.agent_version_portfolio}
                    runDate={rev.review_date}
                  />
                )}
                {tab === 'raisonnement' && (
                  <DustRunViewer dustConversationId={rev.dust_conversation_id} defaultOpen />
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
