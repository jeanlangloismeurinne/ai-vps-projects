import { useState, useEffect } from 'react'
import ScoutResultPanel from './ScoutResultPanel'
import ThesisChat from './ThesisChat'
import ThesisValidationPanel from './ThesisValidationPanel'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function WatchlistItemDrawer({ itemId, onClose, onUpdate }) {
  const [item, setItem] = useState(null)
  const [tab, setTab] = useState('analyse')
  const [launching, setLaunching] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)

  const load = () => {
    if (!itemId) return
    fetch(`${API}/watchlist/${itemId}/full`)
      .then(r => r.json())
      .then(setItem)
      .catch(() => {})
  }

  useEffect(() => { load() }, [itemId])

  // Polling job
  useEffect(() => {
    if (!jobId || jobStatus === 'done' || jobStatus === 'error') return
    const interval = setInterval(() => {
      fetch(`${API}/trigger/status/${jobId}`)
        .then(r => r.json())
        .then(d => {
          setJobStatus(d.status)
          if (d.status === 'done') { clearInterval(interval); load() }
          if (d.status === 'error') clearInterval(interval)
        })
        .catch(() => clearInterval(interval))
    }, 3000)
    return () => clearInterval(interval)
  }, [jobId, jobStatus])

  const launchScout = async () => {
    if (!item) return
    setLaunching(true)
    try {
      const r = await fetch(`${API}/trigger/regime0/${item.ticker}?watchlist_id=${itemId}`, { method: 'POST' })
      const d = await r.json()
      setJobId(d.job_id)
      setJobStatus('pending')
    } catch (e) {}
    setLaunching(false)
  }

  if (!itemId) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-full max-w-2xl bg-gray-900 border-l border-gray-700 overflow-y-auto flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <div>
            <span className="font-mono font-bold text-white text-lg">{item?.ticker || '…'}</span>
            <span className="ml-2 text-gray-400">{item?.company_name}</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">✕</button>
        </div>

        {jobStatus && jobStatus !== 'done' && jobStatus !== 'error' && (
          <div className="px-6 py-2 bg-blue-900/30 text-blue-300 text-sm border-b border-gray-700">
            Scout en cours… ({jobStatus})
          </div>
        )}
        {jobStatus === 'error' && (
          <div className="px-6 py-2 bg-red-900/30 text-red-300 text-sm border-b border-gray-700">
            Erreur durant l&apos;analyse
          </div>
        )}

        <div className="flex border-b border-gray-700">
          {['analyse', 'chat', 'validation'].map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-5 py-2.5 text-sm font-medium capitalize transition-colors ${
                tab === t ? 'border-b-2 border-blue-500 text-white' : 'text-gray-400 hover:text-gray-200'
              }`}>
              {t === 'analyse' ? 'Analyse' : t === 'chat' ? 'Chat' : 'Validation'}
            </button>
          ))}
        </div>

        <div className="flex-1 p-6">
          {tab === 'analyse' && item && (
            <ScoutResultPanel item={item} onRelance={launchScout} />
          )}
          {tab === 'chat' && item && (
            <ThesisChat
              entityType="watchlist"
              entityId={itemId}
              ticker={item.ticker}
              isValidated={item.thesis_status === 'validated'}
            />
          )}
          {tab === 'validation' && item && (
            <ThesisValidationPanel
              entityType="watchlist"
              entityId={itemId}
              item={item}
              onValidated={() => { load(); onUpdate?.() }}
            />
          )}
        </div>
      </div>
    </div>
  )
}
