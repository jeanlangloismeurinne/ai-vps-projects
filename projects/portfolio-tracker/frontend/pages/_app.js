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
    fetch(`${API}/admin/agents`)
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

export default function App({ Component, pageProps }) {
  return (
    <div className="min-h-screen bg-gray-950">
      <Script src="/feedback-widget.js" data-api="" data-project="portfolio-tracker" strategy="lazyOnload" />
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-2 sticky top-0 z-40 flex-wrap">
        <span className="text-white font-bold mr-3">📈 PT</span>
        {/* V1 */}
        <NavLink href="/portfolio">Portefeuille V1</NavLink>
        <NavLink href="/watchlist-v2">Watchlist V1</NavLink>
        <NavLink href="/calendrier">Calendrier</NavLink>
        <NavLink href="/admin">Admin</NavLink>
        {/* Separator */}
        <span className="text-gray-700 mx-1">|</span>
        {/* V0 */}
        <NavLink href="/" exact>Portfolio (V0)</NavLink>
        <NavLink href="/watchlist">Watchlist (V0)</NavLink>
        <NavLink href="/calendar">Calendrier</NavLink>
        <NavLink href="/analysts">Analystes</NavLink>
        <div className="ml-auto flex items-center gap-3">
          <AgentSyncBadge />
          <MarketTemperatureBadge />
        </div>
      </nav>
      <main className="px-6 py-6 max-w-7xl mx-auto">
        <Component {...pageProps} />
      </main>
    </div>
  )
}
