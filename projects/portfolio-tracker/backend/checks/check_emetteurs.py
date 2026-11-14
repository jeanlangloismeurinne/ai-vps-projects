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
  [A16] les pages de relations investisseurs d'une AUTRE société (concurrent, client) : le système
        les admet lui-même, signé, critère cité ; l'utilisateur les révoque, le système ne les rétablit pas
  [A17] une source inconnue est jugée sur quelques publications : au seuil, le système l'admet ;
        en dessous, elle est mise en suspens et attend votre arbitrage ; la note est calculée par
        le code, jamais déclarée par l'évaluateur (arbitrage du 2026-11-14)
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


def _a16(b: Bilan) -> None:
    depot = C.DepotMemoire()
    asyncio.run(_fiche_cotee(depot))
    concurrent = "https://investors.concurrent.example/resultats/t3.pdf"
    avant = C.qualifier(asyncio.run(C.lire_fiche(depot, COTEE)), concurrent, "mesure")
    b.check(not avant.admise and avant.niveau == "C+",
            "[A16] avant l'acte du système, la page d'un concurrent n'est pas admise (la forme ne suffit pas)")
    adresses = [concurrent, "https://ir.client.example/communique", "https://www.ir.client.example/autre",
                "https://blog.quelconque.example/investors/x", "https://investors.example/x",
                "https://irlande.example/x", "pas une adresse"]
    rendu = asyncio.run(C.admettre_pages_investisseurs(depot, adresses, le=JOUR))
    b.check([(r["source"], r["issue"]) for r in rendu]
            == [("investors.concurrent.example", "admise"), ("ir.client.example", "admise")],
            "[A16] seules les adresses DÉDIÉES (ir., investors., …) sous le domaine d'une société sont reconnues, "
            "une fois chacune ; un chemin « /investors » d'un site quelconque, un domaine entier ou un nom qui "
            "commence pareil ne le sont pas")
    actes = asyncio.run(C.vue_ecran(depot))["journal_des_sources"]
    b.check(all(a["auteur"] == C.AUTEUR_PAGES_INVESTISSEURS and a["critere"] == C.CRITERE_PAGES_INVESTISSEURS
                and a["portee"] == C.PORTEE_GENERALE and a["le"] == JOUR and a["motif"].strip()
                for a in actes) and len(actes) == 2,
            "[A16] chaque admission est un acte du journal signé du système, qui cite son critère, daté et motivé")
    f = asyncio.run(C.lire_fiche(depot, COTEE))
    q = C.qualifier(f, concurrent, "mesure")
    b.check(q.admise and q.niveau == "A" and q.source == "investors.concurrent.example",
            "[A16] après l'acte, la page du concurrent vaut le niveau du critère pour toute analyse")
    b.check(asyncio.run(C.admettre_pages_investisseurs(depot, [concurrent], le=JOUR))
            == [{"source": "investors.concurrent.example", "issue": "deja_admise", "rang": 1}]
            and len(asyncio.run(C.vue_ecran(depot))["journal_des_sources"]) == 2,
            "[A16] rejouer ne réécrit rien : la page est déjà admise")
    asyncio.run(C.revoquer_source(depot, source="investors.concurrent.example", portee=C.PORTEE_GENERALE,
                                  auteur=C.UTILISATEUR, motif="société en litige, déclarations contestées",
                                  le="2026-11-20"))
    rendu = asyncio.run(C.admettre_pages_investisseurs(depot, [concurrent], le="2026-11-21"))
    f = asyncio.run(C.lire_fiche(depot, COTEE))
    b.check(rendu and rendu[0]["issue"] == "ecartee" and not C.qualifier(f, concurrent, "mesure").admise,
            "[A16] une page que l'utilisateur a révoquée reste révoquée : le système ne la rétablit pas")


QUESTIONS = ("auteur_identifie", "date_de_publication", "origine_des_chiffres", "premiere_main_ou_citee",
             "non_promotionnel")


def _publication(adresse: str, non: tuple[str, ...] = (), *, sans: str = "", constat: str = "vu") -> C.ExempleEvalue:
    """Une publication lue : « oui » partout sauf aux questions `non`."""
    return C.ExempleEvalue(adresse=adresse, reponses=tuple(
        C.Reponse(q, q not in non, constat) for q in QUESTIONS if q != sans))


def _evaluation(source: str, publications, *, critere: str = "presse_financiere", niveau: str = "B+",
                natures=("mesure", "evenement"), evaluateur: str = C.AUTEUR_EVALUATEUR) -> C.Evaluation:
    return C.Evaluation(source=source, portee=C.PORTEE_GENERALE, natures=tuple(natures), niveau=niveau,
                        critere=critere, exemples=tuple(publications), evaluateur=evaluateur)


