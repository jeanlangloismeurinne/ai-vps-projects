import Link from 'next/link'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import {
  Card, CardHeader, CardBody,
  Badge, KeyValue, Section,
  EmptyState, ErrorState,
} from '../../../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

function fmtDatetime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function fmtCost(val) {
  if (val == null) return '—'
  return `${Number(val).toFixed(4)} $`
}

// La liste renvoyée par GET /tickers/{id}/research contient uniquement :
// id, status, cost_usd, created_at
// Ne rien afficher de plus — un champ absent vaut « — » affiché, pas du vide.
function MemoRow({ memo, tickerId }) {
  const statusVariant = memo.status === 'validated' ? 'active'
    : memo.status === 'draft' ? 'draft'
    : 'gray'

  return (
    <tr className="border-t border-gray-800 hover:bg-gray-900/40 transition-colors">
      <td className="py-3 px-4 text-xs text-gray-400 font-mono">#{memo.id != null ? memo.id : '— champ absent'}</td>
      <td className="py-3 px-4 text-xs">
        {memo.status != null
          ? <Badge variant={statusVariant}>{memo.status}</Badge>
          : <span className="text-amber-600 italic">— champ absent</span>}
      </td>
      <td className="py-3 px-4 text-xs text-gray-400">
        {memo.cost_usd != null ? fmtCost(memo.cost_usd) : '—'}
      </td>
      <td className="py-3 px-4 text-xs text-gray-500">
        {memo.created_at != null ? fmtDatetime(memo.created_at) : '—'}
      </td>
      <td className="py-3 px-4 text-xs">
        <Link
          href={`/v2/research/${memo.id}`}
          className="text-emerald-400 hover:text-emerald-300 font-medium"
        >
          Voir le memo →
        </Link>
      </td>
    </tr>
  )
}

export default function TickerResearchList() {
  const router = useRouter()
  const { ticker_id } = router.query

  const [memos, setMemos]   = useState(null)
  const [err, setErr]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!ticker_id) return
    fetch(`${API}/tickers/${ticker_id}/research`)
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`)))
      .then(d => { setMemos(Array.isArray(d) ? d : []); setLoading(false) })
      .catch(e => { setErr(String(e)); setLoading(false) })
  }, [ticker_id])

  if (loading) return (
    <div className="py-12 text-center text-sm text-gray-500">Chargement…</div>
  )

  if (err) return (
    <div>
      <Link href="/v2" className="text-xs text-gray-500 hover:text-gray-300 mb-4 inline-block">
        ← Accueil V2
      </Link>
      <ErrorState detail={err} />
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Link href="/v2" className="hover:text-gray-300">V2</Link>
        <span>›</span>
        <Link href={`/v2/tickers/${ticker_id}/knowledge`} className="hover:text-gray-300">
          {ticker_id}
        </Link>
        <span>›</span>
        <span className="text-gray-300">Research memos</span>
      </div>

      {/* Titre */}
      <div>
        <h1 className="text-2xl font-bold text-white">
          Research memos — {ticker_id || '—'}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Notes de recherche fondamentale produites par le research-agent. Chaque memo est
          la base factuelle NEUTRE sur laquelle bull et bear construisent leurs cas.
        </p>
      </div>

      {/* Table des memos */}
      <Card>
        <CardHeader
          title="Memos"
          subtitle={
            memos
              ? `${memos.length} memo${memos.length !== 1 ? 's' : ''}`
              : undefined
          }
        />
        {!memos || memos.length === 0 ? (
          <EmptyState
            title="Aucun memo disponible"
            description="Le research-agent n'a pas encore produit de note de recherche pour ce ticker."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] text-gray-600 uppercase tracking-wide border-b border-gray-800">
                  <th className="py-2 px-4 font-medium">ID</th>
                  <th className="py-2 px-4 font-medium">Statut</th>
                  <th className="py-2 px-4 font-medium">Coût</th>
                  <th className="py-2 px-4 font-medium">Créé le</th>
                  <th className="py-2 px-4 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {memos.map(memo => (
                  <MemoRow key={memo.id} memo={memo} tickerId={ticker_id} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
