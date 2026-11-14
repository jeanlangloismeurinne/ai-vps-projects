"""Module M1 « Fiche de l'émetteur et sources » sur des sociétés FICTIVES — aucune base, aucun
réseau, aucun modèle, aucune dépense. C'est la part « société fictive » de l'acceptation écrite
avant la construction (`roadmap/V3/M1-fiche-emetteur.md` §2) ; chaque section porte le numéro de la
ligne d'acceptation qu'elle prouve, et `negatif_emetteurs.sh` prouve que chacune vire au rouge.

  [A1]  ajouter un titre = un geste, aucun fichier de code ; relu tel qu'établi
  [A2]  sans numéro de régulateur, sans cotation : la fiche est valide
  [A3]  sans kit de spécialité : sources générales + son site ; avec : celles de la spécialité en plus
  [A4]  une correction est une révision nouvelle ; les précédentes se relisent
  [A5]  une source vaut pour une NATURE d'information
  [A6]  toute admission est datée, motivée, signée ; celle du système cite son critère écrit
  [A7]  celui qui utilise une source ne la qualifie jamais
  [A8]  la correction de l'utilisateur l'emporte sur le système
  [A9]  une source révoquée signale les pièces qui s'y appuient, et elles seules
  [A10] dans le doute, la source n'est pas admise
  [A11] le chef de dossier s'arrête tant que la fiche n'existe pas
  [A0]  le module n'importe que la bibliothèque standard, lui-même et le contrat du chef de dossier

Les sociétés, domaines et registres ci-dessous sont inventés (`.example` est un domaine réservé).
"""
from __future__ import annotations

import ast
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.modules.chef_de_dossier import automate as A  # noqa: E402
from app.modules.chef_de_dossier import contrat as CD  # noqa: E402
from app.modules.emetteurs import contrat as C  # noqa: E402

COTEE = "FICTIVE-COTEE"        # cotée, avec une référence de régulateur et une spécialité
NON_COTEE = "FICTIVE-PRIVEE"   # ni cotation, ni référence externe, ni spécialité
JOUR = "2026-11-13"
SYSTEME = "systeme:evaluateur_de_sources"


def refuse(coro) -> str | None:
    """Le message du refus, ou None si le geste est passé."""
    try:
        asyncio.run(coro)
    except C.ActeRefuse as exc:
        return str(exc)
    return None


async def _fiche_cotee(depot, **remplace):
    args = dict(raison_sociale="Société Fictive Cotée SA", auteur=C.UTILISATEUR, motif="ouverture du dossier",
                le=JOUR, pays="FR", cotations=[("PLACE-FICTIVE", "FICT")],
                references=[("registre_fictif", "0001234")],
                lieux=[("site", "https://www.fictive-cotee.example/"),
                       ("relations_investisseurs", "fictive-cotee.example/investisseurs"),
                       ("relations_investisseurs", "ir.fictive-cotee.example")],
                specialite="specialite_fictive")
    args.update(remplace)
    return await C.etablir_fiche(depot, COTEE, **args)


async def _fiche_non_cotee(depot):
    return await C.etablir_fiche(depot, NON_COTEE, raison_sociale="Société Fictive Privée",
                                 auteur=C.UTILISATEUR, motif="ouverture du dossier", le=JOUR,
                                 lieux=[("site", "fictive-privee.example")])


async def _sources_de_base(depot):
    """Trois admissions de l'utilisateur : une générale, une de spécialité, une propre à l'émetteur."""
    await C.admettre_source(depot, source="autorite.example", portee=C.PORTEE_GENERALE,
                            natures=["mesure", "evenement", "interpretation"], niveau="A",
                            auteur=C.UTILISATEUR, motif="autorité de marché fictive", le=JOUR)
    await C.admettre_source(depot, source="revue-specialisee.example",
                            portee=C.PREFIXE_PORTEE_SPECIALITE + "specialite_fictive",
                            natures=["interpretation"], niveau="B", auteur=C.UTILISATEUR,
                            motif="rédaction spécialisée fictive", le=JOUR)
    await C.admettre_source(depot, source="client-de-la-cotee.example",
                            portee=C.PREFIXE_PORTEE_EMETTEUR + COTEE, natures=["evenement"], niveau="B+",
                            auteur=C.UTILISATEUR, motif="principal client, publie ses commandes", le=JOUR)


