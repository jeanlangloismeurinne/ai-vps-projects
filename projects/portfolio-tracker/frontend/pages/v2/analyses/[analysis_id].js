/**
 * Détail d'une analyse V2 (bull | bear | synthesis).
 *
 * Structure réelle des payloads (établie sur les IDs 8, 9, 10, 11, 4 — production) :
 *
 * CHAMPS COMMUNS (tous types) :
 *   id, ticker_id, analysis_type, schema_version,
 *   result_json, result_json_original,
 *   context_pack_entry_id, research_memo_id,
 *   bull_analysis_id, bear_analysis_id, round, supersedes_id,
 *   provider_used, model_used, prompt_snapshot, grounding_report,
 *   tokens_in, tokens_out, cost_usd, status, created_at, updated_at, knowledge_refs
 *
 * result_json BULL :
 *   arguments[], conviction, catalyseurs[], indicateurs{conviction,qualite_info,marge_securite},
 *   valorisation{methode,scenarios{base,bear,bull},assumptions{multiple_sortie,croissance_revenue,expansion_marge_fcf},
 *                horizon_ans,reverse_dcf{verdict,croissance_implicite_prix_actuel_pct}},
 *   schema_version, grounding_report{etayees,non_etayees,affirmations_total},
 *   variant_perception{type,enonce,horizon_mois,source_entry_refs[],catalyseur_re_rating}
 *
 * result_json BEAR (tout ce que bull a +) :
 *   refutation_du_bull[]{cible,contre_argument,source_entry_refs[]},  <-- VIDE en production, rempli en mode refutation
 *   failles_bull_conventionnel[],
 *   scenario_destruction_valeur{prix_bear,perte_pct,declencheurs[]},
 *   conviction_negative
 *
 * result_json SYNTHESIS :
 *   hypotheses[]{id,kpi,unite,enonce,statut,horizon,base_rate{taux,ajustement,reference_class},
 *                seuil_alerte,seuil_invalidation,source_entry_refs[]},
 *   risk_matrix{axes{conviction,qualite_info,marge_securite,qualite_business},
 *               verdict, rationale, pre_mortem[],
 *               position_sizing{inputs,methode,pct_max,pct_formule,cap_applique{actif,contrainte,valeur_pct},
 *                               pct_recommande,cout_opportunite,override_utilisateur,
 *                               ajustement_justification,risques_correles_portefeuille[]},
 *               sources_summary{tier_A,tier_B,total_entries,tier_C_llm_memory},
 *               risques_acceptes[]{risque,probabilite,impact,reversible,base_rate,
 *                                  reponse_si_materialise,hypothese_liee,source_entry_refs[]},
 *               conditions_entree[], needs_second_round, second_round_trigger},
 *   schema_version
 */

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

function fmtDatetime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function fmtCost(val) {
  if (val == null) return '— champ absent'
  return `${Number(val).toFixed(4)} $`
}

function fmtPct(val, scale = 1) {
  if (val == null) return '—'
  return `${(Number(val) * scale).toFixed(1)} %`
}

// Sentinel visible pour un champ qui doit être là mais n'est pas
function Absent() {
  return <span className="text-amber-600 italic text-xs">— champ absent</span>
}

// Sentinel visible pour un null intentionnel
function NonRenseigne() {
  return <span className="text-gray-600 italic text-xs">non renseigné</span>
}

// ── Badges ────────────────────────────────────────────────────────────────────

const STATUS_VARIANT = { draft: 'draft', final: 'emerald', superseded: 'superseded' }
const TYPE_LABELS = { bull: 'Bull', bear: 'Bear', synthesis: 'Synthèse' }
const TYPE_VARIANTS = { bull: 'emerald', bear: 'red', synthesis: 'sky' }

// ── Section : Télémétrie (discrète) ───────────────────────────────────────────

function TelemetryBlock({ analysis }) {
  return (
    <Card>
      <CardHeader title="Télémétrie" subtitle="Fournisseur, modèle, tokens, coût" />
      <CardBody>
        <Dl cols={2}>
          <KeyValue
            label="Fournisseur"
            value={analysis.provider_used ?? <Absent />}
          />
          <KeyValue
            label="Modèle"
            value={analysis.model_used ?? <Absent />}
          />
          <KeyValue
            label="Tokens entrants"
            value={analysis.tokens_in != null ? analysis.tokens_in.toLocaleString('fr-FR') : <Absent />}
          />
          <KeyValue
            label="Tokens sortants"
            value={analysis.tokens_out != null ? analysis.tokens_out.toLocaleString('fr-FR') : <Absent />}
          />
          <KeyValue
            label="Coût"
            value={fmtCost(analysis.cost_usd)}
          />
          <KeyValue
            label="Grounding report (racine)"
            value={analysis.grounding_report != null
              ? <span className="text-gray-300">{JSON.stringify(analysis.grounding_report)}</span>
              : <NonRenseigne />}
          />
        </Dl>
      </CardBody>
    </Card>
  )
}

// ── Section : Lignée ──────────────────────────────────────────────────────────

