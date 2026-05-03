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
  const [addError, setAddError] = useState('')
  const [addLoading, setAddLoading] = useState(false)

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

  const openAddModal = () => {
    setAddForm({ ticker: '', company_name: '', sector_schema: '', rationale: '', entry_price_target: '', trigger_alert_price: '' })
    setAddError('')
    setAddModal(true)
  }

  const addItem = async () => {
    if (!addForm.ticker.trim()) { setAddError('Le ticker est obligatoire'); return }
    if (!addForm.company_name.trim()) { setAddError('Le nom de la société est obligatoire'); return }
    setAddLoading(true)
    setAddError('')
    try {
      const payload = {
        ticker: addForm.ticker.trim().toUpperCase(),
        company_name: addForm.company_name.trim(),
        sector_schema: addForm.sector_schema.trim() || null,
        rationale: addForm.rationale.trim() || null,
        entry_price_target: addForm.entry_price_target ? parseFloat(addForm.entry_price_target) : null,
        trigger_alert_price: addForm.trigger_alert_price ? parseFloat(addForm.trigger_alert_price) : null,
      }
      const res = await fetch(`${API}/watchlist`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Erreur ${res.status}`) }
      setAddModal(false)
      load()
    } catch (e) {
      setAddError(e.message || 'Erreur lors de l\'ajout')
    } finally {
      setAddLoading(false)
    }
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
          <button onClick={openAddModal}
            className="px-3 py-1.5 text-sm bg-blue-700 hover:bg-blue-600 text-white rounded font-medium">
            + Ajouter à la watchlist
          </button>
        </div>
      </div>

      <WatchlistAlertBanner alerts={alerts} onAcknowledge={id => { setAlerts(a => a.filter(x => x.id !== id)); load() }} />

      {items.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-gray-500 text-lg mb-2">Watchlist vide</p>
          <p className="text-gray-600 text-sm mb-6">Commence par ajouter un titre à surveiller</p>
          <button onClick={openAddModal} className="px-4 py-2 bg-blue-700 hover:bg-blue-600 text-white text-sm rounded font-medium">
            + Ajouter un titre
          </button>
        </div>
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => !addLoading && setAddModal(false)} />
          <div className="relative bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
              <h3 className="font-semibold text-white">Ajouter à la watchlist</h3>
              <button onClick={() => !addLoading && setAddModal(false)} className="text-gray-400 hover:text-white text-xl leading-none">×</button>
            </div>
            <div className="px-6 py-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Ticker <span className="text-red-400">*</span></label>
                  <input
                    value={addForm.ticker}
                    onChange={e => setAddForm(f => ({ ...f, ticker: e.target.value }))}
                    placeholder="ex. MSFT, CAP.PA"
                    className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-blue-500 focus:outline-none uppercase"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Schéma sectoriel</label>
                  <input
                    value={addForm.sector_schema}
                    onChange={e => setAddForm(f => ({ ...f, sector_schema: e.target.value }))}
                    placeholder="ex. IT_Services"
                    className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Nom de la société <span className="text-red-400">*</span></label>
                <input
                  value={addForm.company_name}
                  onChange={e => setAddForm(f => ({ ...f, company_name: e.target.value }))}
                  placeholder="ex. Microsoft Corporation"
                  className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Prix cible d'entrée (€)</label>
                  <input
                    type="number" step="0.01" min="0"
                    value={addForm.entry_price_target}
                    onChange={e => setAddForm(f => ({ ...f, entry_price_target: e.target.value }))}
                    placeholder="ex. 95.00"
                    className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Prix d'alerte (€)</label>
                  <input
                    type="number" step="0.01" min="0"
                    value={addForm.trigger_alert_price}
                    onChange={e => setAddForm(f => ({ ...f, trigger_alert_price: e.target.value }))}
                    placeholder="ex. 90.00"
                    className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Raison / Thèse préliminaire</label>
                <textarea
                  value={addForm.rationale}
                  onChange={e => setAddForm(f => ({ ...f, rationale: e.target.value }))}
                  placeholder="Pourquoi ce titre est sur ta watchlist…"
                  rows={3}
                  className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2 placeholder-gray-500 focus:border-blue-500 focus:outline-none resize-none"
                />
              </div>
              {addError && (
                <p className="text-sm text-red-400 bg-red-900/30 border border-red-800 rounded px-3 py-2">{addError}</p>
              )}
            </div>
            <div className="px-6 py-4 border-t border-gray-700 flex gap-3">
              <button
                onClick={addItem}
                disabled={addLoading}
                className="flex-1 py-2 bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors"
              >
                {addLoading ? 'Ajout en cours…' : 'Ajouter à la watchlist'}
              </button>
              <button onClick={() => !addLoading && setAddModal(false)} className="px-4 text-gray-400 hover:text-gray-200 text-sm">
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
