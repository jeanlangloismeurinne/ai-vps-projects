"""Vérification du contrat de DÉCISION / VALIDATION (§9, lot 7) — pur, sans réseau ni DB ni LLM.

C'est le contrat où G2 s'exerce le plus fort : la décision est contrainte par l'analyse, pas par
l'UX. Tout le reste du flux produit du jugement ; ici on ne juge plus, on acquitte — et un acte
incohérent avec l'analyse doit être refusé AVANT la moindre écriture, puisqu'il crée une position
réelle et débite du cash réel.

Ce qu'on éprouve ici :

  • **G2** — seuls `PROCEED` / `PROCEED_AVEC_CONDITIONS` créent une position. Un `PASSER` validé
    « quand même » est le mode de panne qui viderait le flux de son sens.
  • **§9 bijection** — les acquittements couvrent EXACTEMENT les risques acceptés. Les trois formes
    de trou sont testées séparément parce qu'elles ne se ressemblent pas : un ack MANQUANT (risque
    avalé en silence), un ack FANTÔME (index inexistant), un ack EN DOUBLE (qui masque un manquant
    si l'on ne comptait que la longueur — le piège classique de ce genre de contrôle).
  • **Q6 cap Kelly** — le sizing n'est jamais libre : égal au recommandé, ou à l'override TRACÉ
    (A7), et jamais au-dessus de `pct_max`.
  • **falsifiabilité** — chaque risque accepté pointe une hypothèse existante : sans ce pont, le
    monitoring n'a rien à surveiller et la thèse n'est pas réfutable.
  • **G2 structurel** — le corps de la requête HTTP n'expose AUCUN champ de jugement. C'est la
    vérification la plus importante du fichier : les autres garde-fous ne valent que si la synthèse,
    le sizing et les conditions viennent de la BASE. S'ils devenaient des champs d'entrée, le
    contrat resterait vert tout en étant décoratif — il suffirait d'envoyer une synthèse
    complaisante. On teste donc la SURFACE, pas seulement les validateurs.
  • **règle #19** — copie runtime `app/contracts/` ↔ contrat figé `roadmap/provenance-cards/`.
    Le contrat figé n'est pas dans l'image (build context = ./backend) : il n'est comparé que s'il
    est monté sur /contract_frozen, et son absence est ANNONCÉE, jamais silencieuse.
"""
import sys
from pathlib import Path

from pydantic import ValidationError

from app.contracts import RiskMatrix, ThesisValidation

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def rejette(payload):
    """True si le contrat REFUSE le payload (comportement attendu)."""
    try:
        ThesisValidation(**payload)
        return False
    except (ValidationError, ValueError):
        return True


# ── Fixtures : une analyse minimale mais VALIDE ──────────────────────────────
REFS = [{"entry_id": 1, "version": 1}]
BR = {"reference_class": "semis 2015-2025", "taux": 0.35}


def risque(nom, hypo):
    return {"risque": nom, "probabilite": 0.3, "impact": "moyen", "reversible": True,
            "base_rate": BR, "reponse_si_materialise": "réduire", "hypothese_liee": hypo,
            "source_entry_refs": REFS}


def hypothese(hid):
    return {"id": hid, "enonce": f"énoncé {hid}", "kpi": "marge brute", "unite": "%",
            "seuil_alerte": 60.0, "seuil_invalidation": 55.0, "horizon": "4 trimestres",
            "base_rate": BR, "source_entry_refs": REFS}


SIZING = {
    "pct_formule": 4.0, "pct_recommande": 4.0, "pct_max": 6.0,
    "methode": "Kelly capée", "cap_applique": {"contrainte": "secteur", "valeur_pct": 6.0, "actif": True},
    "inputs": {"conviction": 0.7, "marge_securite": 0.25, "correlation_portefeuille": 0.4},
    "risques_correles_portefeuille": [], "cout_opportunite": "vs indice",
}

RM = {
    "schema_version": "v2.0.0", "verdict": "PROCEED", "rationale": "…",
    "axes": {"qualite_business": 0.8, "qualite_info": 0.7, "conviction": 0.7, "marge_securite": 0.25},
    "risques_acceptes": [risque("concentration client", "H1"), risque("cyclicité", "H2")],
    "pre_mortem": ["scénario A", "scénario B", "scénario C"],
    "position_sizing": SIZING, "conditions_entree": [],
    "sources_summary": {"tier_A": 40, "tier_B": 9, "tier_C_llm_memory": 0, "total_entries": 49},
}

BASE = {
    "schema_version": "v2.0.0", "thesis_id": 1, "research_memo_id": 2, "synthesis_analysis_id": 3,
    "synthesis": RM, "hypotheses": [hypothese("H1"), hypothese("H2")],
    "risk_acks": [{"risk_index": 0, "accepted": True}, {"risk_index": 1, "accepted": True}],
    "pre_mortem_acked": True, "position_sizing_pct": 4.0,
    "valuation_range": {"low": 90.0, "base": 120.0, "high": 150.0}, "conditions_entree": [],
}

