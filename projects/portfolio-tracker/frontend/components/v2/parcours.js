/**
 * Le PARCOURS DU COMITÉ — vocabulaire et briques partagés par les trois niveaux de drill-down
 * (chantier V3, lot 6). Les libellés sont MÉTIER : le comité lit « recherche épuisée », jamais
 * `recherche_epuisee`. Les valeurs brutes restent dans les données, jamais dans le texte affiché.
 */
import Link from 'next/link'
import { Badge } from './index'

// Pourquoi le système n'a pas pu obtenir l'information (arbitrage du comité n°3, 2026-09-25).
export const CAUSES = {
  recherche_epuisee: {
    titre: 'Recherche épuisée',
    geste: "La source a été lue : l'information n'y est pas publiée. On décide sans, ou on cherche une autre source.",
    variant: 'amber',
  },
  source_indisponible: {
    titre: 'Source indisponible',
    geste: "La lecture a échoué (panne, temps dépassé). Une relance peut ramener l'information.",
    variant: 'red',
  },
  sans_source_possible: {
    titre: 'Aucune source possible',
    geste: "Cette information n'existe pas pour cette société. C'est la question qu'il faut reformuler.",
    variant: 'gray',
  },
  pieces_insuffisantes: {
    titre: 'Pièces insuffisantes',
    geste: 'Tout ce qui était prévu a été collecté, mais les pièces ne permettent pas de conclure.',
    variant: 'amber',
  },
  pas_encore_cherchee: {
    titre: 'Pas encore cherchée',
    geste: "Aucune collecte n'a encore été lancée sur cette question.",
    variant: 'gray',
  },
  fait_nouveau_publie: {
    titre: 'Fait nouveau publié',
    geste: 'Un événement important publié depuis rend la réponse caduque. Elle reste exacte à sa date : à rafraîchir.',
    variant: 'amber',
  },
  actualite_indeterminable: {
    titre: 'Fraîcheur non vérifiable',
    geste: 'Les pièces ne sont pas datables : on ne peut pas prouver que la réponse est à jour.',
    variant: 'amber',
  },
  controle_ko: {
    titre: 'Refusée au contrôle',
    geste: 'Le contrôle de qualité a refusé la réponse ; la question repart en recherche.',
    variant: 'red',
  },
  renvoi_comite: {
    titre: 'Renvoyée par le comité',
    geste: "Le comité a renvoyé la question en recherche ; aucune nouvelle réponse n'a encore été écrite.",
    variant: 'sky',
  },
  reinitialisation: {
    titre: 'Remise à zéro',
    geste: "La question a été remise à zéro ; elle sera refaite à la prochaine relance de l'analyse.",
    variant: 'sky',
  },
  // #138 — l'analyste juge l'information pas encore advenue : le comité juge la CAUSE.
  pas_encore_observable: {
    titre: 'Pas encore observable',
    geste: "L'analyste juge que l'information n'existe pas encore. Aucune recherche n'est relancée avant la date de revue. Si la cause vous paraît fondée, acceptez la question ; sinon renvoyez-la en recherche.",
    variant: 'violet',
  },
}

const AVEC_FAIT = new Set(['fait_nouveau_publie', 'actualite_indeterminable', 'controle_ko', 'renvoi_comite', 'reinitialisation'])

export const NATURES_MANQUE = {
  sans_reponse: 'Sans réponse',
  non_fondee: 'Non fondée',
  perimee: 'Périmée',
  renvoyee: 'Renvoyée',
  rouverte_comite: 'Rouverte par le comité',
  pas_encore_observable: 'Pas encore observable',
}

export const STATUTS = {
  repondu: { label: 'Répondu', variant: 'emerald' },
  approxime: { label: 'Approximé ~', variant: 'sky' },
  sans_objet: { label: 'Sans objet', variant: 'gray' },
  non_fondable: { label: 'Non fondable', variant: 'amber' },
}

export const ACTUALITE = {
  courante: { label: 'À jour', variant: 'emerald' },
  perimee: { label: 'Périmée', variant: 'amber' },
  indeterminable: { label: 'Non vérifiable', variant: 'amber' },
}

// L'état d'une acceptation du comité, recalculé à chaque lecture (arbitrage n°2 : elle tombe sur un
// fait important publié après elle, jamais sur une information de routine).
export const ETATS_ACCEPTATION = {
  en_vigueur: { label: 'Acceptée par le comité', variant: 'emerald' },
  tombee_fait_nouveau: { label: 'Acceptation tombée — fait nouveau', variant: 'amber' },
  tombee_reponse_remplacee: { label: "Acceptation tombée — l'analyse a été refaite", variant: 'amber' },
  non_verifiable: { label: 'Acceptation non vérifiable', variant: 'amber' },
}

// Le badge du comité sur une ligne de question (niveau 2) : sa dernière décision, servie.
export function ComiteBadge({ pos }) {
  if (!pos) return null
  if (!pos.acceptation) {
    return <Badge variant="sky">{pos.derniere.action === 'reinitialiser' ? 'remise à zéro' : 'renvoyée par le comité'}</Badge>
  }
  const e = ETATS_ACCEPTATION[pos.acceptation.etat] || { label: pos.acceptation.etat, variant: 'gray' }
  return <Badge variant={e.variant}>{e.label}</Badge>
}

export const CONTROLES = [
  ['completude', '① Complétude'],
  ['fondation', '② Fondation'],
  ['honnetete_approximation', "③ Honnêteté de l'approximation"],
  ['non_substitution', '④ Non-substitution'],
]

