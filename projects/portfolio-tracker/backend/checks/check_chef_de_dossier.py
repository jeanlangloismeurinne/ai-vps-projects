"""Le chef de dossier conduit une société FICTIVE à travers des modules SIMULÉS — zéro dépense,
aucune base, aucun réseau, aucun modèle. C'est l'acceptation du squelette (module M0) :

  « le chef de dossier conduit une société fictive à travers des modules simulés et s'arrête à 1 $ »

Les coûts ci-dessous sont des nombres inventés portés par des pas simulés : ils éprouvent le
compteur, pas un prix. Chaque section nomme ce qu'elle garde ; `negatif_chef_de_dossier.sh` prouve
que chacune vire au rouge quand on casse la règle.

  [D1] un parcours qui ne peut pas aboutir est refusé avant toute exécution
  [D2] de « titre entré » au dernier pas sans commande manuelle, arrêt EXACTEMENT aux actes déclarés
  [D3] pause à chaque palier de 1 $, avec le coût restant estimé ; rien ne se lance en pause
  [D4] échec répété : arrêt nommé ; un plantage n'emporte pas le dossier
  [D5] « source indisponible » nommée : le dossier continue, la réserve reste
  [D6] lecture humaine de chaque sortie de module, levée module par module (prudent par défaut)
  [D7] l'état se range et se relit ; un passage interrompu puis repris rend le même état
  [D8] modèles et web comptés à part ; aucun pas exécuté deux fois sans raison
  [D9] un arrêt ne se lève que par le geste qui lui correspond
  [D10] l'automate n'importe que la bibliothèque standard et son propre contrat
"""
from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.modules.chef_de_dossier import automate as A  # noqa: E402
from app.modules.chef_de_dossier import contrat as C  # noqa: E402

DOSSIER = "SOCIETE-FICTIVE"   # identifiant maison ; aucune référence externe


class Simulateur:
    """Des modules simulés : chaque pas rend ce qu'on lui a scénarisé et compte ses appels."""

    def __init__(self) -> None:
        self.appels: dict[str, int] = {}
        self.scenarios: dict[str, list[C.Resultat | Exception]] = {}

    def pas(self, nom: str, module: str, apres: tuple[str, ...] = (), modeles: float = 0.0,
            web: float = 0.0, estime: float | None = None) -> C.Pas:
        defaut = C.Resultat(C.FAIT, C.Depense(modeles, web))

        def executer(ctx: C.Contexte) -> C.Resultat:
            self.appels[nom] = self.appels.get(nom, 0) + 1
            file = self.scenarios.get(nom)
            rendu = file.pop(0) if file else defaut
            if isinstance(rendu, Exception):
                raise rendu
            return rendu

        return C.Pas(nom=nom, module=module, apres=apres, executer=executer,
                     cout_estime_usd=(modeles + web) if estime is None else estime)


def parcours_fictif(sim: Simulateur) -> list[C.Pas]:
    """Le parcours M1-M11 en modules simulés, avec les deux actes qui vous reviennent."""
    return [
        sim.pas("fiche", "fiche_emetteur"),
        sim.pas("collecte", "collecte", ("fiche",), web=0.05),
        sim.pas("pieces", "base_de_connaissance", ("collecte",)),
        sim.pas("comptes", "comptes", ("pieces",)),
        sim.pas("filtres", "filtres", ("comptes",), modeles=0.05),
        sim.pas("carte", "carte", ("filtres",), modeles=0.40, web=0.20),
        C.Pas(nom="validation_carte", module="carte", nature=C.HUMAIN, apres=("carte",),
              acte="valider la carte des sources de profit et les débats de la thèse"),
        sim.pas("classeur", "modele_entreprise", ("validation_carte",)),
        sim.pas("recherche", "recherche_ciblee", ("classeur",), modeles=0.50, web=0.40),
        sim.pas("jugements", "jugements", ("recherche",), modeles=0.45),
        sim.pas("valorisation", "valorisation", ("jugements",)),
        sim.pas("memo", "memo_comite", ("valorisation",), modeles=0.10),
        C.Pas(nom="comite", module="memo_comite", nature=C.HUMAIN, apres=("memo",),
              acte="décider en comité"),
    ]