print("§0 — la décision de référence est ACCEPTÉE (sinon tout le reste est ininterprétable)")
tv = ThesisValidation(**BASE)
check("décision cohérente acceptée", tv.position_sizing_pct == 4.0)
check("verdict figé lisible", tv.synthesis.verdict == "PROCEED")
check("hypothèses figées (pilotent le monitoring)", len(tv.hypotheses) == 2)
check("seuil d'invalidation porté par l'hypothèse", tv.hypotheses[0].seuil_invalidation == 55.0)

print("\n§1 — G2 : seul un verdict actionnable crée une position")
for verdict in ("PASSER", "SURVEILLER", "TOO_HARD"):
    check(f"verdict {verdict} REJETÉ",
          rejette({**BASE, "synthesis": {**RM, "verdict": verdict}}))
pac = {**RM, "verdict": "PROCEED_AVEC_CONDITIONS", "conditions_entree": ["sous 140€"]}
check("PROCEED_AVEC_CONDITIONS accepté si conditions figées",
      ThesisValidation(**{**BASE, "synthesis": pac,
                          "conditions_entree": ["sous 140€"]}).conditions_entree == ["sous 140€"])
check("PROCEED_AVEC_CONDITIONS sans conditions REJETÉ",
      rejette({**BASE, "synthesis": pac, "conditions_entree": []}))

print("\n§2 — §9 bijection des acquittements (les 3 formes de trou, distinctes)")
check("ack MANQUANT rejeté (risque avalé en silence)",
      rejette({**BASE, "risk_acks": [{"risk_index": 0, "accepted": True}]}))
check("ack FANTÔME rejeté (index inexistant)",
      rejette({**BASE, "risk_acks": BASE["risk_acks"] + [{"risk_index": 7, "accepted": True}]}))
check("ack EN DOUBLE rejeté (bon compte, mais un risque non couvert)",
      rejette({**BASE, "risk_acks": [{"risk_index": 0, "accepted": True},
                                     {"risk_index": 0, "accepted": True}]}))
check("aucun ack rejeté", rejette({**BASE, "risk_acks": []}))
check("ack `accepted=False` rejeté (on n'acquitte pas un risque par la négative)",
      rejette({**BASE, "risk_acks": [{"risk_index": 0, "accepted": False},
                                     {"risk_index": 1, "accepted": True}]}))

print("\n§3 — pré-mortem acquitté (obligatoire, §9)")
check("pre_mortem_acked=False REJETÉ", rejette({**BASE, "pre_mortem_acked": False}))

print("\n§4 — falsifiabilité : pont risques → hypothèses")
check("hypothèse manquante pour un risque REJETÉE",
      rejette({**BASE, "hypotheses": [hypothese("H1")], "risk_acks": BASE["risk_acks"]}))
check("hypothèse au mauvais id REJETÉE",
      rejette({**BASE, "hypotheses": [hypothese("H1"), hypothese("H9")]}))
check("aucune hypothèse REJETÉE", rejette({**BASE, "hypotheses": []}))

print("\n§5 — Q6 : le sizing n'est jamais libre")
check("sizing ≠ pct_recommande REJETÉ", rejette({**BASE, "position_sizing_pct": 5.0}))
check("sizing au-dessus de pct_max REJETÉ", rejette({**BASE, "position_sizing_pct": 9.0}))
check("sizing arbitrairement bas REJETÉ aussi (ce n'est pas 'prudent', c'est non tracé)",
      rejette({**BASE, "position_sizing_pct": 1.0}))
OVERRIDE = {**SIZING, "override_utilisateur": {"valeur_pct": 5.0, "override_reason": "corrélation SOX"}}
check("override TRACÉ (A7) accepté au sizing overridé",
      ThesisValidation(**{**BASE, "synthesis": {**RM, "position_sizing": OVERRIDE},
                          "position_sizing_pct": 5.0}).position_sizing_pct == 5.0)
check("override tracé : revenir au recommandé est REJETÉ (l'override fait foi)",
      rejette({**BASE, "synthesis": {**RM, "position_sizing": OVERRIDE}, "position_sizing_pct": 4.0}))
check("override SANS motif rejeté en amont (A7, traçabilité)",
      rejette({**BASE, "synthesis": {**RM, "position_sizing": {
          **SIZING, "override_utilisateur": {"valeur_pct": 5.0, "override_reason": ""}}},
          "position_sizing_pct": 5.0}))
check("override au-dessus du cap Kelly REJETÉ (l'override ne perce pas le plafond)",
      rejette({**BASE, "synthesis": {**RM, "position_sizing": {
          **SIZING, "override_utilisateur": {"valeur_pct": 12.0, "override_reason": "conviction"}}},
          "position_sizing_pct": 12.0}))

