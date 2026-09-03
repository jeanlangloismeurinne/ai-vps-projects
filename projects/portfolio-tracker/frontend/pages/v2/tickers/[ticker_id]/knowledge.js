import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import {
  Card, CardHeader, CardBody,
  Badge, KeyValue, Section, Dl,
  EmptyState, ErrorState,
} from '../../../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

// ── Constantes ────────────────────────────────────────────────────────────────

// 7 tiers fins tels que renvoyés par l'API (clés exactes du payload par_tier)
const FINE_TIERS = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C']

// Regroupement grossier utilisé par l'écran readiness (tier_A / tier_B / tier_C)
const COARSE_GROUPS = {
  'tier_A': { label: 'Tier A (readiness)', tiers: ['A', 'A-'],  variant: 'emerald' },
  'tier_B': { label: 'Tier B (readiness)', tiers: ['B+', 'B', 'B-'], variant: 'sky' },
  'tier_C': { label: 'Tier C (readiness)', tiers: ['C+', 'C'],  variant: 'amber' },
}

const TIER_VARIANT = {
  'A':  'emerald',
  'A-': 'emerald',
  'B+': 'sky',
  'B':  'sky',
  'B-': 'sky',
  'C+': 'amber',
  'C':  'amber',
}

const ENTRY_TYPE_LABEL = {
  fact_financial:    'Financier',
  fact_qualitative:  'Qualitatif',
  agent_synthesis:   'Synthèse agent',
  lesson_learned:    'Leçon',
  question:          'Question',
}

const SOURCE_TYPE_LABEL = {
  edgar_official:        'EDGAR officiel',
  company_ir_official:   'IR officiel',
  web_search_reputable:  'Web (fiable)',
  web_search_general:    'Web (général)',
  agent_synthesis:       'Synthèse agent',
  llm_memory:            'Mémoire LLM',
  manual:                'Manuel',
}

const LIMIT_OPTIONS = [20, 50, 100, 200]

// ── Utilitaires ───────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function fmtScore(score) {
  if (score == null) return '—'
  return (score * 100).toFixed(0) + ' %'
}

// ── Ventilation par tier ──────────────────────────────────────────────────────

function TierBreakdown({ parTier, total }) {
  // Calcul des totaux grossiers depuis les 7 tiers fins
  const coarseCounts = {}
  for (const [groupKey, group] of Object.entries(COARSE_GROUPS)) {
    coarseCounts[groupKey] = group.tiers.reduce((sum, t) => sum + (parTier[t] || 0), 0)
  }

  return (
    <Card>
      <CardHeader
        title="Ventilation par tier de fiabilité"
        subtitle={
          <span>
            <strong className="text-amber-400">Note :</strong>{' '}
            l'écran readiness agrège en 3 tiers grossiers (A+A- → tier_A, B+/B/B- → tier_B, C+/C → tier_C).
            Cette page affiche les 7 tiers fins. Les deux écrans doivent se réconcilier ligne à ligne ci-dessous.
          </span>
        }
      />
      <CardBody className="space-y-5">
        {/* Tiers fins */}
        <div>
          <p className="text-[11px] text-gray-600 uppercase tracking-wide mb-2">7 tiers fins</p>
          <div className="flex flex-wrap gap-2">
            {FINE_TIERS.map(t => {
              const count = parTier[t] || 0
              return (
                <div key={t} className="flex items-center gap-1.5">
                  <Badge variant={TIER_VARIANT[t] || 'gray'}>{t}</Badge>
                  <span className="text-sm text-gray-300 font-mono">{count}</span>
                </div>
              )
            })}
            <div className="flex items-center gap-1.5 ml-4 pl-4 border-l border-gray-700">
              <span className="text-xs text-gray-500">Total</span>
              <span className="text-sm text-gray-200 font-semibold font-mono">{total}</span>
            </div>
          </div>
        </div>

        {/* Tiers grossiers (reconciliation avec readiness) */}
        <div>
          <p className="text-[11px] text-gray-600 uppercase tracking-wide mb-2">3 groupes grossiers (reconciliation readiness)</p>
          <div className="flex flex-wrap gap-4">
            {Object.entries(COARSE_GROUPS).map(([groupKey, group]) => {
              const count = coarseCounts[groupKey]
              return (
                <div key={groupKey} className="flex flex-col gap-0.5">
                  <Badge variant={group.variant}>{groupKey}</Badge>
                  <span className="text-[10px] text-gray-500">
                    {group.tiers.join(' + ')} = {group.tiers.map(t => `${t}:${parTier[t]||0}`).join(', ')}
                  </span>
                  <span className="text-sm font-semibold text-gray-200 font-mono">{count} entries</span>
                </div>
              )
            })}
          </div>
        </div>
      </CardBody>
    </Card>
  )
}