SANS_LECTURE = {m: False for m in (
    "fiche_emetteur", "collecte", "base_de_connaissance", "comptes", "filtres", "carte",
    "modele_entreprise", "recherche_ciblee", "jugements", "valorisation", "memo_comite")}


def derouler(etat: C.EtatDossier, parcours, **kw) -> tuple[C.EtatDossier, list[C.Arret]]:
    """Conduit jusqu'au bout en accomplissant chaque geste attendu ; rend la suite des arrêts."""
    arrets: list[C.Arret] = []
    for _ in range(200):
        etat = A.avancer(etat, parcours, **kw)
        a = etat.arret
        arrets.append(a)
        if a.motif == C.ARRET_PARCOURS_TERMINE:
            return etat, arrets
        if a.motif == C.ARRET_ACTE_HUMAIN:
            etat = A.enregistrer_acte(etat, a.cle)
        elif a.motif == C.ARRET_PAUSE_DEPENSE:
            etat = A.lever_pause(etat)
        else:
            etat = A.relancer(etat)
    raise AssertionError("le dossier fictif ne se termine pas")


def refuse(fn, exc) -> bool:
    try:
        fn()
    except exc:
        return True
    return False


def _d1(b: Bilan) -> None:
    """parcours invalides."""
    sim = Simulateur()
    b.check(refuse(lambda: A.verifier_parcours([]), A.ParcoursInvalide), "[D1] parcours vide refusé")
    b.check(refuse(lambda: A.verifier_parcours([sim.pas("a", "m"), sim.pas("a", "m")]),
                   A.ParcoursInvalide), "[D1] pas déclaré deux fois refusé")
    b.check(refuse(lambda: A.verifier_parcours([sim.pas("a", "m", ("zz",))]), A.ParcoursInvalide),
            "[D1] préalable inconnu refusé")
    b.check(refuse(lambda: A.verifier_parcours([sim.pas("a", "m", ("b",)), sim.pas("b", "m", ("a",))]),
                   A.ParcoursInvalide), "[D1] boucle entre pas refusée")
    b.check(refuse(lambda: A.avancer(C.EtatDossier(DOSSIER), [sim.pas("a", "m", ("zz",))]),
                   A.ParcoursInvalide), "[D1] avancer refuse un parcours invalide avant d'exécuter")
    b.check(sim.appels == {}, "[D1] aucun pas exécuté sur un parcours refusé")
    b.check(refuse(lambda: C.Pas(nom="x", module="m"), ValueError),
            "[D1] un pas automatique sans exécution est refusé à la déclaration")
    b.check(refuse(lambda: C.Pas(nom="x", module="m", nature=C.HUMAIN), ValueError),
            "[D1] un pas humain qui ne nomme pas son acte est refusé")


def _d2(b: Bilan) -> None:
    """arrêt exactement aux actes déclarés (lecture levée, palier hors d'atteinte)."""
    sim = Simulateur()
    parcours = parcours_fictif(sim)
    etat, arrets = derouler(C.EtatDossier(DOSSIER), parcours, palier_usd=100.0,
                            lecture_humaine=SANS_LECTURE)
    b.require(arrets, 3, "[D2] trois arrêts : deux actes déclarés puis la fin")
    b.check([a.motif for a in arrets] == [C.ARRET_ACTE_HUMAIN, C.ARRET_ACTE_HUMAIN,
                                          C.ARRET_PARCOURS_TERMINE],
            "[D2] arrêts dans l'ordre : acte, acte, parcours terminé")
    b.check([a.pas for a in arrets[:2]] == ["validation_carte", "comite"],
            "[D2] les deux arrêts sont les actes déclarés, dans l'ordre du parcours")
    b.check(arrets[0].acte.startswith("valider la carte") and arrets[1].acte == "décider en comité",
            "[D2] chaque arrêt nomme l'acte attendu")
    b.check(etat.faits == tuple(p.nom for p in parcours), "[D2] tous les pas faits, dans l'ordre déclaré")
    b.check(all(sim.appels.get(p.nom) == 1 for p in parcours if p.nature == C.AUTOMATIQUE),
            "[D2] chaque pas automatique exécuté une fois et une seule")
    premier = A.avancer(C.EtatDossier(DOSSIER), parcours_fictif(Simulateur()), palier_usd=100.0,
                        lecture_humaine=SANS_LECTURE)
    b.check("classeur" not in premier.faits and premier.faits[-1] == "carte",
            "[D2] rien ne s'exécute au-delà d'un acte en attente")


