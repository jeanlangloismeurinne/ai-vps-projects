export default function PostMortemTab({ position, thesis, hypotheses }) {
  if (!position?.exit_price) return (
    <div className="text-gray-500 text-sm py-4">Position non clôturée</div>
  )

  const pnl = position.exit_price && position.entry_price
    ? ((Number(position.exit_price) / Number(position.entry_price) - 1) * 100).toFixed(1)
    : null

  const entryDate = position.entry_date ? new Date(position.entry_date) : null
  const exitDate = position.exit_date ? new Date(position.exit_date) : null
  const holdingMonths = entryDate && exitDate
    ? Math.round((exitDate - entryDate) / (1000 * 60 * 60 * 24 * 30))
    : null

  const EXIT_REASON_LABELS = {
    thesis_invalidated: 'Thèse invalidée',
    target_reached: 'Objectif atteint',
    reallocation: 'Réallocation',
    stop_loss: 'Stop loss',
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'P&L réalisé', value: pnl != null ? `${pnl > 0 ? '+' : ''}${pnl}%` : '—', color: pnl >= 0 ? 'text-emerald-400' : 'text-red-400' },
          { label: 'Durée détention', value: holdingMonths != null ? `${holdingMonths} mois` : '—', color: 'text-white' },
          { label: 'Prix sortie', value: position.exit_price ? `€${Number(position.exit_price).toFixed(2)}` : '—', color: 'text-white' },
          { label: 'Raison', value: EXIT_REASON_LABELS[position.exit_reason] || position.exit_reason || '—', color: 'text-gray-300' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className={`text-base font-semibold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {position.exit_notes && (
        <div className="bg-gray-800 rounded p-4">
          <p className="text-xs text-gray-500 mb-1">Notes de sortie</p>
          <p className="text-gray-200 text-sm">{position.exit_notes}</p>
        </div>
      )}
    </div>
  )
}