export const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

export function StatutBadge({ statut }) {
  const s = STATUTS[statut] || { label: statut, variant: 'gray' }
  return <Badge variant={s.variant}>{s.label}</Badge>
}

export function ActualiteBadge({ actualite }) {
  if (!actualite) return null
  const a = ACTUALITE[actualite] || { label: actualite, variant: 'gray' }
  return <Badge variant={a.variant}>{a.label}</Badge>
}

// Un contrôle `sans_objet` s'affiche « — sans objet », JAMAIS « ✓ » : un vert sur un contrôle qui
// n'avait rien à contrôler est la forme la plus rassurante d'un trou (maquette niveau 3, règle 1).
export function EtatControle({ etat }) {
  if (etat === 'ok') return <span className="text-emerald-400">✓ ok</span>
  if (etat === 'ko') return <span className="text-red-400 font-semibold">✗ ko</span>
  return <span className="text-gray-500">— sans objet</span>
}

export function ScoreQualite({ qualite }) {
  if (!qualite) return <span className="text-gray-500">aucune réponse au dossier</span>
  if (qualite.etat !== 'mesure') {
    return <span className="text-gray-400">ce cadre ne s'applique pas à cette société</span>
  }
  const pct = Math.round(qualite.score * 100)
  const couleur = pct >= 80 ? 'text-emerald-300' : pct >= 40 ? 'text-sky-300' : 'text-amber-300'
  return <span className={`text-lg font-bold ${couleur}`}>{pct} %</span>
}

// #138 — la justification d'une attente, ENTIÈRE : le comité juge la cause sur pièce, pas sur un résumé.
export function AttenteBloc({ a }) {
  const date = d => new Date(d).toLocaleDateString('fr-FR')
  return (
    <dl className="text-xs grid grid-cols-[auto,1fr] gap-x-3 gap-y-0.5 rounded border border-violet-900/60 bg-violet-950/20 px-2.5 py-2">
      <dt className="text-gray-500">Cause</dt><dd className="text-gray-200">{a.cause}</dd>
      <dt className="text-gray-500">Fait déclencheur</dt>
      <dd className="text-gray-300">{a.fait_declencheur} — le {date(a.depuis)} (pièce #{a.piece_du_fait})</dd>
      <dt className="text-gray-500">Il faudra</dt><dd className="text-gray-300">{a.historique_requis}</dd>
      <dt className="text-gray-500">Revue</dt><dd className="text-violet-300">le {date(a.revoir_le)}</dd>
    </dl>
  )
}

// Une ligne de l'alerte : ce qui manque, et pourquoi. Le motif du producteur est rendu tel quel.
export function ManqueBloc({ m, tickerId, lien = true }) {
  const c = CAUSES[m.cause] || { titre: m.cause, geste: '', variant: 'gray' }
  const titre = (
    <span className="text-sm font-medium text-gray-100">{m.enonce}</span>
  )
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-950/40 px-3 py-2.5 space-y-1.5">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <p className="text-[11px] text-gray-500 uppercase tracking-wide">
            {m.libelle_framework} · {NATURES_MANQUE[m.nature] || m.nature}
          </p>
          {lien ? (
            <Link href={`/v2/tickers/${tickerId}/frameworks/${m.framework_id}/q/${m.question_id}`}
                  className="hover:underline">{titre}</Link>
          ) : titre}
        </div>
        <Badge variant={c.variant}>{c.titre}</Badge>
      </div>
      <p className="text-xs text-gray-400">{c.geste}</p>
      {/* L'explication n'est affichée que lorsqu'elle porte un FAIT (le motif d'actualité, le
          contrôle refusé) ; pour une cause de collecte elle répète la phrase de la cause, et la
          preuve est la liste des ingrédients ci-dessous (mesuré à la capture du 2026-09-25). */}
      {AVEC_FAIT.has(m.cause) && <p className="text-xs text-gray-500">{m.explication}</p>}
      {m.attente && <AttenteBloc a={m.attente} />}
      {/* La question REPASSE devant le comité : il l'avait acceptée, et l'alerte dit pourquoi
          l'acceptation ne tient plus (arbitrage n°2). */}
      {m.acceptation_tombee && (
        <p className="text-xs text-amber-300">
          Le comité l'avait acceptée ({m.acceptation_tombee.decision.auteur}, le{' '}
          {new Date(m.acceptation_tombee.decision.decide_le).toLocaleDateString('fr-FR')}) — elle
          repasse devant lui : {m.acceptation_tombee.motif_etat}
        </p>
      )}
      {m.ingredients.length > 0 && (
        <ul className="space-y-1 pt-1">
          {m.ingredients.map(i => (
            <li key={i.ingredient_id} className="text-xs text-gray-500 flex gap-2">
              <Badge variant={(CAUSES[i.cause] || {}).variant || 'gray'} className="shrink-0">
                {(CAUSES[i.cause] || {}).titre || i.cause}
              </Badge>
              {/* Le motif du producteur est rendu tel quel, mais une trace technique de 20 lignes
                  noyait l'alerte : 2 lignes visibles, le texte entier au survol. */}
              <span className="line-clamp-2" title={i.motif}>
                <span className="text-gray-300">{i.ingredient_id.replaceAll('_', ' ')}</span>
                {' — '}{i.motif}
              </span>
            </li>
          ))}
        </ul>
      )}
      {m.mandat_ouvert_id && (
        <p className="text-xs text-sky-300">Déjà repartie en recherche (mandat #{m.mandat_ouvert_id}).</p>
      )}
    </div>
  )
}