// ── Signaux de qualité ────────────────────────────────────────────────────────
// Ces 4 signaux doivent être VISIBLES sur chaque carte, pas enfouis.
// llm_memory est le signal le plus important : le modèle a parlé de mémoire,
// sans source vérifiée.

function QualitySignals({ entry }) {
  const signals = []

  if (entry.source_type === 'llm_memory') {
    signals.push(
      <span key="llm" className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-red-900/60 text-red-200 border border-red-700" title="Source non vérifiée : le modèle a parlé de mémoire">
        MÉMOIRE LLM — source non vérifiée
      </span>
    )
  }

  if (entry.has_conflict) {
    signals.push(
      <span key="conflict" className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-orange-900/60 text-orange-300 border border-orange-700">
        Conflit détecté
        {entry.conflict_entry_id != null
          ? ` (entry #${entry.conflict_entry_id})`
          : ''}
      </span>
    )
  }

  if (entry.requires_human_review) {
    signals.push(
      <span key="review" className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-900/60 text-amber-300 border border-amber-700">
        Revue humaine requise
      </span>
    )
  }

  if (entry.is_outdated) {
    signals.push(
      <span key="outdated" className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-800 text-gray-400 border border-gray-600">
        Périmée
      </span>
    )
  }

  if (signals.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1.5 mt-1">
      {signals}
    </div>
  )
}

// ── Contenu repliable ─────────────────────────────────────────────────────────

function CollapsibleContent({ content }) {
  const [expanded, setExpanded] = useState(false)

  if (!content) {
    return <span className="text-amber-600 italic text-xs">— champ absent</span>
  }

  const isLong = content.length > 400
  const displayed = (!isLong || expanded) ? content : content.slice(0, 400) + '…'

  return (
    <div className="space-y-1">
      <pre className="text-xs text-gray-300 whitespace-pre-wrap break-words font-sans leading-relaxed bg-gray-900/60 rounded-md px-3 py-2 border border-gray-800">
        {displayed}
      </pre>
      {isLong && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="text-xs text-emerald-500 hover:text-emerald-300 transition-colors"
        >
          {expanded ? 'Replier' : `Afficher tout (${content.length} car.)`}
        </button>
      )}
    </div>
  )
}

// ── Carte d'une entry ─────────────────────────────────────────────────────────

