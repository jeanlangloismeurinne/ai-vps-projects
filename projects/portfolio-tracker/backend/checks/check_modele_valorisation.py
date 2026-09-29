"""Vérification du MODÈLE DE VALORISATION propre à une entreprise — contrat, pont, évaluation (#97).

Sans réseau, sans modèle, sans base. Deux modèles FICTIFS, un par forme de fourchette arbitrée le
2026-09-29 — les chiffres éprouvent la mécanique, pas les titres :
  · forme RVMD (incertitude BINAIRE) : arbre d'événements, somme des programmes pondérée ;
  · forme NVDA (incertitude CONTINUE) : trois scénarios nommés sur des segments.

  • §1 LE CONTRAT refuse chaque incohérence interne, avec son motif (jamais « un refus quelconque »).
  • §2 LE PONT refuse chaque incohérence avec le dossier ou l'exécution, sous son code [A]…[E].
  • §3 L'ÉVALUATION rend les valeurs calculées À LA MAIN (arithmétique brute dans ce fichier, jamais
       via un gabarit : 4ᵉ faux vert), y compris, pour l'arbre, la valeur de chaque événement en échec
       et en succès ; changer une hypothèse recalcule, sans modèle.
  • §4 STRUCTURE : le module ne touche ni la base, ni le réseau, ni un agent.

Cible : pydantic v2 (container). Tester en container, **pas** le python hôte.
"""
from __future__ import annotations

import ast
import copy
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan  # noqa: E402

from pydantic import ValidationError  # noqa: E402

from app.contracts.modele_valorisation_schema import ModeleValorisation  # noqa: E402
from app.valorisation.modele import ModeleRefuse, evaluer_modele, valider_pont_modele  # noqa: E402

MODULE = Path(__file__).resolve().parent.parent / "app" / "valorisation" / "modele.py"
b = Bilan()


def proche(a: object, attendu: float) -> bool:
    return isinstance(a, (int, float)) and abs(a - attendu) <= 1e-9 * max(1.0, abs(attendu))


from _modeles_fictifs import (  # noqa: E402
    ARBRE, DOSSIER_NVDA, DOSSIER_RVMD, METHODO, SCENARIOS, hyp, jugement, piece, reprise)




def modifie(base: dict, **chemins) -> dict:
    m = copy.deepcopy(base)
    for k, v in chemins.items():
        m[k] = v
    return m


def refus_contrat(payload: dict) -> str:
    try:
        ModeleValorisation.model_validate(payload)
    except ValidationError as e:
        return str(e)
    except Exception as e:  # noqa: BLE001 — une panne du validateur est un FAIL nommé, pas une mort
        return f"AUTRE EXCEPTION {type(e).__name__}: {e}"
    return "PAS DE REFUS"


def refus_pont(payload: dict, dossier: dict, ticker: str) -> str:
    try:
        m = ModeleValorisation.model_validate(payload)
    except ValidationError as e:
        return f"REFUS DU CONTRAT (pas du pont) : {e}"
    try:
        valider_pont_modele(m, ticker_id=ticker, **dossier)
    except ModeleRefuse as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return f"AUTRE EXCEPTION {type(e).__name__}: {e}"
    return "PAS DE REFUS"


# ── §1 Le contrat ────────────────────────────────────────────────────────────────────────────
print("§1 contrat")
b.check(refus_contrat(ARBRE) == "PAS DE REFUS", "le modèle arbre est conforme")
b.check(refus_contrat(SCENARIOS) == "PAS DE REFUS", "le modèle scénarios est conforme")