def _a17(b: Bilan) -> None:
    from app.modules.emetteurs import regles
    ref = regles.referentiel()["evaluation_des_sources"]
    b.check(set(ref["questions"]) == set(QUESTIONS) and ref["seuil"] == 0.8 and ref["exemples_min"] == 3,
            "[A17] le référentiel porte la grille : cinq questions, seuil 0,80, trois publications au moins")
    depot = C.DepotMemoire()
    asyncio.run(_fiche_cotee(depot))
    ev = lambda e: asyncio.run(C.evaluer_source(depot, e, le=JOUR))  # noqa: E731
    fiche = lambda: asyncio.run(C.lire_fiche(depot, COTEE))  # noqa: E731
    journal = lambda: asyncio.run(C.vue_ecran(depot))["journal_des_sources"]  # noqa: E731

    # Au-dessus du seuil : admise par le système, sous le critère proposé, l'évaluation au journal.
    bonne = [_publication(f"https://www.bonne-presse.example/a{i}") for i in range(3)]
    r = ev(_evaluation("bonne-presse.example", bonne))
    a = journal()[-1]
    b.check(r["issue"] == "admise" and r["note"] == 1.0 and a["acte"] == C.ADMETTRE
            and a["auteur"] == C.AUTEUR_EVALUATEUR and a["critere"] == "presse_financiere" and a["niveau"] == "B+",
            "[A17] note 1,00 : la source est admise par le système, signée, sous le critère proposé")
    b.check(len(a["evaluation"].get("exemples", [])) == 3 and a["evaluation"].get("note") == 1.0
            and a["evaluation"].get("seuil") == 0.8 and "1.00" in a["motif"],
            "[A17] l'admission garde l'évaluation entière (publications lues, réponses, note, seuil)")
    q = C.qualifier(fiche(), "https://bonne-presse.example/x", "mesure")
    b.check(q.admise and q.niveau == "B+", "[A17] admise, elle qualifie ses pièces au niveau accordé")

    # Exactement au seuil : admise (4 « oui » sur 5 partout = 0,80).
    r = ev(_evaluation("juste.example", [_publication(f"https://juste.example/{i}", ("origine_des_chiffres",))
                                         for i in range(3)]))
    b.check(r["issue"] == "admise" and r["note"] == 0.8, "[A17] note égale au seuil : admise")

    # Sous le seuil : en suspens, non admise, et l'arbitrage vous revient.
    faible = [_publication("https://faible.example/1", ("origine_des_chiffres", "non_promotionnel")),
              _publication("https://faible.example/2", ("origine_des_chiffres",)),
              _publication("https://faible.example/3", ("origine_des_chiffres", "auteur_identifie"))]
    r = ev(_evaluation("faible.example", faible))
    b.check(r["issue"] == "en_suspens" and r["note"] == round(10 / 15, 4),
            "[A17] note 0,67 : en suspens ; la note est la part des « oui », calculée par le code")
    f = fiche()
    b.check([(x.source, x.niveau, x.critere, x.note, x.seuil) for x in f.en_suspens]
            == [("faible.example", "B+", "presse_financiere", round(10 / 15, 4), 0.8)],
            "[A17] la fiche porte la source en suspens, avec ce que l'évaluateur proposait")
    q = C.qualifier(f, "https://faible.example/article", "mesure")
    b.check(not q.admise and q.niveau == "C+" and "suspens" in q.motif and "arbitrage" in q.motif,
            "[A17] en suspens, la source n'est pas admise : ses pièces valent le plancher, le motif le dit")
    vue = asyncio.run(C.vue_ecran(depot))
    b.check([x["source"] for x in vue["en_suspens"]] == ["faible.example"]
            and vue["en_suspens"][0]["evaluation"]["exemples"][0]["reponses"][2]["oui"] is False
            and "evaluation_des_sources" in vue["referentiel"],
            "[A17] l'écran montre ce qui attend votre arbitrage, avec les réponses publication par publication")

    # Pas assez de publications lues, ou aucun critère : en suspens, quelle que soit la note.
    r = ev(_evaluation("rare.example", [_publication("https://rare.example/1"), _publication("https://rare.example/2")]))
    b.check(r["issue"] == "en_suspens" and r["note"] == 1.0 and "trop peu" in r["motif"],
            "[A17] deux publications lues sur trois : en suspens même à 1,00 (on ne juge pas sur si peu)")
    r = ev(_evaluation("inclassable.example", [_publication(f"https://inclassable.example/{i}") for i in range(3)],
                       critere=""))
    b.check(r["issue"] == "en_suspens" and "aucun critère" in r["motif"],
            "[A17] aucun critère écrit ne convient : en suspens, même à 1,00")

    # Une évaluation mal formée n'entre pas au journal.
    avant = len(journal())
    refus = [
        ("une publication d'un autre site", _evaluation("x1.example", [_publication("https://x1.example/1"),
                                                                       _publication("https://x1.example/2"),
                                                                       _publication("https://autre.example/3")])),
        ("un domaine qui ressemble", _evaluation("x2.example", [_publication(f"https://faux-x2.example/{i}")
                                                                 for i in range(3)])),
        ("une question sans réponse", _evaluation("x3.example", [_publication("https://x3.example/1"),
                                                                  _publication("https://x3.example/2"),
                                                                  _publication("https://x3.example/3",
                                                                               sans="non_promotionnel")])),
        ("une réponse sans constat", _evaluation("x4.example", [_publication(f"https://x4.example/{i}", constat=" ")
                                                                 for i in range(3)])),
        ("la même publication deux fois", _evaluation("x5.example", [_publication("https://x5.example/1")] * 3)),
        ("un rôle qui utilise les sources", _evaluation("x6.example", [_publication(f"https://x6.example/{i}")
                                                                       for i in range(3)],
                                                        evaluateur="systeme:collecteur")),
        ("un niveau au-delà du critère", _evaluation("x7.example", [_publication(f"https://x7.example/{i}")
                                                                     for i in range(3)], niveau="A")),
    ]
    for quoi, e in refus:
        b.check(refuse(C.evaluer_source(depot, e, le=JOUR)) is not None, f"[A17] évaluation refusée : {quoi}")
    b.check(len(journal()) == avant, "[A17] une évaluation refusée n'écrit rien au journal")
    b.check(refuse(regles.acter_source(depot, acte=C.SUSPENDRE, source="y.example", portee=C.PORTEE_GENERALE,
                                       natures=["mesure"], niveau="B", auteur=C.UTILISATEUR, motif="m", le=JOUR,
                                       critere="", evaluation={"note": 0.1})) is not None,
            "[A17] seul le système met une source en suspens")
    mauvaise = [_publication(f"https://bonne-presse.example/b{i}", ("origine_des_chiffres", "non_promotionnel"))
                for i in range(3)]
    b.check(refuse(C.evaluer_source(depot, _evaluation("bonne-presse.example", mauvaise, niveau="B"), le=JOUR))
            is not None
            and C.qualifier(fiche(), "https://bonne-presse.example/x", "mesure").admise,
            "[A17] une source admise n'est pas remise en suspens par une évaluation (on la révoque d'abord)")

    # Votre arbitrage tient : admise par vous, ou écartée — le système n'y revient pas.
    asyncio.run(C.admettre_source(depot, source="faible.example", portee=C.PORTEE_GENERALE,
                                  natures=["mesure", "evenement"], niveau="B", auteur=C.UTILISATEUR,
                                  motif="j'accepte la source, au niveau B", le="2026-11-15"))
    f = fiche()
    b.check(not f.en_suspens or all(x.source != "faible.example" for x in f.en_suspens),
            "[A17] admise par vous : elle sort des sources en suspens")
    b.check(C.qualifier(f, "https://faible.example/a", "mesure").niveau == "B",
            "[A17] admise par vous : ses pièces valent le niveau que vous avez donné")
    b.check(refuse(C.evaluer_source(depot, _evaluation("faible.example", faible), le="2026-11-16")) is not None,
            "[A17] le système ne réévalue pas une source que vous avez arbitrée")
    asyncio.run(C.revoquer_source(depot, source="rare.example", portee=C.PORTEE_GENERALE, auteur=C.UTILISATEUR,
                                  motif="blog personnel, pas une source", le="2026-11-15"))
    f = fiche()
    b.check(all(x.source != "rare.example" for x in f.en_suspens)
            and not C.qualifier(f, "https://rare.example/1", "mesure").admise,
            "[A17] écartée par vous : elle sort des sources en suspens, et n'est pas admise")
    b.check(C.pieces_a_signaler(f, [C.Origine("p1", "https://rare.example/1", "mesure")]) == (),
            "[A17] écarter une source en suspens ne signale aucune pièce : aucune ne s'appuyait dessus")
    b.check(refuse(C.evaluer_source(depot, _evaluation("rare.example", [_publication(f"https://rare.example/{i}")
                                                                         for i in range(3)]), le="2026-11-16"))
            is not None, "[A17] le système ne réévalue pas une source que vous avez écartée")

    # Le système peut réévaluer une source qu'il a lui-même mise en suspens (publications nouvelles).
    r = ev(_evaluation("inclassable.example", [_publication(f"https://inclassable.example/{i}") for i in range(3)]))
    b.check(r["issue"] == "admise" and all(x.source != "inclassable.example" for x in fiche().en_suspens),
            "[A17] réévaluée par le système avec un critère : admise, elle sort des sources en suspens")


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
                         ("[A11]", _a11), ("[A16]", _a16), ("[A17]", _a17), ("[A0]", _a0)):
        try:
            section(b)
        except Exception as exc:  # noqa: BLE001 — une section qui plante est un échec NOMMÉ
            b.check(False, f"{nom} section interrompue — {type(exc).__name__}: {exc}")
    return b.summary()


if __name__ == "__main__":
    sys.exit(main())