def _d3(b: Bilan) -> None:
    """la pause tous les 1 $."""
    sim = Simulateur()
    parcours = parcours_fictif(sim)
    etat = C.EtatDossier(DOSSIER)
    etat = A.avancer(etat, parcours, lecture_humaine=SANS_LECTURE)           # → validation de la carte
    b.check(abs(etat.depense.total_usd - 0.70) < 1e-9, "[D3] 0,70 $ consommés avant la carte validée")
    b.check(etat.arret.motif == C.ARRET_ACTE_HUMAIN, "[D3] sous 1 $ : pas de pause, l'acte d'abord")
    etat = A.avancer(A.enregistrer_acte(etat, "validation_carte"), parcours, lecture_humaine=SANS_LECTURE)
    a = etat.arret
    b.check(a.motif == C.ARRET_PAUSE_DEPENSE, "[D3] pause dès que 1 $ est consommé")
    b.check(abs(a.depense_totale_usd - 1.60) < 1e-9, "[D3] la pause dit la dépense totale (1,60 $)")
    b.check(abs(a.cout_restant_estime_usd - 0.55) < 1e-9,
            "[D3] la pause dit le coût restant estimé jusqu'au comité (0,55 $)")
    b.check(a.ratio_constate == 1.0, "[D3] la pause dit l'écart dépensé / estimé constaté")
    b.check("jugements" not in sim.appels, "[D3] le pas suivant n'est pas lancé pendant la pause")
    fige = A.avancer(etat, parcours, lecture_humaine=SANS_LECTURE)
    b.check(fige == etat and "jugements" not in sim.appels,
            "[D3] avancer sur un dossier en pause ne fait rien")
    etat = A.avancer(A.lever_pause(etat), parcours, lecture_humaine=SANS_LECTURE)
    b.check(etat.arret.motif == C.ARRET_ACTE_HUMAIN and etat.arret.pas == "comite",
            "[D3] pause levée : le dossier repart jusqu'à l'acte suivant")
    b.check(abs(etat.depense.total_usd - 2.15) < 1e-9 and abs(etat.depense_acquittee_usd - 1.60) < 1e-9,
            "[D3] le palier suivant se compte depuis la dernière pause levée")
    # palier réglable : à 0,25 $ le même parcours s'arrête plus souvent, jamais au-delà d'un pas.
    sim2 = Simulateur()
    _, arrets2 = derouler(C.EtatDossier(DOSSIER), parcours_fictif(sim2), palier_usd=0.25,
                          lecture_humaine=SANS_LECTURE)
    pauses = [x for x in arrets2 if x.motif == C.ARRET_PAUSE_DEPENSE]
    b.require(pauses, 3, "[D3] à 0,25 $ de palier : trois pauses (0,70 $, 1,60 $, 2,05 $)")
    b.check([round(x.depense_totale_usd, 2) for x in pauses] == [0.70, 1.60, 2.05],
            "[D3] chaque pause tombe après le pas qui franchit le palier, jamais plus tard")
    # estimation fausse : le ratio le dit.
    sim3 = Simulateur()
    p3 = [sim3.pas("a", "m", modeles=1.50, estime=0.50), sim3.pas("b", "m", ("a",), estime=2.0)]
    e3 = A.avancer(C.EtatDossier(DOSSIER), p3, lecture_humaine={"m": False})
    b.check(e3.arret.motif == C.ARRET_PAUSE_DEPENSE and e3.arret.ratio_constate == 3.0
            and abs(e3.arret.cout_restant_estime_usd - 2.0) < 1e-9,
            "[D3] estimation dépassée : ratio 3,00 affiché, estimation restante non retouchée")


