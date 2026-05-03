import { useState, useEffect } from 'react'
import WatchlistAlertBanner from '../components/WatchlistAlertBanner'
import ReadinessWidget from '../components/ReadinessWidget'
import WatchlistItemDrawer from '../components/WatchlistItemDrawer'
import PromoteToPositionDrawer from '../components/PromoteToPositionDrawer'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

function GapBadge({ gap }) {
  if (gap == null) return <span className="text-gray-600">—</span>
  const g = Number(gap)
  const color = g <= 0 ? 'text-emerald-400' : g <= 5 ? 'text-amber-400' : 'text-gray-400'
  return <span className={`font-medium ${color}`}>{g > 0 ? '+' : ''}{g.toFixed(1)}%</span>
}

function ConvictionBadge({ signal }) {
  if (!signal) return <span className="text-gray-600">—</span>
  const colors = { strong: 'bg-emerald-900 text-emerald-300', moderate: 'bg-blue-900 text-blue-300', weak: 'bg-amber-900 text-amber-300', avoid: 'bg-red-900 text-red-300' }
  return <span className={`text-xs px-1.5 py-0.5 rounded ${colors[signal] || 'bg-gray-800 text-gray-400'}`}>{signal}</span>
}

function ThesisStatusBadge({ status }) {
  if (!status || status === 'draft') return null
  const colors = { validated: 'bg-emerald-900 text-emerald-300', promoted: 'bg-purple-900 text-purple-300' }
  return <span className={`text-xs px-1.5 py-0.5 rounded ${colors[status] || 'bg-gray-800 text-gray-400'}`}>{status}</span>
}

export default function Watchlist() {
  const [items, setItems] = useState([])
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [promoteItem, setPromoteItem] = useState(null)
  const [addModal, setAddModal] = useState(false)
  const [addForm, setAddForm] = useState({ ticker: '', company_name: '', sector_schema: '', rationale: '', entry_price_target: '', trigger_alert_price: '' })

  const load = () => {
    fetch(`${API}/watchlist`).then(r => r.json()).then(data => { setItems(data); setLoading(false) }).catch(() => setLoading(false))
    fetch(`${API}/watchlist/alerts`).then(r => r.json()).then(setAlerts).catch(() => {})
  }

  useEffect(() => { load() }, [])

  const refresh = async () => {
    setRefreshing(true)
    await fetch(`${API}/watchlist/refresh-prices`, { method: 'POST' })
    load()
    setRefreshing(false)
  }

  const addItem = async () => {
    const payload = { ...addForm, entry_price_target: addForm.entry_price_target ? parseFloat(addForm.entry_price_target) : null, trigger_alert_price: addForm.trigger_alert_price ? parseFloat(addForm.trigger_alert_price) : null }
    await fetch(`${API}/watchlist`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    setAddModal(false)
    load()
  }

  if (loading) return <div className="text-gray-400 py-12 text-center">Chargement…</div>

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Watchlist</h1>
        <div className="flex gap-2">
          <button onClick={refresh} disabled={refreshing}
            className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 text-gray-200 rounded disabled:opacity-50">
            {refreshing ? '↻ Refresh…' : '↻ Refresh'}
          </button>
          <button onClick={() => setAddModal(true)}
            className="px-3 py-1.5 text-sm bg-blue-700 hover:bg-blue-600 text-white rounded">
            + Ajouter
          </button>
        </div>
      </div>

      <WatchlistAlertBanner alerts={alerts} onAcknowledge={id => { setAlerts(a => a.filter(x => x.id !== id)); load() }} />

      {items.length === 0 ? (
        <div className="text-center py-16 text-gray-500">Watchlist vide</div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-800">
          <table className="w-full text-sm">
            <thead className="bg-gray-900">
              <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                <th className="px-4 py-3">Ticker</th>
                <th className="px-4 py-3">Société</th>
                <th className="px-4 py-3 text-right">Prix</th>
                <th className="px-4 py-3 text-right">Cible</th>
                <th className="px-4 py-3 text-right">Écart</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">Conviction</th>
                <th className="px-4 py-3">Thèse</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {items.map(item => (
                <tr key={item.id} className="hover:bg-gray-800/50 cursor-pointer"
                  onClick={() => setSelectedId(item.id)}>
                  <td className="px-4 py-3 font-mono font-bold text-blue-400">{item.ticker}</td>
                  <td className="px-4 py-3 text-gray-300">{item.company_name || '—'}</td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {item.current_price != null ? `€${Number(item.current_price).toFixed(2)}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {item.entry_price_target != null ? `€${Number(item.entry_price_target).toFixed(2)}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right"><GapBadge gap={item.gap_to_entry} /></td>
                  <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                    <ReadinessWidget itemId={item.id} score={Number(item.readiness_score || 0)} cashReady={item.cash_ready} onUpdate={load} />
                  </td>
                  <td className="px-4 py-3"><ConvictionBadge signal={item.conviction_signal} /></td>
                  <td className="px-4 py-3"><ThesisStatusBadge status={item.thesis_status} /></td>
                  <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                    {item.status === 'watching' && (
                      <button onClick={() => setPromoteItem(item)}
                        className="text-xs px-2 py-1 bg-emerald-900 hover:bg-emerald-800 text-emerald-300 rounded">
                        Promouvoir
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedId && (
        <WatchlistItemDrawer itemId={selectedId} onClose={() => setSelectedId(null)} onUpdate={load} />
      )}

      {promoteItem && (
        <PromoteToPositionDrawer item={promoteItem} onClose={() => setPromoteItem(null)} onDone={load} />
      )}

      {addModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setAddModal(false)} />
          <div className="relative bg-gray-800 border border-gray-700 rounded-xl p-6 space-y-4 w-96">
            <h3 className="text-sm font-medium text-white">Ajouter à la watchlist</h3>
            {['ticker', 'company_name', 'sector_schema', 'rationale', 'entry_price_target', 'trigger_alert_price'].map(k => (
              <div key={k}>
                <label className="text-xs text-gray-400 block mb-1 capitalize">{k.replace(/_/g, ' ')}</label>
                <input value={addForm[k]} onChange={e => setAddForm(f => ({ ...f, [k]: e.target.value }))}
                  className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2" />
              </div>
            ))}
            <div className="flex gap-2">
              <button onClick={addItem} className="flex-1 py-2 bg-blue-700 text-white text-sm rounded">Ajouter</button>
              <button onClick={() => setAddModal(false)} className="px-3 text-gray-400 text-sm">Annuler</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
