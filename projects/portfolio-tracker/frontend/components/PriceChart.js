import { useMemo, useState, useRef, useCallback } from 'react'

const W = 400
const PAD_X = 8

export default function PriceChart({ data = [], height = 120, color = '#6366f1', showAxes = false, showDates = false }) {
  const svgRef = useRef(null)
  const [hover, setHover] = useState(null)

  const PAD_TOP = showAxes ? 14 : 8
  const PAD_BOTTOM = showDates ? 22 : 8

  const { points, minY, maxY, viewBox, pts } = useMemo(() => {
    const empty = { points: '', minY: 0, maxY: 0, viewBox: `0 0 ${W} ${height}`, pts: [] }
    if (!data || data.length < 2) return empty
    const prices = data.map(d => Number(d.close || d.price || 0)).filter(v => !isNaN(v))
    if (prices.length < 2) return empty
    const minY = Math.min(...prices)
    const maxY = Math.max(...prices)
    const range = maxY - minY || 1
    const chartH = height - PAD_TOP - PAD_BOTTOM
    const pts = prices.map((p, i) => {
      const x = PAD_X + (i / (prices.length - 1)) * (W - PAD_X * 2)
      const y = PAD_TOP + chartH - ((p - minY) / range) * chartH
      return { x, y, price: p, date: data[i]?.date || '' }
    })
    const points = pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
    return { points, minY, maxY, viewBox: `0 0 ${W} ${height}`, pts }
  }, [data, height, PAD_TOP, PAD_BOTTOM])

  const dateLabels = useMemo(() => {
    if (!showDates || pts.length < 2) return []
    const n = pts.length
    const indices = [0, Math.floor(n * 0.25), Math.floor(n * 0.5), Math.floor(n * 0.75), n - 1]
    return [...new Set(indices)].map(i => {
      const d = pts[i]
      let label = ''
      try { label = new Date(d.date).toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' }) } catch {}
      return { x: d.x, label }
    })
  }, [pts, showDates])

  const onMove = useCallback((clientX) => {
    if (!svgRef.current || pts.length < 2) return
    const rect = svgRef.current.getBoundingClientRect()
    const svgX = ((clientX - rect.left) / rect.width) * W
    let near = 0, minD = Infinity
    pts.forEach((p, i) => {
      const d = Math.abs(p.x - svgX)
      if (d < minD) { minD = d; near = i }
    })
    setHover(pts[near])
  }, [pts])

  const fmtDate = (s) => {
    if (!s) return ''
    try { return new Date(s).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' }) }
    catch { return s }
  }

  const fmtPrice = (p) => p == null ? '—' : (p >= 100 ? p.toFixed(0) : p.toFixed(2))

  if (!data || data.length < 2) {
    return (
      <div className="flex items-center justify-center text-gray-600 text-xs" style={{ height }}>
        Pas de données
      </div>
    )
  }

  const isPositive = (data[data.length - 1].close || 0) >= (data[0].close || 0)
  const lineColor = color === 'auto' ? (isPositive ? '#34d399' : '#f87171') : color
  const gradId = `grad-${lineColor.replace('#', '')}`

  return (
    <div className="relative select-none" style={{ height }}>
      <svg
        ref={svgRef}
        viewBox={viewBox}
        className="w-full absolute inset-0"
        style={{ height }}
        preserveAspectRatio="none"
        onMouseMove={e => onMove(e.clientX)}
        onMouseLeave={() => setHover(null)}
        onTouchMove={e => onMove(e.touches[0].clientX)}
        onTouchEnd={() => setHover(null)}
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={lineColor} stopOpacity="0.3" />
            <stop offset="100%" stopColor={lineColor} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {points && (
          <>
            <polygon
              points={`${PAD_X},${height - PAD_BOTTOM} ${points} ${W - PAD_X},${height - PAD_BOTTOM}`}
              fill={`url(#${gradId})`}
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
        {hover && (
          <>
            <line
              x1={hover.x} y1={PAD_TOP} x2={hover.x} y2={height - PAD_BOTTOM}
              stroke="#6b7280" strokeWidth="1" strokeDasharray="3,3"
            />
            <circle cx={hover.x} cy={hover.y} r="3" fill={lineColor} stroke="#1f2937" strokeWidth="1.5" />
          </>
        )}
      </svg>
      {hover && (
        <div
          className="absolute top-1 pointer-events-none z-10"
          style={{
            left: `${(hover.x / W) * 100}%`,
            transform: hover.x > W * 0.6 ? 'translateX(calc(-100% - 8px))' : 'translateX(8px)',
          }}
        >
          <div className="bg-gray-900 border border-gray-700 rounded px-2 py-1 shadow-lg whitespace-nowrap">
            <div className="text-white text-xs font-semibold">{fmtPrice(hover.price)}</div>
            <div className="text-gray-400 text-xs">{fmtDate(hover.date)}</div>
          </div>
        </div>
      )}
      {/* Y-axis labels — HTML pour éviter la déformation SVG sur mobile */}
      {showAxes && pts.length >= 2 && (
        <>
          <div className="absolute left-1 text-gray-500 pointer-events-none select-none leading-none"
               style={{ top: PAD_TOP - 10, fontSize: 9 }}>
            {maxY.toFixed(0)}
          </div>
          <div className="absolute left-1 text-gray-500 pointer-events-none select-none leading-none"
               style={{ bottom: PAD_BOTTOM, fontSize: 9 }}>
            {minY.toFixed(0)}
          </div>
        </>
      )}

      {/* X-axis date labels — HTML pour éviter la déformation SVG sur mobile */}
      {showDates && dateLabels.map((d, i) => (
        <div
          key={i}
          className="absolute text-gray-600 pointer-events-none select-none leading-none"
          style={{
            bottom: 2,
            left: `${(d.x / W) * 100}%`,
            fontSize: 9,
            transform: i === 0 ? 'none' : i === dateLabels.length - 1 ? 'translateX(-100%)' : 'translateX(-50%)',
            whiteSpace: 'nowrap',
          }}
        >
          {d.label}
        </div>
      ))}
    </div>
  )
}