def _d4(b: Bilan) -> None:
    """échecs."""
    sim = Simulateur()
    parcours = parcours_fictif(sim)
    sim.scenarios["collecte"] = [C.Resultat(C.ECHEC, C.Depense(web_usd=0.01), motif="délai dépassé")]
    etat = A.avancer(C.EtatDossier(DOSSIER), parcours, palier_usd=100.0, lecture_humaine=SANS_LECTURE)
    b.check(sim.appels["collecte"] == 2 and "collecte" in etat.faits and dict(etat.echecs) == {},
            "[D4] un échec isolé : le pas est retenté une fois, puis le dossier continue")
    sim = Simulateur()
    parcours = parcours_fictif(sim)
    sim.scenarios["collecte"] = [C.Resultat(C.ECHEC, motif="refus 1"), RuntimeError("panne simulée")]
    etat = A.avancer(C.EtatDossier(DOSSIER), parcours, palier_usd=100.0, lecture_humaine=SANS_LECTURE)
    a = etat.arret
    b.check(a.motif == C.ARRET_ECHEC_REPETE and a.pas == "collecte",
            "[D4] deux échecs de suite : arrêt qui nomme le pas")
    b.check("RuntimeError" in a.detail and "panne simulée" in a.detail,
            "[D4] un plantage devient un échec motivé, le dossier ne plante pas")
    b.check(sim.appels["collecte"] == 2 and "pieces" not in sim.appels,
            "[D4] ni troisième essai ni pas suivant après un échec répété")
    etat = A.avancer(A.relancer(etat), parcours, palier_usd=100.0, lecture_humaine=SANS_LECTURE)
    b.check("collecte" in etat.faits and sim.appels["collecte"] == 3,
            "[D4] relance décidée par vous : le pas est réessayé")
    mauvais = [C.Pas(nom="x", module="m", executer=lambda ctx: "pas un résultat")]
    em = A.avancer(C.EtatDossier(DOSSIER), mauvais, lecture_humaine={"m": False})
    b.check(em.arret.motif == C.ARRET_ECHEC_REPETE, "[D4] un pas qui ne rend pas un résultat échoue")


def _d5(b: Bilan) -> None:
    """source indisponible."""
    sim = Simulateur()
    parcours = parcours_fictif(sim)
    sim.scenarios["collecte"] = [C.Resultat(C.INDISPONIBLE, motif="aucun dépôt réglementaire pour cet émetteur")]
    etat, arrets = derouler(C.EtatDossier(DOSSIER), parcours, palier_usd=100.0, lecture_humaine=SANS_LECTURE)
    b.check(arrets[-1].motif == C.ARRET_PARCOURS_TERMINE,
            "[D5] une source indisponible n'arrête pas le dossier")
    b.check(etat.reserves == (("collecte", "aucun dépôt réglementaire pour cet émetteur"),),
            "[D5] la réserve reste au dossier, avec son motif")
    b.check(refuse(lambda: C.Resultat(C.INDISPONIBLE), ValueError),
            "[D5] « indisponible » sans motif est refusé")
    b.check("réserve — collecte" in A.afficher(etat), "[D5] la réserve se voit à l'affichage")