def _a1(b: Bilan) -> None:
    depot = C.DepotMemoire()
    f = asyncio.run(_fiche_cotee(depot))
    b.check(f.emetteur == COTEE and f.raison_sociale == "Société Fictive Cotée SA" and f.pays == "FR"
            and f.revision == 1 and f.auteur == C.UTILISATEUR and f.le == JOUR
            and f.version_contrat == C.VERSION_CONTRAT,
            "[A1] un seul geste établit la fiche d'une société inconnue du système")
    b.check(asyncio.run(C.lire_fiche(depot, COTEE)) == f, "[A1] la fiche se relit telle qu'elle a été établie")
    b.check(f.cotations == (C.Cotation("PLACE-FICTIVE", "FICT"),)
            and f.reference("registre_fictif") == "0001234",
            "[A1] cotation et référence externe sont des données de la fiche")
    b.check({(l.genre, l.adresse) for l in f.lieux} == {
        ("site", "fictive-cotee.example"), ("relations_investisseurs", "fictive-cotee.example/investisseurs"),
        ("relations_investisseurs", "ir.fictive-cotee.example")},
        "[A1] les lieux de publication sont rangés sans protocole ni « www. »")
    try:
        asyncio.run(C.lire_fiche(depot, "INCONNUE"))
        absente = False
    except C.FicheAbsente:
        absente = True
    b.check(absente, "[A1] une société sans fiche n'a pas une fiche vide : `FicheAbsente`")
    b.check(refuse(C.etablir_fiche(depot, "nom avec espace", raison_sociale="X", auteur=C.UTILISATEUR,
                                   motif="m", le=JOUR)) is not None,
            "[A1] un identifiant maison mal formé est refusé")
    b.check(refuse(C.etablir_fiche(depot, "AUTRE", raison_sociale="  ", auteur=C.UTILISATEUR, motif="m",
                                   le=JOUR)) is not None, "[A1] une fiche sans raison sociale est refusée")
    b.check(refuse(_fiche_cotee(C.DepotMemoire(), lieux=[("blog", "fictive.example")])) is not None,
            "[A1] un genre de lieu hors du référentiel est refusé")
    b.check(refuse(_fiche_cotee(C.DepotMemoire(), references=[("r", "1"), ("r", "2")])) is not None,
            "[A1] deux références du même registre sont refusées")


def _a2(b: Bilan) -> None:
    depot = C.DepotMemoire()
    f = asyncio.run(_fiche_non_cotee(depot))
    b.check(f.references == () and f.cotations == () and f.pays == "" and f.revision == 1,
            "[A2] sans référence externe ni cotation ni pays, la fiche est valide")
    b.check(f.reference("registre_fictif") is None and f.reference("n_importe_lequel") is None,
            "[A2] demander une référence absente rend `None`, jamais une erreur")
    q = C.qualifier(f, "https://fictive-privee.example/a-propos", "interpretation")
    b.check(q.admise and q.niveau == "B", "[A2] le site d'une société non cotée est reconnu comme le sien")


def _a3(b: Bilan) -> None:
    depot = C.DepotMemoire()
    asyncio.run(_fiche_cotee(depot))
    asyncio.run(_fiche_non_cotee(depot))
    asyncio.run(_sources_de_base(depot))
    sans_kit = asyncio.run(C.lire_fiche(depot, NON_COTEE))
    avec_kit = asyncio.run(C.lire_fiche(depot, COTEE))
    b.check(sans_kit.specialite == "" and [s.source for s in sans_kit.sources] == ["autorite.example"],
            "[A3] sans spécialité, la fiche porte les sources générales et elles seules")
    b.check(C.qualifier(sans_kit, "https://autorite.example/avis/1", "mesure").admise
            and C.qualifier(sans_kit, "fictive-privee.example", "mesure").admise,
            "[A3] sans spécialité : source générale et site de la société admis")
    b.check(not C.qualifier(sans_kit, "https://revue-specialisee.example/x", "interpretation").admise,
            "[A3] une source de spécialité ne vaut pas pour une société qui n'a pas cette spécialité")
    b.require(avec_kit.sources, 3, "[A3] avec spécialité : générale + spécialité + propre à l'émetteur")
    b.check(C.qualifier(avec_kit, "https://revue-specialisee.example/x", "interpretation").admise,
            "[A3] avec la spécialité, la source de spécialité vaut")
    b.check(not C.qualifier(sans_kit, "https://client-de-la-cotee.example/c", "evenement").admise
            and C.qualifier(avec_kit, "https://client-de-la-cotee.example/c", "evenement").admise,
            "[A3] une source propre à un émetteur ne vaut que pour lui")


