import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import {
  Card, CardHeader, CardBody,
  Badge, KeyValue, Section, Dl,
  EmptyState, ErrorState,
} from '../../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

// ── Utilitaires ───────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function fmtDatetime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function fmtEur(val) {
  if (val == null) return '—'
  return `${Number(val).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`
}

function fmtPct(val) {
  if (val == null) return '—'
  return `${Number(val).toFixed(1)} %`
}

function fmtCost(val) {
  if (val == null) return '—'
  return `${Number(val).toFixed(4)} $`
}

// ── Bloc : Fourchette de valorisation ─────────────────────────────────────────
// Garde-fou 1 : deux fourchettes TOUJOURS affichées séparément et étiquetées.
function ValuationRanges({ rangeCourante, rangeFigee }) {
  function RangeRow({ range, label, tag }) {
    if (!range) return (
      <div className="flex items-start gap-2">
        <span className="text-xs text-gray-500 w-40 shrink-0 pt-0.5">{label}</span>
        <span className="text-xs text-gray-600">{tag} — non disponible</span>
      </div>
    )
    return (
      <div className="flex items-start gap-3">
        <div className="w-40 shrink-0">
          <span className="text-xs text-gray-500 block">{label}</span>
          <span className="text-[10px] text-gray-600">{tag}</span>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="text-center">
            <div className="text-[10px] text-gray-600 mb-0.5">Bas</div>
            <div className="text-sm font-medium text-gray-300">{range.low != null ? `${range.low}` : '—'}</div>
          </div>
          <div className="text-gray-700">·</div>
          <div className="text-center">
            <div className="text-[10px] text-gray-600 mb-0.5">Central</div>
            <div className="text-sm font-bold text-gray-100">{range.base != null ? `${range.base}` : '—'}</div>
          </div>
          <div className="text-gray-700">·</div>
          <div className="text-center">
            <div className="text-[10px] text-gray-600 mb-0.5">Haut</div>
            <div className="text-sm font-medium text-gray-300">{range.high != null ? `${range.high}` : '—'}</div>
          </div>
        </div>
      </div>
    )
  }

  // Calcul de l'écart base (figée → courante) pour l'afficher
  let ecart = null
  if (rangeFigee?.base != null && rangeCourante?.base != null) {
    const delta = rangeCourante.base - rangeFigee.base
    const sign = delta >= 0 ? '+' : ''
    ecart = `${sign}${delta} depuis la fourchette figée`
  }

  return (
    <Card>
      <CardHeader
        title="Valorisation"
        subtitle="Les deux fourchettes sont affichées séparément — c'est contre la fourchette figée que la calibration mesurera l'erreur de prévision."
      />
      <CardBody className="space-y-5">
        <RangeRow
          range={rangeFigee}
          label="Fourchette figée"
          tag="Figée au validate · référence de calibration"
        />
        <div className="border-t border-gray-800" />
        <RangeRow
          range={rangeCourante}
          label="Fourchette courante"
          tag="Réactualisable par une revue annuelle"
        />
        {ecart && (
          <p className="text-xs text-gray-500 pt-1">
            Écart central : {ecart}
          </p>
        )}
      </CardBody>
    </Card>
  )
}

