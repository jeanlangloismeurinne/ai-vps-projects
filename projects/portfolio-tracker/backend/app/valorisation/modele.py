"""Le PONT et l'ÉVALUATION du modèle de valorisation d'une entreprise (#97).

`ModeleValorisation` (contrat) garantit la cohérence INTERNE de ce que l'agent propose. Ce module
tient ce qui demande le dossier ou l'exécution — un contrat valide un objet, jamais la cohérence entre
deux (#37) :

  [A] une hypothèse `reponse_reprise` cite une réponse ACQUITTÉE de CE titre, à la bonne question, et
      porte la VALEUR et l'UNITÉ de la ligne de son encadré de chiffres clés — sinon le « même chiffre
      que qf_1 » serait un second chiffre (#95). Jusqu'à l'encadré (4 bis), seule la référence se
      vérifiait : une ligne pouvait citer qf_1 et porter un autre taux ;
  [B] toute pièce citée (hypothèse `piece`, taux de base d'un jugement) est au dossier de CE titre ;
  [C] la mécanique s'exécute dans le bac pour chaque scénario et définit un nombre `valeur_action`
      (une hypothèse au nom d'un gabarit du fonds est refusée par le bac lui-même, donc ici) ;
  [D] la mécanique LIT chaque ligne du tableau — une hypothèse signée que le calcul ignore serait une
      ligne de façade, que le comité croirait décisive (#68 [W] transposé : déclarée, pas employée) ;
  [E] la fourchette est ORDONNÉE : un bas au-dessus du central dit que les scénarios sont croisés ;
  [F] UN SEUL CHIFFRE PAR DOSSIER, option (c) de l'utilisateur (2026-09-29, #99) : une ligne qui tient la
      place d'une question d'une autre méthodologie (`question_reprise`) — question que le référentiel
      déclare reprise (`repris_de`) — REPREND sa réponse si elle tient aujourd'hui ; porte son propre
      chiffre (pièce ou jugement ancré) SEULEMENT si la question est sans objet pour ce titre (qf_1 d'une
      biotech sans chiffre d'affaires) ; et sinon le modèle ATTEND : la valorisation s'instruit après
      les méthodologies dont elle reprend (arbitrage du 2026-09-28).

L'évaluation est DÉTERMINISTE et sans appel au modèle : changer une hypothèse recalcule (acceptation
de la 4 bis). Scénarios nommés : trois exécutions, le central sur le tableau tel quel. Arbre
d'événements : le central sur le tableau (la mécanique pondère elle-même par les probabilités),
le bas avec toutes les probabilités à 0, le haut à 1, et pour chaque événement sa valeur en échec et
en succès, les autres à leur probabilité — ce que le comité demande : « que vaut le titre si ce
programme échoue ? ».

Module PUR : aucune IO. Le dossier (réponses acquittées, pièces) est passé par l'appelant.
"""
from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from app.contracts.modele_valorisation_schema import (
    NOM_RESERVE_SEGMENTS, SORTIE_OBLIGATOIRE, ArbreEvenements, Hypothese, ModeleValorisation,
    OrigineJugement, OriginePiece, OrigineReprise, cle_hypothese, question_reprise,
)
from app.valorisation.bac_a_calcul import ErreurCalcul, executer

__all__ = ["ModeleRefuse", "Evaluation", "ReponseReprenable", "valider_pont_modele", "evaluer_modele",
           "hypotheses_pour_le_bac"]


@dataclass(frozen=True)
class ReponseReprenable:
    """Une réponse que la valorisation peut reprendre : sa question, et son ENCADRÉ (id du chiffre →
    (valeur, unité) ; valeur `None` = chiffre que la réponse déclare non établi)."""
    question_id: str
    chiffres: Mapping[str, tuple[Optional[float], str]]


class ModeleRefuse(Exception):
    """Refus du pont. `code` nomme l'invariant ([A]…[E]), `motif` est lisible par l'analyste."""

    def __init__(self, code: str, motif: str) -> None:
        self.code = code
        self.motif = motif
        super().__init__(f"[{code}] {motif}")


@dataclass(frozen=True)
class Evaluation:
    bas: float
    central: float
    haut: float
    # Arbre d'événements seulement : id → (valeur si échec, valeur si succès).
    par_evenement: dict[str, tuple[float, float]] = field(default_factory=dict)
    operations: int = 0


