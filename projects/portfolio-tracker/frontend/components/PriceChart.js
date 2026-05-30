import { useMemo } from 'react'

export default function PriceChart({ data = [], height = 120, color = '#6366f1', showAxes = false }) {
  const { points, minY, maxY, width, viewBox } = useMemo(() => {
    if (!data || data.length < 2) return { points: '', minY: 0, maxY: 0, width: 400, viewBox: '0 0 400 120' }
    const prices = data.map(d => Number(d.close || d.price || 0)).filter(v => !isNaN(v))
    if (prices.length < 2) return { points: '', minY: 0, maxY: 0, width: 400, viewBox: '0 0 400 120' }
    const minY = Math.min(...prices)
    const maxY = Math.max(...prices)
    const range = maxY - minY || 1
    const w = 400
    const h = height
    const pad = 8
    const points = prices.map((p, i) => {
      const x = pad + (i / (prices.length - 1)) * (w - pad * 2)
      const y = h - pad - ((p - minY) / range) * (h - pad * 2)
      return `${x.toFixed(1)},${y.toFixed(1)}`
    }).join(' ')
    return { points, minY, maxY, width: w, viewBox: `0 0 ${w} ${h}` }
  }, [data, height])

  if (!data || data.length < 2) {
    return (
      <div className="flex items-center justify-center text-gray-600 text-xs" style={{ height }}>
        Pas de données
      </div>
    )
  }

  const isPositive = data.length >= 2 &&
    (data[data.length - 1].close || 0) >= (data[0].close || 0)
  const lineColor = color === 'auto' ? (isPositive ? '#34d399' : '#f87171') : color

  return (
    <svg viewBox={viewBox} className="w-full" style={{ height }} preserveAspectRatio="none">
      {/* Area fill */}
      <defs>
        <linearGradient id={`grad-${lineColor.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={lineColor} stopOpacity="0.3" />
          <stop offset="100%" stopColor={lineColor} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {points && (
        <>
          <polygon
            points={`8,${height - 8} ${points} ${width - 8},${height - 8}`}
            fill={`url(#grad-${lineColor.replace('#', '')})`}
          />
          <polyline
            points={points}
            fill="none"
            stroke={lineColor}
            strokeWidth="1.5"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        </>
      )}
      {showAxes && (
        <>
          <text x="4" y="12" fill="#6b7280" fontSize="9">{maxY.toFixed(0)}</text>
          <text x="4" y={height - 4} fill="#6b7280" fontSize="9">{minY.toFixed(0)}</text>
        </>
      )}
    </svg>
  )
}