// ── Bloc : Décision figée ─────────────────────────────────────────────────────
// Garde-fou 4 : verdict + conditions d'entrée + sizing affichés ensemble.
function DecisionBlock({ thesis }) {
  const verdict = thesis.verdict
  const sizing  = thesis.position_sizing_pct
  const conditions = Array.isArray(thesis.conditions_entree) ? thesis.conditions_entree : []

  return (
    <Card>
      <CardHeader title="La décision figée" subtitle="Figée au validate — lecture seule" />
      <CardBody className="space-y-5">
        {/* Verdict + sizing : garde-fou 4 — toujours ensemble */}
        <div className="flex items-center gap-4 flex-wrap">
          <div>
            <div className="text-xs text-gray-500 mb-1">Verdict</div>
            {verdict ? (
              <Badge variant={verdict === 'PROCEED' ? 'PROCEED' : 'PROCEED_AVEC_CONDITIONS'} className="text-sm px-3 py-1">
                {verdict === 'PROCEED' ? 'Proceed' : 'Proceed avec conditions'}
              </Badge>
            ) : (
              <span className="text-sm text-gray-600">—</span>
            )}
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">Sizing recommandé</div>
            <div className="text-lg font-semibold text-gray-100">
              {sizing != null ? `${sizing} %` : '—'}
            </div>
          </div>
        </div>

        {/* Conditions d'entrée */}
        {conditions.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 mb-2">Conditions d'entrée</div>
            <ul className="space-y-1.5">
              {conditions.map((c, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-300">
                  <span className="text-emerald-600 shrink-0 mt-0.5">›</span>
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Acquittements */}
        <div className="grid grid-cols-2 gap-3 pt-1">
          <AckBadge label="Risques acquittés" value={thesis.risk_acks} />
          <AckBadge label="Pré-mortem acquitté" value={thesis.pre_mortem_acked} />
          <AckBadge label="Matrice de risque acquittée" value={thesis.risk_matrix_acked} />
        </div>
      </CardBody>
    </Card>
  )
}

function AckBadge({ label, value }) {
  const checked = value === true || (Array.isArray(value) && value.length > 0)
  return (
    <div className="flex items-center gap-2">
      <span className={`text-sm ${checked ? 'text-emerald-400' : 'text-gray-600'}`}>
        {checked ? '✓' : '○'}
      </span>
      <span className="text-xs text-gray-400">{label}</span>
    </div>
  )
}

// ── Bloc : Hypothèses ─────────────────────────────────────────────────────────
const HYP_STATUS_VARIANT = {
  en_attente:  'gray',
  confirmee:   'emerald',
  infirmee:    'red',
  suspendue:   'amber',
}
const HYP_STATUS_LABEL = {
  en_attente:  'En attente',
  confirmee:   'Confirmée',
  infirmee:    'Infirmée',
  suspendue:   'Suspendue',
}

function HypothesisCard({ h, index }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/30 p-4 space-y-4">
      {/* En-tête hypothèse */}
      <div className="flex items-start gap-3">
        <span className="text-xs text-gray-600 font-mono w-6 shrink-0 pt-0.5">{h.id || `H${index + 1}`}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-200 font-medium">
            {h.enonce != null && h.enonce !== ''
              ? h.enonce
              : <span className="text-amber-600 italic">— champ absent</span>}
          </p>
          <div className="mt-1">
            <Badge variant={HYP_STATUS_VARIANT[h.statut] || 'gray'}>
              {HYP_STATUS_LABEL[h.statut] || h.statut || 'En attente'}
            </Badge>
          </div>
        </div>
      </div>

      {/* KPIs + seuils (figés) */}
      <Dl cols={3}>
        <KeyValue
          label="KPI"
          value={h.kpi != null && h.kpi !== '' ? h.kpi : <span className="text-amber-600 italic">— champ absent</span>}
        />
        <KeyValue
          label="Unité"
          value={h.unite != null && h.unite !== '' ? h.unite : <span className="text-amber-600 italic">— champ absent</span>}
        />
        <KeyValue
          label="Horizon"
          value={h.horizon != null && h.horizon !== '' ? h.horizon : <span className="text-amber-600 italic">— champ absent</span>}
        />
        {/* Garde-fou 2 : seuils en lecture seule, étiquetés « figés » */}
        <KeyValue label="Seuil d'alerte" value={h.seuil_alerte != null ? h.seuil_alerte : <span className="text-amber-600 italic">— champ absent</span>} locked />
        <KeyValue label="Seuil d'invalidation" value={h.seuil_invalidation != null ? h.seuil_invalidation : <span className="text-amber-600 italic">— champ absent</span>} locked />
      </Dl>

      {/* Base rate détaillée (objet imbriqué : taux / reference_class / ajustement) */}
      <div className="text-xs text-gray-500 space-y-0.5 border border-gray-800 rounded-md px-3 py-2">
        <div className="text-[10px] text-gray-600 uppercase tracking-wide mb-1.5">Base rate · figé</div>
        {h.base_rate != null ? (
          <>
            <div>
              Taux de référence :{' '}
              {h.base_rate.taux != null
                ? <span className="text-gray-300">{(h.base_rate.taux * 100).toFixed(0)} %</span>
                : <span className="text-amber-600 italic">— champ absent</span>}
            </div>
            <div>
              Classe de référence :{' '}
              {h.base_rate.reference_class != null && h.base_rate.reference_class !== ''
                ? <span className="text-gray-300">{h.base_rate.reference_class}</span>
                : <span className="text-amber-600 italic">— champ absent</span>}
            </div>
            <div>
              Ajustement :{' '}
              {h.base_rate.ajustement != null
                ? <span className="text-gray-300">{h.base_rate.ajustement}</span>
                : <span className="text-gray-600 italic">aucun (null)</span>}
            </div>
          </>
        ) : (
          <span className="text-amber-600 italic">— objet base_rate absent</span>
        )}
      </div>

      {/* Observations */}
      {(h.derniere_observation || h.derniere_revue) && (
        <div className="border-t border-gray-800 pt-3 space-y-1">
          {h.derniere_observation && (
            <div className="text-xs text-gray-400">
              <span className="text-gray-600">Dernière observation : </span>
              {h.derniere_observation}
            </div>
          )}
          {h.derniere_revue && (
            <div className="text-xs text-gray-500">
              Revue le {fmtDate(h.derniere_revue)}
            </div>
          )}
        </div>
      )}

      {/* Sources */}
      {Array.isArray(h.source_entry_refs) && h.source_entry_refs.length > 0 && (
        <div className="border-t border-gray-800 pt-3">
          <div className="text-[10px] text-gray-600 uppercase tracking-wide mb-1">Sources figées</div>
          <div className="flex flex-wrap gap-1">
            {h.source_entry_refs.map((ref, i) => (
              <span key={i} className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
                {ref.entry_id}{ref.version ? ` v${ref.version}` : ''}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Bloc : Position liée ──────────────────────────────────────────────────────
function PositionBlock({ position }) {
  if (!position) return null
  return (
    <Card>
      <CardHeader title="Position" />
      <CardBody>
        <Dl cols={3}>
          <KeyValue label="Actions" value={position.shares} />
          <KeyValue label="Prix d'achat" value={fmtEur(position.purchase_price_eur)} />
          <KeyValue label="Date d'entrée" value={fmtDate(position.purchase_date)} />
          <KeyValue label="Statut" value={position.status} />
        </Dl>
      </CardBody>
    </Card>
  )
}

// ── Bloc : Sessions de monitoring ─────────────────────────────────────────────
const ALERT_VARIANT = { RAS: 'gray', REVIEW_REQUIRED: 'amber', CRITICAL: 'red' }
const ALERT_LABEL   = { RAS: 'RAS', REVIEW_REQUIRED: 'Révision requise', CRITICAL: 'Critique' }
const SESSION_STATUS_LABEL = {
  pending:        'En attente',
  running:        'En cours',
  completed:      'Terminée',
  failed:         'Échec',
  pending_manual: 'Manuel',
  blocked_sync:   'Bloquée (sync)',
}

function MonitoringRow({ s }) {
  return (
    <tr className="border-t border-gray-800">
      <td className="py-2 px-3 text-xs text-gray-400 font-mono">#{s.id}</td>
      <td className="py-2 px-3 text-xs text-gray-300">Mode {s.mode}</td>
      <td className="py-2 px-3 text-xs">
        <span className="text-gray-400">{SESSION_STATUS_LABEL[s.status] || s.status}</span>
      </td>
      <td className="py-2 px-3 text-xs">
        {s.alert_level
          ? <Badge variant={ALERT_VARIANT[s.alert_level] || 'gray'}>{ALERT_LABEL[s.alert_level] || s.alert_level}</Badge>
          : <span className="text-gray-600">—</span>}
      </td>
      <td className="py-2 px-3 text-xs">
        {s.verdict
          ? <span className="text-gray-300">{s.verdict}</span>
          : <span className="text-gray-600">—</span>}
      </td>
      <td className="py-2 px-3 text-xs text-gray-500">{fmtCost(s.cost_usd)}</td>
      <td className="py-2 px-3 text-xs text-gray-500">{fmtDatetime(s.created_at)}</td>
    </tr>
  )
}

function MonitoringBlock({ thesisId }) {
  const [sessions, setSessions] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!thesisId) return
    fetch(`${API}/v2/theses/${thesisId}/monitoring`)
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`)))
      .then(d => { setSessions(Array.isArray(d) ? d : []); setLoading(false) })
      .catch(e => { setErr(String(e)); setLoading(false) })
  }, [thesisId])

  return (
    <Card>
      <CardHeader
        title="Sessions de monitoring"
        subtitle={sessions ? `${sessions.length} session${sessions.length !== 1 ? 's' : ''}` : undefined}
      />
      {loading && <CardBody><p className="text-sm text-gray-500">Chargement…</p></CardBody>}
      {err && <CardBody><ErrorState detail={err} /></CardBody>}
      {!loading && !err && sessions && sessions.length === 0 && (
        <EmptyState title="Aucune session de monitoring" description="Les sessions apparaissent après le premier déclenchement du monitoring V2." />
      )}
      {!loading && !err && sessions && sessions.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] text-gray-600 uppercase tracking-wide">
                <th className="py-2 px-3 font-medium">ID</th>
                <th className="py-2 px-3 font-medium">Mode</th>
                <th className="py-2 px-3 font-medium">Statut</th>
                <th className="py-2 px-3 font-medium">Alerte</th>
                <th className="py-2 px-3 font-medium">Verdict</th>
                <th className="py-2 px-3 font-medium">Coût</th>
                <th className="py-2 px-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map(s => <MonitoringRow key={s.id} s={s} />)}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────
export default function ThesisV2Detail() {
  const router = useRouter()
  const { id }  = router.query

  const [thesis,  setThesis]  = useState(null)
  const [err,     setErr]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    fetch(`${API}/v2/theses/${id}`)
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`)))
      .then(d => { setThesis(d); setLoading(false) })
      .catch(e => { setErr(String(e)); setLoading(false) })
  }, [id])

  // ── Chargement / erreur ───────────────────────────────────────────────────
  if (loading) return (
    <div className="py-12 text-center text-sm text-gray-500">Chargement…</div>
  )

  if (err) return (
    <div>
      <Link href="/v2/theses" className="text-xs text-gray-500 hover:text-gray-300 mb-4 inline-block">
        ← Retour aux thèses
      </Link>
      <ErrorState detail={err} />
    </div>
  )

  if (!thesis) return null

  const hypotheses = Array.isArray(thesis.hypotheses) ? thesis.hypotheses : []

  // Nom de ticker pour l'en-tête
  const titre = thesis.ticker_symbol || thesis.ticker_id || `Thèse #${id}`

  return (
    <div className="space-y-6">
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Link href="/v2/theses" className="hover:text-gray-300">Thèses V2</Link>
        <span>›</span>
        <span className="text-gray-300">{titre}</span>
      </div>

      {/* Titre */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-white">{titre}</h1>
        <Badge variant={thesis.status === 'active' ? 'active' : 'gray'}>
          {thesis.status || '—'}
        </Badge>
        {thesis.post_mortem_id && (
          <Badge variant="gray">Post-mortem #{thesis.post_mortem_id}</Badge>
        )}
      </div>

      {/* ── Section 1 : La décision figée ─────────────────────────────────── */}
      {/* Garde-fou 4 : verdict toujours avec conditions + sizing */}
      <DecisionBlock thesis={thesis} />

      {/* ── Section 2 : Valorisation ──────────────────────────────────────── */}
      {/* Garde-fou 1 : deux fourchettes côte à côte, séparées, étiquetées */}
      <ValuationRanges
        rangeCourante={thesis.valuation_range}
        rangeFigee={thesis.valuation_range_figee}
      />

      {/* ── Section 3 : Hypothèses ────────────────────────────────────────── */}
      <Section title={`Hypothèses (${hypotheses.length})`}>
        {hypotheses.length === 0 ? (
          <EmptyState title="Aucune hypothèse" description="Les hypothèses sont définies lors de la création de la thèse." />
        ) : (
          <div className="space-y-3">
            {/* Note de lecture seule — garde-fou 2 */}
            <p className="text-xs text-gray-600 bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2">
              Les seuils d'alerte, d'invalidation et le base rate sont figés au validate.
              Une revue ne peut pas les modifier — elle enregistre uniquement le statut, la dernière observation et la date de revue.
            </p>
            {hypotheses.map((h, i) => (
              <HypothesisCard key={h.id || i} h={h} index={i} />
            ))}
          </div>
        )}
      </Section>

      {/* ── Section 4 : Position ──────────────────────────────────────────── */}
      {thesis.position && (
        <Section title="Position">
          <PositionBlock position={thesis.position} />
        </Section>
      )}

      {/* ── Section 5 : Plan de sortie ────────────────────────────────────── */}
      {thesis.exit_plan && (
        <Section title="Plan de sortie">
          <Card>
            <CardBody>
              <Dl cols={2}>
                <KeyValue label="ID du plan" value={thesis.exit_plan.id} />
                <KeyValue label="Statut du plan" value={thesis.exit_plan.exit_status} />
              </Dl>
            </CardBody>
          </Card>
        </Section>
      )}

      {/* ── Section 6 : Sessions de monitoring ────────────────────────────── */}
      {id && <MonitoringBlock thesisId={id} />}
    </div>
  )
}
