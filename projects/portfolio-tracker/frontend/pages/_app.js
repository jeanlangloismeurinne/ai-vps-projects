import '../styles/globals.css'
import Link from 'next/link'
import { useRouter } from 'next/router'

function NavLink({ href, children }) {
  const router = useRouter()
  const active = router.pathname === href || router.pathname.startsWith(href + '/')
  return (
    <Link href={href}
      className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
        active ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
      }`}>
      {children}
    </Link>
  )
}

export default function App({ Component, pageProps }) {
  return (
    <div className="min-h-screen">
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-2">
        <span className="text-white font-bold mr-4">📈 Portfolio Tracker</span>
        <NavLink href="/">Positions</NavLink>
        <NavLink href="/calendar">Calendrier</NavLink>
        <NavLink href="/watchlist">Watchlist</NavLink>
        <NavLink href="/analysts">Analystes</NavLink>
      </nav>
      <main className="px-6 py-6 max-w-7xl mx-auto">
        <Component {...pageProps} />
      </main>
    </div>
  )
}
