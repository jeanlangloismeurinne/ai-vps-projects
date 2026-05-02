function fmt(val, suffix = '') {
  if (val == null) return <span className="text-gray-600">—</span>
  return <span>{val.toFixed(1)}{suffix}</span>
}

export default function PeerComparison({ peers = [], peersSnapshot = {} }) {
  if (!peers.length) return <p className="text-gray-500 text-sm">Aucun pair configuré.</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700 text-left text-xs text-gray-500">
            <th className="pb-2 pr-4">Ticker</th>
            <th className="pb-2 pr-4">Tier</th>
            <th className="pb-2 pr-4">PE NTM</th>
            <th className="pb-2 pr-4">FCF Yield</th>
            <th className="pb-2 pr-4">YTD</th>
            <th className="pb-2">Hypothèses</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {peers.map(p => {
            const snap = peersSnapshot?.[p.peer_ticker] || {}
            return (
              <tr key={p.id || p.peer_ticker} className="text-gray-300">
                <td className="py-2 pr-4 font-mono font-bold text-blue-400">{p.peer_ticker}</td>
                <td className="py-2 pr-4">
                  <span className="text-xs bg-gray-800 px-1.5 py-0.5 rounded">T{p.tier_level}</span>
                </td>
                <td className="py-2 pr-4">{fmt(snap.pe_ntm, 'x')}</td>
                <td className="py-2 pr-4">{fmt(snap.fcf_yield_pct, '%')}</td>
                <td className="py-2 pr-4">
                  {snap.ytd_change_pct != null ? (
                    <span className={snap.ytd_change_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                      {snap.ytd_change_pct > 0 ? '+' : ''}{snap.ytd_change_pct?.toFixed(1)}%
                    </span>
                  ) : <span className="text-gray-600">—</span>}
                </td>
                <td className="py-2 text-xs text-gray-500">
                  {p.hypotheses_watched?.join(', ') || '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
