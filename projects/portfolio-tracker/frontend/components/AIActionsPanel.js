import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function AIActionsPanel({ ticker, hasThesis, onDone }) {
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [activeRegime, setActiveRegime] = useState(null)

  useEffect(() => {
    if (!jobId || jobStatus === 'done' || jobStatus === 'error') return
    const interval = setInterval(() => {
      fetch(`${API}/trigger/status/${jobId}`)
        .then(r => r.json())
        .then(d => {
          setJobStatus(d.status)
          if (d.status === 'done') { clearInterval(interval); onDone?.() }
          if (d.status === 'error') clearInterval(interval)
        })
        .catch(() => clearInterval(interval))
    }, 3000)
    return () => clearInterval(interval)
  }, [jobId, jobStatus])

  const trigger = async (regime) => {
    setActiveRegime(regime)
    setJobStatus('pending')
    try {
      const r = await fetch(`${API}/trigger/regime${regime}/${ticker}`, { method: 'POST' })
      const d = await r.json()
      setJobId(d.job_id)
    } catch (e) {
      setJobStatus('error')
    }
  }

  const statusLabel = { pending: 'En attente…', running: 'En cours…', done: '✓ Terminé', error: '✗ Erreur' }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-300">Actions IA</h3>
      <div className="flex gap-2 flex-wrap">
        {!hasThesis && (
          <button onClick={() => trigger(1)} disabled={!!jobId && jobStatus !== 'done' && jobStatus !== 'error'}
            className="px-3 py-1.5 text-xs bg-purple-800 hover:bg-purple-700 text-purple-200 rounded font-medium disabled:opacity-50">
            Régime 1 — Thèse
          </button>
        )}
        {hasThesis && (
          <button onClick={() => trigger(2)} disabled={!!jobId && jobStatus !== 'done' && jobStatus !== 'error'}
            className="px-3 py-1.5 text-xs bg-blue-800 hover:bg-blue-700 text-blue-200 rounded font-medium disabled:opacity-50">
            Régime 2 — Revue
          </button>
        )}
        <button onClick={() => trigger(3)} disabled={!!jobId && jobStatus !== 'done' && jobStatus !== 'error'}
          className="px-3 py-1.5 text-xs bg-amber-800 hover:bg-amber-700 text-amber-200 rounded font-medium disabled:opacity-50">
          Régime 3 — Décision
        </button>
      </div>
      {jobStatus && (
        <div className={`text-xs px-2 py-1 rounded ${
          jobStatus === 'done' ? 'bg-emerald-900/30 text-emerald-300' :
          jobStatus === 'error' ? 'bg-red-900/30 text-red-300' :
          'bg-blue-900/30 text-blue-300'
        }`}>
          Régime {activeRegime} : {statusLabel[jobStatus] || jobStatus}
        </div>
      )}
    </div>
  )
}