function LineageBlock({ analysis }) {
  return (
    <Card>
      <CardHeader title="Lignée" subtitle="Round, sources, analyses liées" />
      <CardBody>
        <Dl cols={2}>
          <KeyValue label="Round" value={analysis.round ?? <Absent />} />
          <KeyValue label="Statut" value={
            <Badge variant={STATUS_VARIANT[analysis.status] || 'gray'}>
              {analysis.status || '—'}
            </Badge>
          } />
          <KeyValue
            label="Supersède"
            value={analysis.supersedes_id != null
              ? <Link href={`/v2/analyses/${analysis.supersedes_id}`} className="text-sky-400 hover:underline font-mono">#{analysis.supersedes_id}</Link>
              : <NonRenseigne />}
          />
          <KeyValue
            label="Context pack"
            value={analysis.context_pack_entry_id != null ? `#${analysis.context_pack_entry_id}` : <NonRenseigne />}
          />
          <KeyValue
            label="Research memo"
            value={analysis.research_memo_id != null ? `#${analysis.research_memo_id}` : <NonRenseigne />}
          />
          {/* Uniquement pour la synthèse */}
          {analysis.analysis_type === 'synthesis' && (
            <>
              <KeyValue
                label="Bull utilisé"
                value={analysis.bull_analysis_id != null
                  ? <Link href={`/v2/analyses/${analysis.bull_analysis_id}`} className="text-emerald-400 hover:underline font-mono">#{analysis.bull_analysis_id}</Link>
                  : <span className="text-amber-600 italic text-xs">— aucun bull_analysis_id</span>}
              />
              <KeyValue
                label="Bear utilisé"
                value={analysis.bear_analysis_id != null
                  ? <Link href={`/v2/analyses/${analysis.bear_analysis_id}`} className="text-red-400 hover:underline font-mono">#{analysis.bear_analysis_id}</Link>
                  : <span className="text-amber-600 italic text-xs">— aucun bear_analysis_id</span>}
              />
            </>
          )}
        </Dl>
      </CardBody>
    </Card>
  )
}

// ── Section : Diff result_json vs result_json_original ───────────────────────

/**
 * Compare récursivement deux objets et retourne les chemins dont la valeur diffère.
 * Règle de comparaison : JSON.stringify strict (pas de coercion).
 */
function diffObjects(a, b, prefix = '') {
  const diffs = []
  const allKeys = new Set([
    ...Object.keys(a || {}),
    ...Object.keys(b || {}),
  ])
  for (const key of allKeys) {
    const path = prefix ? `${prefix}.${key}` : key
    const va = (a || {})[key]
    const vb = (b || {})[key]
    if (typeof va === 'object' && va !== null && typeof vb === 'object' && vb !== null) {
      diffs.push(...diffObjects(va, vb, path))
    } else if (JSON.stringify(va) !== JSON.stringify(vb)) {
      diffs.push({ path, rj: va, orig: vb })
    }
  }
  return diffs
}

