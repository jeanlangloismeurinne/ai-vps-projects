import Link from 'next/link'

export default function AgentSyncOverlay({ agentName, adminUrl = '/admin' }) {
  return (
    <div className="absolute inset-0 bg-red-950/95 border border-red-700 flex items-center justify-center z-50 rounded-lg">
      <div className="text-center px-6">
        <p className="text-2xl mb-3">⛔</p>
        <p className="text-red-200 font-semibold text-lg mb-2">Interaction impossible</p>
        <p className="text-red-300 text-sm mb-1">
          Le prompt de l&apos;agent <span className="font-mono font-bold">{agentName}</span> a été modifié
        </p>
        <p className="text-red-300 text-sm mb-5">mais pas encore mis à jour dans Dust.</p>
        <Link href={adminUrl}
          className="inline-block px-4 py-2 bg-red-700 hover:bg-red-600 text-white text-sm rounded font-medium transition-colors">
          Mettre à jour le prompt →
        </Link>
      </div>
    </div>
  )
}