print("\n§6 — valuation_range figée et cohérente")
check("low > base REJETÉ", rejette({**BASE, "valuation_range": {"low": 130.0, "base": 120.0, "high": 150.0}}))
check("base > high REJETÉ", rejette({**BASE, "valuation_range": {"low": 90.0, "base": 160.0, "high": 150.0}}))
check("bornes égales acceptées (fourchette dégénérée mais cohérente)",
      ThesisValidation(**{**BASE, "valuation_range": {"low": 120.0, "base": 120.0, "high": 120.0}}
                       ).valuation_range.base == 120.0)

print("\n§7 — le contrat est FERMÉ (extra='forbid') : pas de champ clandestin")
check("champ inconnu REJETÉ", rejette({**BASE, "sizing_libre_pct": 20.0}))
check("schema_version figé", rejette({**BASE, "schema_version": "v1.0.0"}))

print("\n§8 — G2 STRUCTUREL : le corps HTTP n'expose aucun champ de jugement")
# Le test décisif : si la synthèse / le sizing / les conditions devenaient des champs d'ENTRÉE,
# tous les garde-fous ci-dessus resteraient verts tout en étant contournables — il suffirait
# d'envoyer une analyse complaisante. On vérifie donc la SURFACE de l'API, pas ses validateurs.
try:
    from app.api.analysis_v2 import ValidateV2Body

    champs = set(ValidateV2Body.model_fields)
    for interdit in ("synthesis", "position_sizing_pct", "conditions_entree", "hypotheses",
                     "valuation_range", "verdict", "risk_matrix_acked"):
        check(f"`{interdit}` n'est PAS un champ d'entrée (il vient de la base)",
              interdit not in champs, f"— champs exposés : {sorted(champs)}")
    check("les acquittements, eux, sont bien demandés",
          {"risk_acks", "pre_mortem_acked"} <= champs)
    check("les faits d'exécution sont demandés (hors contrat de décision)",
          {"shares", "purchase_price", "purchase_date"} <= champs)
except ImportError as e:
    check("surface de l'API inspectable", False, f"— import impossible : {e}")

print("\n§9 — dérivation de la fourchette depuis le research memo")
from app.agents.v2.decision import DecisionRefused, _valuation_range_from_memo

MEMO_OK = {"valuation": {"iv_range": [90.0, 150.0], "dcf_scenarios": {"base": 120.0}}}
vr = _valuation_range_from_memo(MEMO_OK)
check("bornes prises dans iv_range", (vr["low"], vr["high"]) == (90.0, 150.0))
check("base prise dans dcf_scenarios (jamais une moyenne inventée)", vr["base"] == 120.0)


def refuse_memo(memo):
    try:
        _valuation_range_from_memo(memo)
        return False
    except DecisionRefused:
        return True


check("memo sans iv_range REFUSÉ", refuse_memo({"valuation": {"dcf_scenarios": {"base": 120.0}}}))
check("memo sans dcf_scenarios.base REFUSÉ", refuse_memo({"valuation": {"iv_range": [90.0, 150.0]}}))
check("memo vide REFUSÉ", refuse_memo({}))
check("base hors bornes -> le CONTRAT tranche (incohérence bloquante, pas figée en silence)",
      rejette({**BASE, "valuation_range": _valuation_range_from_memo(
          {"valuation": {"iv_range": [90.0, 150.0], "dcf_scenarios": {"base": 400.0}}})}))

print("\n§10 — Règle #19 : contrat figé ↔ copie runtime")
FROZEN = Path("/contract_frozen/decision_validate_schema.py")
if FROZEN.exists():
    src = FROZEN.read_text(encoding="utf-8")
    for nom in ("class ThesisValidation", "class RiskAck", "class ValuationRange",
                "position_sizing_pct", "pre_mortem_acked", "risk_acks", "valuation_range"):
        check(f"contrat figé porte `{nom}`", nom in src)
    check("contrat figé : verdicts actionnables identiques",
          '"PROCEED", "PROCEED_AVEC_CONDITIONS"' in src or
          '{"PROCEED", "PROCEED_AVEC_CONDITIONS"}' in src)
    frozen_champs = {c for c in ("thesis_id", "research_memo_id", "synthesis_analysis_id",
                                 "synthesis", "hypotheses", "risk_acks", "pre_mortem_acked",
                                 "position_sizing_pct", "valuation_range", "conditions_entree")
                     if f"{c}:" in src}
    check("aucun champ runtime absent du contrat figé",
          set(ThesisValidation.model_fields) - {"schema_version"} <= frozen_champs,
          f"— écart : {sorted(set(ThesisValidation.model_fields) - {'schema_version'} - frozen_champs)}")
else:
    print("  ---- contrat figé non monté (/contract_frozen) : comparaison NON faite.")
    print("       monter avec -v <repo>/roadmap/provenance-cards:/contract_frozen:ro")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
