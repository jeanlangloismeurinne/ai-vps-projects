import { useState, useEffect, useRef } from 'react'
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
  if (val == null) return '—'
  return `${Number(val).toFixed(4)} $`
}

function fmtPct(val) {
  if (val == null) return '—'
  return `${Number(val).toFixed(1)} %`
}

function fmtNum(val, decimals = 2) {
  if (val == null) return '—'
  return Number(val).toFixed(decimals)
}

// Marqueur visible pour un champ absent (ni null ni undefined — vraiment manquant)
function Absent() {
  return <span className="text-amber-600 italic text-xs">— champ absent</span>
}

// ── Provenance : source_entry_refs ────────────────────────────────────────────
// Le cœur du projet : chaque référence est visible et cliquable vers la KB.
function SourceRefs({ refs, tickerId, label = 'Sources' }) {
  if (!Array.isArray(refs)) {
    return (
      <div className="flex items-center gap-1.5 mt-1">
        <span className="text-[10px] text-gray-600 uppercase tracking-wide">{label} :</span>
        <span className="text-[10px] text-amber-600 italic">non sourcé</span>
      </div>
    )
  }
  if (refs.length === 0) {
    return (
      <div className="flex items-center gap-1.5 mt-1">
        <span className="text-[10px] text-gray-600 uppercase tracking-wide">{label} :</span>
        <span className="text-[10px] text-amber-600 italic">non sourcé</span>
      </div>
    )
  }
  return (
    <div className="flex flex-wrap items-center gap-1 mt-1.5">
      <span className="text-[10px] text-gray-600 uppercase tracking-wide mr-1">{label} :</span>
      {refs.map((ref, i) => {
        const entryId = ref.entry_id != null ? ref.entry_id : '?'
        const version = ref.version != null ? ref.version : '?'
        const href = tickerId ? `/v2/tickers/${tickerId}/knowledge?entry=${entryId}` : '#'
        return (
          <Link
            key={i}
            href={href}
            className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/60 hover:border-emerald-500 transition-colors"
            title={`Entrée #${entryId} version ${version}`}
          >
            #{entryId}<span className="text-emerald-700"> v{version}</span>
          </Link>
        )
      })}
    </div>
  )
}

// ── Diff memo_json vs memo_json_original ──────────────────────────────────────
// Calcule les chemins qui diffèrent entre les deux objets.
// S'ils sont identiques → on le dit explicitement (pas un vide ambigu).
function diffObjects(a, b, path = '') {
  const diffs = []
  if (typeof a !== typeof b) {
    diffs.push({ path, from: b, to: a })
    return diffs
  }
  if (a === null || b === null) {
    if (a !== b) diffs.push({ path, from: b, to: a })
    return diffs
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) {
      diffs.push({ path, from: `[liste len=${b.length}]`, to: `[liste len=${a.length}]` })
    } else {
      a.forEach((item, i) => {
        diffs.push(...diffObjects(item, b[i], `${path}[${i}]`))
      })
    }
    return diffs
  }
  if (typeof a === 'object' && !Array.isArray(a)) {
    const allKeys = new Set([...Object.keys(a), ...Object.keys(b)])
    allKeys.forEach(k => {
      const p = path ? `${path}.${k}` : k
      if (!(k in a)) {
        diffs.push({ path: p, from: b[k], to: '<<manquant>>' })
      } else if (!(k in b)) {
        diffs.push({ path: p, from: '<<manquant>>', to: a[k] })
      } else {
        diffs.push(...diffObjects(a[k], b[k], p))
      }
    })
    return diffs
  }
  if (a !== b) diffs.push({ path, from: b, to: a })
  return diffs
}

