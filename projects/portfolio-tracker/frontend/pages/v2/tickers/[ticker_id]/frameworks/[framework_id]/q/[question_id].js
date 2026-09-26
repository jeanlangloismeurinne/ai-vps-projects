/**
 * NIVEAU 3 du parcours du comité — LA PREUVE d'une question (spec §8.1, maquette
 * `provenance-cards/framework_screen_niveau3.md`). `GET /v2/tickers/:id/frameworks/:fid/q/:qid`.
 *
 * ⚠️ CHAQUE CHAMP DU CONTRAT A SON PIXEL, et c'est gardé : tout champ terminal de
 * `FrameworkAnswerServie` est rendu dans un élément portant `data-champ="<chemin>"`, et
 * `checks/check_parcours.py` §7 exige la BIJECTION entre ces marqueurs et le contrat. Ajouter un
 * champ au contrat sans lui donner un pixel ici fait rougir un assert nommé.
 *
 * Les quatre règles d'affichage de la maquette : ③ « — sans objet » jamais « ✓ » sur une réponse qui
 * n'approxime pas ; le rang affiché avec sa dérivation ; l'actualité jamais en pastille verte muette
 * (état ET motif) ; aucun score composite (rang, nature, actualité restent trois colonnes).
 */
import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import { Card, CardHeader, CardBody, Badge, ErrorState } from '../../../../../../../components/v2'
import {
  API, CONTROLES, ActualiteBadge, EtatControle, ManqueBloc, StatutBadge,
} from '../../../../../../../components/v2/parcours'
import RegistreComite from '../../../../../../../components/v2/RegistreComite'

// Un pixel = un champ. Le marqueur est le chemin du contrat, écrit en LITTÉRAL à chaque usage pour
// que le check le lise dans le source.
function Ligne({ label, children }) {
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-3 text-sm">
      <dt className="text-xs text-gray-500 pt-0.5">{label}</dt>
      <dd className="text-gray-200 min-w-0">{children}</dd>
    </div>
  )
}

function vide(v) {
  return v === null || v === undefined || (Array.isArray(v) && v.length === 0)
}
function Val({ v }) {
  if (vide(v)) return <span className="text-gray-600">—</span>
  if (Array.isArray(v)) return <>{v.join(', ')}</>
  if (typeof v === 'boolean') return <>{v ? 'oui' : 'non'}</>
  return <>{String(v)}</>
}

function Piece({ p }) {
  return (
    <li className="text-xs flex gap-2 items-start">
      <span className="font-mono text-gray-500 shrink-0">#{p.entry_id}</span>
      {!p.present_au_corpus ? (
        <span className="text-red-300">citée mais introuvable au dossier</span>
      ) : (
        <span className="min-w-0">
          {p.source_url
            ? <a href={p.source_url} target="_blank" rel="noreferrer" className="text-gray-200 hover:underline">{p.titre || p.source_type}</a>
            : <span className="text-gray-200">{p.titre || p.source_type}</span>}
          <span className="text-gray-500">
            {' '}· source {p.reliability_tier} · {p.nature} · datée {p.date_du_fait || p.source_date || 'non datée'}
          </span>
          {p.remplacee && <Badge variant="amber" className="ml-2">remplacée depuis</Badge>}
        </span>
      )}
    </li>
  )
}

