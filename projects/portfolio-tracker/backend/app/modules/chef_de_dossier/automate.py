"""L'automate du chef de dossier : état du dossier → pas suivant.

Il ne contient AUCUN modèle de langage et n'appelle aucun réseau : il lit l'état, lance le premier
pas dont les préalables sont faits, compte ce qui est dépensé, et s'arrête dans quatre cas, toujours
en le disant :

  1. un ACTE VOUS REVIENT (pas humain déclaré, lecture d'une sortie de module tant que son taux
     d'erreur n'est pas mesuré, ou acte demandé par un pas en cours de route) ;
  2. un PALIER DE DÉPENSE est franchi (1 $ par défaut) : pause, avec le coût restant estimé ;
  3. un pas ÉCHOUE DEUX FOIS de suite : on n'insiste pas, on nomme le pas et le motif ;
  4. le PARCOURS EST TERMINÉ.

Un arrêt ne se lève jamais tout seul : `enregistrer_acte`, `lever_pause` ou `relancer`.

Limite connue, dite : un pas ne s'interrompt pas en cours d'exécution. La pause tombe donc APRÈS le
pas qui franchit le palier — le dépassement maximal est le coût d'un pas.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Sequence

from .contrat import (
    ACTE_HUMAIN,
    ARRET_ACTE_HUMAIN,
    ARRET_ECHEC_REPETE,
    ARRET_PARCOURS_TERMINE,
    ARRET_PAUSE_DEPENSE,
    ECHEC,
    FAIT,
    HUMAIN,
    INDISPONIBLE,
    Arret,
    Contexte,
    Depense,
    Depot,
    EtatDossier,
    LigneJournal,
    Pas,
    Resultat,
    lire_etat,
)

PALIER_USD = 1.0          # arbitrage du 2026-11-13 : une pause tous les 1 $ consommés sur un dossier
ECHECS_AVANT_ARRET = 2    # « arrêt au premier refus répété »
_EPS = 1e-9


class ParcoursInvalide(ValueError):
    """Le parcours déclaré ne peut pas être conduit (doublon, préalable inconnu, boucle)."""


class GesteRefuse(ValueError):
    """Le geste demandé ne correspond pas à l'arrêt en cours."""


def verifier_parcours(parcours: Sequence[Pas]) -> None:
    """Refuse AVANT toute exécution un parcours qui ne peut pas aboutir — jamais un dossier bloqué
    en silence au milieu."""
    if not parcours:
        raise ParcoursInvalide("parcours vide : aucun pas déclaré")
    noms = [p.nom for p in parcours]
    doublons = sorted({n for n in noms if noms.count(n) > 1})
    if doublons:
        raise ParcoursInvalide(f"pas déclarés deux fois : {', '.join(doublons)}")
    connus = set(noms)
    for p in parcours:
        inconnus = [a for a in p.apres if a not in connus]
        if inconnus:
            raise ParcoursInvalide(f"le pas « {p.nom} » attend un pas inconnu : {', '.join(inconnus)}")
    faits: set[str] = set()
    restants = list(parcours)
    while restants:
        prets = [p for p in restants if all(a in faits for a in p.apres)]
        if not prets:
            raise ParcoursInvalide(
                "boucle entre les pas : " + ", ".join(sorted(p.nom for p in restants)))
        faits.update(p.nom for p in prets)
        restants = [p for p in restants if p.nom not in faits]


def _cle_lecture(pas: str) -> str:
    return f"lecture:{pas}"


def _journal(etat: EtatDossier, pas: str, evenement: str, depense: Depense | None = None,
             detail: str = "") -> EtatDossier:
    d = depense or Depense()
    ligne = LigneJournal(rang=len(etat.journal) + 1, pas=pas, evenement=evenement,
                         modeles_usd=d.modeles_usd, web_usd=d.web_usd, detail=detail)
    return replace(etat, journal=etat.journal + (ligne,))


def cout_restant_estime(etat: EtatDossier, parcours: Sequence[Pas]) -> float:
    return round(sum(p.cout_estime_usd for p in parcours if p.nom not in etat.faits), 6)


def ratio_constate(etat: EtatDossier, parcours: Sequence[Pas]) -> float | None:
    """Dépensé / estimé, sur les pas faits qui portaient une estimation. None tant qu'il n'y a rien
    à comparer — un ratio sur zéro ne se fabrique pas."""
    estime = {p.nom: p.cout_estime_usd for p in parcours}
    depense = dict(etat.depense_par_pas)
    base = sum(estime[n] for n in etat.faits if estime.get(n, 0.0) > 0)
    if base <= 0:
        return None
    reel = sum(depense.get(n, 0.0) for n in etat.faits if estime.get(n, 0.0) > 0)
    return round(reel / base, 4)


