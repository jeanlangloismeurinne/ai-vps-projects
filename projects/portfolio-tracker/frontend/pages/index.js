import { useState, useEffect } from 'react'
import Link from 'next/link'
import RecommendationBadge from '../components/RecommendationBadge'
import MarketTemperatureBadge from '../components/MarketTemperatureBadge'
import CashManagementWidget from '../components/CashManagementWidget'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050/api'

function PnlCell({ pct }) {
  if (pct == null) return <span className="text-gray-600">—</span>
  return (
    <span className={`font-medium ${pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
      {pct > 0 ? '+' : ''}{pct.toFixed(1)}%
    </span>
  )
}

export default function Dashboard() {
  const [snapshot, setSnapshot] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/portfolio`)
      .then(r => r.json())
      .then(data => { setSnapshot(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-gray-400 py-12 text-center">Chargement…</div>
  if (!snapshot) return <div className="text-red-400 py-12 text-center">Erreur de chargement</div>

  const positions = snapshot.positions || []
  const flags = snapshot.concentration_flags || []
  const metrics = snapshot.portfolio_metrics || {}

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Portfolio</h1>
        <div className="flex gap-4 text-sm text-gray-400">
          <span>{metrics.total_positions || 0} positions</span>
          <span>Investi : {(metrics.total_allocation_pct || 0).toFixed(1)}%</span>
          <span className="text-gray-600 text-xs">
            {snapshot.snapshot_date ? new Date(snapshot.snapshot_date).toLocaleString('fr-FR') : ''}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <MarketTemperatureBadge showCash />
      </div>
      <CashManagementWidget />

      {flags.length > 0 && (
        <div className="bg-amber-900/30 border border-amber-700 rounded-lg p-4">
          <p className="text-amber-300 font-medium text-sm mb-1">⚠️ Flags de concentration</p>
          {flags.map((f, i) => (
            <p key={i} className="text-amber-200 text-sm">
              {f.type === 'sector_concentration'
                ? `Secteur ${f.sector} : ${f.total_pct?.toFixed(1)}% (seuil ${f.threshold_pct}%)`
                : `Position ${f.ticker} : ${f.total_pct?.toFixed(1)}% (seuil ${f.threshold_pct}%)`}
            </p>
          ))}
        </div>
      )}

      {positions.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg">Aucune position active</p>
          <p className="text-sm mt-2">Bootstrap via l&apos;API — cf. guide démarrage étape 6</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-800">
          <table className="w-full text-sm">
            <thead className="bg-gray-900">
              <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                <th className="px-4 py-3">Ticker</th>
                <th className="px-4 py-3">Société</th>
                <th className="px-4 py-3">Secteur</th>
                <th className="px-4 py-3 text-right">Alloc.</th>
                <th className="px-4 py-3 text-right">P. Entrée</th>
                <th className="px-4 py-3 text-right">P. Actuel</th>
                <th className="px-4 py-3 text-right">P&L</th>
                <th className="px-4 py-3">Reco.</th>
                <th className="px-4 py-3">Dernière revue</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {positions.map(p => (
                <tr key={p.id} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3">
                    <Link href={`/position/${p.id}`}
                      className="font-mono font-bold text-blue-400 hover:text-blue-300">
                      {p.ticker}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-300">{p.company_name}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs bg-gray-800 px-1.5 py-0.5 rounded text-gray-400">
                      {p.sector_schema}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {p.allocation_pct != null ? `${p.allocation_pct.toFixed(1)}%` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {p.entry_price != null ? `€${p.entry_price.toFixed(2)}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {p.current_price != null ? `€${p.current_price.toFixed(2)}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <PnlCell pct={p.unrealized_pnl_pct} />
                  </td>
                  <td className="px-4 py-3">
                    <RecommendationBadge recommendation={p.recommendation} alertLevel={p.alert_level} />
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {p.last_review_date
                      ? new Date(p.last_review_date).toLocaleDateString('fr-FR')
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