hyps = ARBRE["hypotheses"]
sc = SCENARIOS["fourchette"]["scenarios"]
cas_contrat = [
    ("hypothèse en double", modifie(ARBRE, hypotheses=hyps + [hyp("actions", 11, piece(502))]), "même hypothèse"),
    ("segment non déclaré", modifie(ARBRE, hypotheses=hyps + [hyp("x", 1, piece(502), "programme_z")]), "segment non déclaré"),
    ("segment de façade", modifie(ARBRE, segments=ARBRE["segments"] + [{"id": "programme_c", "libelle": "Côlon", "perimetre": "Cancer colorectal métastatique."}]), "découpage de façade"),
    ("segments en double", modifie(ARBRE, segments=ARBRE["segments"] + [ARBRE["segments"][0]]), "même identifiant"),
    ("nom réservé", modifie(ARBRE, hypotheses=hyps + [hyp("segments", 1, piece(502))]), "réservé"),
    ("probabilité inconnue", modifie(ARBRE, fourchette={"forme": "arbre_evenements", "evenements": [
        {"id": "e", "recit": "Un événement que rien ne probabilise.", "probabilite": "programme_a.inconnue"}]}), "absente du tableau"),
    ("probabilité hors [0,1]", modifie(ARBRE, hypotheses=[h if (h["nom"], h["segment"]) != ("probabilite", "programme_a")
        else {**h, "valeur": 1.3} for h in hyps]), "entre 0 et 1"),
    ("deux événements, une probabilité", modifie(ARBRE, fourchette={"forme": "arbre_evenements", "evenements": [
        {"id": "e1", "recit": "Premier récit d'un même événement.", "probabilite": "programme_a.probabilite"},
        {"id": "e2", "recit": "Second récit d'un même événement.", "probabilite": "programme_a.probabilite"}]}), "un seul événement"),
    ("deux événements, même identifiant", modifie(ARBRE, fourchette={"forme": "arbre_evenements", "evenements": [
        {"id": "e", "recit": "Le programme A obtient son autorisation.", "probabilite": "programme_a.probabilite"},
        {"id": "e", "recit": "Le programme B obtient son autorisation.", "probabilite": "programme_b.probabilite"}]}), "même identifiant"),
    ("rôle manquant", modifie(SCENARIOS, fourchette={"forme": "scenarios_nommes", "scenarios": [sc[0], sc[1], sc[1]]}), "un par rôle"),
    ("central qui modifie le tableau", modifie(SCENARIOS, fourchette={"forme": "scenarios_nommes", "scenarios": [
        sc[0], {**sc[1], "valeurs": {"actions": 12}}, sc[2]]}), "EST le tableau signé"),
    ("scénario haut sans hypothèse", modifie(SCENARIOS, fourchette={"forme": "scenarios_nommes", "scenarios": [
        sc[0], sc[1], {**sc[2], "valeurs": {}}]}), "quelles hypothèses le séparent"),
    ("scénario sur hypothèse inconnue", modifie(SCENARIOS, fourchette={"forme": "scenarios_nommes", "scenarios": [
        {**sc[0], "valeurs": {"centres_de_donnees.prix": 1.0}}, sc[1], sc[2]]}), "absentes du tableau"),
    ("jugement sans taux de base sourcé", modifie(ARBRE, hypotheses=hyps[:3] + [hyp("marge_nette", 0.3, {
        "type": "jugement", "taux_de_base": {"classe_de_reference": "marges nettes des biotechs commerciales",
        "valeur": 0.25, "source_entry_refs": []}, "ecart_justifie": "Molécule sans concurrence directe identifiée."})] + hyps[4:]), "at least 1"),
    ("jugement sans écart justifié", modifie(ARBRE, hypotheses=hyps[:3] + [hyp("marge_nette", 0.3, {
        **jugement(503), "ecart_justifie": "parce que"})] + hyps[4:]), "at least 30"),
    ("origine inconnue", modifie(ARBRE, hypotheses=hyps[:3] + [hyp("marge_nette", 0.3, {"type": "memoire"})] + hyps[4:]), "does not match any of the expected tags"),
    ("méthodologie non décrite", modifie(ARBRE, methodologie="Somme des programmes."), "at least 80"),
]
b.require(cas_contrat, 17, "cas de refus du contrat")
for label, payload, motif in cas_contrat:
    m = refus_contrat(payload)
    b.check(motif in m, f"contrat — « {label} » : motif attendu « {motif} », obtenu « {m[:160]} »")