def hypotheses_pour_le_bac(modele: ModeleValorisation, surcharges: Mapping[str, float] | None = None) -> dict[str, Any]:
    """Le tableau mis en forme pour la mécanique : les hypothèses du dossier entier en noms, celles d'un
    segment sous `segments[<id>][<nom>]`. `surcharges` (clé → valeur) porte un scénario."""
    surcharges = surcharges or {}
    globales: dict[str, Any] = {}
    segments: dict[str, dict[str, float]] = {s.id: {} for s in modele.segments}
    for h in modele.hypotheses:
        v = surcharges.get(cle_hypothese(h), h.valeur)
        if h.segment is None:
            globales[h.nom] = v
        else:
            segments[h.segment][h.nom] = v
    return {**globales, NOM_RESERVE_SEGMENTS: segments}


def _executer(modele: ModeleValorisation, surcharges: Mapping[str, float], quoi: str) -> tuple[float, int]:
    try:
        r = executer(modele.mecanique, hypotheses_pour_le_bac(modele, surcharges))
    except ErreurCalcul as e:
        raise ModeleRefuse("C", f"{quoi} : la mécanique ne s'exécute pas — {e}") from None
    v = r.sorties.get(SORTIE_OBLIGATOIRE)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ModeleRefuse("C", f"{quoi} : la mécanique ne définit pas un nombre `{SORTIE_OBLIGATOIRE}` (reçu : {v!r})")
    return float(v), r.operations