function DiffBlock({ rj, rjOrig }) {
  const diffs = diffObjects(rj, rjOrig)

  return (
    <Card>
      <CardHeader
        title="result_json vs result_json_original"
        subtitle="L'original est la sortie brute du modèle ; result_json est après corrections déterministes Python."
      />
      <CardBody>
        {diffs.length === 0 ? (
          <p className="text-sm text-gray-400">
            Les deux versions sont <strong className="text-gray-200">identiques</strong> — le code Python n'a appliqué aucune correction sur cette analyse.
          </p>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-amber-400">
              {diffs.length} chemin{diffs.length !== 1 ? 's' : ''} diffèrent — le code a rattrapé le modèle sur ces points.
            </p>
            <div className="space-y-2">
              {diffs.map((d, i) => (
                <div key={i} className="rounded-md border border-gray-800 bg-gray-900/30 px-3 py-2 space-y-1">
                  <div className="text-xs font-mono text-gray-400">{d.path}</div>
                  <div className="text-xs">
                    <span className="text-gray-500">result_json : </span>
                    <span className="text-gray-200">{JSON.stringify(d.rj)}</span>
                  </div>
                  <div className="text-xs">
                    <span className="text-gray-500">original :    </span>
                    <span className="text-amber-300">{JSON.stringify(d.orig)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  )
}

// ── Section : knowledge_refs ───────────────────────────────────────────────────

function KnowledgeRefsBlock({ refs }) {
  const [expanded, setExpanded] = useState(false)

  if (!Array.isArray(refs) || refs.length === 0) {
    return (
      <Card>
        <CardHeader title="Références de connaissance (knowledge_refs)" />
        <CardBody>
          <p className="text-sm text-gray-500 italic">Aucune référence.</p>
        </CardBody>
      </Card>
    )
  }

  const shown = expanded ? refs : refs.slice(0, 5)

  return (
    <Card>
      <CardHeader
        title={`Références de connaissance (${refs.length})`}
        subtitle="Provenance figée AU MOMENT DE L'USAGE — snapshot immuable. reliability_at_use est la fiabilité de l'entrée au moment de l'analyse, pas la valeur actuelle."
      />
      <CardBody className="space-y-2">
        <div className="rounded-md border border-amber-900/30 bg-amber-950/10 px-3 py-2 mb-3">
          <p className="text-xs text-amber-400">
            Ces références sont un snapshot figé. Elles ne correspondent pas à une jointure live sur la base de connaissance actuelle :
            les entries peuvent avoir évolué (nouvelles versions) depuis l'analyse.
            <code className="text-amber-300 ml-1">reliability_at_use</code> est la fiabilité telle qu'elle était à l'instant de l'analyse.
          </p>
        </div>
        <div className="space-y-2">
          {shown.map((ref, i) => (
            <div key={i} className="rounded-md border border-gray-800 bg-gray-900/20 px-3 py-2 space-y-1">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-xs font-mono text-gray-300">
                  entry #{ref.entry_id != null ? ref.entry_id : <Absent />} v{ref.entry_version != null ? ref.entry_version : '?'}
                </span>
                <span className="text-xs text-gray-500">
                  fiabilité au moment de l'usage :{' '}
                  {ref.reliability_at_use != null
                    ? <span className="text-sky-400">{Number(ref.reliability_at_use).toFixed(3)}</span>
                    : <Absent />}
                </span>
                {ref.field_path != null && (
                  <span className="text-xs text-gray-500 font-mono">champ : {ref.field_path}</span>
                )}
              </div>
              {ref.content_snapshot != null ? (
                <p className="text-xs text-gray-400 leading-relaxed line-clamp-3" title={ref.content_snapshot}>
                  {ref.content_snapshot}
                </p>
              ) : (
                <p className="text-xs text-gray-600 italic">— content_snapshot absent</p>
              )}
            </div>
          ))}
        </div>
        {refs.length > 5 && (
          <button
            onClick={() => setExpanded(e => !e)}
            className="text-xs text-sky-400 hover:text-sky-300 mt-2"
          >
            {expanded ? `Réduire (${refs.length} au total)` : `Voir les ${refs.length - 5} suivantes…`}
          </button>
        )}
      </CardBody>
    </Card>
  )
}

// ── Section : prompt_snapshot ─────────────────────────────────────────────────

function PromptBlock({ prompt }) {
  const [open, setOpen] = useState(false)

  return (
    <Card>
      <CardHeader
        title="Prompt snapshot"
        subtitle="Prompt envoyé au modèle — figé au moment de l'appel, jamais tronqué."
        action={
          <button onClick={() => setOpen(o => !o)} className="text-xs text-sky-400 hover:text-sky-300">
            {open ? 'Replier' : 'Déplier'}
          </button>
        }
      />
      {open && (
        <CardBody>
          {prompt != null ? (
            <pre className="text-xs text-gray-400 whitespace-pre-wrap break-words font-mono leading-relaxed max-h-[32rem] overflow-y-auto">
              {prompt}
            </pre>
          ) : (
            <NonRenseigne />
          )}
        </CardBody>
      )}
    </Card>
  )
}

// ── Blocs métier : BULL & BEAR ─────────────────────────────────────────────────

function SourceRefs({ refs }) {
  if (!Array.isArray(refs) || refs.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {refs.map((r, i) => (
        <span key={i} className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
          #{r.entry_id != null ? r.entry_id : '?'}{r.version ? ` v${r.version}` : ''}
        </span>
      ))}
    </div>
  )
}

function ArgumentCard({ arg, index }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/30 p-4 space-y-3">
      <div className="font-medium text-sm text-gray-200">
        {arg.titre != null && arg.titre !== ''
          ? arg.titre
          : <Absent />}
      </div>
      <Dl cols={2}>
        <KeyValue
          label="Probabilité"
          value={arg.probabilite != null ? `${(arg.probabilite * 100).toFixed(0)} %` : <Absent />}
        />
        <KeyValue label="Base rate" value={
          arg.base_rate != null ? (
            <span>
              {arg.base_rate.taux != null ? `${(arg.base_rate.taux * 100).toFixed(0)} %` : <Absent />}
              {' '}
              <span className="text-xs text-gray-500">
                ({arg.base_rate.ajustement != null
                  ? `ajust. ${arg.base_rate.ajustement}`
                  : 'sans ajustement'})
              </span>
            </span>
          ) : <Absent />
        } />
      </Dl>
      {arg.base_rate?.reference_class != null && (
        <p className="text-xs text-gray-500 italic border-l-2 border-gray-700 pl-2">
          Classe de référence : {arg.base_rate.reference_class}
        </p>
      )}
      {arg.explication != null && arg.explication !== '' ? (
        <p className="text-sm text-gray-300 leading-relaxed">{arg.explication}</p>
      ) : (
        <Absent />
      )}
      {/* Sources */}
      {Array.isArray(arg.source_entry_refs) && arg.source_entry_refs.length > 0 && (
        <div>
          <span className="text-[10px] text-gray-600 uppercase tracking-wide">Sources</span>
          <SourceRefs refs={arg.source_entry_refs} />
        </div>
      )}
      {/* Recherche divergente */}
      {Array.isArray(arg.recherche_divergente) && arg.recherche_divergente.length > 0 && (
        <div className="border-t border-gray-800 pt-2 space-y-1">
          <span className="text-[10px] text-gray-600 uppercase tracking-wide">Recherche divergente (falsification)</span>
          {arg.recherche_divergente.map((d, i) => (
            <div key={i} className="text-xs text-gray-500 flex gap-2">
              <span className="text-gray-600 shrink-0">›</span>
              <span>
                {d.query}
                {d.finding_entry_id != null && (
                  <span className="ml-1 font-mono text-[10px] px-1 py-0.5 rounded bg-gray-800 text-gray-400">
                    entry #{d.finding_entry_id}
                  </span>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ValuationCard({ val }) {
  if (!val) return <div className="text-sm text-gray-500 italic">— valorisation absente</div>
  const sc = val.scenarios || {}
  const rdcf = val.reverse_dcf || {}
  const assump = val.assumptions || {}

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/30 p-4 space-y-4">
      <p className="text-xs text-gray-500 leading-relaxed">{val.methode ?? <Absent />}</p>
      <Dl cols={3}>
        <KeyValue label="Horizon (ans)" value={val.horizon_ans ?? <Absent />} />
        <KeyValue label="Scén. base" value={sc.base != null ? `${sc.base} $` : <Absent />} />
        <KeyValue label="Scén. bear" value={sc.bear != null ? `${sc.bear} $` : <Absent />} />
        <KeyValue label="Scén. bull" value={sc.bull != null ? `${sc.bull} $` : <Absent />} />
        <KeyValue label="Multiple sortie" value={assump.multiple_sortie != null ? `${assump.multiple_sortie}×` : <Absent />} />
        <KeyValue label="Croissance rev." value={assump.croissance_revenue != null ? `${assump.croissance_revenue}` : <Absent />} />
        <KeyValue label="Expansion marge FCF" value={assump.expansion_marge_fcf != null ? `${assump.expansion_marge_fcf}` : <Absent />} />
      </Dl>
      {/* Reverse DCF — règle 5 : toujours présent */}
      <div className="border-t border-gray-800 pt-3 space-y-1">
        <div className="text-[10px] text-gray-600 uppercase tracking-wide mb-1">Reverse-DCF (que price le marché ?)</div>
        <KeyValue
          label="Croissance implicite prix actuel"
          value={rdcf.croissance_implicite_prix_actuel_pct != null
            ? `${rdcf.croissance_implicite_prix_actuel_pct} %/an`
            : <Absent />}
        />
        {rdcf.verdict != null && (
          <p className="text-xs text-gray-400 leading-relaxed mt-1">{rdcf.verdict}</p>
        )}
      </div>
    </div>
  )
}

function BullBearResultBlock({ rj, type }) {
  if (!rj) return <ErrorState detail="result_json absent ou vide." />

  const args = Array.isArray(rj.arguments) ? rj.arguments : []
  const catalyseurs = Array.isArray(rj.catalyseurs) ? rj.catalyseurs : []
  const indic = rj.indicateurs || {}
  const grounding = rj.grounding_report || {}
  const vp = rj.variant_perception || {}

  return (
    <div className="space-y-6">
      {/* Indicateurs */}
      <Card>
        <CardHeader title="Indicateurs" subtitle="Trois axes séparés — jamais fusionnés (règle A3)" />
        <CardBody>
          <Dl cols={3}>
            <KeyValue
              label="Conviction"
              value={indic.conviction != null ? fmtPct(indic.conviction) : <Absent />}
            />
            <KeyValue
              label="Qualité info"
              value={indic.qualite_info != null ? fmtPct(indic.qualite_info) : <Absent />}
            />
            <KeyValue
              label="Marge de sécurité"
              value={indic.marge_securite != null
                ? <span className={Number(indic.marge_securite) < 0 ? 'text-red-400' : 'text-emerald-400'}>
                    {fmtPct(indic.marge_securite)}
                  </span>
                : <Absent />}
            />
          </Dl>
          <div className="mt-3 pt-3 border-t border-gray-800">
            <KeyValue
              label={type === 'bull' ? 'Conviction globale (1-10)' : 'Conviction négative (1-10)'}
              value={type === 'bear'
                ? (rj.conviction_negative != null ? rj.conviction_negative : <Absent />)
                : (rj.conviction != null ? rj.conviction : <Absent />)}
            />
          </div>
        </CardBody>
      </Card>

      {/* Perception variante — règle 6 */}
      <Card>
        <CardHeader
          title="Perception variante"
          subtitle="Edge explicite — sans edge, pas de thèse (règle 6)"
        />
        <CardBody className="space-y-3">
          <Dl cols={2}>
            <KeyValue label="Type" value={vp.type ?? <Absent />} />
            <KeyValue label="Horizon (mois)" value={vp.horizon_mois ?? <Absent />} />
          </Dl>
          <div>
            <div className="text-xs text-gray-500 mb-1">Énoncé</div>
            <p className="text-sm text-gray-300 leading-relaxed">
              {vp.enonce != null && vp.enonce !== '' ? vp.enonce : <Absent />}
            </p>
          </div>
          {vp.catalyseur_re_rating != null && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Catalyseur de re-rating</div>
              <p className="text-sm text-gray-400">{vp.catalyseur_re_rating}</p>
            </div>
          )}
          <SourceRefs refs={vp.source_entry_refs} />
        </CardBody>
      </Card>

      {/* Arguments */}
      <Section title={`Arguments (${args.length})`}>
        {args.length === 0
          ? <EmptyState title="Aucun argument" />
          : args.map((a, i) => <ArgumentCard key={i} arg={a} index={i} />)}
      </Section>

      {/* Valorisation */}
      <Section title="Valorisation">
        <ValuationCard val={rj.valorisation} />
      </Section>

      {/* Grounding report (dans result_json) */}
      {grounding && Object.keys(grounding).length > 0 && (
        <Card>
          <CardHeader title="Grounding report (dans result_json)" />
          <CardBody>
            <Dl cols={3}>
              <KeyValue label="Affirmations total" value={grounding.affirmations_total ?? <Absent />} />
              <KeyValue label="Étayées" value={grounding.etayees ?? <Absent />} />
              <KeyValue label="Non étayées" value={grounding.non_etayees ?? <Absent />} />
            </Dl>
          </CardBody>
        </Card>
      )}

      {/* Catalyseurs */}
      {catalyseurs.length > 0 && (
        <Card>
          <CardHeader title="Catalyseurs" />
          <CardBody>
            <ul className="space-y-2">
              {catalyseurs.map((c, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-300">
                  <span className={`shrink-0 mt-0.5 ${type === 'bear' ? 'text-red-600' : 'text-emerald-600'}`}>›</span>
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      {/* Bear-only : failles bull conventionnel */}
      {type === 'bear' && (() => {
        const failles = Array.isArray(rj.failles_bull_conventionnel) ? rj.failles_bull_conventionnel : []
        return failles.length > 0 ? (
          <Card>
            <CardHeader
              title="Failles du bull conventionnel"
              subtitle="Angles morts du cas haussier de consensus (produits sans voir le bull spécifique)"
            />
            <CardBody>
              <ul className="space-y-2">
                {failles.map((f, i) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-300">
                    <span className="text-red-600 shrink-0 mt-0.5">›</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
        ) : null
      })()}

      {/* Bear-only : scénario destruction de valeur */}
      {type === 'bear' && (() => {
        const sdv = rj.scenario_destruction_valeur
        if (!sdv) return (
          <Card>
            <CardHeader title="Scénario de destruction de valeur" />
            <CardBody><Absent /></CardBody>
          </Card>
        )
        const declencheurs = Array.isArray(sdv.declencheurs) ? sdv.declencheurs : []
        return (
          <Card>
            <CardHeader title="Scénario de destruction de valeur" />
            <CardBody className="space-y-3">
              <Dl cols={2}>
                <KeyValue
                  label="Prix bear (objectif à la baisse)"
                  value={sdv.prix_bear != null ? `${sdv.prix_bear} $` : <Absent />}
                />
                <KeyValue
                  label="Perte potentielle"
                  value={sdv.perte_pct != null
                    ? <span className="text-red-400 font-semibold">-{sdv.perte_pct} %</span>
                    : <Absent />}
                />
              </Dl>
              {declencheurs.length > 0 && (
                <div>
                  <div className="text-xs text-gray-500 mb-1">Déclencheurs</div>
                  <ul className="space-y-1">
                    {declencheurs.map((d, i) => (
                      <li key={i} className="flex gap-2 text-sm text-gray-300">
                        <span className="text-red-600 shrink-0 mt-0.5">›</span>
                        <span>{d}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardBody>
          </Card>
        )
      })()}

      {/* Bear-only : réfutation du bull */}
      {type === 'bear' && (() => {
        const refutation = Array.isArray(rj.refutation_du_bull) ? rj.refutation_du_bull : []
        return (
          <Card>
            <CardHeader
              title={`Réfutation du bull (${refutation.length} argument${refutation.length !== 1 ? 's' : ''})`}
              subtitle="Rempli uniquement en mode réfutation — vide si cette analyse a été produite en isolation."
            />
            <CardBody>
              {refutation.length === 0 ? (
                <p className="text-sm text-gray-500 italic">
                  Vide — cette analyse a été produite isolément (mode production).
                  La réfutation argument-par-argument du bull est réservée au mode réfutation.
                </p>
              ) : (
                <div className="space-y-4">
                  {refutation.map((r, i) => (
                    <div key={i} className="rounded-lg border border-red-900/40 bg-red-950/10 p-4 space-y-2">
                      <div className="text-xs text-gray-500 font-medium">
                        Cible : <span className="text-gray-300">{r.cible ?? <Absent />}</span>
                      </div>
                      <p className="text-sm text-gray-300 leading-relaxed">
                        {r.contre_argument ?? <Absent />}
                      </p>
                      <SourceRefs refs={r.source_entry_refs} />
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        )
      })()}
    </div>
  )
}

// ── Blocs métier : SYNTHESIS ───────────────────────────────────────────────────

function PositionSizingBlock({ ps }) {
  if (!ps) return <div className="text-sm text-gray-500 italic">— position_sizing absent</div>
  const inputs = ps.inputs || {}
  const cap = ps.cap_applique || {}
  const risquesCorrElEs = Array.isArray(ps.risques_correles_portefeuille) ? ps.risques_correles_portefeuille : []

  // Signaler si le CAP a mordu (pct_formule !== pct_recommande)
  const capAMordu = cap.actif && ps.pct_formule != null && ps.pct_recommande != null
    && Number(ps.pct_formule) !== Number(ps.pct_recommande)

  return (
    <div className="space-y-4">
      {/* Alerte CAP */}
      {capAMordu && (
        <div className="rounded-md border border-amber-700 bg-amber-950/20 px-3 py-2">
          <p className="text-xs text-amber-400 font-semibold">
            Le garde-fou de concentration a mordu.
          </p>
          <p className="text-xs text-amber-300 mt-0.5">
            Formule Kelly : <strong>{ps.pct_formule} %</strong> → recommandé : <strong>{ps.pct_recommande} %</strong>
            {cap.contrainte && ` (contrainte : ${cap.contrainte})`}
          </p>
          <p className="text-xs text-amber-400/80 mt-0.5">
            Ce n'est pas un détail — la formule a voulu allouer plus que le plafond. L'écart est justifié ci-dessous.
          </p>
        </div>
      )}

      <Dl cols={3}>
        <KeyValue
          label="% formulé (Kelly brut)"
          value={ps.pct_formule != null ? `${ps.pct_formule} %` : <Absent />}
        />
        <KeyValue
          label="% recommandé"
          value={ps.pct_recommande != null
            ? <span className={`font-semibold ${capAMordu ? 'text-amber-400' : 'text-gray-100'}`}>
                {ps.pct_recommande} %
              </span>
            : <Absent />}
        />
        <KeyValue
          label="% max (plafond sectoriel)"
          value={ps.pct_max != null ? `${ps.pct_max} %` : <Absent />}
        />
        <KeyValue label="Méthode" value={ps.methode ?? <Absent />} />
        <KeyValue label="Cap appliqué" value={
          cap.actif != null
            ? <span className={cap.actif ? 'text-amber-400' : 'text-gray-400'}>
                {cap.actif ? `Oui — ${cap.contrainte || '?'} (${cap.valeur_pct ?? '?'} %)` : 'Non'}
              </span>
            : <NonRenseigne />
        } />
        <KeyValue
          label="Override utilisateur"
          value={ps.override_utilisateur != null
            ? JSON.stringify(ps.override_utilisateur)
            : <NonRenseigne />}
        />
      </Dl>

      {/* Justification d'ajustement */}
      {ps.ajustement_justification != null && (
        <div>
          <div className="text-xs text-gray-500 mb-1">Justification de l'ajustement</div>
          <p className="text-sm text-gray-300 leading-relaxed border-l-2 border-amber-700 pl-3">
            {ps.ajustement_justification}
          </p>
        </div>
      )}

      {/* Inputs */}
      <div>
        <div className="text-xs text-gray-500 mb-1">Inputs du sizing</div>
        <Dl cols={3}>
          <KeyValue label="Conviction" value={inputs.conviction != null ? fmtPct(inputs.conviction) : <Absent />} />
          <KeyValue label="Marge sécurité" value={inputs.marge_securite != null ? fmtPct(inputs.marge_securite) : <Absent />} />
          <KeyValue label="Corrél. portefeuille" value={inputs.correlation_portefeuille != null ? fmtPct(inputs.correlation_portefeuille) : <Absent />} />
        </Dl>
      </div>

      {/* Coût d'opportunité */}
      {ps.cout_opportunite != null && (
        <div>
          <div className="text-xs text-gray-500 mb-1">Coût d'opportunité</div>
          <p className="text-sm text-gray-400 italic">{ps.cout_opportunite}</p>
        </div>
      )}

      {/* Risques corrélés */}
      {risquesCorrElEs.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 mb-1">Risques corrélés au portefeuille</div>
          <div className="space-y-1">
            {risquesCorrElEs.map((r, i) => (
              <div key={i} className="flex justify-between text-xs text-gray-400 bg-gray-900/30 border border-gray-800 rounded px-2 py-1">
                <span>{r.facteur ?? <Absent />}</span>
                <span className="text-gray-500">{r.exposition_pct != null ? `${r.exposition_pct} %` : '—'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function RisqueAccepte({ r, index }) {
  const impactVariant = { fort: 'red', moyen: 'amber', faible: 'gray' }
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/30 p-4 space-y-3">
      <div className="flex items-start gap-3 flex-wrap">
        <Badge variant={impactVariant[r.impact] || 'gray'}>Impact {r.impact ?? '—'}</Badge>
        {r.probabilite != null && (
          <span className="text-xs text-gray-500">
            P = <span className="text-gray-300">{(r.probabilite * 100).toFixed(0)} %</span>
          </span>
        )}
        {r.reversible != null && (
          <span className={`text-xs ${r.reversible ? 'text-emerald-400' : 'text-red-400'}`}>
            {r.reversible ? 'réversible' : 'irréversible'}
          </span>
        )}
        {r.hypothese_liee != null && (
          <span className="text-xs text-sky-400 font-mono">→ {r.hypothese_liee}</span>
        )}
      </div>
      <p className="text-sm text-gray-200 font-medium">
        {r.risque != null && r.risque !== '' ? r.risque : <Absent />}
      </p>
      {r.base_rate && (
        <p className="text-xs text-gray-500 italic border-l-2 border-gray-700 pl-2">
          Classe de référence : {r.base_rate.reference_class ?? <Absent />}
          {r.base_rate.taux != null && ` · taux ${(r.base_rate.taux * 100).toFixed(0)} %`}
        </p>
      )}
      {r.reponse_si_materialise != null && (
        <div>
          <div className="text-xs text-gray-600 mb-0.5">Réponse si matérialisé</div>
          <p className="text-xs text-gray-400">{r.reponse_si_materialise}</p>
        </div>
      )}
      <SourceRefs refs={r.source_entry_refs} />
    </div>
  )
}

function HypothesisCard({ h, index }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/30 p-4 space-y-3">
      <div className="flex items-start gap-3">
        <span className="text-xs text-gray-600 font-mono w-6 shrink-0 pt-0.5">{h.id ?? `H${index + 1}`}</span>
        <p className="text-sm text-gray-200 font-medium flex-1 min-w-0">
          {h.enonce != null && h.enonce !== '' ? h.enonce : <Absent />}
        </p>
      </div>
      <Dl cols={3}>
        <KeyValue label="KPI" value={h.kpi != null && h.kpi !== '' ? h.kpi : <Absent />} />
        <KeyValue label="Unité" value={h.unite != null && h.unite !== '' ? h.unite : <Absent />} />
        <KeyValue label="Horizon" value={h.horizon ?? <Absent />} />
        <KeyValue label="Seuil d'alerte" value={h.seuil_alerte != null ? h.seuil_alerte : <Absent />} locked />
        <KeyValue label="Seuil d'invalidation" value={h.seuil_invalidation != null ? h.seuil_invalidation : <Absent />} locked />
        <KeyValue label="Statut" value={h.statut ?? '—'} />
      </Dl>
      {h.base_rate && (
        <div className="text-xs text-gray-500 border border-gray-800 rounded-md px-3 py-2 space-y-0.5">
          <div className="text-[10px] text-gray-600 uppercase tracking-wide mb-1">Base rate</div>
          <div>Taux : {h.base_rate.taux != null ? `${(h.base_rate.taux * 100).toFixed(0)} %` : <Absent />}</div>
          <div>Classe : {h.base_rate.reference_class ?? <Absent />}</div>
          <div>Ajustement : {h.base_rate.ajustement != null ? h.base_rate.ajustement : <NonRenseigne />}</div>
        </div>
      )}
      <SourceRefs refs={h.source_entry_refs} />
    </div>
  )
}

function SynthesisResultBlock({ rj }) {
  if (!rj) return <ErrorState detail="result_json absent ou vide." />

  const hypotheses = Array.isArray(rj.hypotheses) ? rj.hypotheses : []
  const rm = rj.risk_matrix || {}
  const axes = rm.axes || {}
  const premortem = Array.isArray(rm.pre_mortem) ? rm.pre_mortem : []
  const risquesAcceptes = Array.isArray(rm.risques_acceptes) ? rm.risques_acceptes : []
  const condEntree = Array.isArray(rm.conditions_entree) ? rm.conditions_entree : []
  const srcSummary = rm.sources_summary || {}

  return (
    <div className="space-y-6">
      {/* Verdict + Rationale */}
      <Card>
        <CardHeader
          title="Verdict de la synthèse"
          subtitle="Seul verdict du flux entier (Q2) — ni bull ni bear ne portent de verdict."
        />
        <CardBody className="space-y-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div>
              <div className="text-xs text-gray-500 mb-1">Verdict</div>
              {rm.verdict ? (
                <Badge
                  variant={rm.verdict === 'PROCEED' ? 'PROCEED' : rm.verdict === 'PROCEED_AVEC_CONDITIONS' ? 'PROCEED_AVEC_CONDITIONS' : 'gray'}
                  className="text-sm px-3 py-1"
                >
                  {rm.verdict}
                </Badge>
              ) : (
                <Absent />
              )}
            </div>
          </div>
          {rm.rationale != null && (
            <p className="text-sm text-gray-300 leading-relaxed">{rm.rationale}</p>
          )}

          {/* Axes */}
          <div>
            <div className="text-xs text-gray-500 mb-2">4 axes séparés (jamais fusionnés — règle A3)</div>
            <Dl cols={4}>
              <KeyValue label="Qualité business" value={axes.qualite_business != null ? fmtPct(axes.qualite_business) : <Absent />} />
              <KeyValue label="Qualité info" value={axes.qualite_info != null ? fmtPct(axes.qualite_info) : <Absent />} />
              <KeyValue label="Conviction" value={axes.conviction != null ? fmtPct(axes.conviction) : <Absent />} />
              <KeyValue
                label="Marge sécurité"
                value={axes.marge_securite != null
                  ? <span className={Number(axes.marge_securite) < 0 ? 'text-red-400' : 'text-emerald-400'}>
                      {fmtPct(axes.marge_securite)}
                    </span>
                  : <Absent />}
              />
            </Dl>
          </div>

          {/* Sources summary */}
          {Object.keys(srcSummary).length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Résumé des sources</div>
              <Dl cols={4}>
                <KeyValue label="Tier A" value={srcSummary.tier_A ?? '—'} />
                <KeyValue label="Tier B" value={srcSummary.tier_B ?? '—'} />
                <KeyValue label="Tier C / mémoire" value={srcSummary.tier_C_llm_memory ?? '—'} />
                <KeyValue label="Total" value={srcSummary.total_entries ?? '—'} />
              </Dl>
            </div>
          )}

          {/* Needs second round */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Second round :</span>
            {rm.needs_second_round != null ? (
              <Badge variant={rm.needs_second_round ? 'amber' : 'gray'}>
                {rm.needs_second_round ? 'Oui' : 'Non'}
              </Badge>
            ) : <Absent />}
            {rm.second_round_trigger != null && (
              <span className="text-xs text-gray-400">{rm.second_round_trigger}</span>
            )}
          </div>
        </CardBody>
      </Card>

      {/* Conditions d'entrée */}
      {condEntree.length > 0 && (
        <Card>
          <CardHeader
            title="Conditions d'entrée"
            subtitle="Requises car verdict PROCEED_AVEC_CONDITIONS"
          />
          <CardBody>
            <ul className="space-y-2">
              {condEntree.map((c, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-300">
                  <span className="text-sky-600 shrink-0 mt-0.5">›</span>
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      {/* Position sizing */}
      <Card>
        <CardHeader
          title="Position sizing"
          subtitle="Kelly fractionnaire — pct_formule vs pct_recommande : tout écart doit être justifié."
        />
        <CardBody>
          <PositionSizingBlock ps={rm.position_sizing} />
        </CardBody>
      </Card>

      {/* Pré-mortem (Klein) */}
      {premortem.length > 0 && (
        <Card>
          <CardHeader
            title={`Pré-mortem (${premortem.length} scénarios)`}
            subtitle="Méthode Klein : dans 3 ans, la thèse a échoué — pourquoi ?"
          />
          <CardBody>
            <ul className="space-y-3">
              {premortem.map((p, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-300">
                  <span className="text-red-600 shrink-0 mt-0.5 font-bold">{i + 1}.</span>
                  <span className="leading-relaxed">{p}</span>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      {/* Risques acceptés */}
      <Section title={`Risques acceptés (${risquesAcceptes.length})`}>
        {risquesAcceptes.length === 0
          ? <EmptyState title="Aucun risque accepté" />
          : risquesAcceptes.map((r, i) => <RisqueAccepte key={i} r={r} index={i} />)}
      </Section>

      {/* Hypothèses de monitoring */}
      <Section title={`Hypothèses de monitoring (${hypotheses.length})`}>
        <p className="text-xs text-gray-600 bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2 -mt-1">
          Chaque risque accepté engendre une hypothèse falsifiable.
          Les seuils sont figés — une revue de monitoring ne peut pas les modifier.
        </p>
        {hypotheses.length === 0
          ? <EmptyState title="Aucune hypothèse" />
          : hypotheses.map((h, i) => <HypothesisCard key={h.id || i} h={h} index={i} />)}
      </Section>
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function AnalysisDetail() {
  const router = useRouter()
  const { analysis_id } = router.query

  const [analysis, setAnalysis] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!analysis_id) return
    setLoading(true)
    fetch(`${API}/analyses/${analysis_id}`)
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`)))
      .then(d => { setAnalysis(d); setLoading(false) })
      .catch(e => { setErr(String(e)); setLoading(false) })
  }, [analysis_id])

  if (loading) return (
    <div className="py-12 text-center text-sm text-gray-500">Chargement…</div>
  )
  if (err) return (
    <div>
      <Link href="/v2" className="text-xs text-gray-500 hover:text-gray-300 mb-4 inline-block">
        ← Retour V2
      </Link>
      <ErrorState detail={err} />
    </div>
  )
  if (!analysis) return null

  const type = analysis.analysis_type
  const rj = analysis.result_json
  const rjOrig = analysis.result_json_original
  const knowledgeRefs = Array.isArray(analysis.knowledge_refs) ? analysis.knowledge_refs : []

  const typeLabel = TYPE_LABELS[type] || type
  const typeVariant = TYPE_VARIANTS[type] || 'gray'

  const superseded = analysis.status === 'superseded'

  return (
    <div className="space-y-6">
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Link href="/v2" className="hover:text-gray-300">V2</Link>
        <span>›</span>
        {analysis.ticker_id && (
          <>
            <Link href={`/v2/tickers/${analysis.ticker_id}/analyses`} className="hover:text-gray-300">
              {analysis.ticker_id}
            </Link>
            <span>›</span>
          </>
        )}
        <span className="text-gray-300">Analyse #{analysis_id}</span>
      </div>

      {/* Titre */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-white">
          {typeLabel} #{analysis_id} — {analysis.ticker_id ?? '—'}
        </h1>
        <Badge variant={typeVariant}>{typeLabel}</Badge>
        <Badge variant={STATUS_VARIANT[analysis.status] || 'gray'}>
          {analysis.status || '—'}
        </Badge>
        {analysis.round != null && (
          <Badge variant="gray">Tour {analysis.round}</Badge>
        )}
      </div>

      {/* Alerte superseded */}
      {superseded && (
        <div className="rounded-xl border border-amber-700 bg-amber-950/20 px-4 py-3">
          <p className="text-sm text-amber-400 font-semibold">Cette analyse est remplacée (superseded).</p>
          <p className="text-xs text-amber-300 mt-1">
            Un tour de réfutation a produit une nouvelle version.
            Cette opinion est périmée et ne représente pas la position courante.
            {analysis.supersedes_id == null
              ? null
              : <> Elle a elle-même remplacé l'analyse{' '}
                  <Link href={`/v2/analyses/${analysis.supersedes_id}`} className="underline">
                    #{analysis.supersedes_id}
                  </Link>.
                </>}
          </p>
        </div>
      )}

      {/* ── Télémétrie + Lignée ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TelemetryBlock analysis={analysis} />
        <LineageBlock analysis={analysis} />
      </div>

      {/* ── Corps métier ─────────────────────────────────────────────────────── */}
      {type === 'synthesis' && <SynthesisResultBlock rj={rj} />}
      {(type === 'bull' || type === 'bear') && <BullBearResultBlock rj={rj} type={type} />}
      {type !== 'synthesis' && type !== 'bull' && type !== 'bear' && (
        <Card>
          <CardHeader title={`result_json (type inconnu : ${type})`} />
          <CardBody>
            <pre className="text-xs text-gray-400 whitespace-pre-wrap break-words font-mono max-h-64 overflow-y-auto">
              {JSON.stringify(rj, null, 2)}
            </pre>
          </CardBody>
        </Card>
      )}

      {/* ── Diff result_json vs result_json_original ─────────────────────────── */}
      <DiffBlock rj={rj} rjOrig={rjOrig} />

      {/* ── knowledge_refs ───────────────────────────────────────────────────── */}
      <KnowledgeRefsBlock refs={knowledgeRefs} />

      {/* ── prompt_snapshot ──────────────────────────────────────────────────── */}
      <PromptBlock prompt={analysis.prompt_snapshot} />
    </div>
  )
}
