import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050/api'

const TIMING_STYLE = {
  high:   'bg-emerald-900 text-emerald-300',
  medium: 'bg-blue-900 text-blue-300',
  low:    'bg-red-900 text-red-300',
}

const VERDICT_STYLE = {
  early:       'text-emerald-400',
  timely:      'text-blue-400',
  lagging:     'text-red-400',
  contrarian:  'text-purple-400',
}

export default function Analysts() {
  const [actions, setActions] = useState([])
  const [trackRecords, setTrackRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('track-records')

  useEffect(() => {
    Promise.all([
      fetch(`${API}/analysts?limit=100`).then(r => r.json()),
      fetch(`${API}/analysts/track-records`).then(r => r.json()),
    ]).then(([a, tr]) => {
      setActions(a)
      setTrackRecords(tr)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-gray-400 py-12 text-center">Chargement…</div>

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-white">Analystes</h1>

      <div className="flex gap-2 border-b border-gray-800 pb-0">
        {['track-records', 'actions'].map(t => (
          <button key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? 'border-blue-500 text-white' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
            {t === 'track-records' ? 'Track Records' : 'Historique actions'}
          </button>
        ))}
      </div>

      {tab === 'track-records' && (
        <div>
          {trackRecords.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Aucun track record — enregistrez des actions analystes</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-800">
              <table className="w-full text-sm">
                <thead className="bg-gray-900">
                  <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                    <th className="px-4 py-3">Firm</th>
                    <th className="px-4 py-3">Ticker</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                    <th className="px-4 py-3 text-right">Lagging %</th>
                    <th className="px-4 py-3 text-right">Signal quality</th>
                    <th className="px-4 py-3 text-right">Contrarian</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {trackRecords.map(tr => (
                    <tr key={`${tr.analyst_firm}-${tr.ticker}`} className="hover:bg-gray-800/50">
                      <td className="px-4 py-3 font-medium text-gray-200">{tr.analyst_firm}</td>
                      <td className="px-4 py-3 font-mono text-blue-400">{tr.ticker}</td>
                      <td className="px-4 py-3 text-right text-gray-300">{tr.total_actions}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={parseFloat(tr.lagging_rate) > 0.5 ? 'text-red-400' : 'text-gray-300'}>
                          {(parseFloat(tr.lagging_rate || 0) * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={parseFloat(tr.signal_quality_rate) > 0.4 ? 'text-emerald-400' : 'text-gray-300'}>
                          {(parseFloat(tr.signal_quality_rate || 0) * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-purple-400">{tr.contrarian_calls}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 'actions' && (
        <div>
          {actions.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Aucune action enregistrée</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-800">
              <table className="w-full text-sm">
                <thead className="bg-gray-900">
                  <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Firm</th>
                    <th className="px-4 py-3">Ticker</th>
                    <th className="px-4 py-3">Action</th>
                    <th className="px-4 py-3">Cible</th>
                    <th className="px-4 py-3">Cours</th>
                    <th className="px-4 py-3">Verdict</th>
                    <th className="px-4 py-3">Timing</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {actions.map(a => (
                    <tr key={a.id} className="hover:bg-gray-800/50">
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {a.action_date ? new Date(a.action_date).toLocaleDateString('fr-FR') : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-200">{a.analyst_firm}</td>
                      <td className="px-4 py-3 font-mono text-blue-400">{a.ticker}</td>
                      <td className="px-4 py-3">
                        {a.from_recommendation && a.to_recommendation ? (
                          <span className="text-xs">
                            <span className="text-gray-400">{a.from_recommendation}</span>
                            <span className="text-gray-600 mx-1">→</span>
                            <span className="text-gray-200">{a.to_recommendation}</span>
                          </span>
                        ) : (
                          <span className="text-gray-300">{a.action_type || '—'}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-300">
                        {a.to_target != null ? `€${a.to_target}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-300">
                        {a.stock_price_at_action != null ? `€${a.stock_price_at_action}` : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium ${VERDICT_STYLE[a.verdict] || 'text-gray-500'}`}>
                          {a.verdict || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {a.timing_quality ? (
                          <span className={`text-xs px-1.5 py-0.5 rounded ${TIMING_STYLE[a.timing_quality] || ''}`}>
                            {a.timing_quality}
                          </span>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
