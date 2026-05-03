import { useState, useEffect } from 'react'
import MarketTemperatureBadge from './MarketTemperatureBadge'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export default function CashManagementWidget() {
  const [settings, setSettings] = useState(null)
  const [market, setMarket] = useState(null)
  const [modal, setModal] = useState(false)
  const [opForm, setOpForm] = useState({ type: 'deposit', amount: '' })
  const [saving, setSaving] = useState(false)

  const load = () => {
    fetch(`${API}/portfolio/settings`).then(r => r.json()).then(setSettings).catch(() => {})
    fetch(`${API}/market/temperature`).then(r => r.json()).then(setMarket).catch(() => {})
  }
  useEffect(() => { load() }, [])

  const doOperation = async () => {
    setSaving(true)
    try {
      await fetch(`${API}/portfolio/cash-operation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation_type: opForm.type, amount_eur: parseFloat(opForm.amount) }),
      })
      setModal(false)
      load()
    } catch (e) {}
    setSaving(false)
  }

  if (!settings) return null

  const total = Number(settings.total_capital_eur) || 0
  const cash = Number(settings.cash_balance_eur) || 0
  const deployed = total - cash
  const deployedPct = total > 0 ? (deployed / total * 100) : 0
  const cashTargetPct = market?.cash_target_pct || 15
  const cashTargetEur = total * cashTargetPct / 100
  const delta = cash - cashTargetEur

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-300">Gestion du cash</h3>
        <MarketTemperatureBadge showCash />
      </div>

      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Capital total', value: `€${total.toLocaleString('fr-FR', { maximumFractionDigits: 0 })}` },
          { label: 'Cash disponible', value: `€${cash.toLocaleString('fr-FR', { maximumFractionDigits: 0 })}` },
          { label: 'Cash déployé', value: `€${deployed.toLocaleString('fr-FR', { maximumFractionDigits: 0 })}` },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gray-800 rounded p-2.5">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-sm font-semibold text-white">{value}</p>
          </div>
        ))}
      </div>

      <div className="space-y-1">
        <div className="flex justify-between text-xs text-gray-400">
          <span>Déployé {deployedPct.toFixed(1)}%</span>
          <span>Cash cible recommandé : {cashTargetPct}%</span>
        </div>
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <div className="h-full bg-blue-600 rounded-full transition-all" style={{ width: `${Math.min(deployedPct, 100)}%` }} />
        </div>
        <p className={`text-xs ${delta >= 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
          {delta >= 0 ? `+€${delta.toFixed(0)} au-dessus de la cible` : `−€${Math.abs(delta).toFixed(0)} sous la cible`}
        </p>
      </div>

      <button onClick={() => setModal(true)}
        className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs rounded">
        + Enregistrer un mouvement
      </button>

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setModal(false)} />
          <div className="relative bg-gray-800 border border-gray-700 rounded-xl p-6 space-y-4 w-72">
            <h4 className="text-sm font-medium text-white">Mouvement de cash</h4>
            <div className="flex gap-2">
              {['deposit', 'withdrawal'].map(t => (
                <button key={t} onClick={() => setOpForm(f => ({ ...f, type: t }))}
                  className={`flex-1 py-1.5 text-xs rounded ${opForm.type === t ? 'bg-blue-700 text-white' : 'bg-gray-700 text-gray-300'}`}>
                  {t === 'deposit' ? 'Dépôt' : 'Retrait'}
                </button>
              ))}
            </div>
            <input type="number" placeholder="Montant (€)" value={opForm.amount}
              onChange={e => setOpForm(f => ({ ...f, amount: e.target.value }))}
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-2" />
            <div className="flex gap-2">
              <button onClick={doOperation} disabled={saving || !opForm.amount}
                className="flex-1 py-2 bg-blue-700 hover:bg-blue-600 text-white text-sm rounded disabled:opacity-50">
                {saving ? '…' : 'Confirmer'}
              </button>
              <button onClick={() => setModal(false)} className="px-3 text-gray-400 hover:text-gray-200 text-sm">Annuler</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
