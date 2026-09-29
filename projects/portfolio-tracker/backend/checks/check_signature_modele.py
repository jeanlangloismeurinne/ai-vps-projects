"""Vérification de la SIGNATURE du modèle de valorisation — contrat et règles de lecture (roadmap 05,
capacité 4 bis, migration 051). Sans réseau, sans modèle, sans base : le registre est construit en
mémoire à partir des deux modèles fictifs partagés (`_modeles_fictifs`).

  • §1 LE CONTRAT : signer ⟺ fourchette ; fourchette ordonnée ; la ligne porte le modèle de son titre
       et de sa version ; un état servi incohérent avec ses pièces est refusé.
  • §2 CE QUE LE COMITÉ VOIT (`servir_atelier`) : aucun modèle → en attente → signé → nouvelle version
       en attente (la signée reste affichée, l'écart ligne à ligne) → remplacée par une plus récente →
       écartée (la signée reste la référence) ; un modèle signé qui ne tient plus est « à revoir » en
       disant pourquoi, la fourchette SIGNÉE toujours au PV ; une proposition qui ne tient pas n'est pas
       signable.
  • §3 STRUCTURE : `valorisation/signature.py` est le seul à écrire dans les registres de la 051.

Cible : pydantic v2 (container). Tester en container, **pas** le python hôte.
"""
from __future__ import annotations

import copy
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan, strip_code  # noqa: E402
from _modeles_fictifs import ARBRE, DOSSIER_NVDA, DOSSIER_RVMD, SCENARIOS, hyp, piece  # noqa: E402

from pydantic import ValidationError  # noqa: E402

from app.contracts.modele_valorisation_schema import ModeleValorisation  # noqa: E402
from app.contracts.signature_modele_schema import (  # noqa: E402
    AtelierServi, DecisionModele, Fourchette, PropositionServie, VersionModele)
from app.valorisation.modele import evaluer_modele  # noqa: E402
from app.valorisation.signature import (  # noqa: E402
    DossierValorisation, ecart_entre, reponses_reprenables, servir_atelier, version_en_attente)

APP = Path(__file__).resolve().parent.parent / "app"
b = Bilan()
T0 = datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc)


def refus(cls, **champs) -> str:
    try:
        cls.model_validate(champs)
    except ValidationError as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return f"AUTRE EXCEPTION {type(e).__name__}: {e}"
    return "PAS DE REFUS"


def dossier(d: dict, ticker: str, **surcharges) -> DossierValorisation:
    x = {**d, **surcharges}
    return DossierValorisation(ticker_id=ticker, reponses_acquittees=x["reponses_acquittees"],
                               pieces_du_dossier=frozenset(x["pieces_du_dossier"]),
                               questions_sans_objet=frozenset(x["questions_sans_objet"]),
                               reprises_admises=x["reprises_admises"])


def version(base: dict, n: int, id_: int) -> VersionModele:
    m = copy.deepcopy(base)
    m["version"] = n
    return VersionModele(id=id_, ticker_id=m["ticker_id"], version=n, auteur="agent de valorisation",
                         propose_le=T0 + timedelta(hours=n), modele=ModeleValorisation.model_validate(m))


def decision(id_: int, v: VersionModele, action: str, fourchette=None) -> DecisionModele:
    return DecisionModele(id=id_, modele_id=v.id, ticker_id=v.ticker_id, version=v.version, action=action,
                          auteur="membre du comité", motif="relu en séance, hypothèses ancrées",
                          fourchette=fourchette, decide_le=T0 + timedelta(days=id_))


def vu(label: str, versions, pv, d: DossierValorisation) -> AtelierServi:
    """`servir_atelier`, dont une EXCEPTION devient un FAIL nommé au lieu de tuer le script avant son
    bilan (2ᵉ faux vert) : le contrat de l'état servi refuse certaines erreurs de la règle, et ce refus
    doit se lire sous l'assert qu'il concerne. Rend alors un état vide qui fait rougir les suivants."""
    try:
        return servir_atelier(versions, pv, d, genere_le=T0)
    except Exception as e:  # noqa: BLE001
        b.check(False, f"{label} — servir_atelier a levé : {type(e).__name__}: {str(e)[:160]}")
        return AtelierServi.model_construct(ticker_id=d.ticker_id, etat="ERREUR", signee=None,
                                            en_attente=None, versions_proposees=-1, proces_verbal=[],
                                            genere_le=T0)


