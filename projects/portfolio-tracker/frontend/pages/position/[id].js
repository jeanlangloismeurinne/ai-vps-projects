import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import HypothesisScorecard from '../../components/HypothesisScorecard'
import ThesisTimeline from '../../components/ThesisTimeline'
import SectorPulseLog from '../../components/SectorPulseLog'
import PeerComparison from '../../components/PeerComparison'
import RecommendationBadge from '../../components/RecommendationBadge'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050/api'

function Section({ title, children }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
      <h2 className="text-base font-semibold text-gray-200 mb-4">{title}</h2>
      {children}
    </div>
  )
}

export default function PositionDetail() {
  const router = useRouter()
  const { id } = router.query
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(null)

  useEffect(() => {
    if (!id) return
    fetch(`${API}/positions/${id}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [id])

  const triggerRegime = async (regime) => {
    const ticker = data?.position?.ticker
    if (!ticker) return
    setTriggering(regime)
    try {
      await fetch(`${API}/trigger/regime${regime}/${ticker}`, { method: 'POST' })
      alert(`Régime ${regime} déclenché pour ${ticker}`)
    } catch (e) {
      alert('Erreur lors du déclenchement')
    }
    setTriggering(null)
  }

  if (loading) return <div className="text-gray-400 py-12 text-center">Chargement…</div>
  if (!data) return <div className="text-red-400 py-12 text-center">Position introuvable</div>

  const { position, thesis, hypotheses, reviews, peers, sector_pulses } = data
  const lastReview = reviews?.[0]

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-white font-mono">{position.ticker}</h1>
            <span className="text-xl text-gray-400">{position.company_name}</span>
          </div>
          {thesis?.thesis_one_liner && (
            <p className="text-gray-300 mt-2 max-w-2xl italic">&ldquo;{thesis.thesis_one_liner}&rdquo;</p>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          <button onClick={() => triggerRegime(2)}
            disabled={triggering === 2}
            className="px-3 py-1.5 text-xs bg-blue-800 hover:bg-blue-700 text-blue-200 rounded font-medium disabled:opacity-50">
            {triggering === 2 ? '…' : 'Régime 2'}
          </button>
          <button onClick={() => triggerRegime(3)}
            disabled={triggering === 3}
            className="px-3 py-1.5 text-xs bg-amber-800 hover:bg-amber-700 text-amber-200 rounded font-medium disabled:opacity-50">
            {triggering === 3 ? '…' : 'Régime 3'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Prix entrée', value: position.entry_price != null ? `€${Number(position.entry_price).toFixed(2)}` : '—' },
          { label: 'Allocation', value: position.allocation_pct != null ? `${position.allocation_pct}%` : '—' },
          { label: 'Secteur', value: position.sector_schema },
          { label: 'Exchange', value: position.exchange },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className="text-base font-semibold text-white">{value}</p>
          </div>
        ))}
      </div>

      {lastReview && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 flex items-center gap-4">
          <span className="text-sm text-gray-400">Dernière revue :</span>
          <RecommendationBadge recommendation={lastReview.recommendation} alertLevel={lastReview.alert_level} />
          <span className="text-sm text-gray-500">
            {lastReview.review_date ? new Date(lastReview.review_date).toLocaleDateString('fr-FR') : ''}
          </span>
          {lastReview.rationale && (
            <span className="text-sm text-gray-300 truncate">{lastReview.rationale}</span>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Section title="Hypothèses fondatrices">
          <HypothesisScorecard hypotheses={hypotheses} />
        </Section>

        <Section title="Historique des revues">
          <ThesisTimeline reviews={reviews} />
        </Section>

        <Section title="Sector Pulses">
          <SectorPulseLog pulses={sector_pulses} />
        </Section>

        <Section title="Comparaison peers">
          <PeerComparison peers={peers} />
        </Section>
      </div>

      {thesis?.scenarios_json && (
        <Section title="Scénarios 5 ans">
          <ScenarioTable scenarios={typeof thesis.scenarios_json === 'string'
            ? JSON.parse(thesis.scenarios_json) : thesis.scenarios_json} />
        </Section>
      )}
    </div>
  )
}

function ScenarioTable({ scenarios }) {
  if (!scenarios) return null
  const items = ['bear', 'central', 'bull']
  const colors = { bear: 'text-red-400', central: 'text-blue-400', bull: 'text-emerald-400' }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b border-gray-700">
            <th className="pb-2 pr-4">Scénario</th>
            <th className="pb-2 pr-4">EPS CAGR</th>
            <th className="pb-2 pr-4">PE sortie</th>
            <th className="pb-2 pr-4">Cible 5y</th>
            <th className="pb-2">CAGR total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {items.map(key => {
            const s = scenarios[key] || {}
            return (
              <tr key={key}>
                <td className={`py-2 pr-4 font-semibold capitalize ${colors[key]}`}>{key}</td>
                <td className="py-2 pr-4 text-gray-300">{s.eps_cagr_pct != null ? `${s.eps_cagr_pct}%` : '—'}</td>
                <td className="py-2 pr-4 text-gray-300">{s.exit_pe != null ? `${s.exit_pe}x` : '—'}</td>
                <td className="py-2 pr-4 text-gray-300">{s.price_target_5y != null ? `€${s.price_target_5y}` : '—'}</td>
                <td className={`py-2 font-semibold ${colors[key]}`}>{s.cagr_pct != null ? `${s.cagr_pct}%` : '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
