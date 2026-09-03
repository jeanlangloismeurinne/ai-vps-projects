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

function fmtDatetime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function fmtPct(val) {
  if (val == null) return null
  return `${(val * 100).toFixed(0)} %`
}

// ── Bloc : Verdict en manchette ───────────────────────────────────────────────
// Le `rationale` commence toujours par un en-tête entre crochets écrit par le CODE
// (pas par le LLM) : "[Verdict recomputé : … — ligne écrite par le code depuis l'index `covers`]".
// On le sépare du corps narratif pour le mettre en valeur — c'est la garantie que le
// verdict est recalculé algorithmiquement, pas généré par le modèle.

const VERDICT_VARIANT = {
  ready:            'emerald',
  thin_qualitative: 'amber',
}
const VERDICT_LABEL = {
  ready:            'Ready — analyse possible',
  thin_qualitative: 'Thin qualitative — couverture insuffisante',
}

function VerdictBanner({ verdict, rationale, createdAt, schemaVersion }) {
  if (!verdict) {
    return (
      <div className="rounded-xl border border-amber-900/50 bg-amber-950/20 px-4 py-4">
        <p className="text-sm text-amber-400">
          <span className="font-semibold">— champ absent</span> : le verdict n'est pas présent dans la réponse.
        </p>
      </div>
    )
  }

  // Découpe le rationale : en-tête code vs corps LLM
  let headerCode = null
  let bodyLlm = rationale || null

  if (rationale) {
    const match = rationale.match(/^(\[.*?\])\s*\n\n([\s\S]*)$/s)
    if (match) {
      headerCode = match[1]
      bodyLlm = match[2].trim()
    }
  }

  const variant = VERDICT_VARIANT[verdict] || 'gray'
  const label = VERDICT_LABEL[verdict] || verdict

  return (
    <Card>
      <CardBody className="space-y-4">
        {/* Verdict badge + méta */}
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div className="space-y-1.5">
            <div className="text-xs text-gray-500 uppercase tracking-wide">Verdict readiness</div>
            <Badge variant={variant} className="text-sm px-3 py-1">{label}</Badge>
          </div>
          <div className="text-right space-y-1">
            <div className="text-xs text-gray-500">Calculé le {fmtDatetime(createdAt)}</div>
            {schemaVersion && (
              <div className="text-[10px] font-mono text-gray-600">{schemaVersion}</div>
            )}
          </div>
        </div>

        {/* En-tête CODE — garantie algo, pas prose LLM */}
        {headerCode ? (
          <div className="rounded-md border border-emerald-900/40 bg-emerald-950/20 px-3 py-2">
            <div className="text-[10px] text-emerald-600 uppercase tracking-wide mb-1 font-semibold">
              Garantie algorithmique — ligne écrite par le code
            </div>
            <p className="text-xs text-emerald-300/90 font-mono leading-relaxed">{headerCode}</p>
          </div>
        ) : (
          <div className="rounded-md border border-amber-900/40 bg-amber-950/20 px-3 py-2">
            <p className="text-xs text-amber-400 italic">
              — En-tête algorithmique absent : le rationale ne commence pas par le marqueur attendu [Verdict recomputé].
              Le verdict affiché peut ne pas être recalculé.
            </p>
          </div>
        )}

        {/* Corps LLM — lecture du curator */}
        {bodyLlm ? (
          <div className="space-y-1">
            <div className="text-[10px] text-gray-600 uppercase tracking-wide">Lecture du curator (LLM)</div>
            <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{bodyLlm}</p>
          </div>
        ) : rationale == null ? (
          <p className="text-xs text-amber-600 italic">— champ absent : rationale manquant</p>
        ) : null}
      </CardBody>
    </Card>
  )
}

// ── Bloc : Couverture par bloc ─────────────────────────────────────────────────
// Chaque bloc (`structuree`, `qualitative_marche`) a un `bloc_ok` et une liste de dimensions.
// Chaque dimension a : ok, dimension, tier_atteint, tier_plancher, champs_requis[],
// champs_non_fondables[], fondations[{ champ, entry_ids[] }].
// Ce qui est fondé vs non fondé doit se voir d'un coup d'œil.