def fourchette_calculee(v: VersionModele) -> Fourchette:
    ev = evaluer_modele(v.modele)
    return Fourchette(bas=ev.bas, central=ev.central, haut=ev.haut, par_evenement=dict(ev.par_evenement))


# ── §1 Le contrat ────────────────────────────────────────────────────────────────────────────
print("§1 contrat")
F = {"bas": 20.0, "central": 38.0, "haut": 61.0}
D = {"id": 1, "modele_id": 1, "ticker_id": "RVMD", "version": 1, "auteur": "membre", "motif": "relu",
     "decide_le": T0}
b.check(refus(DecisionModele, **D, action="signer", fourchette=F) == "PAS DE REFUS", "une signature avec sa fourchette est conforme")
b.check(refus(DecisionModele, **D, action="ecarter") == "PAS DE REFUS", "un écart sans fourchette est conforme")
b.check("porte la fourchette signée" in refus(DecisionModele, **D, action="signer"),
        "signer SANS fourchette est refusé (le PV serait illisible six mois plus tard)")
b.check("porte la fourchette signée" in refus(DecisionModele, **D, action="ecarter", fourchette=F),
        "écarter AVEC une fourchette est refusé (écarter n'adopte aucun chiffre)")
b.check("non ordonnée" in refus(Fourchette, bas=40.0, central=38.0, haut=61.0), "une fourchette croisée (bas > central) est refusée")
b.check("non ordonnée" in refus(Fourchette, bas=20.0, central=62.0, haut=61.0), "une fourchette croisée (central > haut) est refusée")
b.check("texte blanc" in refus(DecisionModele, **{**D, "motif": "   "}, action="ecarter"), "un motif blanc est refusé (A7)")
b.check("texte blanc" in refus(DecisionModele, **{**D, "auteur": " "}, action="ecarter"), "une décision non signée est refusée")
b.check(refus(DecisionModele, **D, action="amender") != "PAS DE REFUS", "une action hors vocabulaire est refusée")
v_ok = {"id": 1, "ticker_id": "RVMD", "version": 1, "auteur": "agent", "propose_le": T0, "modele": ARBRE}
b.check(refus(VersionModele, **v_ok) == "PAS DE REFUS", "une version qui porte son propre modèle est conforme")
b.check("ne porte pas le modèle" in refus(VersionModele, **{**v_ok, "ticker_id": "NVDA"}),
        "une ligne NVDA qui porte le modèle RVMD est refusée")
b.check("ne porte pas le modèle" in refus(VersionModele, **{**v_ok, "version": 2}),
        "une ligne v2 qui porte le modèle v1 est refusée")
b.check("signable ssi" in refus(PropositionServie, version=v_ok, signable=True, motif_refus="[B] pièce absente", fourchette=F),
        "une proposition « signable » malgré un motif de refus est refusée")
b.check("montre sa fourchette" in refus(PropositionServie, version=v_ok, signable=True),
        "une proposition signable sans fourchette est refusée")
b.check("attendu d'après ses pièces" in refus(AtelierServi, ticker_id="RVMD", etat="signe", versions_proposees=0, genere_le=T0),
        "un état « signé » servi sans version signée est refusé")

# ── §2 Ce que le comité voit ─────────────────────────────────────────────────────────────────
print("§2 servir_atelier")
DR = dossier(DOSSIER_RVMD, "RVMD")

a = vu('registre vide', [], [], DR)
b.check(a.etat == "aucun_modele_propose" and a.signee is None and a.en_attente is None,
        f"aucun modèle au registre → `aucun_modele_propose` (servi : {a.etat})")

v1 = version(ARBRE, 1, 11)
a = vu('v1 proposée', [v1], [], DR)
b.check(a.etat == "en_attente_de_signature", f"une version proposée → `en_attente_de_signature` (servi : {a.etat})")
b.check(a.en_attente is not None and a.en_attente.signable and a.en_attente.fourchette == fourchette_calculee(v1),
        "la proposition qui tient est signable et montre sa fourchette calculée")
b.check(a.en_attente is not None and a.en_attente.ecart is None, "sans version signée, aucun écart n'est affiché")
b.check(a.en_attente is not None and set(a.en_attente.fourchette.par_evenement) == {"succes_a", "succes_b"},
        "arbre d'événements : la proposition dit la valeur de chaque programme en échec et en succès")

s1 = decision(1, v1, "signer", fourchette_calculee(v1))
a = vu('v1 signée', [v1], [s1], DR)
b.check(a.etat == "signe" and a.signee is not None and a.signee.etat == "tient",
        f"v1 signée, dossier inchangé → `signe`, le modèle tient (servi : {a.etat})")
