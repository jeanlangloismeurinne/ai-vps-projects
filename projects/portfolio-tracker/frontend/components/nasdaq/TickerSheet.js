import { useMemo } from 'react'

const DPM = 30.4375
const W = 900, H1 = 150, H2 = 170, ML = 46, MR = 12, GAP = 22

const dateOf = (n) => new Date(n * 86400000)
const fmtDay = (n) => dateOf(n).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit', timeZone: 'UTC' })

// Épisodes de saut : première séance de chaque série de séances où le saut sur 5 séances dépasse le seuil.
function episodes(s, hot) {
  const out = []
  let last = -99
  for (let i = 5; i < s.d.length; i++) {
    const j = ((s.a[i] - s.a[i - 5]) - (s.d[i] - s.d[i - 5])) / DPM
    if (j >= hot) {
      if (i - last > 5) out.push({ i, j })
      else out[out.length - 1].j = Math.max(out[out.length - 1].j, j)
      last = i
    }
  }
  return out
}

export default function TickerSheet({ row, s, hot, onClose }) {
  const ev = useMemo(() => (s ? episodes(s, hot) : []), [s, hot])
  if (!row) return null
  if (!s) return <p className="text-sm text-gray-500">Série indisponible pour {row.ticker}.</p>

  const n = s.d.length
  const x = (i) => ML + (i / (n - 1)) * (W - ML - MR)
  const ages = s.a.map(a => a / DPM)
  const amax = Math.max(12, ...ages) * 1.08
  const ya = (v) => 8 + (1 - v / amax) * (H1 - 8 - 6)
  const pmin = Math.min(...s.p), pmax = Math.max(...s.p)
  const yp = (v) => 8 + (1 - (v - pmin) / (pmax - pmin || 1)) * (H2 - 8 - 6)
  const top2 = H1 + GAP
  const total = H1 + GAP + H2 + 22

  const monthTicks = []
  for (let i = 0; i < n; i++) {
    const d = dateOf(s.d[i])
    if (i === 0 || d.getUTCMonth() !== dateOf(s.d[i - 1]).getUTCMonth()) {
      if (d.getUTCMonth() % 2 === 0) monthTicks.push([i, d.toLocaleDateString('fr-FR', { month: 'short', year: '2-digit', timeZone: 'UTC' })])
    }
  }
  const agePath = ages.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${ya(v).toFixed(1)}`).join(' ')
  const pricePath = s.p.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${yp(v).toFixed(1)}`).join(' ')
  const yTicksA = [0, 6, 12, 24, 36, 60, 120].filter(v => v < amax)

  return (
    <div>
      <div className="flex items-center gap-3 mb-2">
        <h3 className="text-sm font-semibold text-white">{row.ticker} <span className="font-normal text-gray-400">{row.name.replace(/ - .*$/, '')}</span></h3>
        <span className="text-xs text-gray-500">{n} dernières séances · sauts ≥ {hot} mois sur 5 séances repérés en rouge</span>
        <button onClick={onClose} className="ml-auto text-xs px-2 py-1 rounded border border-gray-700 text-gray-300 hover:text-white">Fermer</button>
      </div>
      <svg viewBox={`0 0 ${W} ${total}`} className="w-full max-w-[900px]" role="img" aria-label={`Ancienneté et cours de ${row.ticker}`}>
        {yTicksA.map(v => (
          <g key={v}>
            <line x1={ML} x2={W - MR} y1={ya(v)} y2={ya(v)} stroke={v === 12 ? '#7f1d1d' : '#1f2937'} strokeDasharray={v === 12 ? '4 3' : undefined} />
            <text x={ML - 5} y={ya(v) + 3} fontSize="10" fill="#9ca3af" textAnchor="end">{v}</text>
          </g>
        ))}
        <text x={4} y={12} fontSize="10" fill="#9ca3af">mois</text>
        {ev.map(e => (
          <g key={e.i}>
            <line x1={x(e.i)} x2={x(e.i)} y1={0} y2={total - 22} stroke="#ef4444" strokeOpacity="0.5" strokeDasharray="3 3" />
            <text x={x(e.i) + 3} y={12} fontSize="10" fill="#fca5a5">+{e.j.toFixed(0)} m · {fmtDay(s.d[e.i])}</text>
          </g>
        ))}
        <path d={agePath} fill="none" stroke="#38bdf8" strokeWidth="1.6" />
        {s.l.map((v, i) => v ? <circle key={i} cx={x(i)} cy={ya(ages[i])} r="1.8" fill="#ef4444" /> : null)}
        <text x={W - MR} y={H1 + 12} fontSize="10" fill="#6b7280" textAnchor="end">Ancienneté du cours (mois) — pointillé : 12 mois, points rouges : plus bas historique</text>

        {[pmin, (pmin + pmax) / 2, pmax].map((v, k) => (
          <g key={k}>
            <line x1={ML} x2={W - MR} y1={top2 + yp(v)} y2={top2 + yp(v)} stroke="#1f2937" />
            <text x={ML - 5} y={top2 + yp(v) + 3} fontSize="10" fill="#9ca3af" textAnchor="end">{v.toFixed(0)}</text>
          </g>
        ))}
        <path d={pricePath} transform={`translate(0,${top2})`} fill="none" stroke="#e5e7eb" strokeWidth="1.4" />
        {monthTicks.map(([i, l]) => (
          <text key={i} x={x(i)} y={top2 + H2 + 14} fontSize="10" fill="#9ca3af" textAnchor="middle">{l}</text>
        ))}
        <text x={W - MR} y={top2 + 12} fontSize="10" fill="#6b7280" textAnchor="end">Cours ajusté ($)</text>
      </svg>
    </div>
  )
}
