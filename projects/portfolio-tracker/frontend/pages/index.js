import Link from 'next/link'

function SpaceCard({ href, badge, badgeClass, title, desc, points, cta, accent, icon = '📈' }) {
  return (
    <Link href={href}
      className={`group flex flex-col rounded-2xl border ${accent} bg-gray-900/60 p-7 transition-colors hover:bg-gray-900`}>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">{icon}</span>
        <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${badgeClass}`}>{badge}</span>
      </div>
      <h2 className="text-xl font-bold text-white mb-2">{title}</h2>
      <p className="text-sm text-gray-400 mb-4">{desc}</p>
      <ul className="text-sm text-gray-300 space-y-1.5 mb-6">
        {points.map((p, i) => (
          <li key={i} className="flex gap-2"><span className="text-gray-600">—</span><span>{p}</span></li>
        ))}
      </ul>
      <span className="mt-auto inline-flex items-center gap-1.5 text-sm font-medium text-white">
        {cta} <span className="transition-transform group-hover:translate-x-0.5">→</span>
      </span>
    </Link>
  )
}

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 py-12">
      <div className="text-center mb-10">
        <div className="text-4xl mb-3">📈</div>
        <h1 className="text-2xl font-bold text-white">Portfolio Tracker</h1>
        <p className="text-sm text-gray-500 mt-1">Choisis l'espace de travail</p>
      </div>

      <div className="grid md:grid-cols-3 gap-6 w-full max-w-5xl">
        <SpaceCard
          href="/portfolio"
          badge="V1 — en production"
          badgeClass="bg-indigo-800/60 text-indigo-200"
          accent="border-indigo-900/60 hover:border-indigo-700"
          title="Espace V1"
          desc="Le flux actuel, éprouvé : agents Dust, watchlist, thèses et monitoring."
          points={[
            'Portefeuille & positions suivies',
            'Watchlist + analyse opportunité/thèse',
            'Calendrier & monitoring (agents Dust)',
          ]}
          cta="Ouvrir la V1"
        />
        <SpaceCard
          href="/v2"
          badge="V2 — en construction"
          badgeClass="bg-emerald-800/60 text-emerald-200"
          accent="border-emerald-900/60 hover:border-emerald-700"
          title="Espace V2"
          desc="La nouvelle architecture, disjointe de la V1 : Knowledge Platform, agents DeepInfra, analyses bull/bear/synthèse auditées."
          points={[
            'Base de connaissance versionnée & scorée',
            'Curator (readiness) → research → bull/bear → synthèse',
            'Provider DeepInfra — en validation',
          ]}
          cta="Ouvrir la V2"
        />
        <SpaceCard
          href="/nasdaq"
          icon="🫧"
          badge="NASDAQ — en construction"
          badgeClass="bg-sky-800/60 text-sky-200"
          accent="border-sky-900/60 hover:border-sky-700"
          title="Suivi NASDAQ"
          desc="Spécification indépendante : positionner chaque action du NASDAQ par ancienneté du cours et multiple sur 10 ans."
          points={[
            'Ancienneté du cours (mois) + alertes à 12 mois',
            'Multiple sur 10 ans, graphique à bulles',
            'Recalcul quotidien après clôture US',
          ]}
          cta="Ouvrir le suivi NASDAQ"
        />
      </div>

      <p className="text-xs text-gray-600 mt-10 max-w-xl text-center">
        V1 et V2 partagent l'univers de tickers mais restent disjoints : expérimenter en V2 ne touche pas
        aux données V1. Le suivi NASDAQ est indépendant des deux.
      </p>
    </div>
  )
}