def _arreter(etat: EtatDossier, parcours: Sequence[Pas], motif: str, *, pas: str = "", cle: str = "",
             acte: str = "", detail: str = "") -> EtatDossier:
    arret = Arret(motif=motif, pas=pas, cle=cle, acte=acte, detail=detail,
                  depense_totale_usd=etat.depense.total_usd,
                  cout_restant_estime_usd=cout_restant_estime(etat, parcours),
                  ratio_constate=ratio_constate(etat, parcours))
    return replace(_journal(etat, pas, f"arret:{motif}", detail=acte or detail), arret=arret)


def _lecture_requise(pas: Pas, lecture_humaine: Mapping[str, bool] | None) -> bool:
    """La lecture humaine de la sortie d'un module est la règle simple ; s'en passer est le
    raffinement (principe 3). Donc : requise SAUF si l'interrupteur du module est explicitement
    levé. Un module absent de la table est lu."""
    if pas.nature == HUMAIN:
        return False
    return True if lecture_humaine is None else bool(lecture_humaine.get(pas.module, True))


def _ajouter_depense(etat: EtatDossier, pas: str, d: Depense) -> EtatDossier:
    par_pas = dict(etat.depense_par_pas)
    par_pas[pas] = round(par_pas.get(pas, 0.0) + d.total_usd, 6)
    return replace(etat, depense=etat.depense.plus(d), depense_par_pas=tuple(par_pas.items()))


def _executer(pas: Pas, contexte: Contexte) -> Resultat:
    """Un pas qui plante n'emporte pas le dossier : c'est un échec, motivé par ce qu'il a levé."""
    try:
        rendu = pas.executer(contexte)  # type: ignore[misc]
    except Exception as exc:  # noqa: BLE001 — tout plantage d'un pas est un échec nommé
        return Resultat(issue=ECHEC, motif=f"le pas a planté : {type(exc).__name__}: {exc}")
    if not isinstance(rendu, Resultat):
        return Resultat(issue=ECHEC, motif=f"le pas n'a pas rendu un résultat ({type(rendu).__name__})")
    return rendu


def avancer(etat: EtatDossier, parcours: Sequence[Pas], *, palier_usd: float = PALIER_USD,
            lecture_humaine: Mapping[str, bool] | None = None) -> EtatDossier:
    """Conduit le dossier aussi loin qu'il peut aller seul, et rend l'état à l'arrêt.

    Sur un dossier déjà arrêté, ne fait rien : un arrêt se lève par un geste explicite."""
    verifier_parcours(parcours)
    if palier_usd <= 0:
        raise ValueError("le palier de dépense est strictement positif")
    if etat.arret is not None:
        return etat

    for _ in range(len(parcours) * (ECHECS_AVANT_ARRET + 2) + 1):
        faits = set(etat.faits)

        # 1. Une sortie de module attend d'être lue : rien ne s'appuie dessus avant.
        for p in parcours:
            if p.nom in faits and _lecture_requise(p, lecture_humaine) \
                    and _cle_lecture(p.nom) not in etat.actes_accomplis:
                return _arreter(etat, parcours, ARRET_ACTE_HUMAIN, pas=p.nom, cle=_cle_lecture(p.nom),
                                acte=f"relire la sortie du module « {p.module} » (pas « {p.nom} »)")

        restants = [p for p in parcours if p.nom not in faits]
        if not restants:
            return _arreter(etat, parcours, ARRET_PARCOURS_TERMINE)

        # 2. Le palier de dépense : avant de lancer quoi que ce soit de plus.
        if etat.depense.total_usd - etat.depense_acquittee_usd >= palier_usd - _EPS:
            return _arreter(etat, parcours, ARRET_PAUSE_DEPENSE, cle="pause",
                            detail=f"{etat.depense.total_usd:.2f} $ consommés sur ce dossier")

        # 3. Le pas suivant : le premier, dans l'ordre déclaré, dont les préalables sont faits.
        pas = next(p for p in restants if all(a in faits for a in p.apres))

        if pas.nature == HUMAIN:
            if pas.nom in etat.actes_accomplis:
                etat = _journal(replace(etat, faits=etat.faits + (pas.nom,)), pas.nom, "acte_enregistre")
                continue
            return _arreter(etat, parcours, ARRET_ACTE_HUMAIN, pas=pas.nom, cle=pas.nom, acte=pas.acte)

        rendu = _executer(pas, Contexte(dossier=etat.dossier, actes_accomplis=etat.actes_accomplis))
        etat = _ajouter_depense(etat, pas.nom, rendu.depense)
        etat = _journal(etat, pas.nom, rendu.issue, rendu.depense, rendu.motif)

        if rendu.issue in (FAIT, INDISPONIBLE):
            echecs = tuple((n, c) for n, c in etat.echecs if n != pas.nom)
            reserves = etat.reserves + (((pas.nom, rendu.motif),) if rendu.issue == INDISPONIBLE else ())
            etat = replace(etat, faits=etat.faits + (pas.nom,), echecs=echecs, reserves=reserves)
        elif rendu.issue == ACTE_HUMAIN:
            deja = sum(1 for a in etat.actes_accomplis if a.startswith(f"acte:{pas.nom}:"))
            return _arreter(etat, parcours, ARRET_ACTE_HUMAIN, pas=pas.nom,
                            cle=f"acte:{pas.nom}:{deja + 1}", acte=rendu.acte, detail=rendu.motif)
        else:  # ECHEC
            compte = dict(etat.echecs).get(pas.nom, 0) + 1
            etat = replace(etat, echecs=tuple(
                [(n, c) for n, c in etat.echecs if n != pas.nom] + [(pas.nom, compte)]))
            if compte >= ECHECS_AVANT_ARRET:
                return _arreter(etat, parcours, ARRET_ECHEC_REPETE, pas=pas.nom, cle=f"relance:{pas.nom}",
                                detail=rendu.motif)

    # Inatteignable si le parcours est valide ; si on y arrive, on le dit au lieu de tourner.
    raise RuntimeError("le chef de dossier n'a pas convergé : parcours ou pas incohérent")


