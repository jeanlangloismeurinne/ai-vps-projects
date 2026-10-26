import { useEffect, useMemo, useRef, useState } from 'react'

const M = { l: 58, r: 16, t: 14, b: 40 }
const R_MIN = 2.5
const R_MAX = 42
const RED = '239,68,68'
const GRAY = '156,163,175'

export const fmtCap = (v) => {
  if (v == null) return 'n.d.'
  if (v >= 1e12) return `${(v / 1e12).toFixed(2)} T$`
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)} Md$`
  if (v >= 1e6) return `${(v / 1e6).toFixed(0)} M$`
  return `${Math.round(v)} $`
}
export const fmtMult = (r) => (r.multiple_10y == null ? '–' : `${r.multiple_10y.toFixed(r.multiple_10y < 10 ? 2 : 1)}×${r.lt_10y ? ' (<10 ans)' : ''}`)
export const fmtAge = (r) => (r.is_atl ? 'ATL' : `${r.age_months} mois`)

const BASES = [
  { v: 'lin', l: 'Linéaire' }, { v: 1.5, l: 'Log base 1,5' }, { v: 2, l: 'Log base 2' },
  { v: 3, l: 'Log base 3' }, { v: 10, l: 'Log base 10' },
]

export const BASES_LIST = BASES
export const fmtJump = (v) => (v == null ? '–' : `${v > 0 ? '+' : ''}${v.toFixed(1)}`)

export default function BubbleChart({ rows, base, trail, maxCap, selected, onSelect, jumpWin, jumpHot = 6, compact }) {
  const tx = (age) => (base === 'lin' ? age : Math.log(1 + age) / Math.log(base))
  const wrap = useRef(null)
  const canvas = useRef(null)
  const [size, setSize] = useState({ w: 900, h: 520 })
  const [view, setView] = useState(null) // {x0,x1,y0,y1} ; y en log10
  const [hover, setHover] = useState(null)
  const drag = useRef(null)

  const pts = useMemo(() => {
    const tr = (r) => (trail && r.prev ? r.prev : null)
    const finite = rows.flatMap(r => [r, tr(r)]).filter(r => r && !r.is_atl && !r.atl && (r.age_months ?? r.age) != null)
      .map(r => r.age_months ?? r.age)
    const maxAge = finite.length ? Math.max(...finite) : 12
    const xmax = base === 'lin' ? Math.max(24, Math.ceil(maxAge / 12) * 12) : Math.max(tx(12), tx(maxAge) * 1.1)
    const withMult = rows.filter(r => r.multiple_10y > 0)
    const ys = withMult.flatMap(r => [clampY(Math.log10(r.multiple_10y)),
      ...(tr(r)?.mult > 0 ? [clampY(Math.log10(tr(r).mult))] : [])])
    let ymin = ys.length ? Math.min(...ys) : -0.5
    let ymax = ys.length ? Math.max(...ys) : 0.5
    if (ymax - ymin < 0.6) { const c = (ymin + ymax) / 2; ymin = c - 0.3; ymax = c + 0.3 }
    const padY = (ymax - ymin) * 0.08
    ymin -= padY; ymax += padY
    const capRef = maxCap || Math.max(1, ...rows.map(r => r.market_cap || 0))
    const list = withMult.map(r => {
      const p = tr(r)
      return {
        r, x: r.is_atl ? xmax : tx(r.age_months), y: clampY(Math.log10(r.multiple_10y)),
        rad: r.market_cap ? Math.max(R_MIN, R_MAX * Math.sqrt(r.market_cap / capRef)) : R_MIN,
        from: p && p.mult > 0 ? { x: p.atl ? xmax : tx(p.age), y: clampY(Math.log10(p.mult)) } : null,
      }
    })
    list.sort((a, b) => b.rad - a.rad)
    return { list, xmax, ymin, ymax }
  }, [rows, base, trail, maxCap]) // eslint-disable-line

  useEffect(() => { setView({ x0: -xpad(pts.xmax), x1: pts.xmax + xpad(pts.xmax), y0: pts.ymin, y1: pts.ymax }) }, [pts])

  useEffect(() => {
    const el = wrap.current
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: compact ? Math.max(300, Math.min(420, el.clientWidth * 0.6)) : Math.max(380, Math.min(640, el.clientWidth * 0.56)) }))
    ro.observe(el)
    return () => ro.disconnect()
  }, [compact])

  const px = (x) => M.l + ((x - view.x0) / (view.x1 - view.x0)) * (size.w - M.l - M.r)
  const py = (y) => M.t + (1 - (y - view.y0) / (view.y1 - view.y0)) * (size.h - M.t - M.b)

  const radScale = () => Math.min(2.2, Math.max(1, Math.sqrt((pts.xmax * 1.08) / (view.x1 - view.x0))))

  useEffect(() => {
    if (!view) return
    const cv = canvas.current
    const dpr = window.devicePixelRatio || 1
    cv.width = size.w * dpr; cv.height = size.h * dpr
    const g = cv.getContext('2d')
    g.setTransform(dpr, 0, 0, dpr, 0, 0)
    g.clearRect(0, 0, size.w, size.h)
    g.font = '11px ui-sans-serif, system-ui'
    g.fillStyle = '#9ca3af'; g.strokeStyle = '#1f2937'

    g.textAlign = 'center'
    const ticks = []
    if (base === 'lin') {
      const step = (view.x1 - view.x0) > 150 ? 24 : 12
      for (let a = 0; a <= view.x1; a += step) ticks.push([a, a])
    } else {
      ticks.push([0, 0])
      for (let a = 1, k = 0; k < 40 && tx(a) <= view.x1 * 1.001; a = Math.round(base ** ++k * 100) / 100) {
        if (!ticks.length || a !== ticks[ticks.length - 1][1]) ticks.push([tx(a), a])
      }
    }
    for (const [t, a] of ticks) {
      if (t < view.x0 || t > view.x1) continue
      g.beginPath(); g.moveTo(px(t), M.t); g.lineTo(px(t), size.h - M.b); g.stroke()
      g.fillText(String(Math.round(a * 10) / 10), px(t), size.h - M.b + 15)
    }
    g.fillText(base === 'lin' ? 'Ancienneté du cours (mois)' : `Ancienneté du cours (mois, échelle log base ${base})`, M.l + (size.w - M.l - M.r) / 2, size.h - 6)
    g.textAlign = 'right'
    const yTicks = []
    for (let d = Math.floor(view.y0) - 1; d <= Math.ceil(view.y1) + 1; d++) for (const m of [1, 2, 5]) yTicks.push(Math.log10(m * 10 ** d))
    for (const y of yTicks) {
      if (y < view.y0 || y > view.y1) continue
      g.beginPath(); g.moveTo(M.l, py(y)); g.lineTo(size.w - M.r, py(y)); g.stroke()
      const v = 10 ** y
      g.fillText(`${v >= 1 ? Math.round(v) : v.toFixed(2).replace(/0+$/, '')}×`, M.l - 6, py(y) + 4)
    }
    g.save(); g.translate(13, M.t + (size.h - M.t - M.b) / 2); g.rotate(-Math.PI / 2)
    g.textAlign = 'center'; g.fillText('Multiple sur 10 ans (échelle log)', 0, 0); g.restore()

    g.save()
    g.beginPath(); g.rect(M.l, M.t, size.w - M.l - M.r, size.h - M.t - M.b); g.clip()
    if (0 >= view.y0 && 0 <= view.y1) {
      g.strokeStyle = '#6b7280'; g.setLineDash([5, 4]); g.lineWidth = 1.2
      g.beginPath(); g.moveTo(M.l, py(0)); g.lineTo(size.w - M.r, py(0)); g.stroke(); g.setLineDash([])
    }
    if (pts.xmax >= view.x0 && pts.xmax <= view.x1) {
      g.strokeStyle = '#4b5563'; g.setLineDash([2, 4])
      g.beginPath(); g.moveTo(px(pts.xmax), M.t); g.lineTo(px(pts.xmax), size.h - M.b); g.stroke(); g.setLineDash([])
    }
    const sc = radScale()
    if (trail) {
      for (const p of pts.list) {
        if (!p.from) continue
        const x0 = px(p.from.x), y0 = py(p.from.y), x1 = px(p.x), y1 = py(p.y)
        if (Math.hypot(x1 - x0, y1 - y0) < 3) continue
        const hot = jumpWin && p.r['jump' + jumpWin] != null && p.r['jump' + jumpWin] >= jumpHot
        g.strokeStyle = hot ? 'rgba(248,113,113,0.95)' : 'rgba(125,211,252,0.55)'
        g.lineWidth = hot ? 2 : 1.2
        g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke()
        g.fillStyle = g.strokeStyle
        g.beginPath(); g.arc(x0, y0, hot ? 3 : 2.2, 0, 2 * Math.PI); g.fill()
      }
    }
    for (const p of pts.list) {
      const x = px(p.x), y = py(p.y), rad = p.rad * sc
      if (x < M.l - rad || x > size.w - M.r + rad || y < M.t - rad || y > size.h - M.b + rad) continue
      const c = p.r.alert ? RED : GRAY
      g.beginPath(); g.arc(x, y, rad, 0, 2 * Math.PI)
      g.fillStyle = `rgba(${c},${p.r.alert ? 0.30 : 0.20})`; g.fill()
      g.strokeStyle = selected === p.r.ticker ? '#fbbf24' : `rgba(${c},0.75)`; g.lineWidth = hover === p || selected === p.r.ticker ? 2.4 : 0.8; g.stroke()
      if (rad > 20) { g.fillStyle = '#e5e7eb'; g.textAlign = 'center'; g.fillText(p.r.ticker, x, y + 4) }
    }
    g.restore()
    g.fillStyle = '#9ca3af'; g.textAlign = 'left'
    if (pts.xmax >= view.x0 && pts.xmax <= view.x1) g.fillText('ATL →', Math.min(px(pts.xmax) + 4, size.w - 40), M.t + 12)
  }, [view, size, pts, hover, base, trail, selected, jumpWin, jumpHot])

  const locate = (e) => {
    const b = canvas.current.getBoundingClientRect()
    return { mx: e.clientX - b.left, my: e.clientY - b.top }
  }
  const hit = (mx, my) => {
    if (!view) return null
    let best = null
    for (const p of pts.list) {
      const rad = p.rad * radScale()
      const d = Math.hypot(px(p.x) - mx, py(p.y) - my)
      if (d <= Math.max(rad, 4) && (!best || p.rad < best.rad)) best = p
    }
    return best
  }
  const onMove = (e) => {
    const { mx, my } = locate(e)
    if (drag.current) {
      const dx = (mx - drag.current.mx) / (size.w - M.l - M.r) * (drag.current.v.x1 - drag.current.v.x0)
      const dy = (my - drag.current.my) / (size.h - M.t - M.b) * (drag.current.v.y1 - drag.current.v.y0)
      const v = drag.current.v
      setView({ x0: v.x0 - dx, x1: v.x1 - dx, y0: v.y0 + dy, y1: v.y1 + dy })
      setHover(null); return
    }
    const h = hit(mx, my)
    setHover(h ? Object.assign(h, { mx, my }) : null)
  }
  const onWheel = (e) => {
    e.preventDefault()
    if (!view) return
    const { mx, my } = locate(e)
    const f = e.deltaY < 0 ? 0.8 : 1.25
    const cx = view.x0 + ((mx - M.l) / (size.w - M.l - M.r)) * (view.x1 - view.x0)
    const cy = view.y1 - ((my - M.t) / (size.h - M.t - M.b)) * (view.y1 - view.y0)
    setView({ x0: cx - (cx - view.x0) * f, x1: cx + (view.x1 - cx) * f, y0: cy - (cy - view.y0) * f, y1: cy + (view.y1 - cy) * f })
  }
  useEffect(() => {
    const cv = canvas.current
    const h = (e) => onWheel(e)
    cv.addEventListener('wheel', h, { passive: false })
    return () => cv.removeEventListener('wheel', h)
  })

  const reset = () => setView({ x0: -xpad(pts.xmax), x1: pts.xmax + xpad(pts.xmax), y0: pts.ymin, y1: pts.ymax })

  return (
    <div>
    <div ref={wrap} className="relative w-full select-none">
      <canvas ref={canvas} style={{ width: size.w, height: size.h, cursor: drag.current ? 'grabbing' : hover ? 'pointer' : 'grab' }}
        onMouseMove={onMove} onMouseLeave={() => { setHover(null); drag.current = null }}
        onMouseDown={(e) => { const { mx, my } = locate(e); drag.current = { mx, my, v: view } }}
        onMouseUp={(e) => {
          const { mx, my } = locate(e), d = drag.current
          drag.current = null
          if (d && Math.hypot(mx - d.mx, my - d.my) < 4) { const h = hit(mx, my); if (h && onSelect) onSelect(h.r.ticker) }
        }} />
      <button onClick={reset} className="absolute top-2 right-3 text-[11px] px-2 py-1 rounded bg-gray-800 text-gray-300 hover:text-white border border-gray-700">
        Réinitialiser le zoom
      </button>
      {hover && (
        <div className="absolute z-10 pointer-events-none rounded-lg border border-gray-700 bg-gray-950/95 px-3 py-2 text-xs text-gray-200 shadow-lg"
          style={{ left: Math.min(hover.mx + 14, size.w - 230), top: Math.min(hover.my + 14, size.h - 150), width: 220 }}>
          <div className="font-semibold text-white">{hover.r.ticker} <span className="font-normal text-gray-400">{hover.r.name.replace(/ - .*$/, '')}</span></div>
          <div>Cours : {hover.r.price.toFixed(2)} $</div>
          <div>Ancienneté : {fmtAge(hover.r)}{hover.r.alert ? ' · ALERTE' : ''}</div>
          <div>Multiple 10 ans : {fmtMult(hover.r)}</div>
          <div>Saut d'ancienneté : {fmtJump(hover.r.jump5)} m (5 j) · {fmtJump(hover.r.jump20)} m (20 j)</div>
          <div>Capitalisation : {fmtCap(hover.r.market_cap)}{hover.r.market_cap == null ? ' (taille minimale)' : ''}</div>
          {hover.r.short_history && <div className="text-amber-400">Historique court (&lt; 1 an)</div>}
        </div>
      )}
    </div>
    </div>
  )
}

// Au-delà de 1000× ou sous 0,001× (réductions de capital en série), le point est collé au bord ; l'infobulle garde la vraie valeur.
function clampY(y) { return Math.max(-3, Math.min(3, y)) }

function xpad(xmax) { return xmax * 0.04 }