def _a4(b: Bilan) -> None:
    depot = C.DepotMemoire()
    f1 = asyncio.run(_fiche_cotee(depot))
    f2 = asyncio.run(_fiche_cotee(depot, raison_sociale="Société Fictive Cotée SE", motif="changement de forme sociale",
                                  le="2026-12-01"))
    b.check(f2.revision == 2 and f2.raison_sociale.endswith("SE") and f2.le == "2026-12-01"
            and f2.motif == "changement de forme sociale", "[A4] une correction ajoute une révision datée et motivée")
    vue = asyncio.run(C.vue_ecran(depot, COTEE))
    b.require(vue["revisions"], 2, "[A4] les deux révisions se relisent")
    b.check(vue["revisions"][0]["raison_sociale"] == f1.raison_sociale and vue["revisions"][0]["revision"] == 1,
            "[A4] la révision précédente est intacte")
    b.check(refuse(_fiche_cotee(depot, raison_sociale="Société Fictive Cotée SE")) is not None
            and len(asyncio.run(C.vue_ecran(depot, COTEE))["revisions"]) == 2,
            "[A4] redire exactement la même fiche n'ajoute pas de révision")
    b.check(refuse(_fiche_cotee(depot, raison_sociale="Autre", motif=" ")) is not None,
            "[A4] une révision sans motif est refusée")
    b.check(refuse(_fiche_cotee(depot, raison_sociale="Autre", auteur="quelqu'un")) is not None,
            "[A4] une révision sans signature reconnue est refusée")
    b.check(refuse(_fiche_cotee(depot, raison_sociale="Autre", le="hier")) is not None,
            "[A4] une révision sans date lisible est refusée")


def _a5(b: Bilan) -> None:
    depot = C.DepotMemoire()
    asyncio.run(_fiche_cotee(depot))
    asyncio.run(_sources_de_base(depot))
    f = asyncio.run(C.lire_fiche(depot, COTEE))
    oui = C.qualifier(f, "https://www.revue-specialisee.example/analyse/42", "interpretation")
    non = C.qualifier(f, "https://www.revue-specialisee.example/analyse/42", "mesure")
    b.check(oui.admise and oui.niveau == "B" and oui.source == "revue-specialisee.example",
            "[A5] admise pour l'interprétation : niveau de l'admission")
    b.check(not non.admise and non.niveau == "C+" and "pas pour mesure" in non.motif,
            "[A5] la même page n'est pas admise pour une mesure, et le motif le dit")
    ir = C.qualifier(f, "https://fictive-cotee.example/investisseurs/resultats.pdf", "mesure")
    site = C.qualifier(f, "https://fictive-cotee.example/produits", "mesure")
    sous = C.qualifier(f, "https://ir.fictive-cotee.example/communiques", "evenement")
    b.check(ir.admise and ir.niveau == "A" and sous.admise and sous.niveau == "A",
            "[A5] les pages de relations investisseurs de la société valent plus que le reste de son site")
    b.check(site.admise and site.niveau == "B", "[A5] le reste du site de la société : niveau du genre « site »")
    b.check(not C.qualifier(f, "https://fictive-cotee.example/investisseurs-anciens/x", "mesure").niveau == "A",
            "[A5] un chemin qui ressemble à celui des relations investisseurs n'en est pas un")
    try:
        C.qualifier(f, "https://autorite.example", "rumeur")
        inconnue = False
    except ValueError:
        inconnue = True
    b.check(inconnue, "[A5] une nature d'information hors du référentiel est refusée")


