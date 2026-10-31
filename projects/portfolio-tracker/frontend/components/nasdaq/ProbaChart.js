const COL = { 1: '#22c55e', 0: '#ef4444', n: '#6b7280' }

// Courbe de probabilité ; l'aire sous la courbe est colorée point par point selon ce qui s'est réellement passé
// dans les 12 mois suivants : vert = nouveau plus haut atteint, rouge = manqué, gris = 12 mois pas encore écoulés.
export default function ProbaChart({ curve, w = 900, h = 170, compact = false, thr = null }) {
  if (!curve || !curve.d.length) return null
  const ML = compact ? 4 : 40, MR = compact ? 4 : 10, MT = 6, MB = compact ? 4 : 20
  const n = curve.d.length
  const d0 = curve.d[0], d1 = curve.d[n - 1]
  const step = n > 1 ? (d1 - d0) / (n - 1) : 30
  const span = d1 - d0 + step
  const x = (dn) => ML + ((dn - d0) / span) * (w - ML - MR)
  const y = (p) => MT + (1 - p) * (h - MT - MB)
  const base = y(0)
  const pts = curve.d.map((dn, i) => [x(dn), y(curve.p[i])])
  const xEnd = x(d1 + step)
  const bands = pts.map(([px, py], i) => {
    const [nx, ny] = i < n - 1 ? pts[i + 1] : [xEnd, py]
    const k = curve.o[i] === null ? 'n' : curve.o[i]
    return <polygon key={i} points={`${px},${base} ${px},${py} ${nx},${ny} ${nx},${base}`} fill={COL[k]} fillOpacity={k === 'n' ? 0.25 : 0.5} />
  })
  const line = pts.map(([px, py], i) => `${i ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)}`).join(' ')
  const years = []
  if (!compact) {
    let last = -1
    curve.d.forEach((dn, i) => {
      const yr = new Date(dn * 86400000).getUTCFullYear()
      if (yr !== last) { years.push([x(dn), yr]); last = yr }
    })
  }
  const stride = Math.max(1, Math.ceil(years.length / 9))
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" role="img" aria-label="Probabilité estimée de nouveau plus haut à 12 mois">
      {!compact && [0, 0.25, 0.5, 0.75, 1].map(v => (
        <g key={v}>
          <line x1={ML} x2={w - MR} y1={y(v)} y2={y(v)} stroke="#1f2937" />
          <text x={ML - 5} y={y(v) + 3} fontSize="10" fill="#9ca3af" textAnchor="end">{Math.round(v * 100)} %</text>
        </g>
      ))}
      {bands}
      <path d={line} fill="none" stroke="#e5e7eb" strokeWidth={compact ? 1.2 : 1.5} />
      {thr !== null && <line x1={ML} x2={w - MR} y1={y(thr)} y2={y(thr)} stroke="#38bdf8" strokeDasharray="5 3" />}
      {years.filter((_, k) => k % stride === 0).map(([px, yr]) => (
        <text key={yr} x={px} y={h - 5} fontSize="10" fill="#9ca3af" textAnchor="start">{yr}</text>
      ))}
    </svg>
  )
}

export function Legend() {
  return (
    <div className="flex flex-wrap gap-3 text-xs text-gray-400">
      <span><i className="inline-block w-3 h-3 align-middle mr-1 rounded-sm" style={{ background: COL[1], opacity: 0.6 }} />nouveau plus haut atteint dans les 12 mois</span>
      <span><i className="inline-block w-3 h-3 align-middle mr-1 rounded-sm" style={{ background: COL[0], opacity: 0.6 }} />non atteint</span>
      <span><i className="inline-block w-3 h-3 align-middle mr-1 rounded-sm" style={{ background: COL.n, opacity: 0.4 }} />12 mois pas encore écoulés</span>
    </div>
  )
}
