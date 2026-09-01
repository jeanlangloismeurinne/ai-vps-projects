/**
 * Primitives UI V2 — accent emerald, sans état, sans dépendances npm.
 * À importer : import { Card, Badge, KeyValue, EmptyState, ErrorState } from '../../components/v2'
 */

// ── Card ─────────────────────────────────────────────────────────────────────
export function Card({ children, className = '' }) {
  return (
    <div className={`rounded-xl border border-gray-800 bg-gray-900/50 overflow-hidden ${className}`}>
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action }) {
  return (
    <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between gap-2">
      <div>
        <h2 className="text-sm font-semibold text-gray-200">{title}</h2>
        {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}

export function CardBody({ children, className = '' }) {
  return <div className={`px-4 py-4 ${className}`}>{children}</div>
}

// ── Badge ─────────────────────────────────────────────────────────────────────
const BADGE_VARIANTS = {
  // Statuts thèse
  active:        'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  draft:         'bg-gray-800 text-gray-400 border border-gray-700',
  archived:      'bg-gray-900 text-gray-600 border border-gray-800',
  superseded:    'bg-gray-800 text-gray-500 border border-gray-700',
  // Verdicts
  PROCEED:                    'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  PROCEED_AVEC_CONDITIONS:    'bg-sky-900/50 text-sky-300 border border-sky-700',
  // Alert levels
  RAS:            'bg-gray-800 text-gray-400 border border-gray-700',
  REVIEW_REQUIRED:'bg-amber-900/50 text-amber-300 border border-amber-700',
  CRITICAL:       'bg-red-900/50 text-red-300 border border-red-700',
  // Génériques
  emerald:  'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  sky:      'bg-sky-900/50 text-sky-300 border border-sky-700',
  amber:    'bg-amber-900/50 text-amber-300 border border-amber-700',
  red:      'bg-red-900/50 text-red-300 border border-red-700',
  gray:     'bg-gray-800 text-gray-400 border border-gray-700',
}

export function Badge({ variant = 'gray', children, className = '' }) {
  const cls = BADGE_VARIANTS[variant] || BADGE_VARIANTS.gray
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls} ${className}`}>
      {children}
    </span>
  )
}

// ── KeyValue ──────────────────────────────────────────────────────────────────
export function KeyValue({ label, value, note, locked = false }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-gray-500 flex items-center gap-1">
        {label}
        {locked && (
          <span className="text-gray-600 text-[10px] font-medium uppercase tracking-wide" title="Figé au validate — lecture seule">
            · figé
          </span>
        )}
      </dt>
      <dd className="text-sm text-gray-200">
        {value ?? <span className="text-gray-600">—</span>}
        {note && <span className="text-xs text-gray-500 ml-1">{note}</span>}
      </dd>
    </div>
  )
}

// ── EmptyState ────────────────────────────────────────────────────────────────
export function EmptyState({ title, description }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center mb-4">
        <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <p className="text-sm font-medium text-gray-400">{title}</p>
      {description && <p className="text-xs text-gray-600 mt-1 max-w-xs">{description}</p>}
    </div>
  )
}

// ── ErrorState ────────────────────────────────────────────────────────────────
export function ErrorState({ detail }) {
  return (
    <div className="rounded-xl border border-red-900/50 bg-red-950/20 px-4 py-4">
      <p className="text-sm text-red-400">{detail || 'Erreur de chargement.'}</p>
    </div>
  )
}

// ── Section ───────────────────────────────────────────────────────────────────
export function Section({ title, children, className = '' }) {
  return (
    <section className={`space-y-3 ${className}`}>
      <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">{title}</h3>
      {children}
    </section>
  )
}

// ── Dl (liste de définitions en grille) ───────────────────────────────────────
export function Dl({ children, cols = 2 }) {
  const gridCls = {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-2 sm:grid-cols-3',
    4: 'grid-cols-2 sm:grid-cols-4',
  }[cols] || 'grid-cols-2'
  return <dl className={`grid ${gridCls} gap-x-6 gap-y-4`}>{children}</dl>
}