def _a6(b: Bilan) -> None:
    depot = C.DepotMemoire()
    base = dict(source="cabinet-etudes.example", portee=C.PORTEE_GENERALE, natures=["mesure"], niveau="B",
                auteur=SYSTEME, motif="publie ses propres estimations de marché", le=JOUR,
                critere="organisme_publiant_ses_estimations")
    b.check(refuse(C.admettre_source(depot, **{**base, "critere": ""})) is not None,
            "[A6] une admission du système sans critère écrit est refusée")
    b.check(refuse(C.admettre_source(depot, **{**base, "critere": "au_jugé"})) is not None,
            "[A6] un critère qui n'est pas au référentiel est refusé")
    b.check(refuse(C.admettre_source(depot, **{**base, "motif": ""})) is not None,
            "[A6] une admission sans motif est refusée")
    b.check(refuse(C.admettre_source(depot, **{**base, "le": ""})) is not None,
            "[A6] une admission sans date est refusée")
    b.check(refuse(C.admettre_source(depot, **{**base, "auteur": ""})) is not None,
            "[A6] une admission sans auteur est refusée")
    b.check(refuse(C.admettre_source(depot, **{**base, "niveau": "A"})) is not None,
            "[A6] le système n'accorde pas plus que le plafond de son critère")
    b.check(refuse(C.admettre_source(depot, **{**base, "critere": "redaction_specialisee"})) is not None,
            "[A6] le système n'admet pas pour une nature que son critère ne couvre pas")
    b.check(refuse(C.admettre_source(depot, **{**base, "natures": []})) is not None,
            "[A6] une admission sans nature d'information est refusée")
    b.check(refuse(C.admettre_source(depot, **{**base, "source": "cabinet-etudes.example/rapports"})) is not None,
            "[A6] une source se nomme par son domaine, pas par une page")
    b.check(refuse(C.admettre_source(depot, **{**base, "source": "pas un domaine"})) is not None
            and refuse(C.admettre_source(depot, **{**base, "source": "sans_point"})) is not None,
            "[A6] une source qui n'est pas un domaine est refusée")
    b.check(refuse(C.admettre_source(depot, **{**base, "portee": "emetteur:INCONNUE"})) is not None,
            "[A6] une portée sur un émetteur sans fiche est refusée")
    b.check(asyncio.run(C.vue_ecran(depot))["journal_des_sources"] == [],
            "[A6] aucun des refus n'a laissé de trace au journal")
    rang = asyncio.run(C.admettre_source(depot, **base))
    journal = asyncio.run(C.vue_ecran(depot))["journal_des_sources"]
    b.require(journal, 1, "[A6] l'admission conforme est au journal")
    a = journal[0]
    b.check(rang == 1 and a["auteur"] == SYSTEME and a["le"] == JOUR and a["motif"] == base["motif"]
            and a["critere"] == base["critere"] and a["natures"] == ["mesure"] and a["en_vigueur"] is True,
            "[A6] le journal porte la date, le motif, l'auteur et le critère de l'admission")
    b.check(refuse(C.admettre_source(depot, **base)) is not None,
            "[A6] redire la même admission n'ajoute rien au journal")


def _a7(b: Bilan) -> None:
    depot = C.DepotMemoire()
    base = dict(source="revue.example", portee=C.PORTEE_GENERALE, natures=["interpretation"], niveau="B",
                motif="couverture de fond", le=JOUR, critere="redaction_specialisee")
    for role in ("collecteur", "analyste"):
        msg = refuse(C.admettre_source(depot, auteur=f"systeme:{role}", **base))
        b.check(msg is not None and "utilise les sources" in msg,
                f"[A7] le rôle « {role} » utilise les sources : son admission est refusée")
    asyncio.run(C.admettre_source(depot, auteur=SYSTEME, **base))
    msg = refuse(C.revoquer_source(depot, source="revue.example", portee=C.PORTEE_GENERALE,
                                   auteur="systeme:collecteur", motif="ne me convient plus", le=JOUR))
    b.check(msg is not None and "utilise les sources" in msg,
            "[A7] un rôle qui utilise les sources ne peut pas non plus en révoquer une")


def _a8(b: Bilan) -> None:
    depot = C.DepotMemoire()
    cle = dict(source="revue.example", portee=C.PORTEE_GENERALE)
    adm = dict(natures=["interpretation"], niveau="B", motif="couverture de fond", le=JOUR,
               critere="redaction_specialisee")
    asyncio.run(C.admettre_source(depot, auteur=SYSTEME, **cle, **adm))
    asyncio.run(C.revoquer_source(depot, auteur=C.UTILISATEUR, motif="reprend des rumeurs", le=JOUR, **cle))
    msg = refuse(C.admettre_source(depot, auteur=SYSTEME, **cle, **adm))
    b.check(msg is not None and "l'utilisateur a statué" in msg,
            "[A8] le système ne réadmet pas une source que l'utilisateur a révoquée")
    asyncio.run(C.admettre_source(depot, auteur=C.UTILISATEUR, **cle, **{**adm, "motif": "ligne éditoriale revue"}))
    msg = refuse(C.revoquer_source(depot, auteur=SYSTEME, motif="critère non tenu", le=JOUR, **cle))
    b.check(msg is not None and "l'utilisateur a statué" in msg,
            "[A8] le système ne révoque pas une source que l'utilisateur a admise")
    b.require(asyncio.run(C.vue_ecran(depot))["journal_des_sources"], 3,
              "[A8] le journal garde les trois actes passés, aucun des deux refus")
    autre = dict(source="autre-revue.example", portee=C.PORTEE_GENERALE)
    asyncio.run(C.admettre_source(depot, auteur=SYSTEME, **autre, **adm))
    b.check(refuse(C.revoquer_source(depot, auteur=SYSTEME, motif="critère non tenu", le=JOUR, **autre)) is None,
            "[A8] le système révoque librement ce que lui seul a admis")
    b.check(refuse(C.revoquer_source(depot, auteur=C.UTILISATEUR, motif="m", le=JOUR, **autre)) is not None,
            "[A8] on ne révoque pas une source qui n'est pas admise")