b.check(a.signee is not None and a.signee.fourchette_du_jour == s1.fourchette,
        "la fourchette du jour d'un modèle qui tient est la fourchette signée")
b.check(a.en_attente is None, "la version signée n'est plus en attente")

# v2 : l'analyste relève les ventes au pic du programme A — un jugement changé = nouvelle version (#97 n°6).
m2 = copy.deepcopy(ARBRE)
next(h for h in m2["hypotheses"] if h["nom"] == "ventes_pic" and h["segment"] == "programme_a")["valeur"] = 140
v2 = version(m2, 2, 12)
a = vu('v2 proposée après la signature de v1', [v1, v2], [s1], DR)
b.check(a.etat == "signe_nouvelle_version_en_attente", f"v2 proposée après la signature de v1 → nouvelle version en attente (servi : {a.etat})")
b.check(a.signee is not None and a.signee.version.version == 1 and a.signee.signature.fourchette == s1.fourchette,
        "la version SIGNÉE reste affichée avec sa fourchette tant que v2 n'est pas signée (#97 n°6)")
e = a.en_attente.ecart if a.en_attente else None
b.check(e is not None and [(l.cle, l.avant, l.apres) for l in e.hypotheses_modifiees] == [("programme_a.ventes_pic", 100.0, 140.0)]
        and not e.hypotheses_ajoutees and not e.mecanique_changee and not e.forme_changee,
        f"l'écart dit la seule ligne changée, avant → après (servi : {e})")
b.check(a.en_attente is not None and a.signee is not None
        and a.en_attente.fourchette.central > a.signee.signature.fourchette.central,
        "des ventes au pic plus hautes relèvent le central proposé au-dessus du signé")

# v3 proposée avant que le comité ait décidé v2 : v2 est remplacée.
v3 = version(m2, 3, 13)
b.check(version_en_attente([v1, v2, v3], [s1]) == v3, "v3 proposée avant la séance → seule v3 est en attente")
a = vu('v3 proposée avant la séance', [v1, v2, v3], [s1], DR)
b.check(a.en_attente is not None and a.en_attente.version.version == 3 and a.versions_proposees == 3,
        "v2 remplacée n'est plus décidable, elle reste comptée au registre")

x3 = decision(2, v3, "ecarter")
a = vu('v3 écartée → la v1 signée reste la référence', [v1, v2, v3], [x3, s1], DR)
b.check(a.etat == "signe" and a.signee.version.version == 1 and a.en_attente is None,
        f"v3 écartée → la v1 signée reste la référence (servi : {a.etat})")
b.check([d.id for d in a.proces_verbal] == [2, 1], "le PV est servi le plus récent d'abord")

x1 = decision(1, v1, "ecarter")
a = vu('toutes les versions écartées', [v1], [x1], DR)
b.check(a.etat == "aucun_modele_signe" and a.signee is None and a.en_attente is None,
        f"toutes les versions écartées → `aucun_modele_signe`, jamais « aucun modèle proposé » (servi : {a.etat})")

# v4 signée après v1 : la signature en vigueur est la plus récente.
v4 = version(m2, 4, 14)
s4 = decision(3, v4, "signer", fourchette_calculee(v4))
a = vu('une signature plus récente remplace', [v1, v2, v3, v4], [s4, x3, s1], DR)
b.check(a.signee is not None and a.signee.version.version == 4, "une signature plus récente remplace la précédente")

# Le dossier bouge après la signature.
DR_sans_piece = dossier(DOSSIER_RVMD, "RVMD", pieces_du_dossier={501, 502, 503})
a = vu('une pièce du tableau remplacée depuis', [v1], [s1], DR_sans_piece)
b.check(a.signee is not None and a.signee.etat == "a_revoir" and "504" in a.signee.motif_etat,
        f"une pièce du tableau remplacée depuis → modèle signé « à revoir », la pièce NOMMÉE (servi : {a.signee.motif_etat if a.signee else None})")
b.check(a.etat == "signe" and a.signee.signature.fourchette == s1.fourchette,
        "« à revoir » ne retire pas la valorisation : la fourchette signée reste au PV et affichée")
