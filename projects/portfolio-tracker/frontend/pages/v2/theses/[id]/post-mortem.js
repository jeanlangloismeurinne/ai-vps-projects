import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import {
  Card, CardHeader, CardBody,
  Badge, KeyValue, Section, Dl,
  EmptyState, ErrorState,
} from '../../../../components/v2'

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

// ── Statut final des hypothèses ───────────────────────────────────────────────

const STATUT_FINAL_VARIANT = {
  confirmee:               'emerald',
  partiellement_confirmee: 'sky',
  invalidee:               'red',
  suspendue:               'amber',
}

const STATUT_FINAL_LABEL = {
  confirmee:               'Confirmée',
  partiellement_confirmee: 'Partiellement confirmée',
  invalidee:               'Invalidée',
  suspendue:               'Suspendue',
}

// ── Bandeau de résultat ───────────────────────────────────────────────────────

function ResultBanner({ pm }) {
  const perf = pm.performance_pct
  const isPositive = perf != null && perf >= 0
  const isNegative = perf != null && perf < 0

  return (
    <Card>
      <CardBody>
        <div className="flex items-center gap-8 flex-wrap">
          <div className="text-center">
            <div className="text-xs text-gray-500 mb-1">Performance</div>
            <div className={`text-3xl font-bold ${
              isPositive ? 'text-emerald-400'
              : isNegative ? 'text-red-400'
              : 'text-gray-300'
            }`}>
              {perf != null ? `${perf >= 0 ? '+' : ''}${Number(perf).toFixed(1)} %` : '—'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500 mb-1">Durée de détention</div>
            <div className="text-3xl font-bold text-gray-200">
              {pm.duree_jours != null ? `${pm.duree_jours} j` : '—'}
            </div>
          </div>
          <div className="flex-1 min-w-[200px]">
            <div className="text-xs text-gray-600 bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2">
              <span className="font-medium text-gray-500">Valeurs calculées par le système</span> — <code className="text-gray-500">duree_jours</code> et <code className="text-gray-500">performance_pct</code> sont calculés à partir de la trésorerie réellement encaissée et des dates d'achat/vente, pas déclarés par le modèle.
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  )
}

// ── Décision de sortie ────────────────────────────────────────────────────────

function DecisionSortieBlock({ decision_sortie }) {
  if (decision_sortie == null) {
    return (
      <Card>
        <CardHeader title="Décision de sortie" />
        <CardBody>
          <span className="text-sm text-amber-600 italic">— champ absent</span>
        </CardBody>
      </Card>
    )
  }
  return (
    <Card>
      <CardHeader title="Décision de sortie" />
      <CardBody>
        <p className="text-sm text-gray-300 leading-relaxed">{decision_sortie}</p>
      </CardBody>
    </Card>
  )
}

// ── Sort des hypothèses ───────────────────────────────────────────────────────

function HypothesesFinalesBlock({ hypotheses_finales }) {
  if (!Array.isArray(hypotheses_finales) || hypotheses_finales.length === 0) {
    return (
      <Card>
        <CardHeader title="Sort des hypothèses" />
        <CardBody>
          <p className="text-sm text-gray-500">Aucune hypothèse finale enregistrée.</p>
        </CardBody>
      </Card>
    )
  }
  return (
    <Card>
      <CardHeader
        title="Sort des hypothèses"
        subtitle={`${hypotheses_finales.length} hypothèse${hypotheses_finales.length !== 1 ? 's' : ''} — couverture exhaustive du plan figé`}
      />
      <CardBody className="space-y-3">
        {hypotheses_finales.map((h, i) => (
          <div key={i} className="rounded-lg border border-gray-800 bg-gray-900/30 p-4 space-y-2">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-xs font-mono text-gray-400">
                {h.hypothese_id != null ? h.hypothese_id : <span className="text-amber-600 italic">— champ absent</span>}
              </span>
              {h.statut_final != null ? (
                <Badge variant={STATUT_FINAL_VARIANT[h.statut_final] || 'gray'}>
                  {STATUT_FINAL_LABEL[h.statut_final] || h.statut_final}
                </Badge>
              ) : (
                <span className="text-amber-600 italic text-xs">— statut absent</span>
              )}
            </div>
            {h.predite_vs_realisee != null ? (
              <p className="text-sm text-gray-400">{h.predite_vs_realisee}</p>
            ) : (
              <span className="text-amber-600 italic text-sm">— champ absent</span>
            )}
          </div>
        ))}
      </CardBody>
    </Card>
  )
}

// ── Leçons ────────────────────────────────────────────────────────────────────

function LeconsBlock({ lecons, lesson_entry_ids }) {
  if (!Array.isArray(lecons) || lecons.length === 0) {
    return (
      <Card>
        <CardHeader title="Leçons" />
        <CardBody>
          <p className="text-sm text-gray-500">Aucune leçon enregistrée.</p>
        </CardBody>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader
        title="Leçons"
        subtitle={`${lecons.length} leçon${lecons.length !== 1 ? 's' : ''} — versées à la base de connaissance`}
      />
      <CardBody className="space-y-4">
        <div className="text-xs text-gray-600 bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2">
          Ces leçons ont été versées à la base de connaissance sous forme d'entries de type <code>lesson_learned</code>.
          {Array.isArray(lesson_entry_ids) && lesson_entry_ids.length > 0 && (
            <span>
              {' '}IDs d'entries correspondantes :{' '}
              {lesson_entry_ids.map((eid, i) => (
                <span key={i}>
                  <span className="font-mono text-gray-400">#{eid}</span>
                  {i < lesson_entry_ids.length - 1 ? ', ' : ''}
                </span>
              ))}
            </span>
          )}
        </div>

        {lecons.map((l, i) => (
          <div key={i} className="rounded-lg border border-gray-800 bg-gray-900/30 p-4 space-y-2">
            {l.lecon != null ? (
              <p className="text-sm text-gray-300 leading-relaxed">{l.lecon}</p>
            ) : (
              <span className="text-amber-600 italic text-sm">— champ absent</span>
            )}
            {Array.isArray(l.tags) && l.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {l.tags.map((tag, j) => (
                  <span key={j} className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-800 border border-gray-700 text-gray-400">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </CardBody>
    </Card>
  )
}

// ── Calibration ───────────────────────────────────────────────────────────────

function CalibrationBlock({ calibration, thesisId }) {
  const hasData = Array.isArray(calibration) && calibration.length > 0

  return (
    <Card>
      <CardHeader
        title="Calibration de cette thèse"
        subtitle="Registre prédit → réalisé — source de vérité pour l'apprentissage long terme"
        action={
          <Link href="/v2/calibration" className="text-xs text-emerald-400 hover:text-emerald-300">
            Voir la calibration globale →
          </Link>
        }
      />
      <CardBody className="space-y-4">
        <div className="text-xs text-gray-600 bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2">
          <span className="font-medium text-gray-500">Registre calculé · fait foi</span> — La colonne <code>predite</code> est la valeur <strong>figée au validate</strong>, jamais l'opinion réactualisée par une revue ultérieure. Mesurer son erreur contre sa dernière opinion ne mesure rien : c'est contre la prévision initiale que l'écart est révélateur.
        </div>

        {!hasData ? (
          <p className="text-sm text-gray-500">
            Aucune paire de calibration enregistrée pour cette thèse.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] text-gray-600 uppercase tracking-wide border-b border-gray-800">
                  <th className="py-2 px-3 font-medium">Métrique</th>
                  <th className="py-2 px-3 font-medium text-right">Prédit</th>
                  <th className="py-2 px-3 font-medium text-right">Réalisé</th>
                  <th className="py-2 px-3 font-medium text-right">Écart</th>
                </tr>
              </thead>
              <tbody>
                {calibration.map((row, i) => {
                  const ecart = row.ecart
                  const ecartPositive = ecart != null && ecart > 0
                  const ecartNegative = ecart != null && ecart < 0
                  return (
                    <tr key={i} className="border-t border-gray-800">
                      <td className="py-2 px-3 text-xs font-mono text-gray-400">{row.metric ?? '—'}</td>
                      <td className="py-2 px-3 text-xs text-gray-300 text-right">
                        {row.predite != null ? row.predite : <span className="text-amber-600 italic">—</span>}
                      </td>
                      <td className="py-2 px-3 text-xs text-gray-300 text-right">
                        {row.realisee != null ? row.realisee : <span className="text-amber-600 italic">—</span>}
                      </td>
                      <td className={`py-2 px-3 text-xs font-mono text-right ${
                        ecartPositive ? 'text-emerald-400'
                        : ecartNegative ? 'text-red-400'
                        : 'text-gray-500'
                      }`}>
                        {ecart != null
                          ? `${ecart >= 0 ? '+' : ''}${typeof ecart === 'number' ? ecart.toFixed(2) : ecart}`
                          : <span className="text-amber-600 italic">—</span>
                        }
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  )
}

// ── Bouton de génération de calibration (appel modèle facturé) ────────────────

function GenerateCalibrationButton({ thesisId, onSuccess }) {
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)
  const [errKind, setErrKind] = useState(null)

  async function handleClick() {
    const confirmed = window.confirm(
      'Lancer la calibration ?\n\n' +
      'Cet appel sollicite un modèle IA — il est facturé. Continuer ?'
    )
    if (!confirmed) return

    setLoading(true)
    setErr(null)
    setErrKind(null)
    try {
      const res = await fetch(`${API}/v2/theses/${thesisId}/calibration`, {
        method: 'POST',
      })
      if (res.ok) {
        onSuccess()
        return
      }
      const data = await res.json().catch(() => ({}))
      const detail = data.detail || `Erreur ${res.status}`
      if (res.status === 409) {
        setErr(detail)
        setErrKind('409')
      } else if (res.status === 422) {
        setErr(detail)
        setErrKind('422')
      } else {
        setErr(detail)
        setErrKind('other')
      }
    } catch (e) {
      setErr(String(e))
      setErrKind('other')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      <button
        onClick={handleClick}
        disabled={loading}
        className="px-5 py-2.5 rounded-lg bg-sky-700 hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium text-white transition-colors"
      >
        {loading ? 'Calibration en cours…' : 'Lancer la calibration — appel modèle facturé'}
      </button>
      {err && (
        <div className={`rounded-lg border px-3 py-2 text-sm ${
          errKind === '409'
            ? 'border-amber-800 bg-amber-950/20 text-amber-300'
            : 'border-red-900/50 bg-red-950/20 text-red-400'
        }`}>
          {errKind === '409' && (
            <span className="text-[10px] font-medium uppercase tracking-wide text-amber-500 block mb-0.5">
              Pré-condition d'état non remplie (409)
            </span>
          )}
          {errKind === '422' && (
            <span className="text-[10px] font-medium uppercase tracking-wide text-red-500 block mb-0.5">
              Refus de l'agent — sortie incohérente (422)
            </span>
          )}
          {err}
        </div>
      )}
    </div>
  )
}

// ── Bouton de génération du post-mortem (appel modèle facturé) ────────────────

function GeneratePostMortemButton({ thesisId, onSuccess }) {
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)
  const [errKind, setErrKind] = useState(null)

  async function handleClick() {
    const confirmed = window.confirm(
      'Générer le post-mortem ?\n\n' +
      'Cet appel sollicite un modèle IA — il est facturé. La pré-condition est que la position soit entièrement soldée. Continuer ?'
    )
    if (!confirmed) return

    setLoading(true)
    setErr(null)
    setErrKind(null)
    try {
      const res = await fetch(`${API}/v2/theses/${thesisId}/post-mortem`, {
        method: 'POST',
      })
      if (res.ok) {
        onSuccess()
        return
      }
      const data = await res.json().catch(() => ({}))
      const detail = data.detail || `Erreur ${res.status}`
      if (res.status === 409) {
        setErr(detail)
        setErrKind('409')
      } else if (res.status === 422) {
        setErr(detail)
        setErrKind('422')
      } else {
        setErr(detail)
        setErrKind('other')
      }
    } catch (e) {
      setErr(String(e))
      setErrKind('other')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      <button
        onClick={handleClick}
        disabled={loading}
        className="px-5 py-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium text-white transition-colors"
      >
        {loading ? 'Génération en cours…' : 'Générer le post-mortem — appel modèle facturé'}
      </button>
      {err && (
        <div className={`rounded-lg border px-3 py-2 text-sm ${
          errKind === '409'
            ? 'border-amber-800 bg-amber-950/20 text-amber-300'
            : 'border-red-900/50 bg-red-950/20 text-red-400'
        }`}>
          {errKind === '409' && (
            <span className="text-[10px] font-medium uppercase tracking-wide text-amber-500 block mb-0.5">
              Pré-condition d'état non remplie (409)
            </span>
          )}
          {errKind === '422' && (
            <span className="text-[10px] font-medium uppercase tracking-wide text-red-500 block mb-0.5">
              Refus de l'agent — sortie incohérente (422)
            </span>
          )}
          {err}
        </div>
      )}
    </div>
  )
}

// ── Bloc : Coût (deux appels distincts) ──────────────────────────────────────

function CostBlock({ pm }) {
  return (
    <Card>
      <CardHeader
        title="Coût des appels modèle"
        subtitle="Deux appels distincts — ils ne sont pas additionnés"
      />
      <CardBody className="space-y-4">
        {/* Appel post-mortem */}
        <div>
          <p className="text-[10px] text-gray-600 uppercase tracking-wide mb-2">Appel post-mortem</p>
          <Dl cols={4}>
            <KeyValue label="Modèle" value={pm.model_used ?? <span className="text-gray-600">—</span>} />
            <KeyValue label="Coût" value={fmtCost(pm.cost_usd)} />
            <KeyValue label="Tokens entrants" value={pm.tokens_in ?? <span className="text-gray-600">—</span>} />
            <KeyValue label="Tokens sortants" value={pm.tokens_out ?? <span className="text-gray-600">—</span>} />
          </Dl>
        </div>
        <div className="border-t border-gray-800" />
        {/* Appel calibration — second appel distinct */}
        <div>
          <p className="text-[10px] text-gray-600 uppercase tracking-wide mb-2">
            Appel calibration
            {pm.calibration_at == null && (
              <span className="ml-2 text-gray-700 normal-case">(pas encore effectué)</span>
            )}
          </p>
          <Dl cols={4}>
            <KeyValue label="Date" value={fmtDatetime(pm.calibration_at)} />
            <KeyValue label="Coût" value={fmtCost(pm.calibration_cost_usd)} />
            <KeyValue label="Tokens entrants" value={pm.calibration_tokens_in ?? <span className="text-gray-600">—</span>} />
            <KeyValue label="Tokens sortants" value={pm.calibration_tokens_out ?? <span className="text-gray-600">—</span>} />
          </Dl>
        </div>
      </CardBody>
    </Card>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function PostMortemPage() {
  const router = useRouter()
  const { id } = router.query

  const [thesis, setThesis] = useState(null)
  const [pm, setPm] = useState(null)
  const [pmNotFound, setPmNotFound] = useState(false)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)

  async function loadData() {
    if (!id) return
    setLoading(true)
    setErr(null)
    setPmNotFound(false)

    try {
      const [thesisRes, pmRes] = await Promise.all([
        fetch(`${API}/v2/theses/${id}`),
        fetch(`${API}/v2/theses/${id}/post-mortem`),
      ])

      if (!thesisRes.ok) {
        const d = await thesisRes.json().catch(() => ({}))
        throw new Error(d.detail || `Erreur ${thesisRes.status} sur la thèse`)
      }
      const thesisData = await thesisRes.json()
      setThesis(thesisData)

      if (pmRes.status === 404) {
        setPmNotFound(true)
        setPm(null)
      } else if (!pmRes.ok) {
        const d = await pmRes.json().catch(() => ({}))
        throw new Error(d.detail || `Erreur ${pmRes.status} sur le post-mortem`)
      } else {
        const pmData = await pmRes.json()
        setPm(pmData)
      }
    } catch (e) {
      setErr(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [id])

  // ── Chargement / erreur ──────────────────────────────────────────────────────
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

  const ticker = thesis?.ticker_id || `Thèse #${id}`

  // ── État : pas de post-mortem (404) ──────────────────────────────────────────
  if (pmNotFound) {
    return (
      <div className="space-y-6">
        {/* Fil d'Ariane */}
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Link href="/v2/theses" className="hover:text-gray-300">Thèses V2</Link>
          <span>›</span>
          <Link href={`/v2/theses/${id}`} className="hover:text-gray-300">{ticker}</Link>
          <span>›</span>
          <span className="text-gray-300">Post-mortem</span>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-2xl font-bold text-white">Post-mortem</h1>
          {thesis?.status && (
            <Badge variant={thesis.status === 'active' ? 'active' : 'gray'}>{thesis.status}</Badge>
          )}
        </div>

        <EmptyState
          title="Aucun post-mortem"
          description="Un post-mortem suppose une position entièrement soldée — c'est une pré-condition d'état vérifiée avant toute dépense de tokens (le backend rend 409 si la position n'est pas clôturée)."
        />

        <GeneratePostMortemButton thesisId={id} onSuccess={loadData} />
      </div>
    )
  }

  if (!pm) return null

  const calibration = Array.isArray(pm.calibration) ? pm.calibration : []
  const lessonEntryIds = Array.isArray(pm.lesson_entry_ids) ? pm.lesson_entry_ids : []
  const lecons = Array.isArray(pm.result_json?.lecons) ? pm.result_json.lecons : []
  const hypothesesFinales = Array.isArray(pm.result_json?.hypotheses_finales)
    ? pm.result_json.hypotheses_finales
    : []
  const decisionSortie = pm.result_json?.decision_sortie ?? null

  return (
    <div className="space-y-6">
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Link href="/v2/theses" className="hover:text-gray-300">Thèses V2</Link>
        <span>›</span>
        <Link href={`/v2/theses/${id}`} className="hover:text-gray-300">{ticker}</Link>
        <span>›</span>
        <span className="text-gray-300">Post-mortem</span>
      </div>

      {/* Titre */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-white">Post-mortem</h1>
        {thesis?.status && (
          <Badge variant={thesis.status === 'active' ? 'active' : 'gray'}>{thesis.status}</Badge>
        )}
      </div>

      {/* Bandeau de résultat */}
      <ResultBanner pm={pm} />

      {/* Décision de sortie */}
      <DecisionSortieBlock decision_sortie={decisionSortie} />

      {/* Sort des hypothèses */}
      <HypothesesFinalesBlock hypotheses_finales={hypothesesFinales} />

      {/* Leçons */}
      <LeconsBlock lecons={lecons} lesson_entry_ids={lessonEntryIds} />

      {/* Calibration */}
      <CalibrationBlock calibration={calibration} thesisId={id} />

      {/* Bouton de calibration si registre vide */}
      {calibration.length === 0 && (
        <Section title="Lancer la calibration">
          <p className="text-xs text-gray-500">
            Le registre de calibration est vide. Lancer l'appel modèle pour calculer les paires prédit / réalisé de cette thèse.
          </p>
          <GenerateCalibrationButton thesisId={id} onSuccess={loadData} />
        </Section>
      )}

      {/* Coût */}
      <CostBlock pm={pm} />
    </div>
  )
}
