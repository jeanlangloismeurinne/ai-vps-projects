import '../styles/globals.css'
import Link from 'next/link'
import { useRouter } from 'next/router'
import { useState, useEffect } from 'react'
import Script from 'next/script'
import MarketTemperatureBadge from '../components/MarketTemperatureBadge'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

function NavLink({ href, children, exact = false }) {
  const router = useRouter()
  const active = exact
    ? router.pathname === href
    : router.pathname === href || router.pathname.startsWith(href + '/')
  return (
    <Link href={href}
      className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
        active ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
      }`}>
      {children}
    </Link>
  )
}

function AgentSyncBadge() {
  const [outOfSync, setOutOfSync] = useState(0)
  useEffect(() => {
    fetch(`${API}/admin/agents?flow_version=v1`)
      .then(r => r.json())
      .then(agents => {
        const count = Array.isArray(agents) ? agents.filter(a => !a.synced).length : 0
        setOutOfSync(count)
      })
      .catch(() => {})
  }, [])
  if (!outOfSync) return null
  return (
    <Link href="/admin"
      className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-900/50 border border-amber-700 text-amber-300 text-xs rounded-lg font-medium hover:bg-amber-900/70 transition-colors">
      ⚠️ Admin — {outOfSync} agent{outOfSync > 1 ? 's' : ''} hors sync
    </Link>
  )
}

// ── Espace V1 (existant, inchangé) ───────────────────────────────────────────
function V1Nav() {
  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-2 sticky top-0 z-40 flex-wrap">
      <Link href="/" className="text-white font-bold mr-3">📈 PT</Link>
      <NavLink href="/portfolio">Portefeuille</NavLink>
      <NavLink href="/watchlist-v2">Watchlist</NavLink>
      <NavLink href="/calendrier">Calendrier</NavLink>
      <NavLink href="/admin">Admin</NavLink>
      <div className="ml-auto flex items-center gap-3">
        <AgentSyncBadge />
        <MarketTemperatureBadge />
        <Link href="/" className="px-3 py-1.5 text-xs text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-lg transition-colors">
          V1 / V2
        </Link>
        <a href="https://jlmvpscode.duckdns.org"
          className="px-3 py-1.5 text-xs text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-lg transition-colors">
          ← Hub
        </a>
      </div>
    </nav>
  )
}

// ── Espace V2 (nouveau, disjoint) ────────────────────────────────────────────
function V2Nav() {
  return (
    <nav className="bg-gray-900 border-b border-emerald-900/60 px-6 py-3 flex items-center gap-2 sticky top-0 z-40 flex-wrap">
      <Link href="/v2" className="text-white font-bold mr-2">🧪 PT</Link>
      <span className="px-2 py-0.5 rounded bg-emerald-800/60 text-emerald-200 text-[11px] font-semibold mr-2">V2</span>
      <NavLink href="/v2" exact>Tableau de bord</NavLink>
      <NavLink href="/v2/theses">Thèses</NavLink>
      <div className="ml-auto flex items-center gap-3">
        <Link href="/" className="px-3 py-1.5 text-xs text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-lg transition-colors">
          V1 / V2
        </Link>
        <a href="https://jlmvpscode.duckdns.org"
          className="px-3 py-1.5 text-xs text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-lg transition-colors">
          ← Hub
        </a>
      </div>
    </nav>
  )
}

export default function App({ Component, pageProps }) {
  const router = useRouter()
  const isLanding = router.pathname === '/'
  const isV2 = router.pathname === '/v2' || router.pathname.startsWith('/v2/')

  return (
    <div className="min-h-screen bg-gray-950">
      <Script src="/feedback-widget.js" data-api="" data-project="portfolio-tracker" strategy="lazyOnload" />
      {!isLanding && (isV2 ? <V2Nav /> : <V1Nav />)}
      <main className={isLanding ? '' : 'px-6 py-6 max-w-7xl mx-auto'}>
        <Component {...pageProps} />
      </main>
    </div>
  )
}
