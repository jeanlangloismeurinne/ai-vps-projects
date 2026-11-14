"""L'automate du chef de dossier : état du dossier → pas suivant.

Il ne contient AUCUN modèle de langage et n'appelle aucun réseau : il lit l'état, lance le premier
pas dont les préalables sont faits, compte ce qui est dépensé, et s'arrête — quand plus rien ne peut
avancer — dans cinq cas, toujours en le disant :

  1. un ACTE VOUS REVIENT (pas humain déclaré, lecture d'une sortie de module tant que son taux
     d'erreur n'est pas mesuré, ou acte demandé par un pas en cours de route) ;
  2. un PALIER DE DÉPENSE est franchi (1 $ par défaut) : pause, avec le coût restant estimé ;
  3. un pas ÉCHOUE DEUX FOIS de suite : on n'insiste pas, on nomme le pas et le motif ;
  4. le PARCOURS EST TERMINÉ ;
  5. un TRAVAIL EST EN COURS (une collecte lancée) et tout ce qui reste en dépend : le dossier attend,
     sans limite de temps, et reprend seul au passage suivant (arbitrage du 2026-11-14).

On parallélise ce qui peut l'être : un pas en cours, un acte attendu ou un échec répété ne retient que
les pas qui en dépendent. L'arrêt énumère tout ce qui est attendu. Un acte se fait par
`enregistrer_acte`, une pause se lève par `lever_pause`, un échec répété par `relancer`.

Limite connue, dite : un pas ne s'interrompt pas en cours d'exécution. La pause tombe donc APRÈS le
pas qui franchit le palier — le dépassement maximal est le coût d'un pas.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Sequence

from .contrat import (
    ACTE_HUMAIN,
    ARRET_ACTE_HUMAIN,
    ARRET_ATTENTE,
    ARRET_ECHEC_REPETE,
    ARRET_PARCOURS_TERMINE,
    ARRET_PAUSE_DEPENSE,
    ECHEC,
    EN_COURS,
    FAIT,
    HUMAIN,
    INDISPONIBLE,
    Arret,
    Attente,
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


def _appeler(fn, contexte: Contexte) -> Resultat:
    """Un pas qui plante n'emporte pas le dossier : c'est un échec, motivé par ce qu'il a levé."""
    try:
        rendu = fn(contexte)
    except Exception as exc:  # noqa: BLE001 — tout plantage d'un pas est un échec nommé
        return Resultat(issue=ECHEC, motif=f"le pas a planté : {type(exc).__name__}: {exc}")
    if not isinstance(rendu, Resultat):
        return Resultat(issue=ECHEC, motif=f"le pas n'a pas rendu un résultat ({type(rendu).__name__})")
    return rendu


def _sans(paires: tuple, nom: str) -> tuple:
    return tuple(x for x in paires if x[0] != nom)


def _appliquer(etat: EtatDossier, pas: Pas, rendu: Resultat, *, suivi: bool) -> EtatDossier:
    """Range ce qu'un pas a rendu — à son lancement (`suivi=False`) ou quand on suit le travail
    qu'il a lancé (`suivi=True`)."""
    if rendu.issue == EN_COURS and pas.suivre is None:
        rendu = Resultat(issue=ECHEC, depense=rendu.depense,
                         motif="le pas rend « en cours » sans dire comment le suivre : il ne serait jamais attendu")
    etat = _ajouter_depense(etat, pas.nom, rendu.depense)
    deja_en_cours = any(n == pas.nom for n, _ in etat.en_cours)
    if rendu.issue == EN_COURS:
        if suivi and deja_en_cours and rendu.depense.total_usd == 0:
            return etat  # toujours en cours, rien de neuf : pas une ligne de journal par passage
        etat = _journal(etat, pas.nom, EN_COURS, rendu.depense, rendu.motif)
        en_cours = _sans(etat.en_cours, pas.nom) + ((pas.nom, rendu.motif),)
        # Le compteur d'échecs n'est PAS remis à zéro : un lancement réussi n'est pas un travail
        # abouti ; une collecte qui échoue deux fois en route doit arrêter le dossier.
        return replace(etat, en_cours=en_cours)

    etat = _journal(etat, pas.nom, rendu.issue, rendu.depense, rendu.motif)
    etat = replace(etat, en_cours=_sans(etat.en_cours, pas.nom))
    if rendu.issue in (FAIT, INDISPONIBLE):
        reserves = etat.reserves + (((pas.nom, rendu.motif),) if rendu.issue == INDISPONIBLE else ())
        return replace(etat, faits=etat.faits + (pas.nom,), echecs=_sans(etat.echecs, pas.nom),
                       reserves=reserves)
    if rendu.issue == ACTE_HUMAIN:
        deja = sum(1 for a in etat.actes_accomplis if a.startswith(f"acte:{pas.nom}:"))
        demande = (pas.nom, f"acte:{pas.nom}:{deja + 1}", rendu.acte)
        return replace(etat, demandes=etat.demandes + (demande,))
    compte = dict(etat.echecs).get(pas.nom, 0) + 1   # ECHEC (au lancement ou en cours de route)
    return replace(etat, echecs=_sans(etat.echecs, pas.nom) + ((pas.nom, compte),))


