import { noFloor, pct, ratioColor, times } from './ValeurPanel'

// Badge de carte : écart au plancher et part empruntée de la hausse sur 10 ans. Un clic ouvre l'onglet Valeur.
export function ValeurBadge({ v, onClick }) {
  if (!v) return null
  const p = v.period
  let main
  if (v.ratio == null) main = <span className="text-red-400">{noFloor(v)}</span>
  else main = <span className={ratioColor(v.ratio, v.degraded)}>{times(v.ratio)} le plancher{v.degraded ? ' · caduc' : ''}</span>
  const borrowed = p?.ok && p.borrowed != null
    ? (p.borrowed > 0.05 ? <span className="text-amber-300">{Math.round(100 * p.borrowed)} % emprunté</span> : <span className="text-emerald-300">hausse méritée</span>)
    : null
  return (
    <button onClick={onClick} title="Ouvrir l'onglet Valeur"
      className="mt-2 inline-flex flex-wrap items-center gap-x-2 gap-y-0.5 rounded border border-gray-700 bg-gray-950/60 px-2 py-0.5 text-xs hover:border-emerald-700">
      {main}
      {borrowed && <span className="text-gray-600">·</span>}
      {borrowed}
      {p?.ok && <span className="text-gray-500">({pct(p.annual?.total, 0)}/an sur 10 ans)</span>}
    </button>
  )
}