function DiffBlock({ memoJson, memoJsonOriginal }) {
  const [open, setOpen] = useState(false)
  const diffs = diffObjects(memoJson, memoJsonOriginal)
  const identical = diffs.length === 0

  return (
    <Card>
      <CardHeader
        title="Corrections déterministes"
        subtitle="Écart entre memo_json (corrigé) et memo_json_original (sortie brute du modèle)"
        action={
          <button
            onClick={() => setOpen(v => !v)}
            className="text-xs text-gray-400 hover:text-gray-200 px-2 py-1 rounded border border-gray-700 hover:border-gray-500 transition-colors"
          >
            {open ? 'Replier' : 'Voir'}
          </button>
        }
      />
      <CardBody>
        {identical ? (
          <p className="text-sm text-gray-400">
            <span className="text-emerald-400 font-medium">Aucune correction déterministe appliquée</span>
            {' '}— memo_json et memo_json_original sont strictement identiques.
          </p>
        ) : (
          <>
            <p className="text-sm text-amber-400 font-medium mb-3">
              {diffs.length} champ{diffs.length !== 1 ? 's' : ''} modifié{diffs.length !== 1 ? 's' : ''} par les corrections déterministes
            </p>
            {open && (
              <div className="space-y-2 mt-2">
                {diffs.map((d, i) => (
                  <div key={i} className="rounded-lg border border-gray-800 bg-gray-900/30 px-3 py-2 text-xs space-y-1">
                    <div className="font-mono text-gray-400">{d.path}</div>
                    <div className="flex gap-4">
                      <div>
                        <span className="text-gray-600">Original : </span>
                        <span className="text-red-400">{JSON.stringify(d.from)}</span>
                      </div>
                      <div>
                        <span className="text-gray-600">Corrigé : </span>
                        <span className="text-emerald-400">{JSON.stringify(d.to)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </CardBody>
    </Card>
  )
}

// ── Télémétrie ────────────────────────────────────────────────────────────────
function Telemetry({ memo }) {
  return (
    <Card>
      <CardHeader title="Télémétrie" subtitle="Méta-données de l'appel modèle" />
      <CardBody>
        <Dl cols={3}>
          <KeyValue label="Fournisseur" value={memo.provider_used != null ? memo.provider_used : <Absent />} />
          <KeyValue label="Modèle" value={memo.model_used != null ? memo.model_used : <Absent />} />
          <KeyValue label="Statut" value={memo.status != null ? <Badge variant={memo.status === 'validated' ? 'active' : 'draft'}>{memo.status}</Badge> : <Absent />} />
          <KeyValue label="Tokens en entrée" value={memo.tokens_in != null ? memo.tokens_in.toLocaleString('fr-FR') : '—'} />
          <KeyValue label="Tokens en sortie" value={memo.tokens_out != null ? memo.tokens_out.toLocaleString('fr-FR') : '—'} />
          <KeyValue label="Coût" value={fmtCost(memo.cost_usd)} />
          <KeyValue label="Créé le" value={fmtDatetime(memo.created_at)} />
          <KeyValue label="Mis à jour" value={fmtDatetime(memo.updated_at)} />
          <KeyValue label="Schema" value={memo.schema_version != null ? memo.schema_version : <Absent />} />
          <KeyValue label="context_pack_entry_id" value={memo.context_pack_entry_id != null ? `#${memo.context_pack_entry_id}` : '—'} />
          <KeyValue label="readiness_report_id" value={memo.readiness_report_id != null ? `#${memo.readiness_report_id}` : '—'} />
        </Dl>
        {/* grounding_report : null volontaire → pas de vide muet */}
        <div className="mt-4 pt-4 border-t border-gray-800">
          <div className="text-xs text-gray-500 mb-1">Grounding report</div>
          {memo.grounding_report === undefined
            ? <Absent />
            : memo.grounding_report === null
              ? <span className="text-sm text-gray-600 italic">non renseigné (null)</span>
              : <pre className="text-xs text-gray-300 whitespace-pre-wrap break-words">{JSON.stringify(memo.grounding_report, null, 2)}</pre>
          }
        </div>
      </CardBody>
    </Card>
  )
}

// ── Prompt snapshot ───────────────────────────────────────────────────────────
function PromptSnapshot({ prompt }) {
  const [open, setOpen] = useState(false)
  const textRef = useRef(null)

  if (prompt === undefined) return (
    <Card>
      <CardHeader title="Prompt snapshot" />
      <CardBody><Absent /></CardBody>
    </Card>
  )
  if (prompt === null) return (
    <Card>
      <CardHeader title="Prompt snapshot" />
      <CardBody><span className="text-sm text-gray-600 italic">non renseigné (null)</span></CardBody>
    </Card>
  )

  const preview = prompt.length > 300 ? prompt.slice(0, 300) + '…' : prompt

  return (
    <Card>
      <CardHeader
        title="Prompt snapshot"
        subtitle={`${prompt.length.toLocaleString('fr-FR')} caractères — jamais tronqué silencieusement`}
        action={
          <button
            onClick={() => setOpen(v => !v)}
            className="text-xs text-gray-400 hover:text-gray-200 px-2 py-1 rounded border border-gray-700 hover:border-gray-500 transition-colors"
          >
            {open ? 'Replier' : 'Voir tout'}
          </button>
        }
      />
      <CardBody>
        <pre
          ref={textRef}
          className="text-xs text-gray-400 whitespace-pre-wrap break-words font-mono leading-relaxed max-h-[600px] overflow-y-auto"
        >
          {open ? prompt : preview}
        </pre>
      </CardBody>
    </Card>
  )
}

// ── Posture ───────────────────────────────────────────────────────────────────
const POSTURE_VARIANT = { NEUTRE: 'gray', BULLISH: 'emerald', BEARISH: 'red' }

// ── Moat ──────────────────────────────────────────────────────────────────────
function MoatSection({ moat, tickerId }) {
  if (!moat) return (
    <Card>
      <CardHeader title="Fossé concurrentiel (Moat)" />
      <CardBody><Absent /></CardBody>
    </Card>
  )

  const types = Array.isArray(moat.type) ? moat.type : []
  const preuves = Array.isArray(moat.preuves) ? moat.preuves : []
  const dur = moat.durabilite_ans

  return (
    <Card>
      <CardHeader title="Fossé concurrentiel (Moat)" />
      <CardBody className="space-y-5">
        {/* Résumé */}
        <Dl cols={3}>
          <div>
            <div className="text-xs text-gray-500 mb-1">Types</div>
            <div className="flex flex-wrap gap-1">
              {types.length > 0
                ? types.map((t, i) => <Badge key={i} variant="sky">{t}</Badge>)
                : <Absent />}
            </div>
          </div>
          <KeyValue
            label="Score (1-5)"
            value={moat.score != null ? `${moat.score} / 5` : <Absent />}
          />
          <KeyValue
            label="Tendance"
            value={moat.trend != null ? moat.trend : <Absent />}
          />
        </Dl>

        {/* Durabilité */}
        {dur ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900/30 px-3 py-3 space-y-2">
            <div className="text-xs text-gray-600 uppercase tracking-wide">Durabilité estimée</div>
            <Dl cols={3}>
              <KeyValue
                label="Forte (ans)"
                value={dur.forte != null ? dur.forte : <Absent />}
              />
              <KeyValue
                label="Incertaine (ans)"
                value={dur.incertaine != null ? dur.incertaine : <Absent />}
              />
            </Dl>
            {/* Base rate */}
            {dur.base_rate ? (
              <div className="text-xs text-gray-500 space-y-0.5 pt-1 border-t border-gray-800">
                <div className="text-[10px] text-gray-600 uppercase tracking-wide mb-1">Base rate</div>
                <div>Taux : <span className="text-gray-300">{dur.base_rate.taux != null ? dur.base_rate.taux : <Absent />}</span></div>
                <div>Classe de référence : <span className="text-gray-300">{dur.base_rate.reference_class != null ? dur.base_rate.reference_class : <Absent />}</span></div>
                <div>Ajustement : {dur.base_rate.ajustement !== null && dur.base_rate.ajustement !== undefined
                  ? <span className="text-gray-300">{dur.base_rate.ajustement}</span>
                  : <span className="text-gray-600 italic">aucun (null)</span>}
                </div>
              </div>
            ) : (
              <div className="text-xs text-amber-600 italic pt-1">base_rate absent</div>
            )}
          </div>
        ) : (
          <div className="text-xs text-amber-600 italic">durabilite_ans absent</div>
        )}

        {/* Preuves */}
        <div>
          <div className="text-xs text-gray-600 uppercase tracking-wide mb-2">
            Preuves ({preuves.length})
            {preuves.length === 0 && <span className="text-amber-600 italic ml-2">— aucune preuve : le moat n'est pas étayé</span>}
          </div>
          <div className="space-y-2">
            {preuves.map((p, i) => (
              <div key={i} className="rounded-lg border border-gray-800 bg-gray-900/20 px-3 py-2">
                <p className="text-sm text-gray-300">
                  {p.fait != null ? p.fait : <Absent />}
                </p>
                <SourceRefs refs={p.source_entry_refs} tickerId={tickerId} />
              </div>
            ))}
          </div>
        </div>
      </CardBody>
    </Card>
  )
}

// ── Industrie ─────────────────────────────────────────────────────────────────
function IndustrySection({ industry, tickerId }) {
  if (!industry) return (
    <Card>
      <CardHeader title="Industrie" />
      <CardBody><Absent /></CardBody>
    </Card>
  )

  const vectors = Array.isArray(industry.disruption_vectors) ? industry.disruption_vectors : []
  const prosp = industry.croissance_marche_prospective

  return (
    <Card>
      <CardHeader title="Industrie" />
      <CardBody className="space-y-5">
        <Dl cols={2}>
          <KeyValue label="Cyclicité" value={industry.cyclicite != null ? industry.cyclicite : <Absent />} />
          <KeyValue label="Position vs pairs" value={industry.position_vs_pairs != null ? industry.position_vs_pairs : <Absent />} />
          <KeyValue
            label="Croissance marché historique"
            value={industry.croissance_marche_historique_pct != null ? fmtPct(industry.croissance_marche_historique_pct) : <Absent />}
          />
          {prosp ? (
            <div className="flex flex-col gap-0.5">
              <dt className="text-xs text-gray-500">Croissance marché prospective</dt>
              <dd className="text-sm text-gray-200">
                {prosp.taux_pct != null ? fmtPct(prosp.taux_pct) : <Absent />}
                {prosp.base_rate && (
                  <span className="text-xs text-gray-500 ml-2">
                    (base rate : {prosp.base_rate.taux_pct != null ? prosp.base_rate.taux_pct : '—'} — {prosp.base_rate.reference_class || '—'})
                  </span>
                )}
              </dd>
            </div>
          ) : (
            <KeyValue label="Croissance marché prospective" value={<Absent />} />
          )}
        </Dl>

        {/* Structure 5 forces */}
        <div>
          <div className="text-xs text-gray-500 mb-1">Structure 5 forces</div>
          <p className="text-sm text-gray-300">
            {industry.structure_5forces != null ? industry.structure_5forces : <Absent />}
          </p>
        </div>

        {/* Vecteurs de disruption */}
        {vectors.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 mb-1">Vecteurs de disruption</div>
            <ul className="space-y-1">
              {vectors.map((v, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-300">
                  <span className="text-amber-600 shrink-0">›</span>
                  <span>{v}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <SourceRefs refs={industry.source_entry_refs} tickerId={tickerId} />
      </CardBody>
    </Card>
  )
}

// ── Financials ────────────────────────────────────────────────────────────────
function FinancialsSection({ financials, tickerId }) {
  if (!financials) return (
    <Card>
      <CardHeader title="Financiers" />
      <CardBody><Absent /></CardBody>
    </Card>
  )

  const eq = financials.earnings_quality
  const lev = financials.levier

  return (
    <Card>
      <CardHeader title="Financiers" />
      <CardBody className="space-y-5">
        <Dl cols={3}>
          <KeyValue label="ROIC" value={financials.roic_pct != null ? fmtPct(financials.roic_pct) : <Absent />} />
          <KeyValue label="WACC estimé" value={financials.wacc_estime_pct != null ? fmtPct(financials.wacc_estime_pct) : <Absent />} />
          <KeyValue label="ROIC vs WACC" value={financials.roic_vs_wacc != null ? financials.roic_vs_wacc : <Absent />} />
          <KeyValue label="Tendance ROIC 5 ans" value={financials.roic_trend_5y != null ? financials.roic_trend_5y : <Absent />} />
          <KeyValue label="Conversion FCF" value={financials.fcf_conversion_pct != null ? fmtPct(financials.fcf_conversion_pct) : <Absent />} />
          <KeyValue label="Intensité capex" value={financials.intensite_capex_pct != null ? fmtPct(financials.intensite_capex_pct) : <Absent />} />
          {lev ? (
            <KeyValue
              label="Levier (Dette nette/EBITDA)"
              value={lev.dette_nette_ebitda != null ? fmtNum(lev.dette_nette_ebitda) : <Absent />}
            />
          ) : (
            <KeyValue label="Levier" value={<Absent />} />
          )}
        </Dl>

        {/* Qualité des earnings */}
        {eq ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900/30 px-3 py-3 space-y-2">
            <div className="text-xs text-gray-600 uppercase tracking-wide">Qualité des earnings</div>
            <Dl cols={2}>
              <KeyValue label="Score" value={eq.score != null ? eq.score : <Absent />} />
              <KeyValue
                label="Accruals flag"
                value={eq.accruals_flag !== undefined
                  ? <Badge variant={eq.accruals_flag ? 'amber' : 'emerald'}>{eq.accruals_flag ? 'Oui' : 'Non'}</Badge>
                  : <Absent />}
              />
            </Dl>
            {eq.note != null && (
              <p className="text-xs text-gray-400 pt-1 border-t border-gray-800">{eq.note}</p>
            )}
          </div>
        ) : (
          <div className="text-xs text-amber-600 italic">earnings_quality absent</div>
        )}

        <SourceRefs refs={financials.source_entry_refs} tickerId={tickerId} />
      </CardBody>
    </Card>
  )
}

// ── Management ────────────────────────────────────────────────────────────────
function ManagementSection({ management, tickerId }) {
  if (!management) return (
    <Card>
      <CardHeader title="Management" />
      <CardBody><Absent /></CardBody>
    </Card>
  )

  const scorecard = management.capital_allocation_scorecard

  return (
    <Card>
      <CardHeader title="Management" />
      <CardBody className="space-y-5">
        <Dl cols={2}>
          <KeyValue label="Score (1-5)" value={management.score != null ? `${management.score} / 5` : <Absent />} />
          <KeyValue
            label="Skin in the game"
            value={management.skin_in_game_pct != null ? fmtPct(management.skin_in_game_pct) : <Absent />}
          />
        </Dl>

        <div>
          <div className="text-xs text-gray-500 mb-1">Candeur</div>
          <p className="text-sm text-gray-300">
            {management.candeur != null ? management.candeur : <Absent />}
          </p>
        </div>

        <div>
          <div className="text-xs text-gray-500 mb-1">Incitations</div>
          <p className="text-sm text-gray-300">
            {management.incitations != null ? management.incitations : <Absent />}
          </p>
        </div>

        {/* Capital allocation scorecard */}
        {scorecard ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900/30 px-3 py-3 space-y-2">
            <div className="text-xs text-gray-600 uppercase tracking-wide mb-2">Capital allocation scorecard</div>
            <Dl cols={2}>
              <KeyValue label="M&A" value={scorecard.ma != null ? scorecard.ma : <Absent />} />
              <KeyValue label="Rachats" value={scorecard.buybacks != null ? scorecard.buybacks : <Absent />} />
              <KeyValue label="Dividendes" value={scorecard.dividendes != null ? scorecard.dividendes : <Absent />} />
              <KeyValue label="Réinvestissement" value={scorecard.reinvestissement != null ? scorecard.reinvestissement : <Absent />} />
            </Dl>
            {scorecard.note != null && (
              <p className="text-xs text-gray-400 pt-2 border-t border-gray-800">{scorecard.note}</p>
            )}
          </div>
        ) : (
          <div className="text-xs text-amber-600 italic">capital_allocation_scorecard absent</div>
        )}

        <SourceRefs refs={management.source_entry_refs} tickerId={tickerId} />
      </CardBody>
    </Card>
  )
}

// ── Business Model ────────────────────────────────────────────────────────────
function BusinessModelSection({ bm, tickerId }) {
  if (!bm) return (
    <Card>
      <CardHeader title="Modèle d'affaires" />
      <CardBody><Absent /></CardBody>
    </Card>
  )

  const drivers = Array.isArray(bm.drivers_revenus) ? bm.drivers_revenus : []

  return (
    <Card>
      <CardHeader title="Modèle d'affaires" />
      <CardBody className="space-y-5">
        <div>
          <div className="text-xs text-gray-500 mb-1">Description</div>
          <p className="text-sm text-gray-300 leading-relaxed">
            {bm.description != null ? bm.description : <Absent />}
          </p>
        </div>

        <Dl cols={2}>
          <KeyValue
            label="Récurrence des revenus"
            value={bm.recurrence_pct != null ? fmtPct(bm.recurrence_pct) : <Absent />}
          />
        </Dl>

        {bm.unit_economics != null && (
          <div>
            <div className="text-xs text-gray-500 mb-1">Économie unitaire</div>
            <p className="text-sm text-gray-300">{bm.unit_economics}</p>
          </div>
        )}

        {drivers.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 mb-2">Drivers de revenus</div>
            <ul className="space-y-1.5">
              {drivers.map((d, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-300">
                  <span className="text-emerald-600 shrink-0 mt-0.5">›</span>
                  <span>{d}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <SourceRefs refs={bm.source_entry_refs} tickerId={tickerId} />
      </CardBody>
    </Card>
  )
}

// ── Valorisation ──────────────────────────────────────────────────────────────
function ValuationSection({ valuation }) {
  if (!valuation) return (
    <Card>
      <CardHeader title="Valorisation" />
      <CardBody><Absent /></CardBody>
    </Card>
  )

  const dcf = valuation.dcf_scenarios
  const epv = valuation.epv
  const rdcf = valuation.reverse_dcf
  const rel = valuation.relatif
  const bra = valuation.base_rate_anchor
  const iv = Array.isArray(valuation.iv_range) ? valuation.iv_range : []

  return (
    <Card>
      <CardHeader title="Valorisation" />
      <CardBody className="space-y-6">
        {/* Prix actuel + IV range + marge de sécurité */}
        <div className="rounded-lg border border-emerald-900/40 bg-emerald-950/20 px-4 py-3">
          <Dl cols={3}>
            <KeyValue
              label="Prix actuel"
              value={valuation.prix_actuel != null ? `${valuation.prix_actuel} $` : <Absent />}
            />
            <KeyValue
              label="Fourchette IV (min – max)"
              value={iv.length === 2
                ? `${iv[0]} $ – ${iv[1]} $`
                : iv.length > 0 ? iv.join(' / ') : <Absent />}
            />
            <KeyValue
              label="Marge de sécurité (base)"
              value={valuation.marge_securite_base_pct != null
                ? <span className={valuation.marge_securite_base_pct < 0 ? 'text-red-400' : 'text-emerald-400'}>
                    {fmtPct(valuation.marge_securite_base_pct)}
                  </span>
                : <Absent />}
            />
          </Dl>
        </div>

        {/* Reverse DCF — la question centrale */}
        <div className="rounded-lg border border-sky-900/40 bg-sky-950/20 px-4 py-3 space-y-2">
          <div className="text-xs text-sky-400 uppercase tracking-wide font-medium">
            Reverse DCF — que price le marché ?
          </div>
          {rdcf ? (
            <>
              <div className="text-sm font-semibold text-gray-100">
                Croissance implicite :{' '}
                {rdcf.croissance_implicite_prix_actuel_pct != null
                  ? <span className="text-sky-300">{fmtPct(rdcf.croissance_implicite_prix_actuel_pct)}/an</span>
                  : <Absent />}
              </div>
              {rdcf.verdict != null && (
                <p className="text-sm text-gray-300">{rdcf.verdict}</p>
              )}
            </>
          ) : (
            <Absent />
          )}
        </div>

        {/* Scénarios DCF */}
        {dcf ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900/30 px-4 py-3 space-y-3">
            <div className="text-xs text-gray-600 uppercase tracking-wide">DCF scénarisé</div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-[10px] text-red-500 uppercase mb-1">Bear</div>
                <div className="text-lg font-semibold text-red-300">
                  {dcf.bear != null ? `${dcf.bear} $` : <Absent />}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-gray-400 uppercase mb-1">Base</div>
                <div className="text-lg font-bold text-gray-100">
                  {dcf.base != null ? `${dcf.base} $` : <Absent />}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-emerald-500 uppercase mb-1">Bull</div>
                <div className="text-lg font-semibold text-emerald-300">
                  {dcf.bull != null ? `${dcf.bull} $` : <Absent />}
                </div>
              </div>
            </div>
            {/* Drivers — les clés varient selon le ticker (cf. MSFT vs NVDA) */}
            {dcf.drivers && (
              <div className="pt-2 border-t border-gray-800">
                <div className="text-[10px] text-gray-600 uppercase tracking-wide mb-2">Hypothèses DCF</div>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
                  {Object.entries(dcf.drivers).map(([k, v]) => (
                    <span key={k}>
                      <span className="text-gray-600">{k} : </span>
                      <span className="text-gray-300">{v != null ? String(v) : '—'}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-xs text-amber-600 italic">dcf_scenarios absent</div>
        )}

        {/* EPV */}
        {epv ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900/30 px-3 py-3 space-y-1">
            <div className="text-xs text-gray-600 uppercase tracking-wide">EPV (Earnings Power Value)</div>
            <div className="text-sm font-semibold text-gray-200">
              {epv.valeur_rentabilite != null ? `${epv.valeur_rentabilite} $` : <Absent />}
            </div>
            {epv.note != null && (
              <p className="text-xs text-gray-400 pt-1 border-t border-gray-800">{epv.note}</p>
            )}
          </div>
        ) : (
          <div className="text-xs text-amber-600 italic">epv absent</div>
        )}

        {/* Valorisation relative */}
        {rel ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900/30 px-3 py-3 space-y-2">
            <div className="text-xs text-gray-600 uppercase tracking-wide">Valorisation relative</div>
            <Dl cols={1}>
              <KeyValue label="Multiples" value={rel.multiple != null ? rel.multiple : <Absent />} />
              <KeyValue label="vs historique" value={rel.vs_historique != null ? rel.vs_historique : <Absent />} />
              <KeyValue label="vs pairs" value={rel.vs_pairs != null ? rel.vs_pairs : <Absent />} />
            </Dl>
          </div>
        ) : (
          <div className="text-xs text-amber-600 italic">relatif absent</div>
        )}

        {/* Base rate anchor */}
        {bra ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900/30 px-3 py-3 space-y-1">
            <div className="text-xs text-gray-600 uppercase tracking-wide">Base rate anchor</div>
            <Dl cols={2}>
              <KeyValue label="Taux de base" value={bra.taux_base_pct != null ? fmtPct(bra.taux_base_pct) : <Absent />} />
              <KeyValue label="Classe de référence" value={bra.reference_class != null ? bra.reference_class : <Absent />} />
            </Dl>
            {bra.note != null && (
              <p className="text-xs text-gray-400 pt-1 border-t border-gray-800">{bra.note}</p>
            )}
          </div>
        ) : (
          <div className="text-xs text-amber-600 italic">base_rate_anchor absent</div>
        )}
      </CardBody>
    </Card>
  )
}

// ── Incertitudes ──────────────────────────────────────────────────────────────
const STATUT_LABEL = {
  resolue:        'Résolue',
  en_cours:       'En cours',
  non_resolvable: 'Non résolvable',
}
const STATUT_VARIANT = {
  resolue:        'emerald',
  en_cours:       'amber',
  non_resolvable: 'red',
}

function IncertitudesBloquantes({ items, tickerId }) {
  if (!Array.isArray(items)) return (
    <div className="text-xs text-amber-600 italic">incertitudes_bloquantes absent</div>
  )
  if (items.length === 0) return (
    <EmptyState title="Aucune incertitude bloquante" description="Aucune incertitude susceptible d'inverser la thèse n'a été identifiée." />
  )
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={i} className="rounded-lg border border-red-900/30 bg-red-950/10 px-4 py-3 space-y-2">
          <div className="flex items-start gap-3">
            {item.statut != null && (
              <Badge variant={STATUT_VARIANT[item.statut] || 'gray'}>
                {STATUT_LABEL[item.statut] || item.statut}
              </Badge>
            )}
            <p className="text-sm text-gray-200 font-medium flex-1">
              {item.question != null ? item.question : <Absent />}
            </p>
          </div>
          {item.impact_si_non_resolu != null && (
            <p className="text-sm text-gray-400 pl-0">
              <span className="text-gray-600 text-xs">Impact si non résolu : </span>
              {item.impact_si_non_resolu}
            </p>
          )}
          <SourceRefs refs={item.source_entry_refs} tickerId={tickerId} />
        </div>
      ))}
    </div>
  )
}

function IncertitudesInvestissables({ items }) {
  if (!Array.isArray(items)) return (
    <div className="text-xs text-amber-600 italic">incertitudes_investissables absent</div>
  )
  if (items.length === 0) return (
    <EmptyState title="Aucune incertitude investissable" description="Aucune incertitude à fourchette quantifiée n'a été identifiée." />
  )
  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={i} className="rounded-lg border border-gray-800 bg-gray-900/30 px-4 py-3">
          <p className="text-sm text-gray-200">
            {item.question != null ? item.question : <Absent />}
          </p>
          {item.fourchette != null && (
            <p className="text-xs text-gray-500 mt-1">
              <span className="text-gray-600">Fourchette : </span>
              {item.fourchette}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────
export default function ResearchMemoDetail() {
  const router = useRouter()
  const { memo_id } = router.query

  const [memo, setMemo]     = useState(null)
  const [err, setErr]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!memo_id) return
    fetch(`${API}/research/${memo_id}`)
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`)))
      .then(d => { setMemo(d); setLoading(false) })
      .catch(e => { setErr(String(e)); setLoading(false) })
  }, [memo_id])

  if (loading) return (
    <div className="py-12 text-center text-sm text-gray-500">Chargement…</div>
  )

  if (err) return (
    <div>
      <Link href="/v2" className="text-xs text-gray-500 hover:text-gray-300 mb-4 inline-block">
        ← Accueil V2
      </Link>
      <ErrorState detail={err} />
    </div>
  )

  if (!memo) return null

  const tickerId = memo.ticker_id
  const mj = memo.memo_json
  const mjo = memo.memo_json_original

  return (
    <div className="space-y-6">
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-xs text-gray-500 flex-wrap">
        <Link href="/v2" className="hover:text-gray-300">V2</Link>
        <span>›</span>
        {tickerId && (
          <>
            <Link href={`/v2/tickers/${tickerId}/knowledge`} className="hover:text-gray-300">
              {tickerId}
            </Link>
            <span>›</span>
            <Link href={`/v2/tickers/${tickerId}/research`} className="hover:text-gray-300">
              Research memos
            </Link>
            <span>›</span>
          </>
        )}
        <span className="text-gray-300">Memo #{memo_id}</span>
      </div>

      {/* En-tête */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-white">
          Research Memo #{memo.id != null ? memo.id : '—'}
          {tickerId && <span className="text-gray-400"> — {tickerId}</span>}
        </h1>
        {mj && mj.posture != null && (
          <Badge variant={POSTURE_VARIANT[mj.posture] || 'gray'}>
            {mj.posture}
          </Badge>
        )}
        {memo.schema_version != null && (
          <span className="text-xs text-gray-600 font-mono">{memo.schema_version}</span>
        )}
      </div>

      {/* ── Section 1 : Télémétrie (discrète mais présente) ────────────────── */}
      <Telemetry memo={memo} />

      {/* ── Section 2 : Corrections déterministes ─────────────────────────── */}
      {mj !== undefined && mjo !== undefined && (
        <DiffBlock memoJson={mj} memoJsonOriginal={mjo} />
      )}

      {/* ── Section 3 : Modèle d'affaires ─────────────────────────────────── */}
      {mj && (
        <Section title="Modèle d'affaires">
          <BusinessModelSection bm={mj.business_model} tickerId={tickerId} />
        </Section>
      )}

      {/* ── Section 4 : Fossé concurrentiel ───────────────────────────────── */}
      {mj && (
        <Section title="Fossé concurrentiel">
          <MoatSection moat={mj.moat} tickerId={tickerId} />
        </Section>
      )}

      {/* ── Section 5 : Industrie ─────────────────────────────────────────── */}
      {mj && (
        <Section title="Industrie">
          <IndustrySection industry={mj.industry} tickerId={tickerId} />
        </Section>
      )}

      {/* ── Section 6 : Financiers ────────────────────────────────────────── */}
      {mj && (
        <Section title="Financiers">
          <FinancialsSection financials={mj.financials} tickerId={tickerId} />
        </Section>
      )}

      {/* ── Section 7 : Management ────────────────────────────────────────── */}
      {mj && (
        <Section title="Management">
          <ManagementSection management={mj.management} tickerId={tickerId} />
        </Section>
      )}

      {/* ── Section 8 : Valorisation ──────────────────────────────────────── */}
      {mj && (
        <Section title="Valorisation">
          <ValuationSection valuation={mj.valuation} />
        </Section>
      )}

      {/* ── Section 9 : Incertitudes bloquantes ───────────────────────────── */}
      {mj && (
        <Section title={`Incertitudes bloquantes (${Array.isArray(mj.incertitudes_bloquantes) ? mj.incertitudes_bloquantes.length : '—'})`}>
          <IncertitudesBloquantes items={mj.incertitudes_bloquantes} tickerId={tickerId} />
        </Section>
      )}

      {/* ── Section 10 : Incertitudes investissables ──────────────────────── */}
      {mj && (
        <Section title={`Incertitudes investissables (${Array.isArray(mj.incertitudes_investissables) ? mj.incertitudes_investissables.length : '—'})`}>
          <IncertitudesInvestissables items={mj.incertitudes_investissables} />
        </Section>
      )}

      {/* ── Section 11 : Prompt snapshot (repliable) ──────────────────────── */}
      <Section title="Prompt snapshot">
        <PromptSnapshot prompt={memo.prompt_snapshot} />
      </Section>
    </div>
  )
}