function EntryCard({ entry }) {
  const [showContent, setShowContent] = useState(false)

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/40 overflow-hidden">
      {/* En-tête */}
      <div className="px-4 py-3 border-b border-gray-800 space-y-1.5">
        {/* Titre + ID */}
        <div className="flex items-start gap-3">
          <span className="text-[10px] text-gray-600 font-mono shrink-0 pt-0.5">#{entry.id}</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-200 leading-snug">
              {entry.title != null && entry.title !== ''
                ? entry.title
                : <span className="text-amber-600 italic">— champ absent</span>}
            </p>
            {/* Signaux de qualité — en vedette juste sous le titre */}
            <QualitySignals entry={entry} />
          </div>
        </div>

        {/* Badges tier + type + source_type */}
        <div className="flex flex-wrap items-center gap-2 ml-7">
          <Badge variant={TIER_VARIANT[entry.reliability_tier] || 'gray'}>
            {entry.reliability_tier != null ? entry.reliability_tier : <span className="text-amber-600 italic">— tier absent</span>}
          </Badge>
          <span className="text-xs text-gray-400">
            score : {fmtScore(entry.reliability_score)}
          </span>
          <span className="text-gray-700">·</span>
          <span className="text-xs text-gray-400">
            {ENTRY_TYPE_LABEL[entry.entry_type] || entry.entry_type || <span className="text-amber-600 italic">— type absent</span>}
          </span>
          <span className="text-gray-700">·</span>
          <span className={`text-xs font-medium ${entry.source_type === 'llm_memory' ? 'text-red-400' : 'text-gray-400'}`}>
            {SOURCE_TYPE_LABEL[entry.source_type] || entry.source_type || <span className="text-amber-600 italic">— source_type absent</span>}
          </span>
        </div>
      </div>

      {/* Corps */}
      <div className="px-4 py-3 space-y-3">
        {/* Métadonnées clés */}
        <Dl cols={3}>
          <KeyValue
            label="Source URL"
            value={
              entry.source_url != null
                ? (
                  <a
                    href={entry.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-emerald-400 hover:text-emerald-200 underline underline-offset-2 break-all"
                  >
                    {entry.source_url.length > 60
                      ? entry.source_url.slice(0, 60) + '…'
                      : entry.source_url}
                  </a>
                )
                : <span className="text-gray-600 italic">non renseigné</span>
            }
          />
          <KeyValue
            label="Date source"
            value={
              entry.source_date != null
                ? fmtDate(entry.source_date)
                : <span className="text-gray-600 italic">non renseigné</span>
            }
          />
          <KeyValue
            label="Période fiscale"
            value={
              entry.fiscal_period != null
                ? entry.fiscal_period
                : <span className="text-gray-600 italic">non renseigné</span>
            }
          />
          <KeyValue
            label="Version"
            value={entry.version != null ? `v${entry.version}` : <span className="text-amber-600 italic">— champ absent</span>}
          />
          <KeyValue
            label="Valide depuis"
            value={
              entry.valid_from != null
                ? fmtDate(entry.valid_from)
                : <span className="text-amber-600 italic">— champ absent</span>
            }
          />
          <KeyValue
            label="Langue"
            value={
              entry.lang != null
                ? entry.lang
                : <span className="text-amber-600 italic">— champ absent</span>
            }
          />
        </Dl>

        {/* Note de fiabilité */}
        {entry.reliability_note != null ? (
          <p className="text-xs text-gray-500 bg-gray-900/50 border border-gray-800 rounded px-2 py-1">
            {entry.reliability_note}
          </p>
        ) : (
          <p className="text-xs text-amber-600 italic">— reliability_note absente</p>
        )}

        {/* Champs covers (MVDD) */}
        <div>
          <p className="text-[10px] text-gray-600 uppercase tracking-wide mb-1">Champs MVDD couverts (covers)</p>
          {Array.isArray(entry.covers) && entry.covers.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {entry.covers.map((c, i) => (
                <span key={i} className="inline-flex items-center px-1.5 py-0.5 rounded bg-gray-800 border border-gray-700 text-[10px] text-gray-300 font-mono">
                  {c}
                </span>
              ))}
            </div>
          ) : entry.covers === null ? (
            <span className="text-xs text-gray-600 italic">non renseigné (null)</span>
          ) : (
            <span className="text-xs text-amber-600 italic">— champ absent</span>
          )}
        </div>

        {/* Tags */}
        {Array.isArray(entry.tags) && entry.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {entry.tags.map((tag, i) => (
              <span key={i} className="inline-flex items-center px-1.5 py-0.5 rounded bg-gray-800/60 text-[10px] text-gray-500 border border-gray-800">
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Contenu textuel */}
        <div>
          <button
            onClick={() => setShowContent(c => !c)}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-1"
          >
            <span>{showContent ? '▼' : '▶'}</span>
            <span>{showContent ? 'Masquer le contenu' : 'Afficher le contenu'}</span>
          </button>
          {showContent && (
            <div className="mt-2">
              <CollapsibleContent content={entry.content} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Filtres ───────────────────────────────────────────────────────────────────

function Filters({ filters, onChange }) {
  return (
    <Card>
      <CardHeader title="Filtres" />
      <CardBody>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {/* entry_type */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Type d'entry</label>
            <select
              value={filters.entry_type}
              onChange={e => onChange({ ...filters, entry_type: e.target.value, offset: 0 })}
              className="text-sm bg-gray-800 border border-gray-700 text-gray-200 rounded px-2 py-1"
            >
              <option value="">Tous</option>
              {Object.entries(ENTRY_TYPE_LABEL).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </div>

          {/* reliability_tier */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Tier de fiabilité</label>
            <select
              value={filters.reliability_tier}
              onChange={e => onChange({ ...filters, reliability_tier: e.target.value, offset: 0 })}
              className="text-sm bg-gray-800 border border-gray-700 text-gray-200 rounded px-2 py-1"
            >
              <option value="">Tous</option>
              {FINE_TIERS.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {/* covers (filtre sur chemin MVDD) */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Champ MVDD (covers)</label>
            <input
              type="text"
              value={filters.covers}
              onChange={e => onChange({ ...filters, covers: e.target.value, offset: 0 })}
              placeholder="ex: financials.roic_pct"
              className="text-sm bg-gray-800 border border-gray-700 text-gray-200 rounded px-2 py-1 placeholder-gray-600"
            />
          </div>

          {/* include_inactive */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Entrées inactives</label>
            <label className="flex items-center gap-2 mt-1 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.include_inactive}
                onChange={e => onChange({ ...filters, include_inactive: e.target.checked, offset: 0 })}
                className="rounded border-gray-700 bg-gray-800 text-emerald-500"
              />
              <span className="text-sm text-gray-300">Inclure</span>
            </label>
          </div>
        </div>

        {/* Limite */}
        <div className="flex items-center gap-3 mt-4 pt-4 border-t border-gray-800">
          <label className="text-xs text-gray-500">Résultats par page :</label>
          <div className="flex gap-1">
            {LIMIT_OPTIONS.map(l => (
              <button
                key={l}
                onClick={() => onChange({ ...filters, limit: l, offset: 0 })}
                className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                  filters.limit === l
                    ? 'bg-emerald-800 text-emerald-200 border border-emerald-700'
                    : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600'
                }`}
              >
                {l}
              </button>
            ))}
          </div>
        </div>
      </CardBody>
    </Card>
  )
}

// ── Pagination ────────────────────────────────────────────────────────────────

function Pagination({ total, limit, offset, onChange }) {
  const page     = Math.floor(offset / limit) + 1
  const pageCount = Math.ceil(total / limit)

  if (pageCount <= 1) return null

  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-500 text-xs">
        {offset + 1}–{Math.min(offset + limit, total)} sur {total}
      </span>
      <div className="flex gap-2">
        <button
          disabled={page <= 1}
          onClick={() => onChange(Math.max(0, offset - limit))}
          className="px-3 py-1 rounded text-xs bg-gray-800 border border-gray-700 text-gray-300 disabled:opacity-40 hover:border-gray-500 transition-colors"
        >
          ← Précédent
        </button>
        <span className="px-3 py-1 text-xs text-gray-500">
          {page} / {pageCount}
        </span>
        <button
          disabled={page >= pageCount}
          onClick={() => onChange(offset + limit)}
          className="px-3 py-1 rounded text-xs bg-gray-800 border border-gray-700 text-gray-300 disabled:opacity-40 hover:border-gray-500 transition-colors"
        >
          Suivant →
        </button>
      </div>
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function KnowledgeV2() {
  const router   = useRouter()
  const { ticker_id } = router.query

  const [data,    setData]    = useState(null)   // { total, par_tier, entries }
  const [err,     setErr]     = useState(null)
  const [loading, setLoading] = useState(false)

  const [filters, setFilters] = useState({
    entry_type:      '',
    reliability_tier: '',
    covers:          '',
    include_inactive: false,
    limit:           50,
    offset:          0,
  })

  const fetchData = useCallback(() => {
    if (!ticker_id) return

    setLoading(true)
    setErr(null)

    const params = new URLSearchParams()
    if (filters.entry_type)       params.set('entry_type',       filters.entry_type)
    if (filters.reliability_tier) params.set('reliability_tier', filters.reliability_tier)
    if (filters.covers)           params.set('covers',           filters.covers)
    if (filters.include_inactive) params.set('include_inactive', 'true')
    params.set('limit',  String(filters.limit))
    params.set('offset', String(filters.offset))

    const url = `${API}/tickers/${ticker_id}/knowledge/entries?${params.toString()}`

    fetch(url)
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`)))
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setErr(String(e)); setLoading(false) })
  }, [ticker_id, filters])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // ── Chargement / erreur ───────────────────────────────────────────────────

  if (!ticker_id) {
    return <div className="py-12 text-center text-sm text-gray-500">Chargement…</div>
  }

  return (
    <div className="space-y-6">
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Link href="/v2/theses" className="hover:text-gray-300">Thèses V2</Link>
        <span>›</span>
        <Link href={`/v2/tickers/${ticker_id}`} className="hover:text-gray-300">{ticker_id}</Link>
        <span>›</span>
        <span className="text-gray-300">Base de connaissance</span>
      </div>

      {/* Titre */}
      <div>
        <h1 className="text-2xl font-bold text-white">
          {ticker_id} — Base de connaissance V2
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Entries de connaissance structurées qui fondent les analyses V2.
          Source : <code className="text-xs text-gray-400">/tickers/{ticker_id}/knowledge/entries</code>
        </p>
      </div>

      {/* Ventilation par tier (toujours affichée si données disponibles) */}
      {data && (
        <TierBreakdown parTier={data.par_tier} total={data.total} />
      )}

      {/* Filtres */}
      <Filters filters={filters} onChange={setFilters} />

      {/* État de chargement */}
      {loading && (
        <Card>
          <CardBody>
            <p className="text-sm text-gray-500">Chargement…</p>
          </CardBody>
        </Card>
      )}

      {/* Erreur */}
      {!loading && err && (
        <ErrorState detail={err} />
      )}

      {/* Liste des entries */}
      {!loading && !err && data && (
        <>
          {/* En-tête liste */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-400">
              {data.total === 0
                ? 'Aucune entry'
                : `${data.total} entry${data.total > 1 ? 's' : ''} — page ${Math.floor(filters.offset / filters.limit) + 1}`}
              {filters.entry_type || filters.reliability_tier || filters.covers || filters.include_inactive
                ? ' (filtres actifs)'
                : ''}
            </p>
            <button
              onClick={fetchData}
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors border border-gray-700 rounded px-2 py-1"
            >
              Rafraîchir
            </button>
          </div>

          {data.entries.length === 0 ? (
            <EmptyState
              title="Aucune entry dans ces critères"
              description="Modifiez les filtres ou incluez les entrées inactives."
            />
          ) : (
            <>
              <div className="space-y-3">
                {data.entries.map(entry => (
                  <EntryCard key={entry.id} entry={entry} />
                ))}
              </div>
              <Pagination
                total={data.total}
                limit={filters.limit}
                offset={filters.offset}
                onChange={newOffset => setFilters(f => ({ ...f, offset: newOffset }))}
              />
            </>
          )}
        </>
      )}
    </div>
  )
}