def _a9(b: Bilan) -> None:
    depot = C.DepotMemoire()
    asyncio.run(_fiche_cotee(depot))
    asyncio.run(_fiche_non_cotee(depot))
    asyncio.run(_sources_de_base(depot))
    origines = [
        C.Origine("piece-1", "https://www.revue-specialisee.example/analyse/42", "interpretation"),
        C.Origine("piece-2", "https://autorite.example/avis/1", "mesure"),
        C.Origine("piece-3", "https://revue-specialisee.example/chiffres", "mesure"),
        C.Origine("piece-4", "https://fictive-cotee.example/investisseurs/r.pdf", "mesure"),
        C.Origine("piece-5", "adresse illisible", "interpretation"),
    ]
    avant = C.pieces_a_signaler(asyncio.run(C.lire_fiche(depot, COTEE)), origines)
    b.check(avant == (), "[A9] tant que rien n'est révoqué, aucune pièce n'est signalée")
    asyncio.run(C.revoquer_source(depot, source="revue-specialisee.example",
                                  portee=C.PREFIXE_PORTEE_SPECIALITE + "specialite_fictive",
                                  auteur=C.UTILISATEUR, motif="a publié une information démentie", le="2026-12-02"))
    f = asyncio.run(C.lire_fiche(depot, COTEE))
    signalees = C.pieces_a_signaler(f, origines)
    b.require(signalees, 1, "[A9] une seule pièce s'appuyait sur la source révoquée")
    s = signalees[0] if signalees else None
    b.check(s is not None and s.piece == "piece-1" and s.source == "revue-specialisee.example"
            and s.revoquee_le == "2026-12-02" and s.motif == "a publié une information démentie",
            "[A9] la pièce signalée porte la source, la date et le motif de la révocation")
    b.check(not C.qualifier(f, origines[0].adresse, "interpretation").admise
            and "révoquée le 2026-12-02" in C.qualifier(f, origines[0].adresse, "interpretation").motif,
            "[A9] la source révoquée n'est plus admise, et le motif dit quand et pourquoi")
    b.check(C.pieces_a_signaler(asyncio.run(C.lire_fiche(depot, NON_COTEE)), origines) == (),
            "[A9] une société que la révocation ne concerne pas n'a aucune pièce signalée")
    asyncio.run(C.admettre_source(depot, source="revue-specialisee.example", portee=C.PORTEE_GENERALE,
                                  natures=["interpretation"], niveau="B", auteur=C.UTILISATEUR,
                                  motif="réadmise après rectificatif", le="2026-12-20"))
    b.check(C.pieces_a_signaler(asyncio.run(C.lire_fiche(depot, COTEE)), origines) == (),
            "[A9] une pièce couverte par une autre admission en vigueur n'est pas signalée")


def _a10(b: Bilan) -> None:
    depot = C.DepotMemoire()
    asyncio.run(_fiche_cotee(depot))
    asyncio.run(_sources_de_base(depot))
    f = asyncio.run(C.lire_fiche(depot, COTEE))
    for adresse, niveau, quoi in (
            ("https://inconnu.example/x", "C+", "une adresse inconnue"),
            ("pas une adresse", "C", "une adresse illisible"),
            ("", "C", "une adresse vide"),
            ("https://fausse-autorite.example/x", "C+", "un domaine qui ressemble à une source admise"),
            ("https://autorite.example.pirate.example/x", "C+", "un domaine qui contient celui d'une source admise"),
            ("https://nonfictive-cotee.example/", "C+", "un domaine qui finit comme le site de la société")):
        q = C.qualifier(f, adresse, "interpretation")
        b.check(not q.admise and q.niveau == niveau and q.motif.strip() != "",
                f"[A10] {quoi} n'est pas admise, niveau {niveau}, motif dit")
    q = C.qualifier(f, "https://donnees.autorite.example/x", "mesure")
    b.check(q.admise and q.niveau == "A", "[A10] un sous-domaine d'une source admise est couvert")