def _dernier_motif(etat: EtatDossier, pas: str) -> str:
    for ligne in reversed(etat.journal):
        if ligne.pas == pas and ligne.evenement == ECHEC:
            return ligne.detail
    return ""


def _attentes(etat: EtatDossier, parcours: Sequence[Pas],
              lecture_humaine: Mapping[str, bool] | None) -> tuple[Attente, ...]:
    """Tout ce que le dossier attend, dans l'ordre du parcours : vos actes d'abord (lectures, actes
    déclarés, actes demandés en cours de route), puis les relances, puis les travaux en cours."""
    faits = set(etat.faits)
    actes, echecs, travaux = [], [], []
    en_cours = dict(etat.en_cours)
    demandes = {p: (c, a) for p, c, a in etat.demandes}
    for p in parcours:
        if p.nom in faits:
            if _lecture_requise(p, lecture_humaine) and _cle_lecture(p.nom) not in etat.actes_accomplis:
                actes.append(Attente(ARRET_ACTE_HUMAIN, p.nom, _cle_lecture(p.nom),
                                     f"relire la sortie du module « {p.module} » (pas « {p.nom} »)"))
            continue
        if p.nom in demandes:
            cle, acte = demandes[p.nom]
            actes.append(Attente(ARRET_ACTE_HUMAIN, p.nom, cle, acte))
        elif p.nom in en_cours:
            travaux.append(Attente(ARRET_ATTENTE, p.nom, detail=en_cours[p.nom]))
        elif dict(etat.echecs).get(p.nom, 0) >= ECHECS_AVANT_ARRET:
            echecs.append(Attente(ARRET_ECHEC_REPETE, p.nom, f"relance:{p.nom}",
                                  detail=_dernier_motif(etat, p.nom)))
        elif p.nature == HUMAIN and _disponibles(etat, parcours, lecture_humaine, p.apres):
            actes.append(Attente(ARRET_ACTE_HUMAIN, p.nom, p.nom, p.acte))
    return tuple(actes + echecs + travaux)


def _disponibles(etat: EtatDossier, parcours: Sequence[Pas], lecture_humaine: Mapping[str, bool] | None,
                 noms: Sequence[str]) -> bool:
    """Ces pas sont faits ET leur sortie est lue (ou n'a pas à l'être) : on peut s'appuyer dessus."""
    par_nom = {p.nom: p for p in parcours}
    return all(n in etat.faits and (not _lecture_requise(par_nom[n], lecture_humaine)
                                    or _cle_lecture(n) in etat.actes_accomplis) for n in noms)


def _arret(etat: EtatDossier, parcours: Sequence[Pas], motif: str, attentes: tuple[Attente, ...],
           detail: str = "") -> Arret:
    principale = next((a for a in attentes if a.motif == motif), None)
    return Arret(motif=motif, pas=principale.pas if principale else "",
                 cle=principale.cle if principale else ("pause" if motif == ARRET_PAUSE_DEPENSE else ""),
                 acte=principale.acte if principale else "",
                 detail=detail or (principale.detail if principale else ""),
                 depense_totale_usd=etat.depense.total_usd,
                 cout_restant_estime_usd=cout_restant_estime(etat, parcours),
                 ratio_constate=ratio_constate(etat, parcours), attentes=attentes)