def _d6(b: Bilan) -> None:
    """lecture humaine des sorties de module."""
    sim = Simulateur()
    parcours = parcours_fictif(sim)
    etat = A.avancer(C.EtatDossier(DOSSIER), parcours, palier_usd=100.0)      # aucun interrupteur levé
    a = etat.arret
    b.check(a.motif == C.ARRET_ACTE_HUMAIN and a.cle == "lecture:fiche" and "fiche_emetteur" in a.acte,
            "[D6] par défaut, la première sortie de module attend votre lecture")
    b.check("collecte" not in sim.appels, "[D6] rien ne s'appuie sur une sortie non lue")
    _, arrets = derouler(C.EtatDossier(DOSSIER), parcours_fictif(Simulateur()), palier_usd=100.0)
    lectures = [x for x in arrets if x.cle.startswith("lecture:")]
    b.require(lectures, 11, "[D6] sans interrupteur levé : une lecture par pas automatique")
    leve = dict(SANS_LECTURE, carte=True)
    _, arrets = derouler(C.EtatDossier(DOSSIER), parcours_fictif(Simulateur()), palier_usd=100.0,
                         lecture_humaine=leve)
    b.check([x.cle for x in arrets if x.cle.startswith("lecture:")] == ["lecture:carte"],
            "[D6] l'interrupteur se lève module par module")
    _, arrets = derouler(C.EtatDossier(DOSSIER), parcours_fictif(Simulateur()), palier_usd=100.0,
                         lecture_humaine={"carte": False})
    b.require([x for x in arrets if x.cle.startswith("lecture:")], 10,
              "[D6] un module absent de la table est lu (prudent par défaut)")


def _d7_d8(b: Bilan) -> None:
    """rangement, relecture, reprise ; comptage."""
    sim = Simulateur()
    parcours = parcours_fictif(sim)
    ref, _ = derouler(C.EtatDossier(DOSSIER), parcours)
    depot = C.DepotMemoire()
    b.check(C.lire_etat(depot, DOSSIER) == C.EtatDossier(DOSSIER),
            "[D7] un dossier jamais ouvert se lit « titre entré »")
    sim_b = Simulateur()
    parcours_b = parcours_fictif(sim_b)
    relectures: list[bool] = []
    for _ in range(200):
        e = A.conduire(depot, DOSSIER, parcours_b)
        # entre deux gestes, l'état ne vit QUE dans le dépôt, sérialisé.
        relu = C.EtatDossier.depuis_dict(json.loads(json.dumps(depot.charger(DOSSIER))))
        relectures.append(relu == e)
        if e.arret.motif == C.ARRET_PARCOURS_TERMINE:
            break
        geste = {C.ARRET_ACTE_HUMAIN: lambda s: A.enregistrer_acte(s, s.arret.cle),
                 C.ARRET_PAUSE_DEPENSE: A.lever_pause, C.ARRET_ECHEC_REPETE: A.relancer}[e.arret.motif]
        depot.ranger(DOSSIER, geste(relu).vers_dict())
    final = C.lire_etat(depot, DOSSIER)
    b.check(len(relectures) > 10 and all(relectures),
            "[D7] à chaque arrêt, l'état rangé puis relu (JSON) est identique à l'état rendu")
    b.check(final == ref, "[D7] interrompu et repris à chaque arrêt : même état qu'en un seul passage")
    b.check(final.journal == ref.journal and len(ref.journal) > 20,
            "[D7] deux passages rendent le même journal, ligne à ligne")
    b.check(refuse(lambda: C.EtatDossier.depuis_dict(dict(ref.vers_dict(), version_contrat="0.9.0")),
                   ValueError), "[D7] un état d'une autre version de contrat est refusé")

    # comptage [D8]
    b.check(abs(ref.depense.modeles_usd - 1.50) < 1e-9 and abs(ref.depense.web_usd - 0.65) < 1e-9,
            "[D8] modèles (1,50 $) et web (0,65 $) comptés à part")
    b.check(abs(sum(x for _, x in ref.depense_par_pas) - ref.depense.total_usd) < 1e-9,
            "[D8] la dépense totale est la somme des dépenses par pas")
    b.check(abs(sum(l.modeles_usd + l.web_usd for l in ref.journal) - ref.depense.total_usd) < 1e-9,
            "[D8] le journal porte chaque dépense")
    b.check(all(n == 1 for n in sim.appels.values()), "[D8] aucun pas exécuté deux fois")
    sim = Simulateur()
    sim.scenarios["a"] = [C.Resultat(C.ECHEC, C.Depense(0.30, 0.10), motif="refus")]
    e = A.avancer(C.EtatDossier(DOSSIER), [sim.pas("a", "m", modeles=0.20)], lecture_humaine={"m": False})
    b.check(abs(e.depense.total_usd - 0.60) < 1e-9, "[D8] un essai échoué est compté comme dépensé")
    b.check(refuse(lambda: C.Depense(modeles_usd=-0.01), ValueError), "[D8] une dépense négative est refusée")