b.check(a.signee is not None and a.signee.fourchette_du_jour is not None, "la mécanique tourne encore : la fourchette du jour est rendue")
DR_sans_qf1 = dossier(DOSSIER_RVMD, "RVMD", reponses_acquittees={})
a = vu('la réponse reprise n est plus acquittée', [v1], [s1], DR_sans_qf1)
b.check(a.signee is not None and a.signee.etat == "a_revoir" and "#901" in a.signee.motif_etat,
        "la réponse reprise (coût du capital de qf_1) n'est plus acquittée → « à revoir », la réponse nommée")
a = vu('une proposition qui ne tient pas', [v1, v2], [s1], DR_sans_piece)
b.check(a.en_attente is not None and not a.en_attente.signable and a.en_attente.fourchette is None
        and "504" in (a.en_attente.motif_refus or ""),
        "une proposition qui ne tient pas contre le dossier du jour n'est pas signable, et dit pourquoi")

# L'écart sur l'autre forme : un segment ajouté (produit lancé), une origine changée.
n2 = copy.deepcopy(SCENARIOS)
n2["segments"].append({"id": "automobile", "libelle": "Automobile", "perimetre": "Calculateurs embarqués pour véhicules."})
n2["hypotheses"] += [hyp("ca", 5, piece(601), "automobile"), hyp("marge_fcf", 0.1, piece(601), "automobile"),
                     hyp("croissance", 0.4, piece(601), "automobile")]
next(h for h in n2["hypotheses"] if h["nom"] == "actions")["origine"] = piece(601)
e = ecart_entre(ModeleValorisation.model_validate(SCENARIOS), ModeleValorisation.model_validate(n2))
b.check(e.segments_ajoutes == ["automobile"] and e.hypotheses_ajoutees == ["automobile.ca", "automobile.croissance", "automobile.marge_fcf"],
        f"un produit lancé = un segment et ses lignes AJOUTÉS, nommés (servi : {e.segments_ajoutes}, {e.hypotheses_ajoutees})")
b.check(e.origines_changees == ["actions"] and not e.hypotheses_modifiees,
        "même chiffre, autre source : l'origine changée est signalée sans passer pour un chiffre modifié")
b.check(ecart_entre(ModeleValorisation.model_validate(SCENARIOS), ModeleValorisation.model_validate(ARBRE | {"ticker_id": "NVDA"})).forme_changee,
        "passer des scénarios à un arbre d'événements est signalé comme changement de forme")
DN = dossier(DOSSIER_NVDA, "NVDA")
vn = version(SCENARIOS, 1, 21)
a = vu('scénarios nommés', [vn], [], DN)
b.check(a.en_attente is not None and a.en_attente.signable and a.en_attente.fourchette.par_evenement == {},
        "scénarios nommés : signable, sans détail par événement")

# ── §2 bis Les réponses reprenables ─────────────────────────────────────────────────────────
print("§2 bis réponses reprenables")
from types import SimpleNamespace as NS  # noqa: E402


def lue(aid: int, qid: str, verdict: str, statut: str, actualite: str | None):
    return NS(answer_id=aid, verdict=verdict,
              servie=NS(question_id=qid, statut=statut,
                        fondation=None if actualite is None else NS(actualite=actualite)))


rep = reponses_reprenables([
    lue(1, "qf_1", "acquitte", "repondu", "courante"),
    lue(2, "qf_2", "acquitte", "approxime", "courante"),
    lue(3, "mo_1", "acquitte", "repondu", "perimee"),
    lue(4, "mo_2", "acquitte", "repondu", "indeterminable"),
    lue(5, "qf_3", "renvoye", "repondu", "courante"),
    lue(6, "qf_7", "acquitte", "sans_objet", None),
    lue(7, "qf_4", None, "repondu", "courante"),
])
b.check(rep == {1: "qf_1", 2: "qf_2"},
        f"seules les réponses acquittées ET courantes, qui portent un chiffre, sont reprenables (rendues : {rep})")
b.check(3 not in rep, "une réponse acquittée mais PÉRIMÉE par un fait publié depuis n'est pas reprise")
b.check(6 not in rep, "un hors-sujet motivé tient, mais ne porte aucun chiffre à reprendre")


# ── §3 Structure ─────────────────────────────────────────────────────────────────────────────
print("§3 structure")
ecrivains = sorted(str(p.relative_to(APP)) for p in APP.rglob("*.py")
                   if "INSERT INTO modeles_valorisation" in strip_code(p.read_text()))
b.check(ecrivains == ["valorisation/signature.py"],
        f"`valorisation/signature.py` est le SEUL à écrire dans les registres de la 051 (trouvés : {ecrivains})")

sys.exit(b.summary())