# ── §2 Le pont ───────────────────────────────────────────────────────────────────────────────
print("§2 pont")
b.check(refus_pont(ARBRE, DOSSIER_RVMD, "RVMD") == "PAS DE REFUS", "le modèle arbre passe le pont")
b.check(refus_pont(SCENARIOS, DOSSIER_NVDA, "NVDA") == "PAS DE REFUS", "le modèle scénarios passe le pont")


def remplace_hyp(base: dict, cle: tuple, **champs) -> dict:
    m = copy.deepcopy(base)
    m["hypotheses"] = [{**h, **champs} if (h["nom"], h["segment"]) == cle else h for h in m["hypotheses"]]
    return m


cas_pont = [
    ("modèle d'un autre titre", ARBRE, DOSSIER_RVMD, "NVDA", "[A]", "présenté pour"),
    ("réponse reprise non acquittée", ARBRE, {**DOSSIER_RVMD, "reponses_acquittees": {}}, "RVMD", "[A]", "n'est pas une réponse acquittée"),
    ("réponse reprise d'une autre question", ARBRE, {**DOSSIER_RVMD, "reponses_acquittees": {901: "qf_2"}}, "RVMD", "[A]", "répond à qf_2"),
    ("pièce hors dossier", ARBRE, {**DOSSIER_RVMD, "pieces_du_dossier": {501, 503, 504}}, "RVMD", "[B]", "[502]"),
    ("taux de base hors dossier", ARBRE, {**DOSSIER_RVMD, "pieces_du_dossier": {501, 502, 504}}, "RVMD", "[B]", "[503]"),
    # Les fixtures [C] lisent tout le tableau : sinon [D] les arrête avant l'exécution (assert à côté).
    ("mécanique qui échoue", modifie(ARBRE, mecanique=ARBRE["mecanique"] + "valeur_action = valeur_action / 0\n"), DOSSIER_RVMD, "RVMD", "[C]", "division par zéro"),
    ("sortie absente", modifie(ARBRE, mecanique=ARBRE["mecanique"].replace("valeur_action =", "autre =")), DOSSIER_RVMD, "RVMD", "[C]", "ne définit pas un nombre"),
    ("sortie non numérique", modifie(ARBRE, mecanique=ARBRE["mecanique"] + "valeur_action = [1]\n"), DOSSIER_RVMD, "RVMD", "[C]", "ne définit pas un nombre"),
    ("hypothèse au nom d'un gabarit", modifie(remplace_hyp(ARBRE, ("actions", None), nom="dcf"),
        mecanique=ARBRE["mecanique"].replace("tresorerie_nette), actions)", "tresorerie_nette), dcf)")), DOSSIER_RVMD, "RVMD", "[C]", "nom d'hypothèse non admis"),
    ("hypothèse globale ignorée", modifie(ARBRE, hypotheses=hyps + [hyp("taux_impot", 0.21, piece(501))]), DOSSIER_RVMD, "RVMD", "[D]", "taux_impot"),
    ("hypothèse de segment ignorée", modifie(ARBRE, hypotheses=hyps + [hyp("prix", 100, piece(504), "programme_a")]), DOSSIER_RVMD, "RVMD", "[D]", "programme_a.prix"),
    ("scénarios croisés", modifie(SCENARIOS, fourchette={"forme": "scenarios_nommes", "scenarios": [
        {**sc[0], "valeurs": {"centres_de_donnees.croissance": 0.3}}, sc[1],
        {**sc[2], "valeurs": {"centres_de_donnees.croissance": 0.0}}]}), DOSSIER_NVDA, "NVDA", "[E]", "croisés"),
]
b.require(cas_pont, 12, "cas de refus du pont")
for label, payload, dossier, ticker, code, fragment in cas_pont:
    m = refus_pont(payload, dossier, ticker)
    b.check(m.startswith(code) and fragment in m,
            f"pont — « {label} » : refus {code} « {fragment} » attendu, obtenu « {m[:160]} »")