function Preuve({ pr, tickerId }) {
  const a = pr.answer
  const citees = pr.pieces.filter(p => p.role === 'citee')
  const ingredients = pr.pieces.filter(p => p.role === 'ingredient')
  const approx = a.statut === 'approxime'
  return (
    <div className="space-y-4">
      {/* ── LA RÉPONSE ─────────────────────────────────────────────── */}
      <Card>
        <CardHeader
          title="La réponse"
          action={<span className="flex items-center gap-2">
            <span data-champ="statut"><StatutBadge statut={a.statut} /></span>
            <span className="text-xs text-gray-500">par <span data-champ="analyste">{a.analyste}</span></span>
          </span>}
        />
        <CardBody className="space-y-3">
          <p className="text-sm text-gray-100" data-champ="reponse.verbatim"><Val v={a.reponse?.verbatim} /></p>
          <dl className="space-y-1.5">
            <Ligne label="valeur">
              {/* Un nombre estimé ne se compose JAMAIS comme un nombre mesuré. */}
              <span data-champ="reponse.valeur" className={approx ? 'text-gray-400' : ''}>
                <Val v={a.reponse?.valeur} />{approx && !vide(a.reponse?.valeur) && ' ~'}
              </span>{' '}
              <span data-champ="reponse.unite"><Val v={a.reponse?.unite} /></span>
            </Ligne>
            <Ligne label="sens"><span data-champ="reponse.sens"><Val v={a.reponse?.sens} /></span></Ligne>
          </dl>
        </CardBody>
      </Card>

      {/* ── CE QUI LA FONDE ────────────────────────────────────────── */}
      <Card>
        <CardHeader title="Ce qui la fonde" subtitle="Rang, nature et fraîcheur : trois colonnes, jamais une note unique." />
        <CardBody>
          <dl className="space-y-1.5">
            <Ligne label="rang (dérivé)">
              <span data-champ="fondation.rang_derive"><Val v={a.fondation?.rang_derive} /></span>
              {pr.rang_plus_faible_cite && (
                <span className="text-xs text-gray-500">
                  {' '}← {approx ? 'un cran sous' : 'égal à'} {pr.rang_plus_faible_cite}, la plus faible des {citees.length} pièce(s) citée(s)
                </span>
              )}
            </Ligne>
            <Ligne label="nature"><span data-champ="fondation.nature_effective"><Val v={a.fondation?.nature_effective} /></span></Ligne>
            <Ligne label="fraîcheur">
              <span data-champ="fondation.actualite"><ActualiteBadge actualite={a.fondation?.actualite} />{vide(a.fondation?.actualite) && <Val v={null} />}</span>
              <p className="text-xs text-gray-500 mt-1" data-champ="fondation.motif_actualite"><Val v={a.fondation?.motif_actualite} /></p>
            </Ligne>
            <Ligne label="pièces citées">
              <span className="hidden" data-champ="fondation.cited_entry_ids"><Val v={a.fondation?.cited_entry_ids} /></span>
              {citees.length === 0 ? <Val v={null} /> : <ul className="space-y-1">{citees.map(p => <Piece key={p.entry_id} p={p} />)}</ul>}
            </Ligne>
          </dl>
        </CardBody>
      </Card>

      {/* ── L'APPROXIMATION — les quatre ensemble, ou rien ───────────── */}
      {a.approximation && (
        <Card>
          <CardHeader title="L'approximation" subtitle="Une méthode sans sa sensibilité se lirait comme une mesure." />
          <CardBody>
            <dl className="space-y-1.5">
              <Ligne label="méthode"><span data-champ="approximation.methode">{a.approximation.methode}</span></Ligne>
              <Ligne label="ingrédients">
                <span className="hidden" data-champ="approximation.ingredients_entry_ids"><Val v={a.approximation.ingredients_entry_ids} /></span>
                <ul className="space-y-1">{ingredients.map(p => <Piece key={p.entry_id} p={p} />)}</ul>
              </Ligne>
              <Ligne label="hypothèses">
                <ul className="list-disc ml-4 space-y-0.5" data-champ="approximation.hypotheses_explicites">
                  {a.approximation.hypotheses_explicites.map((h, i) => <li key={i}>{h}</li>)}
                </ul>
              </Ligne>
              <Ligne label="sensibilité"><span data-champ="approximation.sensibilite">{a.approximation.sensibilite}</span></Ligne>
            </dl>
          </CardBody>
        </Card>
      )}

      {/* ── HORS SUJET — un résultat, jamais une case vide ─────────── */}
      {a.sans_objet && (
        <Card>
          <CardHeader title="Sans objet pour cette société" />
          <CardBody>
            <dl className="space-y-1.5">
              <Ligne label="motif"><span data-champ="sans_objet.motif">{a.sans_objet.motif}</span></Ligne>
              <Ligne label="substitut"><span data-champ="sans_objet.substitut_applique"><Val v={a.sans_objet.substitut_applique} /></span></Ligne>
              <Ligne label="réponse substitut"><span data-champ="sans_objet.substitut_answer_id"><Val v={a.sans_objet.substitut_answer_id} /></span></Ligne>
              <Ligne label="aucun substitut"><span data-champ="sans_objet.aucun_substitut"><Val v={a.sans_objet.aucun_substitut} /></span></Ligne>
            </dl>
          </CardBody>
        </Card>
      )}

      {/* ── LE MANQUE ──────────────────────────────────────────────── */}
      {a.gap && (
        <Card>
          <CardHeader title="Ce que l'analyste n'a pas pu fonder" />
          <CardBody>
            <dl className="space-y-1.5">
              <Ligne label="manque"><span data-champ="gap.manque">{a.gap.manque}</span></Ligne>
              <Ligne label="dimension"><span data-champ="gap.dimension">{a.gap.dimension}</span></Ligne>
              <Ligne label="priorité"><span data-champ="gap.priorite">{a.gap.priorite}</span></Ligne>
              <Ligne label="concerne"><span data-champ="gap.champs_cibles"><Val v={a.gap.champs_cibles} /></span></Ligne>
              <Ligne label="couverture"><span data-champ="gap.coverage_actuelle">{a.gap.coverage_actuelle}</span></Ligne>
              <Ligne label="origine"><span data-champ="gap.origine"><Val v={a.gap.origine} /></span></Ligne>
              <Ligne label="remède">
                <span data-champ="gap.remede">
                  {a.gap.remede === 'rafraichissement'
                    ? <Badge variant="sky">rafraîchir (une date postérieure suffit)</Badge>
                    : <Badge variant="amber">collecter (l'information manque)</Badge>}
                </span>
              </Ligne>
              <Ligne label="pistes"><span data-champ="gap.queries_suggerees"><Val v={a.gap.queries_suggerees} /></span></Ligne>
            </dl>
          </CardBody>
        </Card>
      )}

      {/* ── LE CONTRÔLE ────────────────────────────────────────────── */}
      <Card>
        <CardHeader title="Le contrôle de qualité" subtitle="Recalculé à cette lecture, contre le dossier tel qu'il est maintenant." />
        <CardBody>
          {pr.etat_revue === 'non_revalidable' && (
            <p className="text-sm text-gray-400">Personne n'a pu relire cette réponse : la société n'est pas classée, on ne sait pas quelles questions s'appliquent.</p>
          )}
          {pr.etat_revue === 'renvoi_a_emettre' && (
            <div className="space-y-1.5">
              {CONTROLES.map(([k, label]) => (
                <Ligne key={k} label={label}><EtatControle etat={pr.renvoi_a_emettre.controles[k]} /></Ligne>
              ))}
              <p className="text-sm text-red-300">Le contrôle renverrait aujourd'hui cette réponse — le renvoi sera émis au prochain passage.</p>
              <p className="text-xs text-gray-500">{pr.renvoi_a_emettre.motif}</p>
            </div>
          )}
          {/* Les marqueurs du contrôle vivent HORS de toute condition : l'écran les rend même quand
              l'avis manque, pour que la bijection ne dépende pas du dossier affiché. */}
          <dl className={`space-y-1.5 ${a.manager ? '' : 'hidden'}`}>
            <Ligne label="① Complétude"><span data-champ="manager.controles.completude"><EtatControle etat={a.manager?.controles.completude} /></span></Ligne>
            <Ligne label="② Fondation"><span data-champ="manager.controles.fondation"><EtatControle etat={a.manager?.controles.fondation} /></span></Ligne>
            <Ligne label="③ Honnêteté de l'approx."><span data-champ="manager.controles.honnetete_approximation"><EtatControle etat={a.manager?.controles.honnetete_approximation} /></span></Ligne>
            <Ligne label="④ Non-substitution"><span data-champ="manager.controles.non_substitution"><EtatControle etat={a.manager?.controles.non_substitution} /></span></Ligne>
            <Ligne label="verdict">
              <span data-champ="manager.verdict">
                {a.manager?.verdict === 'renvoye'
                  ? <Badge variant="red">⟳ renvoyée</Badge>
                  : <Badge variant="emerald">acquittée</Badge>}
              </span>
            </Ligne>
            <Ligne label="motif"><span data-champ="manager.motif"><Val v={a.manager?.motif} /></span></Ligne>
            <Ligne label="mandat de recherche">
              <span data-champ="manager.mandat_de_recherche_id">
                {a.manager?.mandat_de_recherche_id
                  ? <span className="text-sky-300">mandat #{a.manager.mandat_de_recherche_id} ouvert — la question est repartie en recherche</span>
                  : <Val v={null} />}
              </span>
            </Ligne>
          </dl>
        </CardBody>
      </Card>

      <p className="text-[11px] text-gray-600">
        Réponse #{pr.answer_id} · <span data-champ="ticker_id">{a.ticker_id}</span> ·{' '}
        <span data-champ="framework_id">{a.framework_id}</span> ·{' '}
        <span data-champ="question_id">{a.question_id}</span> · référentiel{' '}
        <span data-champ="framework_version">{a.framework_version}</span> · contrat{' '}
        <span data-champ="schema_version">{a.schema_version}</span>
      </p>
    </div>
  )
}

export default function QuestionNiveau3() {
  const router = useRouter()
  const { ticker_id, framework_id, question_id } = router.query
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    if (!ticker_id || !framework_id || !question_id) return
    setD(null); setErr(null)
    fetch(`${API}/v2/tickers/${ticker_id}/frameworks/${framework_id}/q/${question_id}`)
      .then(r => r.ok ? r.json() : r.json().then(j => Promise.reject(j.detail || `HTTP ${r.status}`)))
      .then(setD)
      .catch(e => setErr(String(e)))
  }, [ticker_id, framework_id, question_id])

  if (err) return <ErrorState detail={err} />
  if (!d) return <p className="text-sm text-gray-500">Recalcul de la preuve…</p>

  return (
    <div className="space-y-5" data-testid="niveau-3">
      <div>
        <Link href={`/v2/tickers/${d.ticker_id}/frameworks/${d.framework_id}`}
              className="text-xs text-gray-500 hover:text-emerald-300">
          ← {d.ticker_id} · {d.libelle_framework}
        </Link>
        <h1 className="text-lg font-bold text-white mt-1">{d.enonce}</h1>
        {d.applicable === false && <Badge variant="gray">ne s'applique pas à cette société</Badge>}
      </div>
      {d.manque && <ManqueBloc m={d.manque} tickerId={d.ticker_id} lien={false} />}
      {d.preuves.length === 0 && <p className="text-sm text-amber-300">Aucune réponse au dossier pour cette question.</p>}
      {d.preuves.map(pr => <Preuve key={pr.answer_id} pr={pr} tickerId={d.ticker_id} />)}
      {/* Le comité agit APRÈS avoir lu la preuve : accepter ou renvoyer, inscrit au procès-verbal. */}
      <RegistreComite key={d.registre.length} d={d} onRecalcule={setD} />
    </div>
  )
}
