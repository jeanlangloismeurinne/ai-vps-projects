import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Card, CardHeader, CardBody, Badge, EmptyState, ErrorState } from '../../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

// Correspondance statut → variante Badge
const STATUS_VARIANT = {
  active:     'active',
  draft:      'draft',
  archived:   'archived',
  superseded: 'superseded',
}

const STATUS_LABEL = {
  active:     'Active',
  draft:      'Brouillon',
  archived:   'Archivée',
  superseded: 'Remplacée',
}

const ALERT_VARIANT = {
  RAS:             'gray',
  REVIEW_REQUIRED: 'amber',
  CRITICAL:        'red',
}

const ALERT_LABEL = {
  RAS:             'RAS',
  REVIEW_REQUIRED: 'Révision',
  CRITICAL:        'Critique',
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function HypothesesBar({ par_statut = {}, nb_total }) {
  if (!nb_total) return <span className="text-gray-600 text-xs">—</span>
  const confirmees  = par_statut['confirmee']   || 0
  const infirmees   = par_statut['infirmee']    || 0
  const en_attente  = nb_total - confirmees - infirmees
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-300">{nb_total} hypothèses</span>
      <span className="flex gap-0.5">
        {confirmees > 0 && (
          <span className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-emerald-900/60 text-emerald-300 border border-emerald-800">
            {confirmees} conf.
          </span>
        )}
        {infirmees > 0 && (
          <span className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-red-900/60 text-red-300 border border-red-800">
            {infirmees} inf.
          </span>
        )}
        {en_attente > 0 && (
          <span className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-gray-800 text-gray-400 border border-gray-700">
            {en_attente} att.
          </span>
        )}
      </span>
    </div>
  )
}

function ThesisRow({ t }) {
  return (
    <Link href={`/v2/theses/${t.id}`}
      className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-0 px-4 py-4 border-t border-gray-800 hover:bg-gray-800/40 transition-colors group">

      {/* Ticker + statut */}
      <div className="w-36 shrink-0 flex items-center gap-2">
        <span className="font-semibold text-white group-hover:text-emerald-300 transition-colors">
          {t.ticker_symbol || t.ticker_id}
        </span>
        <Badge variant={STATUS_VARIANT[t.status] || 'gray'}>
          {STATUS_LABEL[t.status] || t.status}
        </Badge>
      </div>

      {/* Verdict + sizing */}
      <div className="w-56 shrink-0">
        {t.verdict ? (
          <div className="flex items-center gap-2">
            <Badge variant={t.verdict === 'PROCEED' ? 'PROCEED' : 'PROCEED_AVEC_CONDITIONS'}>
              {t.verdict === 'PROCEED' ? 'Proceed' : 'Proceed avec conditions'}
            </Badge>
            {t.position_sizing_pct != null && (
              <span className="text-xs text-gray-400">
                {t.position_sizing_pct}%
              </span>
            )}
          </div>
        ) : (
          <span className="text-xs text-gray-600">Pas encore validée</span>
        )}
      </div>

      {/* Hypothèses */}
      <div className="flex-1 min-w-0">
        <HypothesesBar par_statut={t.hypotheses_par_statut} nb_total={t.nb_hypotheses} />
      </div>

      {/* Position */}
      <div className="w-20 shrink-0 text-xs">
        {t.position ? (
          <span className="text-emerald-400">En position</span>
        ) : (
          <span className="text-gray-600">—</span>
        )}
      </div>

      {/* Dernière session */}
      <div className="w-44 shrink-0 text-xs text-gray-400">
        {t.derniere_session ? (
          <div className="flex flex-col gap-0.5">
            <span>{fmtDate(t.derniere_session.created_at)}</span>
            {t.derniere_session.alert_level && (
              <Badge variant={ALERT_VARIANT[t.derniere_session.alert_level] || 'gray'}>
                {ALERT_LABEL[t.derniere_session.alert_level] || t.derniere_session.alert_level}
              </Badge>
            )}
          </div>
        ) : (
          <span className="text-gray-600">Aucune session</span>
        )}
      </div>

      {/* Plan de sortie */}
      <div className="w-28 shrink-0 text-xs">
        {t.exit_plan ? (
          <span className="text-sky-400">Plan actif</span>
        ) : (
          <span className="text-gray-600">—</span>
        )}
      </div>

      {/* Chevron */}
      <div className="w-5 shrink-0 text-gray-600 group-hover:text-gray-400 hidden sm:block">›</div>
    </Link>
  )
}

export default function ThesesV2List() {
  const [theses, setTheses] = useState(null)
  const [err, setErr]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/v2/theses`)
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`)))
      .then(d => { setTheses(Array.isArray(d) ? d : []); setLoading(false) })
      .catch(e => { setErr(String(e)); setLoading(false) })
  }, [])

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">Thèses V2</h1>
        <p className="text-sm text-gray-500 mt-1">
          Actes de décision figés au validate — verdict, sizing, hypothèses et suivi de monitoring.
        </p>
      </div>

      <Card>
        <CardHeader
          title="Thèses"
          subtitle={theses ? `${theses.length} thèse${theses.length !== 1 ? 's' : ''}` : undefined}
        />

        {loading && (
          <CardBody>
            <p className="text-sm text-gray-500">Chargement…</p>
          </CardBody>
        )}

        {err && (
          <CardBody>
            <ErrorState detail={err} />
          </CardBody>
        )}

        {!loading && !err && theses && theses.length === 0 && (
          <EmptyState
            title="Aucune thèse V2"
            description="Les thèses V2 apparaissent ici après leur création et validation dans le processus d'analyse."
          />
        )}

        {!loading && !err && theses && theses.length > 0 && (
          <>
            {/* En-têtes colonnes */}
            <div className="flex items-center gap-0 px-4 py-2 border-t border-gray-800 text-[11px] text-gray-600 uppercase tracking-wide hidden sm:flex">
              <div className="w-36 shrink-0">Ticker</div>
              <div className="w-56 shrink-0">Verdict · Sizing</div>
              <div className="flex-1">Hypothèses</div>
              <div className="w-20 shrink-0">Position</div>
              <div className="w-44 shrink-0">Dernière session</div>
              <div className="w-28 shrink-0">Plan de sortie</div>
              <div className="w-5 shrink-0" />
            </div>
            {theses.map(t => <ThesisRow key={t.id} t={t} />)}
          </>
        )}
      </Card>
    </div>
  )
}