const BLOC_LABELS = {
  structuree:          'Bloc structuré',
  qualitative_marche:  'Bloc qualitatif-marché',
}

const DIMENSION_LABELS = {
  business_model:      'Modèle économique',
  financials:          'Financials',
  valorisation:        'Valorisation',
  produits:            'Produits',
  positionnement:      'Positionnement',
  marche:              'Marché',
  management_allocation: 'Management & allocation',
  risques:             'Risques',
}

function TierPill({ tier, label }) {
  if (tier == null) {
    return <span className="text-gray-600 text-xs italic">— champ absent</span>
  }
  const isTopTier = tier === 'A' || tier === 'A-'
  const isMid = tier === 'B+' || tier === 'B' || tier === 'B-'
  const cls = isTopTier
    ? 'bg-emerald-900/40 text-emerald-300 border border-emerald-800'
    : isMid
      ? 'bg-sky-900/40 text-sky-300 border border-sky-800'
      : 'bg-amber-900/40 text-amber-300 border border-amber-800'
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono font-medium ${cls}`}>
      {label && <span className="text-[10px] text-current/70 mr-1">{label}</span>}
      {tier}
    </span>
  )
}

function DimensionRow({ dim }) {
  if (!dim) return null

  const dimensionLabel = DIMENSION_LABELS[dim.dimension] || dim.dimension || '— champ absent'
  const champsReqSet = new Set(Array.isArray(dim.champs_requis) ? dim.champs_requis : [])
  const champsNonFondables = Array.isArray(dim.champs_non_fondables) ? dim.champs_non_fondables : []
  const fondations = Array.isArray(dim.fondations) ? dim.fondations : []
  const champsFoundes = new Set(fondations.map(f => f.champ))

  // Calcul des champs fondés vs non fondés parmi les requis
  const fondes = [...champsReqSet].filter(c => champsFoundes.has(c))
  const nonFondes = [...champsReqSet].filter(c => !champsFoundes.has(c) && !champsNonFondables.includes(c))

  return (
    <div className={`rounded-lg border px-4 py-3 space-y-3 ${
      dim.ok
        ? 'border-emerald-900/40 bg-emerald-950/10'
        : 'border-red-900/40 bg-red-950/10'
    }`}>
      {/* En-tête dimension */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${dim.ok ? 'text-gray-200' : 'text-red-300'}`}>
            {dim.ok ? '✓' : '✗'} {dimensionLabel}
          </span>
          {dim.dimension == null && (
            <span className="text-amber-600 text-xs italic">— champ absent</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <TierPill tier={dim.tier_atteint} label="atteint" />
          <span className="text-gray-600 text-xs">≥</span>
          <TierPill tier={dim.tier_plancher} label="plancher" />
        </div>
      </div>

      {/* Champs requis : fondés en vert, manquants en rouge */}
      <div className="flex flex-wrap gap-1.5">
        {[...champsReqSet].map(champ => {
          const fonde = champsFoundes.has(champ)
          const nonFondable = champsNonFondables.includes(champ)
          const fondation = fondations.find(f => f.champ === champ)
          const nEntries = fondation ? fondation.entry_ids?.length ?? 0 : 0
          return (
            <span
              key={champ}
              title={fonde ? `${nEntries} entrée${nEntries !== 1 ? 's' : ''} de connaissance` : nonFondable ? 'Non fondable — lacune déclarée' : 'Non fondé'}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono ${
                fonde
                  ? 'bg-emerald-900/30 text-emerald-300 border border-emerald-800/60'
                  : nonFondable
                    ? 'bg-amber-900/30 text-amber-400 border border-amber-800/60'
                    : 'bg-red-900/30 text-red-400 border border-red-800/60'
              }`}
            >
              {fonde ? '✓' : nonFondable ? '~' : '✗'} {champ}
              {fonde && nEntries > 0 && (
                <span className="text-emerald-600 text-[10px]">({nEntries})</span>
              )}
            </span>
          )
        })}
        {champsReqSet.size === 0 && (
          <span className="text-amber-600 text-xs italic">— champs_requis absent</span>
        )}
      </div>

      {/* Champs non fondables (lacune déclarée) */}
      {champsNonFondables.length > 0 && (
        <p className="text-xs text-amber-400">
          Lacune déclarée (non fondable) : {champsNonFondables.join(', ')}
        </p>
      )}
    </div>
  )
}

function CoverageBloc({ blocKey, bloc }) {
  const label = BLOC_LABELS[blocKey] || blocKey
  if (!bloc) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900/50 px-4 py-4">
        <p className="text-sm text-amber-600 italic">— champ absent : bloc {blocKey} manquant</p>
      </div>
    )
  }

  const dimensions = Array.isArray(bloc.dimensions) ? bloc.dimensions : []

  return (
    <Card>
      <CardHeader
        title={label}
        action={
          bloc.bloc_ok != null ? (
            <Badge variant={bloc.bloc_ok ? 'emerald' : 'red'}>
              {bloc.bloc_ok ? 'Fondé' : 'Lacunaire'}
            </Badge>
          ) : (
            <span className="text-amber-600 text-xs italic">bloc_ok absent</span>
          )
        }
      />
      <CardBody className="space-y-3">
        {dimensions.length === 0 ? (
          <p className="text-sm text-gray-500 italic">Aucune dimension</p>
        ) : (
          dimensions.map((dim, i) => (
            <DimensionRow key={dim.dimension || i} dim={dim} />
          ))
        )}
      </CardBody>
    </Card>
  )
}

// ── Bloc : Compteurs d'entrées par tier ───────────────────────────────────────
// Les tiers ici sont des REGROUPEMENTS grossiers : tier_A = A + A-, tier_B = B+ + B + B-,
// tier_C_llm_memory = C+ + C. L'écran knowledge montre les 7 tiers fins.
// On explique ce regroupement pour que les deux écrans ne se lisent pas comme contradictoires.

function EntriesParTier({ entriesParTier, tickerId }) {
  if (!entriesParTier) {
    return (
      <Card>
        <CardHeader title="Entrées de connaissance par tier" />
        <CardBody>
          <p className="text-sm text-amber-600 italic">— champ absent : entries_par_tier manquant</p>
        </CardBody>
      </Card>
    )
  }

  const { total, tier_A, tier_B, tier_C_llm_memory } = entriesParTier

  return (
    <Card>
      <CardHeader
        title="Entrées de connaissance par tier (regroupés)"
        subtitle="Ces compteurs agrègent en 3 groupes grossiers les 7 tiers fins de l'écran Knowledge."
        action={
          <Link
            href={`/v2/tickers/${tickerId}/knowledge`}
            className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            Voir détail 7 tiers →
          </Link>
        }
      />
      <CardBody className="space-y-4">
        {/* Avertissement regroupement */}
        <div className="rounded-md bg-gray-800/50 border border-gray-700 px-3 py-2">
          <p className="text-xs text-gray-400 leading-relaxed">
            <span className="font-semibold text-gray-300">Regroupement :</span>{' '}
            <span className="font-mono text-emerald-400">tier_A</span> = A + A- &nbsp;·&nbsp;
            <span className="font-mono text-sky-400">tier_B</span> = B+ + B + B- &nbsp;·&nbsp;
            <span className="font-mono text-amber-400">tier_C_llm_memory</span> = C+ + C (mémoire LLM, non sourcée).
            L'écran Knowledge affiche les 7 tiers fins.
          </p>
        </div>

        <Dl cols={4}>
          <KeyValue
            label="Total"
            value={total != null ? String(total) : <span className="text-amber-600 italic">— champ absent</span>}
          />
          <KeyValue
            label="Tier A (A + A-)"
            value={tier_A != null
              ? <span className="text-emerald-300 font-semibold">{tier_A}</span>
              : <span className="text-amber-600 italic">— champ absent</span>}
          />
          <KeyValue
            label="Tier B (B+ / B / B-)"
            value={tier_B != null
              ? <span className="text-sky-300 font-semibold">{tier_B}</span>
              : <span className="text-amber-600 italic">— champ absent</span>}
          />
          <KeyValue
            label="Tier C / LLM memory"
            value={tier_C_llm_memory != null
              ? (tier_C_llm_memory === 0
                ? <span className="text-gray-400">0 — aucune entrée LLM non sourcée</span>
                : <span className="text-amber-300 font-semibold">{tier_C_llm_memory}</span>)
              : <span className="text-amber-600 italic">— champ absent</span>}
          />
        </Dl>
      </CardBody>
    </Card>
  )
}

// ── Bloc : Indicateurs ───────────────────────────────────────────────────────
// `conviction` et `marge_securite` sont null à ce stade — c'est NORMAL.
// Ils naissent plus loin dans la chaîne (analyse). "non applicable à ce stade",
// surtout pas 0 ni vide.

function IndicateursBloc({ indicateurs }) {
  if (!indicateurs) {
    return (
      <Card>
        <CardHeader title="Indicateurs" />
        <CardBody>
          <p className="text-sm text-amber-600 italic">— champ absent : indicateurs manquant</p>
        </CardBody>
      </Card>
    )
  }

  const { conviction, qualite_info, marge_securite } = indicateurs

  return (
    <Card>
      <CardHeader
        title="Indicateurs"
        subtitle="Conviction et marge de sécurité naissent à l'étape d'analyse — pas au gate readiness."
      />
      <CardBody>
        <Dl cols={3}>
          <div className="flex flex-col gap-0.5">
            <dt className="text-xs text-gray-500">Qualité info</dt>
            <dd className="text-sm text-gray-200">
              {qualite_info != null
                ? <span className="font-semibold">{fmtPct(qualite_info)}</span>
                : <span className="text-amber-600 italic">— champ absent</span>}
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="text-xs text-gray-500">Conviction</dt>
            <dd className="text-sm text-gray-200">
              {conviction === null
                ? <span className="text-gray-500 italic">Non applicable à ce stade</span>
                : conviction != null
                  ? String(conviction)
                  : <span className="text-amber-600 italic">— champ absent</span>}
            </dd>
            <dd className="text-[10px] text-gray-600">Calculée à l'analyse, pas au gate</dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="text-xs text-gray-500">Marge de sécurité</dt>
            <dd className="text-sm text-gray-200">
              {marge_securite === null
                ? <span className="text-gray-500 italic">Non applicable à ce stade</span>
                : marge_securite != null
                  ? String(marge_securite)
                  : <span className="text-amber-600 italic">— champ absent</span>}
            </dd>
            <dd className="text-[10px] text-gray-600">Calculée à l'analyse, pas au gate</dd>
          </div>
        </Dl>
      </CardBody>
    </Card>
  )
}

// ── Bloc : Gaps ───────────────────────────────────────────────────────────────
// Une liste vide ici est une BONNE nouvelle. Un EmptyState neutre se lirait comme
// « pas d'information » — on le dit explicitement.

function GapsBloc({ gaps }) {
  const list = Array.isArray(gaps) ? gaps : null

  if (list === null) {
    return (
      <Card>
        <CardHeader title="Lacunes (gaps)" />
        <CardBody>
          <p className="text-sm text-amber-600 italic">— champ absent : gaps manquant</p>
        </CardBody>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader
        title={`Lacunes (gaps) — ${list.length === 0 ? 'aucune' : list.length}`}
        action={
          list.length === 0 ? (
            <Badge variant="emerald">Aucun trou</Badge>
          ) : (
            <Badge variant="amber">{list.length} lacune{list.length > 1 ? 's' : ''}</Badge>
          )
        }
      />
      <CardBody>
        {list.length === 0 ? (
          <div className="rounded-md bg-emerald-950/20 border border-emerald-900/30 px-3 py-3 text-sm text-emerald-300">
            Aucun trou de couverture identifié — tous les champs requis sont fondés au tier plancher.
            Une liste vide ici est un signal positif, pas une absence de données.
          </div>
        ) : (
          <ul className="space-y-2">
            {list.map((gap, i) => (
              <li key={i} className="flex gap-2 text-sm text-gray-300">
                <span className="text-red-500 shrink-0 mt-0.5">✗</span>
                <span>{typeof gap === 'string' ? gap : JSON.stringify(gap)}</span>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  )
}

// ── Bloc : Arrêt Pareto ───────────────────────────────────────────────────────

function ArretParetoBloc({ arretParetoRecommande }) {
  if (arretParetoRecommande == null) {
    return (
      <div className="rounded-xl border border-amber-900/40 bg-amber-950/10 px-4 py-3">
        <p className="text-sm text-amber-600 italic">— champ absent : arret_pareto_recommande manquant</p>
      </div>
    )
  }

  // Ni un succès ni une alerte : une consigne sur l'effort de collecte à venir.
  // Le marqueur reste neutre pour ne pas suggérer que l'un des deux états serait « bon ».
  return (
    <div className={`rounded-xl border px-4 py-3 flex items-center gap-3 ${
      arretParetoRecommande
        ? 'border-sky-900/60 bg-sky-950/20'
        : 'border-gray-800 bg-gray-900/30'
    }`}>
      <span className={`text-lg ${arretParetoRecommande ? 'text-sky-400' : 'text-gray-500'}`}>
        {arretParetoRecommande ? '◼' : '◻'}
      </span>
      <div>
        <div className="text-sm font-medium text-gray-200">
          {arretParetoRecommande
            ? 'Arrêt Pareto recommandé'
            : "Pas d'arrêt Pareto recommandé"}
        </div>
        <div className="text-xs text-gray-500 mt-0.5">
          {arretParetoRecommande
            ? "Le curator estime que la connaissance supplémentaire a un rendement marginal faible : le corpus est assez dense pour analyser sans accumulation supplémentaire."
            : "Le curator n'estime pas le rendement marginal épuisé : continuer à alimenter la connaissance reste payant avant d'analyser."}
        </div>
      </div>
    </div>
  )
}

// ── Bloc : Incertitudes ───────────────────────────────────────────────────────
// La distinction bloquantes vs investissables est le cœur du gate :
// une incertitude investissable n'empêche pas d'investir, une bloquante si.
// Chaque incertitude a : question, fourchette.

function IncertitudeItem({ item, index }) {
  if (!item) return null
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/30 px-4 py-3 space-y-2">
      <p className="text-sm text-gray-200 leading-relaxed">
        {item.question != null && item.question !== ''
          ? item.question
          : <span className="text-amber-600 italic">— champ absent : question</span>}
      </p>
      {item.fourchette != null && item.fourchette !== '' ? (
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-600 uppercase tracking-wide shrink-0">Fourchette</span>
          <span className="text-xs text-sky-300 font-mono">{item.fourchette}</span>
        </div>
      ) : (
        <p className="text-xs text-amber-600 italic">— champ absent : fourchette</p>
      )}
    </div>
  )
}

function IncertitudesBloc({ bloquantes, investissables }) {
  const listeBloquantes = Array.isArray(bloquantes) ? bloquantes : null
  const listeInvestissables = Array.isArray(investissables) ? investissables : null

  return (
    <Card>
      <CardHeader
        title="Incertitudes"
        subtitle="Une incertitude investissable n'empêche pas d'investir. Une bloquante si — c'est le cœur du gate."
      />
      <CardBody className="space-y-5">
        {/* Explication de la distinction */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="rounded-md border border-red-900/40 bg-red-950/10 px-3 py-2">
            <div className="text-xs font-semibold text-red-400 mb-1">Bloquantes</div>
            <p className="text-[11px] text-gray-500 leading-relaxed">
              Doivent être résolues avant toute analyse d'investissement. Si la liste est vide,
              aucun obstacle conceptuel n'est identifié.
            </p>
          </div>
          <div className="rounded-md border border-sky-900/40 bg-sky-950/10 px-3 py-2">
            <div className="text-xs font-semibold text-sky-400 mb-1">Investissables</div>
            <p className="text-[11px] text-gray-500 leading-relaxed">
              Incertitudes résiduelles à quantifier dans l'analyse (fourchettes). Leur présence
              est normale et n'empêche pas d'investir.
            </p>
          </div>
        </div>

        {/* Incertitudes bloquantes */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-red-400">
              Bloquantes ({listeBloquantes == null ? '— absent' : listeBloquantes.length})
            </h4>
            {listeBloquantes !== null && listeBloquantes.length === 0 && (
              <Badge variant="emerald">Aucune — gate franchi</Badge>
            )}
          </div>
          {listeBloquantes === null ? (
            <p className="text-xs text-amber-600 italic">— champ absent : incertitudes_bloquantes manquant</p>
          ) : listeBloquantes.length === 0 ? (
            <div className="rounded-md bg-emerald-950/20 border border-emerald-900/30 px-3 py-2 text-sm text-emerald-300">
              Aucune incertitude bloquante — le gate est franchi de ce côté.
            </div>
          ) : (
            <div className="space-y-2">
              {listeBloquantes.map((item, i) => (
                <IncertitudeItem key={i} item={item} index={i} />
              ))}
            </div>
          )}
        </div>

        {/* Incertitudes investissables */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-sky-400">
            Investissables ({listeInvestissables == null ? '— absent' : listeInvestissables.length})
          </h4>
          {listeInvestissables === null ? (
            <p className="text-xs text-amber-600 italic">— champ absent : incertitudes_investissables manquant</p>
          ) : listeInvestissables.length === 0 ? (
            <p className="text-sm text-gray-500 italic">Aucune incertitude investissable identifiée.</p>
          ) : (
            <div className="space-y-2">
              {listeInvestissables.map((item, i) => (
                <IncertitudeItem key={i} item={item} index={i} />
              ))}
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────
export default function ReadinessPage() {
  const router = useRouter()
  const { ticker_id } = router.query

  const [data,    setData]    = useState(null)
  const [err,     setErr]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!ticker_id) return
    fetch(`${API}/tickers/${ticker_id}/curator/readiness`)
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`)))
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setErr(String(e)); setLoading(false) })
  }, [ticker_id])

  // ── Chargement / erreur ───────────────────────────────────────────────────
  if (loading) return (
    <div className="py-12 text-center text-sm text-gray-500">Chargement…</div>
  )

  if (err) return (
    <div className="space-y-4">
      <Link href={`/v2/tickers/${ticker_id}/knowledge`} className="text-xs text-gray-500 hover:text-gray-300 inline-block">
        ← Retour à la connaissance
      </Link>
      <ErrorState detail={err} />
    </div>
  )

  if (!data) return null

  // Extraction des champs du payload — UNIQUEMENT les clés réelles, sans fallback sur variantes
  const topVerdict             = data.verdict
  const topCreatedAt           = data.created_at
  const topContextPackEntryId  = data.context_pack_entry_id
  const report                 = data.report_json

  // Sous-clés de report_json
  const reportVerdict              = report?.verdict
  const reportSchemaVersion        = report?.schema_version
  const reportRationale            = report?.rationale
  const reportGaps                 = report?.gaps
  const reportCoverage             = report?.coverage
  const reportIndicateurs          = report?.indicateurs
  const reportEntriesParTier       = report?.entries_par_tier
  const reportArretPareto          = report?.arret_pareto_recommande
  const reportIncertBloquantes     = report?.incertitudes_bloquantes
  const reportIncertInvestissables = report?.incertitudes_investissables

  // Couverture par bloc
  const coverageStructuree        = reportCoverage?.structuree
  const coverageQualitativeMarche = reportCoverage?.qualitative_marche

  // Titre de page
  const titreVerdict = topVerdict || reportVerdict || '—'

  return (
    <div className="space-y-6">
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-xs text-gray-500 flex-wrap">
        <Link href="/v2" className="hover:text-gray-300">V2</Link>
        <span>›</span>
        <Link href="/watchlist-v2" className="hover:text-gray-300">Watchlist</Link>
        <span>›</span>
        <span className="text-gray-300">{ticker_id}</span>
        <span>›</span>
        <span className="text-gray-400">Readiness</span>
      </div>

      {/* Titre */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-white">
          {ticker_id} — Gate readiness
        </h1>
        <Badge variant={VERDICT_VARIANT[titreVerdict] || 'gray'}>
          {VERDICT_LABEL[titreVerdict] || titreVerdict}
        </Badge>
        {topContextPackEntryId != null && (
          <span className="text-xs text-gray-600 font-mono">
            context_pack #{topContextPackEntryId}
          </span>
        )}
      </div>

      {/* Note explicative du gate */}
      <div className="rounded-xl border border-gray-800 bg-gray-900/30 px-4 py-3">
        <p className="text-xs text-gray-400 leading-relaxed">
          Ce gate évalue si la connaissance accumulée est suffisante pour lancer une analyse d'investissement.
          Un verdict <span className="text-emerald-400 font-semibold">ready</span> signifie que tous les blocs
          requis sont fondés sur des sources vérifiables. Un verdict{' '}
          <span className="text-amber-400 font-semibold">thin_qualitative</span> signale une couverture
          insuffisante sur la partie qualitative-marché. Les incertitudes bloquantes empêchent d'aller
          plus loin ; les incertitudes investissables sont à quantifier dans l'analyse.
        </p>
      </div>

      {/* ── Section 1 : Verdict ──────────────────────────────────────────────── */}
      <VerdictBanner
        verdict={topVerdict}
        rationale={reportRationale}
        createdAt={topCreatedAt}
        schemaVersion={reportSchemaVersion}
      />

      {/* ── Section 2 : Couverture par bloc ─────────────────────────────────── */}
      <Section title="Couverture par bloc">
        {!reportCoverage ? (
          <div className="rounded-xl border border-amber-900/40 bg-amber-950/10 px-4 py-4">
            <p className="text-sm text-amber-600 italic">— champ absent : coverage manquant</p>
          </div>
        ) : (
          <div className="space-y-4">
            <CoverageBloc blocKey="structuree"          bloc={coverageStructuree} />
            <CoverageBloc blocKey="qualitative_marche"  bloc={coverageQualitativeMarche} />
          </div>
        )}
      </Section>

      {/* ── Section 3 : Lacunes ─────────────────────────────────────────────── */}
      <GapsBloc gaps={reportGaps} />

      {/* ── Section 4 : Arrêt Pareto ────────────────────────────────────────── */}
      <Section title="Recommandation Pareto">
        <ArretParetoBloc arretParetoRecommande={reportArretPareto} />
      </Section>

      {/* ── Section 5 : Incertitudes ────────────────────────────────────────── */}
      <IncertitudesBloc
        bloquantes={reportIncertBloquantes}
        investissables={reportIncertInvestissables}
      />

      {/* ── Section 6 : Compteurs par tier ──────────────────────────────────── */}
      <EntriesParTier
        entriesParTier={reportEntriesParTier}
        tickerId={ticker_id}
      />

      {/* ── Section 7 : Indicateurs ─────────────────────────────────────────── */}
      <IndicateursBloc indicateurs={reportIndicateurs} />

      {/* ── Méta bas de page ────────────────────────────────────────────────── */}
      <div className="rounded-xl border border-gray-800 bg-gray-900/30 px-4 py-3 flex items-center justify-between flex-wrap gap-2">
        <div className="text-xs text-gray-600">
          Rapport #{data.id != null ? data.id : '— champ absent'} · {fmtDatetime(topCreatedAt)}
        </div>
        <Link
          href={`/v2/tickers/${ticker_id}/knowledge`}
          className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
        >
          Voir la base de connaissance complète →
        </Link>
      </div>
    </div>
  )
}