def _d9(b: Bilan) -> None:
    """un arrêt ne se lève que par son geste."""
    sim = Simulateur()
    parcours = parcours_fictif(sim)
    attente = A.avancer(C.EtatDossier(DOSSIER), parcours, palier_usd=100.0, lecture_humaine=SANS_LECTURE)
    b.check(refuse(lambda: A.enregistrer_acte(attente, "comite"), A.GesteRefuse),
            "[D9] on n'enregistre pas un autre acte que celui attendu")
    b.check(refuse(lambda: A.lever_pause(attente), A.GesteRefuse),
            "[D9] lever une pause sur un dossier qui attend un acte est refusé")
    b.check(refuse(lambda: A.relancer(attente), A.GesteRefuse),
            "[D9] relancer sans échec répété est refusé")
    b.check(refuse(lambda: A.enregistrer_acte(C.EtatDossier(DOSSIER), "validation_carte"), A.GesteRefuse),
            "[D9] aucun acte ne s'enregistre d'avance")
    # acte demandé par un pas en cours de route : arrêt nommé, puis le pas reprend.
    sim = Simulateur()
    sim.scenarios["a"] = [C.Resultat(C.ACTE_HUMAIN, motif="deux lectures possibles", acte="trancher l'interprétation")]
    pa = [sim.pas("a", "m")]
    e = A.avancer(C.EtatDossier(DOSSIER), pa, lecture_humaine={"m": False})
    b.check(e.arret.motif == C.ARRET_ACTE_HUMAIN and e.arret.acte == "trancher l'interprétation"
            and "a" not in e.faits, "[D9] un pas peut demander un acte : arrêt nommé, pas non fait")
    e = A.avancer(A.enregistrer_acte(e, e.arret.cle), pa, lecture_humaine={"m": False})
    b.check(e.faits == ("a",) and sim.appels["a"] == 2, "[D9] l'acte accompli, le pas reprend et aboutit")


def _d10(b: Bilan) -> None:
    """aucun modèle, aucun réseau : imports."""
    permis = {"__future__", "dataclasses", "typing"}
    dossier_module = BACKEND / "app" / "modules" / "chef_de_dossier"
    sources = sorted(dossier_module.glob("*.py"))
    b.require(sources, 3, "[D10] trois fichiers source dans le module")
    for src in sources:
        for noeud in ast.walk(ast.parse(src.read_text(encoding="utf-8"))):
            if isinstance(noeud, ast.Import):
                for alias in noeud.names:
                    b.check(alias.name.split(".")[0] in permis,
                            f"[D10] {src.name} importe `{alias.name}` : bibliothèque standard permise seulement")
            elif isinstance(noeud, ast.ImportFrom):
                interne = noeud.level == 1 and noeud.module == "contrat"
                b.check(interne or (noeud.level == 0 and (noeud.module or "").split(".")[0] in permis),
                        f"[D10] {src.name} importe depuis `{'.' * noeud.level}{noeud.module}` : "
                        "son contrat ou la bibliothèque standard seulement")


def main() -> int:
    b = Bilan()
    for nom, section in (("[D1]", _d1), ("[D2]", _d2), ("[D3]", _d3), ("[D4]", _d4), ("[D5]", _d5), ("[D6]", _d6), ("[D7]/[D8]", _d7_d8), ("[D9]", _d9), ("[D10]", _d10)):
        # Une section qui plante (un geste refusé parce que la règle gardée est cassée) ne doit
        # jamais tuer le script avant son bilan : c'est un échec NOMMÉ, et les suivantes tournent.
        try:
            section(b)
        except Exception as exc:  # noqa: BLE001
            b.check(False, f"{nom} section interrompue — {type(exc).__name__}: {exc}")
    return b.summary()


if __name__ == "__main__":
    sys.exit(main())