def _lectures(modele: ModeleValorisation) -> tuple[set[str], set[str]]:
    """Ce que la mécanique peut lire : les NOMS qu'elle emploie, et les TEXTES littéraux (les clés
    `segments["…"]["…"]`). Lecture de l'arbre, jamais du texte : un nom dans un commentaire ne lit
    rien (#56)."""
    try:
        arbre = ast.parse(modele.mecanique)
    except SyntaxError as e:
        raise ModeleRefuse("C", f"mécanique illisible : {e.msg}") from None
    noms = {n.id for n in ast.walk(arbre) if isinstance(n, ast.Name)}
    textes = {n.value for n in ast.walk(arbre) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return noms, textes


def _pieces_citees(h: Hypothese) -> list[int]:
    o = h.origine
    if isinstance(o, OriginePiece):
        return [r.entry_id for r in o.source_entry_refs]
    if isinstance(o, OrigineJugement):
        return [r.entry_id for r in o.taux_de_base.source_entry_refs]
    return []


def valider_pont_modele(
    modele: ModeleValorisation,
    *,
    ticker_id: str,
    reponses_acquittees: Mapping[int, ReponseReprenable],
    pieces_du_dossier: set[int],
    questions_sans_objet: set[str] | frozenset[str],
    reprises_admises: set[str] | frozenset[str],
) -> Evaluation:
    """Refuse (`ModeleRefuse`) ou rend l'évaluation du modèle. `reponses_acquittees` : answer_id → la
    réponse reprenable (question + encadré) de ce titre, qui TIENT aujourd'hui et n'est pas hors sujet ;
    `pieces_du_dossier` : ids des pièces courantes de ce titre ; `questions_sans_objet` : questions sans
    objet pour ce titre (par son stade, ou par une réponse hors-sujet qui tient) ; `reprises_admises` :
    les questions que le référentiel déclare reprises par la valorisation (`repris_de`)."""
    if modele.ticker_id != ticker_id:
        raise ModeleRefuse("A", f"modèle de `{modele.ticker_id}` présenté pour `{ticker_id}`")
    for h in modele.hypotheses:
        o = h.origine
        if isinstance(o, OrigineReprise):
            rep = reponses_acquittees.get(o.answer_id)
            qid = rep.question_id if rep is not None else None
            if qid != o.question_id:   # une seule comparaison : « absente » est le cas qid = None
                raise ModeleRefuse("A", f"`{cle_hypothese(h)}` reprend la réponse #{o.answer_id}, qui n'est pas "
                                        "une réponse acquittée de ce titre" if qid is None else
                                        f"`{cle_hypothese(h)}` dit reprendre {o.question_id}, mais la réponse "
                                        f"#{o.answer_id} répond à {qid}")
            # Le chiffre se lit dans l'ENCADRÉ, jamais dans la prose : même valeur, même unité.
            if o.chiffre not in rep.chiffres:
                raise ModeleRefuse("A", f"`{cle_hypothese(h)}` reprend `{o.chiffre}` de la réponse #{o.answer_id}, "
                                        f"dont l'encadré ne porte pas ce chiffre ({sorted(rep.chiffres)}) — une "
                                        "réponse d'avant l'encadré se réémet avant d'être reprise")
            valeur, unite = rep.chiffres[o.chiffre]
            if valeur is None:
                raise ModeleRefuse("A", f"`{cle_hypothese(h)}` reprend `{o.chiffre}` de la réponse #{o.answer_id}, "
                                        "qui le déclare non établi : il n'y a pas de chiffre à reprendre")
            if unite != h.unite or not math.isclose(valeur, h.valeur, rel_tol=1e-9, abs_tol=1e-12):
                raise ModeleRefuse("A", f"`{cle_hypothese(h)}` porte {h.valeur:g} {h.unite} en disant reprendre "
                                        f"`{o.chiffre}` de la réponse #{o.answer_id}, qui vaut {valeur:g} {unite} — "
                                        "un seul chiffre par dossier (#95)")
        hors = sorted(set(_pieces_citees(h)) - pieces_du_dossier)
        if hors:
            raise ModeleRefuse("B", f"`{cle_hypothese(h)}` cite des pièces absentes du dossier de ce titre : {hors}")

    tenues = {r.question_id: a for a, r in reponses_acquittees.items()}
    for h in modele.hypotheses:
        q = question_reprise(h)
        if q is None:
            continue
        if q not in reprises_admises:
            raise ModeleRefuse("F", f"`{cle_hypothese(h)}` tient la place de {q}, que le référentiel ne déclare "
                                    "reprise par aucun ingrédient de la valorisation")
        if isinstance(h.origine, OrigineReprise):
            continue   # [A] a vérifié que la réponse reprise tient
        if q in tenues:
            raise ModeleRefuse("F", f"`{cle_hypothese(h)}` porte son propre chiffre alors que {q} a une réponse qui "
                                    f"tient au dossier (#{tenues[q]}) : la ligne doit la reprendre — un seul "
                                    "chiffre par dossier")
        if q not in questions_sans_objet:
            raise ModeleRefuse("F", f"`{cle_hypothese(h)}` tient la place de {q}, qui n'a aucune réponse qui tient "
                                    "aujourd'hui et n'est pas sans objet pour ce titre : la valorisation attend "
                                    f"que {q} soit instruite")

    noms, textes = _lectures(modele)
    ignorees = [cle_hypothese(h) for h in modele.hypotheses
                if (h.segment is None and h.nom not in noms)
                or (h.segment is not None and (h.nom not in textes or NOM_RESERVE_SEGMENTS not in noms))]
    if ignorees:
        raise ModeleRefuse("D", f"lignes du tableau que la mécanique ne lit pas : {ignorees}")

    ev = evaluer_modele(modele)
    if not ev.bas <= ev.central <= ev.haut:
        raise ModeleRefuse("E", f"fourchette non ordonnée : bas {ev.bas:.2f}, central {ev.central:.2f}, "
                                f"haut {ev.haut:.2f} — les scénarios sont croisés")
    return ev


def evaluer_modele(modele: ModeleValorisation) -> Evaluation:
    """Exécute le modèle : trois valeurs par action, et le détail par événement pour un arbre.
    Sans appel au modèle de langage ; `ModeleRefuse` [C] si la mécanique ne tourne pas."""
    f = modele.fourchette
    ops = 0
    if isinstance(f, ArbreEvenements):
        central, n = _executer(modele, {}, "central")
        ops += n
        bas, n = _executer(modele, {e.probabilite: 0.0 for e in f.evenements}, "bas (tous les événements échouent)")
        ops += n
        haut, n = _executer(modele, {e.probabilite: 1.0 for e in f.evenements}, "haut (tous les événements réussissent)")
        ops += n
        detail: dict[str, tuple[float, float]] = {}
        for e in f.evenements:
            echec, n1 = _executer(modele, {e.probabilite: 0.0}, f"`{e.id}` en échec")
            succes, n2 = _executer(modele, {e.probabilite: 1.0}, f"`{e.id}` en succès")
            ops += n1 + n2
            detail[e.id] = (echec, succes)
        return Evaluation(bas=bas, central=central, haut=haut, par_evenement=detail, operations=ops)

    valeurs: dict[str, float] = {}
    for s in f.scenarios:
        valeurs[s.role], n = _executer(modele, s.valeurs, f"scénario {s.role}")
        ops += n
    return Evaluation(bas=valeurs["bas"], central=valeurs["central"], haut=valeurs["haut"], operations=ops)
