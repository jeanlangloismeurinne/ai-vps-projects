import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

function fmt(val, decimals = 2) {
  if (val == null) return '—'
  return Number(val).toLocaleString('fr-FR', { maximumFractionDigits: decimals, minimumFractionDigits: decimals })
}

function fmtBig(val) {
  if (val == null) return '—'
  const n = Number(val)
  if (Math.abs(n) >= 1e12) return `${(n / 1e12).toFixed(2)}T`
  if (Math.abs(n) >= 1e9) return `${(n / 1e9).toFixed(1)}B`
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)}M`
  return fmt(val)
}

function PctCell({ val }) {
  if (val == null) return <span className="text-gray-500">—</span>
  const n = Number(val)
  return <span className={n >= 0 ? 'text-emerald-400' : 'text-red-400'}>{n >= 0 ? '+' : ''}{n.toFixed(2)}%</span>
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-gray-800/60 last:border-0">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className="text-white text-sm font-medium">{value ?? '—'}</span>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="mb-5">
      <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-2 font-semibold">{title}</h3>
      <div className="rounded-lg bg-gray-800/40 px-3 divide-y divide-gray-800/60">
        {children}
      </div>
    </div>
  )
}

export default function M1DataPanel({ itemId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!itemId) return
    setLoading(true)
    setError(null)
    fetch(`${API}/watchlist/${itemId}/m1`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [itemId])

  if (loading) return <div className="text-gray-400 text-sm py-8 text-center">Chargement des données marché…</div>
  if (error) return <div className="text-red-400 text-sm py-4">Erreur : {error}</div>
  if (!data) return null

  const p = data.price || {}
  const v = data.valuation || {}
  const d = data.dividend || {}
  const fin = data.financials_3y || {}
  const eps = data.eps_estimates || {}
  const finYears = Object.keys(fin).sort().reverse()
  const epsYears = Object.keys(eps).sort()
  const collectedAt = data.collected_at ? new Date(data.collected_at).toLocaleString('fr-FR') : null

  return (
    <div className="text-sm">
      {collectedAt && (
        <p className="text-gray-600 text-xs mb-4">Données collectées le {collectedAt} · {data.yf_ticker}</p>
      )}

      <Section title="Prix & performance">
        <Row label="Prix actuel" value={p.current_price != null ? `${fmt(p.current_price)} ${p.currency || ''}` : null} />
        <Row label="Market cap" value={fmtBig(p.market_cap)} />
        <Row label="Enterprise value" value={fmtBig(p.enterprise_value)} />
        <Row label="Plus haut 52 sem." value={p['52w_high'] != null ? fmt(p['52w_high']) : null} />
        <Row label="Plus bas 52 sem." value={p['52w_low'] != null ? fmt(p['52w_low']) : null} />
        <Row label="Distance vs 52w high" value={p.distance_from_52w_high_pct != null ? <PctCell val={p.distance_from_52w_high_pct} /> : null} />
        <Row label="Perf YTD" value={<PctCell val={p.ytd_change_pct} />} />
        <Row label="Perf 1 mois" value={<PctCell val={p['1m_change_pct']} />} />
        <Row label="Perf 3 mois" value={<PctCell val={p['3m_change_pct']} />} />
        <Row label="Perf 6 mois" value={<PctCell val={p['6m_change_pct']} />} />
        <Row label="Perf 1 an" value={<PctCell val={p['1y_change_pct']} />} />
      </Section>

      <Section title="Valorisation">
        <Row label="PE NTM (forward)" value={v.pe_ntm != null ? fmt(v.pe_ntm) + 'x' : null} />
        <Row label="PE TTM" value={v.pe_ttm != null ? fmt(v.pe_ttm) + 'x' : null} />
        <Row label="EV/EBITDA" value={v.ev_ebitda != null ? fmt(v.ev_ebitda) + 'x' : null} />
        <Row label="EV/Revenue" value={v.ev_revenue != null ? fmt(v.ev_revenue) + 'x' : null} />
        <Row label="Price / Book" value={v.price_to_book != null ? fmt(v.price_to_book) + 'x' : null} />
        <Row label="FCF Yield" value={v.fcf_yield_pct != null ? <PctCell val={v.fcf_yield_pct} /> : null} />
      </Section>

      {finYears.length > 0 && (
        <div className="mb-5">
          <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-2 font-semibold">Financials 3 ans (yfinance)</h3>
          <div className="overflow-x-auto rounded-lg">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-gray-700">
                  <th className="py-2 text-left font-medium">Année</th>
                  <th className="py-2 text-right font-medium">Revenue</th>
                  <th className="py-2 text-right font-medium">Op. Income</th>
                  <th className="py-2 text-right font-medium">Net Income</th>
                  <th className="py-2 text-right font-medium">FCF</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {finYears.map(yr => {
                  const row = fin[yr] || {}
                  return (
                    <tr key={yr} className="text-gray-300">
                      <td className="py-2 font-mono font-semibold text-gray-400">{yr}</td>
                      <td className="py-2 text-right">{fmtBig(row.revenue)}</td>
                      <td className="py-2 text-right">{fmtBig(row.operating_income)}</td>
                      <td className="py-2 text-right">{fmtBig(row.net_income)}</td>
                      <td className="py-2 text-right">{fmtBig(row.fcf)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Section title="Dividende">
        <Row label="Dividende annuel" value={d.annual_dividend != null ? fmt(d.annual_dividend) : null} />
        <Row label="Rendement" value={d.dividend_yield_pct != null ? <PctCell val={d.dividend_yield_pct} /> : null} />
        <Row label="Payout ratio" value={d.payout_ratio != null ? fmt(d.payout_ratio * 100) + '%' : null} />
      </Section>

      {epsYears.length > 0 ? (
        <div className="mb-5">
          <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-2 font-semibold">Estimations EPS — FMP</h3>
          <div className="overflow-x-auto rounded-lg">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-gray-700">
                  <th className="py-2 text-left font-medium">Année</th>
                  <th className="py-2 text-right font-medium">EPS moy.</th>
                  <th className="py-2 text-right font-medium">CA estimé</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {epsYears.map(yr => {
                  const row = eps[yr] || {}
                  return (
                    <tr key={yr} className="text-gray-300">
                      <td className="py-2 font-mono font-semibold text-gray-400">{yr}</td>
                      <td className="py-2 text-right">{row.eps_avg != null ? fmt(row.eps_avg) : '—'}</td>
                      <td className="py-2 text-right">{fmtBig(row.revenue_avg)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="text-gray-600 text-xs italic mb-4">
          Estimations EPS non disponibles (endpoint FMP payant — plan Starter requis)
        </div>
      )}
    </div>
  )
}