def enregistrer_acte(etat: EtatDossier, cle: str) -> EtatDossier:
    """Vous avez accompli l'acte attendu : l'arrêt est levé. On n'enregistre que l'acte
    EFFECTIVEMENT attendu — jamais un acte d'avance, jamais un autre."""
    a = etat.arret
    if a is None or a.motif != ARRET_ACTE_HUMAIN:
        raise GesteRefuse("aucun acte n'est attendu sur ce dossier")
    if cle != a.cle:
        raise GesteRefuse(f"l'acte attendu est « {a.cle} », pas « {cle} »")
    etat = replace(etat, actes_accomplis=etat.actes_accomplis + (cle,), arret=None)
    return _journal(etat, a.pas, "acte_accompli", detail=a.acte)


def lever_pause(etat: EtatDossier) -> EtatDossier:
    """Vous avez vu la dépense et le coût restant : le dossier peut consommer un palier de plus."""
    a = etat.arret
    if a is None or a.motif != ARRET_PAUSE_DEPENSE:
        raise GesteRefuse("ce dossier n'est pas en pause de dépense")
    etat = replace(etat, depense_acquittee_usd=etat.depense.total_usd, arret=None)
    return _journal(etat, "", "pause_levee", detail=f"{etat.depense.total_usd:.2f} $ acquittés")


def relancer(etat: EtatDossier) -> EtatDossier:
    """Après un échec répété : vous décidez de réessayer. Le compteur du pas repart de zéro."""
    a = etat.arret
    if a is None or a.motif != ARRET_ECHEC_REPETE:
        raise GesteRefuse("aucun échec répété n'arrête ce dossier")
    etat = replace(etat, echecs=tuple((n, c) for n, c in etat.echecs if n != a.pas), arret=None)
    return _journal(etat, a.pas, "relance_decidee")


def conduire(depot: Depot, dossier: str, parcours: Sequence[Pas], *, palier_usd: float = PALIER_USD,
             lecture_humaine: Mapping[str, bool] | None = None) -> EtatDossier:
    """Lit l'état rangé, avance, range. C'est le seul geste qu'une tâche planifiée aura à faire."""
    etat = avancer(lire_etat(depot, dossier), parcours, palier_usd=palier_usd,
                   lecture_humaine=lecture_humaine)
    depot.ranger(dossier, etat.vers_dict())
    return etat


def afficher(etat: EtatDossier) -> str:
    """L'état d'un dossier en clair — ce que l'écran montrera, lisible dès maintenant en texte."""
    lignes = [f"Dossier {etat.dossier} — {len(etat.faits)} pas faits — "
              f"{etat.depense.total_usd:.2f} $ consommés "
              f"(modèles {etat.depense.modeles_usd:.2f} $, web {etat.depense.web_usd:.2f} $)"]
    for pas, motif in etat.reserves:
        lignes.append(f"  réserve — {pas} : {motif}")
    a = etat.arret
    if a is None:
        lignes.append("  en cours")
    else:
        libelles = {
            ARRET_ACTE_HUMAIN: f"attend un acte de votre part : {a.acte}",
            ARRET_PAUSE_DEPENSE: f"en pause de dépense ({a.detail})",
            ARRET_ECHEC_REPETE: f"arrêté : le pas « {a.pas} » a échoué deux fois ({a.detail})",
            ARRET_PARCOURS_TERMINE: "parcours terminé",
        }
        lignes.append("  " + libelles[a.motif])
        ratio = "" if a.ratio_constate is None else f" (dépensé / estimé jusqu'ici : {a.ratio_constate:.2f})"
        lignes.append(f"  coût restant estimé : {a.cout_restant_estime_usd:.2f} ${ratio}")
    return "\n".join(lignes)