def avancer(etat: EtatDossier, parcours: Sequence[Pas], *, palier_usd: float = PALIER_USD,
            lecture_humaine: Mapping[str, bool] | None = None) -> EtatDossier:
    """Conduit le dossier aussi loin qu'il peut aller seul, et rend l'état à l'arrêt.

    On parallélise ce qui peut l'être (arbitrage du 2026-11-14) : un pas en cours, un acte qui vous
    revient ou un échec répété ne retient QUE les pas qui en dépendent ; le reste avance. On ne
    s'arrête que lorsque plus rien ne peut avancer, et l'arrêt dit tout ce qui est attendu.

    Une pause de dépense et un parcours terminé ne se lèvent que par un geste : sur eux, rien ne se
    fait. Les autres arrêts se recalculent à chaque passage (un travail en cours a pu aboutir) ; si
    rien n'a bougé, l'état rendu est exactement celui reçu."""
    verifier_parcours(parcours)
    if palier_usd <= 0:
        raise ValueError("le palier de dépense est strictement positif")
    if etat.arret is not None and etat.arret.motif in (ARRET_PAUSE_DEPENSE, ARRET_PARCOURS_TERMINE):
        return etat
    recu = etat
    etat = replace(etat, arret=None)
    par_nom = {p.nom: p for p in parcours}

    # 1. Les travaux en cours : on demande où ils en sont, une fois par passage.
    for nom, _ in list(etat.en_cours):
        pas = par_nom[nom]
        etat = _appliquer(etat, pas, _appeler(pas.suivre, _contexte(etat)), suivi=True)

    for _ in range(len(parcours) * (ECHECS_AVANT_ARRET + 3) + 1):
        en_cours = {n for n, _ in etat.en_cours}
        demandes = {p for p, _, _ in etat.demandes}
        echecs = dict(etat.echecs)
        prets = [p for p in parcours
                 if p.nom not in etat.faits and p.nom not in en_cours and p.nom not in demandes
                 and echecs.get(p.nom, 0) < ECHECS_AVANT_ARRET
                 and _disponibles(etat, parcours, lecture_humaine, p.apres)]
        humain = next((p for p in prets if p.nature == HUMAIN and p.nom in etat.actes_accomplis), None)
        if humain is not None:
            etat = _journal(replace(etat, faits=etat.faits + (humain.nom,)), humain.nom, "acte_enregistre")
            continue
        a_lancer = [p for p in prets if p.nature != HUMAIN]
        if not a_lancer:
            break
        # 2. Le palier de dépense : avant de lancer quoi que ce soit de plus.
        if etat.depense.total_usd - etat.depense_acquittee_usd >= palier_usd - _EPS:
            arret = _arret(etat, parcours, ARRET_PAUSE_DEPENSE, _attentes(etat, parcours, lecture_humaine),
                           detail=f"{etat.depense.total_usd:.2f} $ consommés sur ce dossier")
            return replace(_journal(etat, "", f"arret:{ARRET_PAUSE_DEPENSE}", detail=arret.detail), arret=arret)
        # 3. Le premier pas prêt, dans l'ordre déclaré.
        pas = a_lancer[0]
        etat = _appliquer(etat, pas, _appeler(pas.executer, _contexte(etat)), suivi=False)
    else:
        # Inatteignable si le parcours est valide ; si on y arrive, on le dit au lieu de tourner.
        raise RuntimeError("le chef de dossier n'a pas convergé : parcours ou pas incohérent")

    attentes = _attentes(etat, parcours, lecture_humaine)
    if not attentes and len(etat.faits) == len(parcours):
        motif = ARRET_PARCOURS_TERMINE
    elif not attentes:
        raise RuntimeError("le chef de dossier n'a plus rien à lancer ni à attendre, et le parcours n'est pas fini")
    else:
        motif = next(m for m in (ARRET_ACTE_HUMAIN, ARRET_ECHEC_REPETE, ARRET_ATTENTE)
                     if any(a.motif == m for a in attentes))
    arret = _arret(etat, parcours, motif, attentes)
    if etat == replace(recu, arret=None) and arret == recu.arret:
        return recu  # rien n'a bougé : même état, pas une ligne de journal de plus
    principale = arret.acte or arret.detail
    return replace(_journal(etat, arret.pas, f"arret:{motif}", detail=principale), arret=arret)