# ── §3 L'évaluation ──────────────────────────────────────────────────────────────────────────
print("§3 évaluation")


def rvmd_main(pa: float, pb: float) -> float:
    a = pa * (30 / 1.1 + 30 / 1.1 ** 2)
    bb = pb * (15 / 1.1 ** 2)
    return (a + bb + 10) / 10


m_arbre = ModeleValorisation.model_validate(ARBRE)
ev = evaluer_modele(m_arbre)
b.check(proche(ev.central, rvmd_main(0.5, 0.4)), f"arbre : central = valeur pondérée ({ev.central})")
b.check(proche(ev.bas, rvmd_main(0, 0)), f"arbre : bas = tous les événements échouent ({ev.bas})")
b.check(proche(ev.haut, rvmd_main(1, 1)), f"arbre : haut = tous réussissent ({ev.haut})")
b.require(ev.par_evenement, 2, "arbre : un détail par événement")
b.check(proche(ev.par_evenement.get("succes_a", (0, 0))[0], rvmd_main(0, 0.4))
        and proche(ev.par_evenement.get("succes_a", (0, 0))[1], rvmd_main(1, 0.4)),
        "arbre : A en échec / en succès, B à sa probabilité")
b.check(proche(ev.par_evenement.get("succes_b", (0, 0))[0], rvmd_main(0.5, 0))
        and proche(ev.par_evenement.get("succes_b", (0, 0))[1], rvmd_main(0.5, 1)),
        "arbre : B en échec / en succès, A à sa probabilité")
b.check(ev.operations > 0, "arbre : opérations comptées")


def nvda_main(g_dc: float, m_dc: float) -> float:
    fl = [100 * m_dc * (1 + g_dc) ** k + 5 for k in (1, 2, 3)]
    v = sum(f / 1.1 ** (i + 1) for i, f in enumerate(fl)) + fl[-1] * 1.03 / 0.07 / 1.1 ** 3
    return v / 10


ev2 = evaluer_modele(ModeleValorisation.model_validate(SCENARIOS))
b.check(proche(ev2.central, nvda_main(0.2, 0.5)), f"scénarios : central = tableau tel quel ({ev2.central})")
b.check(proche(ev2.bas, nvda_main(0.0, 0.4)), f"scénarios : bas = ses deux hypothèses modifiées ({ev2.bas})")
b.check(proche(ev2.haut, nvda_main(0.3, 0.5)), f"scénarios : haut = sa seule hypothèse modifiée ({ev2.haut})")
b.check(ev2.par_evenement == {}, "scénarios : pas de détail par événement")

# Changer UNE hypothèse recalcule — même mécanique, aucun modèle — et le modèle n'est pas modifié.
avant = m_arbre.model_dump()
autre = ModeleValorisation.model_validate(remplace_hyp(ARBRE, ("probabilite", "programme_a"), valeur=0.8))
b.check(proche(evaluer_modele(autre).central, rvmd_main(0.8, 0.4)), "probabilité de A à 0,8 : le central se recalcule")
b.check(proche(evaluer_modele(autre).bas, ev.bas), "le bas ne dépend pas de la probabilité (tous échouent)")
b.check(m_arbre.model_dump() == avant, "l'évaluation ne modifie pas le modèle")
b.check(evaluer_modele(m_arbre) == ev, "même modèle, même évaluation")

# ── §4 Structure ─────────────────────────────────────────────────────────────────────────────
print("§4 structure")
mods: set[str] = set()
for node in ast.walk(ast.parse(MODULE.read_text(encoding="utf-8"))):
    if isinstance(node, ast.Import):
        mods |= {a.name for a in node.names}
    elif isinstance(node, ast.ImportFrom):
        mods.add(node.module or "")
b.check(mods == {"__future__", "ast", "dataclasses", "typing", "app.contracts.modele_valorisation_schema",
                 "app.valorisation.bac_a_calcul"}, f"le module est pur : aucune base, aucun réseau, aucun agent ({sorted(mods)})")

sys.exit(b.summary())