def _a11(b: Bilan) -> None:
    depot = C.DepotMemoire()
    etat = A.avancer(CD.EtatDossier(COTEE), [C.pas_fiche(None)], lecture_humaine={C.NOM_DU_MODULE: False})
    b.check(etat.arret is not None and etat.arret.motif == CD.ARRET_ACTE_HUMAIN
            and etat.arret.acte == C.ACTE_ETABLIR_LA_FICHE and C.NOM_DU_PAS not in etat.faits,
            "[A11] sans fiche, le chef de dossier s'arrête et nomme l'acte attendu")
    f = asyncio.run(_fiche_cotee(depot))
    etat = A.avancer(A.enregistrer_acte(etat, etat.arret.cle), [C.pas_fiche(f)],
                     lecture_humaine={C.NOM_DU_MODULE: False})
    b.check(C.NOM_DU_PAS in etat.faits and etat.depense.total_usd == 0.0
            and etat.arret.motif == CD.ARRET_PARCOURS_TERMINE,
            "[A11] la fiche établie, le dossier repart, sans dépense")
    autre = A.avancer(CD.EtatDossier("AUTRE-DOSSIER"), [C.pas_fiche(f)], lecture_humaine={C.NOM_DU_MODULE: False})
    b.check(C.NOM_DU_PAS not in autre.faits,
            "[A11] la fiche d'une société ne fait pas avancer le dossier d'une autre")
    lu = A.avancer(CD.EtatDossier(COTEE), [C.pas_fiche(f)])
    b.check(lu.arret.motif == CD.ARRET_ACTE_HUMAIN and lu.arret.cle.startswith("lecture:"),
            "[A11] par défaut, la fiche est relue par un humain avant que la suite s'en serve")


def _a0(b: Bilan) -> None:
    permis = {"__future__", "dataclasses", "typing", "json", "re", "datetime", "functools", "pathlib", "urllib"}
    dossier = BACKEND / "app" / "modules" / "emetteurs"
    sources = sorted(dossier.glob("*.py"))
    b.require(sources, 4, "[A0] quatre fichiers source dans le module")
    for src in sources:
        for noeud in ast.walk(ast.parse(src.read_text(encoding="utf-8"))):
            if isinstance(noeud, ast.Import):
                for alias in noeud.names:
                    b.check(alias.name.split(".")[0] in permis,
                            f"[A0] {src.name} importe `{alias.name}` : bibliothèque standard seulement")
            elif isinstance(noeud, ast.ImportFrom):
                interne = noeud.level == 1
                chef = noeud.level == 0 and noeud.module == "app.modules.chef_de_dossier.contrat"
                b.check(interne or chef or (noeud.level == 0 and (noeud.module or "").split(".")[0] in permis),
                        f"[A0] {src.name} importe depuis `{'.' * noeud.level}{noeud.module}` : lui-même, "
                        "le contrat du chef de dossier ou la bibliothèque standard seulement")
    from app.modules.emetteurs import regles
    ref = regles.referentiel()
    b.check(ref["niveau_sans_admission"] in ref["niveaux"] and len(ref["criteres"]) >= 1
            and len(ref["roles_qui_utilisent_les_sources"]) >= 1,
            "[A0] le référentiel se charge : échelle, critères écrits et rôles qui utilisent les sources")


def main() -> int:
    b = Bilan()
    for nom, section in (("[A1]", _a1), ("[A2]", _a2), ("[A3]", _a3), ("[A4]", _a4), ("[A5]", _a5),
                         ("[A6]", _a6), ("[A7]", _a7), ("[A8]", _a8), ("[A9]", _a9), ("[A10]", _a10),
                         ("[A11]", _a11), ("[A0]", _a0)):
        try:
            section(b)
        except Exception as exc:  # noqa: BLE001 — une section qui plante est un échec NOMMÉ
            b.check(False, f"{nom} section interrompue — {type(exc).__name__}: {exc}")
    return b.summary()


if __name__ == "__main__":
    sys.exit(main())