def _contexte(etat: EtatDossier) -> Contexte:
    return Contexte(dossier=etat.dossier, actes_accomplis=etat.actes_accomplis)


def _apres_geste(etat: EtatDossier, attente: Attente) -> Arret | None:
    """Après un geste : une pause reste une pause (elle ne se lève que par `lever_pause`), sans
    l'attente qu'on vient de satisfaire ; tout autre arrêt se recalculera au passage suivant."""
    a = etat.arret
    if a is not None and a.motif == ARRET_PAUSE_DEPENSE:
        return replace(a, attentes=tuple(x for x in a.attentes if x != attente))
    return None


def _attente(etat: EtatDossier, motif: str, vise, nom: str) -> Attente:
    """L'attente de l'arrêt en cours que ce geste satisfait, ou un refus qui dit ce qui est attendu."""
    a = etat.arret
    if a is None:
        raise GesteRefuse("le dossier n'est pas arrêté : rien n'est attendu de vous")
    possibles = [x for x in a.attentes if x.motif == motif]
    if not possibles:
        raise GesteRefuse({ARRET_ACTE_HUMAIN: "aucun acte n'est attendu sur ce dossier",
                           ARRET_ECHEC_REPETE: "aucun échec répété n'arrête ce dossier"}[motif])
    for x in possibles:
        if vise(x):
            return x
    raise GesteRefuse(f"« {nom} » n'est pas attendu ; attendu : {', '.join(x.cle for x in possibles)}")


def enregistrer_acte(etat: EtatDossier, cle: str) -> EtatDossier:
    """Vous avez accompli l'un des actes attendus : il est enregistré. On n'enregistre qu'un acte
    EFFECTIVEMENT attendu à cet arrêt — jamais un acte d'avance, jamais un autre."""
    x = _attente(etat, ARRET_ACTE_HUMAIN, lambda a: a.cle == cle, cle)
    etat = replace(etat, actes_accomplis=etat.actes_accomplis + (x.cle,),
                   demandes=tuple(d for d in etat.demandes if d[1] != x.cle), arret=_apres_geste(etat, x))
    return _journal(etat, x.pas, "acte_accompli", detail=x.acte)


def lever_pause(etat: EtatDossier) -> EtatDossier:
    """Vous avez vu la dépense et le coût restant : le dossier peut consommer un palier de plus."""
    a = etat.arret
    if a is None or a.motif != ARRET_PAUSE_DEPENSE:
        raise GesteRefuse("ce dossier n'est pas en pause de dépense")
    etat = replace(etat, depense_acquittee_usd=etat.depense.total_usd, arret=None)
    return _journal(etat, "", "pause_levee", detail=f"{etat.depense.total_usd:.2f} $ acquittés")


def relancer(etat: EtatDossier, pas: str | None = None) -> EtatDossier:
    """Après un échec répété : vous décidez de réessayer (le premier pas en échec, ou celui nommé).
    Son compteur repart de zéro."""
    x = _attente(etat, ARRET_ECHEC_REPETE, lambda a: pas is None or a.pas == pas, pas or "")
    etat = replace(etat, echecs=_sans(etat.echecs, x.pas), arret=_apres_geste(etat, x))
    return _journal(etat, x.pas, "relance_decidee")


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
            ARRET_ATTENTE: f"attend la fin d'un travail en cours : {a.pas} ({a.detail})",
        }
        lignes.append("  " + libelles[a.motif])
        for x in a.attentes:
            if x.pas == a.pas and x.motif == a.motif:
                continue
            quoi = {ARRET_ACTE_HUMAIN: f"acte de votre part : {x.acte}",
                    ARRET_ECHEC_REPETE: f"le pas « {x.pas} » a échoué deux fois ({x.detail})",
                    ARRET_ATTENTE: f"travail en cours : {x.pas} ({x.detail})"}[x.motif]
            lignes.append(f"  attend aussi — {quoi}")
        ratio = "" if a.ratio_constate is None else f" (dépensé / estimé jusqu'ici : {a.ratio_constate:.2f})"
        lignes.append(f"  coût restant estimé : {a.cout_restant_estime_usd:.2f} ${ratio}")
    return "\n".join(lignes)
