"""Vérification du MONITORING V2 (§10/§11, lot 8) — pur, sans réseau ni DB ni LLM.

Le monitoring est le seul agent V2 qui tourne SANS supervision humaine, sur une position en argent
réel, pendant des années. Ses deux modes de panne ne se ressemblent pas :

  • **le churn** — escalader sur une impression, faire re-décider à chaque trimestre, et user la
    conviction jusqu'à ce qu'une thèse saine soit vendue au pire moment (audit §1.3) ;
  • **la dérive** — ne rien escalader, laisser des hypothèses invalidées vivre indéfiniment parce
    que personne ne les a relues.

Les contrats figés couvrent le premier. Ils ne peuvent PAS couvrir le second, ni le trou central du
premier, parce qu'un contrat ne voit que le payload du modèle — jamais `theses_v2.hypotheses`. D'où
le poids donné ici au **pont inter-objets** (§3) : c'est la partie du garde-fou qui n'existe que
dans le code, donc la seule que rien d'autre ne testera.

Ce qu'on éprouve :

  §1/§2  les contrats Mode6Review et Mode1..Mode5 — explicabilité de sortie, anti-seuil-mécanique
         (§11), anti-churn (statut ⇔ seuils_franchis ⇔ alert_level), thermomètre non contraignant.
  §3     `_valider_pont_hypotheses` — hypothèse INVENTÉE (le trou exact de l'anti-churn : le contrat
         mode 2 est parfaitement satisfait par une escalade sur un seuil jamais pré-enregistré),
         revue annuelle INCOMPLÈTE, et `source_entry_refs` FANTÔME (statut fondé sur une entry
         absente du contexte envoyé).
  §4     `_forcer_champs_derives` — ce que l'appelant sait n'est pas demandé au modèle (#24/#36).
  §5     `_colonnes_routeur` — le routeur lit des colonnes dénormalisées ; leur domaine par mode
         doit coïncider avec les CHECKs de la migration 031, sinon l'INSERT explose en production.
  §6     `_reporter_statuts` — les seuils figés au validate sont EN LECTURE SEULE. Sans ça, un
         modèle peut abaisser le seuil qu'il vient de franchir et annuler l'anti-churn en silence.
  §7     surface HTTP — `MonitoringRunBody` n'expose aucun champ de jugement (#36).
  §8     le routeur — INNER JOIN sur `theses_v2` (le défaut V1 corrigé, convention #34), filtre
         `thesis_v2_id IS NOT NULL`, interrupteur `v2_auto_enabled`, pas de garde `synced`.
  §9     migration 031 ↔ code — les domaines écrits en base sont ceux que le code peut produire.
  §10    règle #19 — copie runtime `app/contracts/` ↔ contrat figé `roadmap/provenance-cards/`.
"""
import ast
import sys
from pathlib import Path

from pydantic import ValidationError

from app.agents.v2.monitoring import (
    MonitoringRefused,
    _colonnes_routeur,
    _forcer_champs_derives,
    _reporter_statuts,
    _valider_pont_hypotheses,
)
from app.api.analysis_v2 import MonitoringRunBody
from app.contracts import (
    Mode1PreEvent,
    Mode2QuarterlyReview,
    Mode3DecisionReview,
    Mode4SectorPulse,
    Mode5Routing,
    Mode6Review,
)

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def rejette(modele, payload):
    """True si le contrat REFUSE le payload (comportement attendu)."""
    try:
        modele(**payload)
        return False
    except (ValidationError, ValueError):
        return True


def accepte(modele, payload):
    try:
        modele(**payload)
        return True
    except (ValidationError, ValueError) as e:
        print(f"       (refus inattendu : {e})")
        return False


# ── Fixtures ─────────────────────────────────────────────────────────────────
REFS = [{"entry_id": 512, "version": 1}]


def hyp(hid, statut="active", refs=None):
    return {"hypothese_id": hid, "statut": statut, "observation": f"observation {hid}",
            "source_entry_refs": refs if refs is not None else REFS}


VALO = {"low": 95.0, "base": 130.0, "high": 160.0}
THERMO = {"zone": "juste",
          "reverse_dcf": {"croissance_implicite_prix_actuel_pct": 14.0,
                          "verdict": "le prix price une croissance > base"},
          "action_suggeree": "surveiller la marge", "contraignant": False}
RENDEMENT_OK = {"iv_reactualisee": 130.0, "rendement_attendu_pct": 12.0,
                "cout_opportunite": "vs meilleure alternative du portefeuille", "suffisant": True}
RENDEMENT_KO = {**RENDEMENT_OK, "rendement_attendu_pct": 2.0, "suffisant": False}

M6 = {"schema_version": "v2.0.0", "thesis_id": 4, "verdict": "CONFIRMER",
      "rationale": "la thèse tient", "hypotheses_reviewed": [hyp("H1"), hyp("H2")],
      "valuation_range_updated": VALO, "thermometer": THERMO,
      "next_review_date": "2027-08-31"}

M2 = {"mode": 2, "thesis_id": 4, "hypotheses_reviewed": [hyp("H1"), hyp("H2")],
      "seuils_franchis": [], "alert_level": "RAS", "valuation_status": "juste"}

# Les hypothèses FIGÉES au validate : le pont inter-objets s'y confronte.
FIGEES = [
    {"id": "H1", "enonce": "…", "kpi": "croissance Azure", "unite": "%",
     "statut": "active", "seuil_alerte": 30.0, "seuil_invalidation": 25.0,
     "base_rate": {"taux": 0.4, "reference_class": "oligopoles"}, "source_entry_refs": REFS},
    {"id": "H2", "enonce": "…", "kpi": "marge opérationnelle", "unite": "%",
     "statut": "active", "seuil_alerte": 42.0, "seuil_invalidation": 38.0,
     "base_rate": {"taux": 0.3, "reference_class": "cycles capex"}, "source_entry_refs": REFS},
]
ENTRIES = [{"id": 512}, {"id": 513}]


print("§1 — Mode 6 : explicabilité, §11 anti-seuil-mécanique, thermomètre contextuel")
check("revue nominale CONFIRMER acceptée", accepte(Mode6Review, M6))
check("SORTIR sans exit_trigger REFUSÉ (pas de sortie muette)",
      rejette(Mode6Review, {**M6, "verdict": "SORTIR"}))
check("REDUIRE sans exit_trigger REFUSÉ",
      rejette(Mode6Review, {**M6, "verdict": "REDUIRE"}))
check("CONFIRMER AVEC exit_trigger REFUSÉ (incohérent)",
      rejette(Mode6Review, {**M6, "exit_trigger": "hypothese_invalidee"}))
check("exit_trigger='hypothese_invalidee' sans hypothèse invalidee REFUSÉ",
      rejette(Mode6Review, {**M6, "verdict": "SORTIR", "exit_trigger": "hypothese_invalidee"}))
check("SORTIR sur hypothèse réellement invalidee ACCEPTÉ",
      accepte(Mode6Review, {**M6, "verdict": "SORTIR", "exit_trigger": "hypothese_invalidee",
                            "hypotheses_reviewed": [hyp("H1", "invalidee"), hyp("H2")]}))
# Le cœur de DÉCISION #5 : une sortie sur valorisation n'est jamais un ratio de prix.
check("exit_trigger='rendement_insuffisant' SANS rendement_prospectif REFUSÉ (anti-seuil-mécanique)",
      rejette(Mode6Review, {**M6, "verdict": "REDUIRE", "exit_trigger": "rendement_insuffisant"}))
check("exit_trigger='rendement_insuffisant' avec suffisant=True REFUSÉ",
      rejette(Mode6Review, {**M6, "verdict": "REDUIRE", "exit_trigger": "rendement_insuffisant",
                            "rendement_prospectif": RENDEMENT_OK}))
check("REDUIRE sur rendement prospectif insuffisant ACCEPTÉ (arbitrage, pas un ratio)",
      accepte(Mode6Review, {**M6, "verdict": "REDUIRE", "exit_trigger": "rendement_insuffisant",
                            "rendement_prospectif": RENDEMENT_KO}))
check("RENFORCER sans rendement_prospectif suffisant REFUSÉ",
      rejette(Mode6Review, {**M6, "verdict": "RENFORCER"}))
check("RENFORCER justifié ACCEPTÉ",
      accepte(Mode6Review, {**M6, "verdict": "RENFORCER", "rendement_prospectif": RENDEMENT_OK}))
check("thermomètre `contraignant=True` REFUSÉ (§11 : ne déclenche jamais seul une vente)",
      rejette(Mode6Review, {**M6, "thermometer": {**THERMO, "contraignant": True}}))
check("zone `surevalue` + CONFIRMER ACCEPTÉ (le thermomètre alimente, il ne décide pas)",
      accepte(Mode6Review, {**M6, "thermometer": {**THERMO, "zone": "surevalue"}}))
check("valuation_range désordonnée (base hors bornes) REFUSÉE",
      rejette(Mode6Review, {**M6, "valuation_range_updated": {"low": 95.0, "base": 200.0, "high": 160.0}}))
check("hypotheses_reviewed vide REFUSÉ", rejette(Mode6Review, {**M6, "hypotheses_reviewed": []}))
check("statut d'hypothèse sans source_entry_refs REFUSÉ (A2)",
      rejette(Mode6Review, {**M6, "hypotheses_reviewed": [hyp("H1", refs=[])]}))
check("champ hors contrat REFUSÉ (extra='forbid')",
      rejette(Mode6Review, {**M6, "recommandation_libre": "vendre"}))


print("\n§2 — Modes 1-5 : anti-churn et périmètre de chaque mode")
check("mode 1 nominal accepté",
      accepte(Mode1PreEvent, {"mode": 1, "thesis_id": 4, "event": "résultats T1",
                              "checklist": ["marge", "guidance"]}))
check("mode 1 checklist de 4 points REFUSÉE (≤ 3)",
      rejette(Mode1PreEvent, {"mode": 1, "thesis_id": 4, "event": "résultats T1",
                              "checklist": ["a", "b", "c", "d"]}))
check("mode 1 avec un verdict REFUSÉ (aucun jugement au pré-event)",
      rejette(Mode1PreEvent, {"mode": 1, "thesis_id": 4, "event": "r", "checklist": ["a"],
                              "verdict": "SORTIR"}))

check("mode 2 RAS sans franchissement accepté", accepte(Mode2QuarterlyReview, M2))
check("mode 2 REVIEW_REQUIRED SANS seuil franchi REFUSÉ — l'ANTI-CHURN du contrat",
      rejette(Mode2QuarterlyReview, {**M2, "alert_level": "REVIEW_REQUIRED"}))
check("mode 2 RAS AVEC seuil franchi REFUSÉ (l'inverse : on n'étouffe pas une alerte)",
      rejette(Mode2QuarterlyReview, {**M2, "hypotheses_reviewed": [hyp("H1", "alerte"), hyp("H2")],
                                     "seuils_franchis": ["H1"], "alert_level": "RAS"}))
check("mode 2 seuils_franchis ≠ statuts alerte/invalidee REFUSÉ (le statut EST le franchissement)",
      rejette(Mode2QuarterlyReview, {**M2, "hypotheses_reviewed": [hyp("H1", "alerte"), hyp("H2")],
                                     "seuils_franchis": [], "alert_level": "RAS"}))
check("mode 2 seuils_franchis hors hypotheses_reviewed REFUSÉ (référentiel interne)",
      rejette(Mode2QuarterlyReview, {**M2, "seuils_franchis": ["H9"], "alert_level": "CRITICAL"}))
check("mode 2 escalade sur franchissement réel ACCEPTÉE",
      accepte(Mode2QuarterlyReview, {**M2, "hypotheses_reviewed": [hyp("H1", "invalidee"), hyp("H2")],
                                     "seuils_franchis": ["H1"], "alert_level": "CRITICAL"}))

M3 = {"mode": 3, "thesis_id": 4, "diagnostic": "d", "munger_inversion": "ce qui tuerait la thèse",
      "hypotheses_reviewed": [hyp("H1"), hyp("H2")], "decision": "MAINTENIR", "rationale": "r"}
check("mode 3 MAINTENIR accepté", accepte(Mode3DecisionReview, M3))
check("mode 3 SORTIR sans exit_trigger REFUSÉ",
      rejette(Mode3DecisionReview, {**M3, "decision": "SORTIR"}))
check("mode 3 MAINTENIR avec exit_trigger REFUSÉ",
      rejette(Mode3DecisionReview, {**M3, "exit_trigger": "rendement_insuffisant"}))
check("mode 3 sans test d'inversion (Munger) REFUSÉ",
      rejette(Mode3DecisionReview, {k: v for k, v in M3.items() if k != "munger_inversion"}))

M4 = {"mode": 4, "thesis_id": 4, "pair_ticker": "AMZN", "sector_score": 3,
      "hypotheses_impactees": ["H1"], "note": "n"}
check("mode 4 nominal accepté", accepte(Mode4SectorPulse, M4))
check("mode 4 score hors -5..+5 REFUSÉ", rejette(Mode4SectorPulse, {**M4, "sector_score": 7}))
check("mode 4 PORTANT un alert_level REFUSÉ — le sector pulse n'escalade jamais seul",
      rejette(Mode4SectorPulse, {**M4, "alert_level": "CRITICAL"}))
check("mode 4 portant un verdict REFUSÉ",
      rejette(Mode4SectorPulse, {**M4, "verdict": "SORTIR"}))

M5 = {"mode": 5, "thesis_id": 4, "source_mode": 2, "route": "synthese", "raison": "dégradation"}
check("mode 5 nominal accepté", accepte(Mode5Routing, M5))
check("mode 5 route hors {synthese, debate} REFUSÉE", rejette(Mode5Routing, {**M5, "route": "vendre"}))
check("mode 5 source_mode=6 REFUSÉ (le routage suit un mode 2 ou 4)",
      rejette(Mode5Routing, {**M5, "source_mode": 6}))
check("mode 5 produisant une donnée nouvelle REFUSÉ (routing PUR)",
      rejette(Mode5Routing, {**M5, "hypotheses_reviewed": [hyp("H1")]}))


print("\n§3 — LE PONT INTER-OBJETS : ce qu'aucun contrat ne peut voir")


def pont_refuse(data, mode, figees=FIGEES, entries=ENTRIES):
    try:
        _valider_pont_hypotheses(data, figees, entries, mode=mode)
        return False
    except MonitoringRefused:
        return True


def pont_passe(data, mode, figees=FIGEES, entries=ENTRIES):
    try:
        _valider_pont_hypotheses(data, figees, entries, mode=mode)
        return True
    except MonitoringRefused as e:
        print(f"       (refus inattendu : {e})")
        return False


check("mode 6 revoyant H1+H2 (toutes les figées) PASSE",
      pont_passe({"hypotheses_reviewed": [hyp("H1"), hyp("H2")]}, 6))
# Le trou exact de l'anti-churn : ce payload satisfait PARFAITEMENT le contrat mode 2 —
# statut alerte ⇔ seuils_franchis ⇔ alert_level. Et pourtant H7 n'a jamais été pré-enregistrée.
h7 = {"mode": 2, "thesis_id": 4, "hypotheses_reviewed": [hyp("H1"), hyp("H2"), hyp("H7", "alerte")],
      "seuils_franchis": ["H7"], "alert_level": "REVIEW_REQUIRED", "valuation_status": "juste"}
check("le contrat mode 2 ACCEPTE une escalade sur une hypothèse inventée (limite connue)",
      accepte(Mode2QuarterlyReview, h7))
check("… et le pont la REFUSE : un seuil non pré-enregistré ne peut pas être franchi",
      pont_refuse(h7, 2))
check("mode 6 ne revoyant qu'une hypothèse sur deux REFUSÉ (garde-fou 7 : dérive d'un an)",
      pont_refuse({"hypotheses_reviewed": [hyp("H1")]}, 6))
check("mode 2 ne revoyant qu'une hypothèse sur deux PASSE (l'exhaustivité n'est due qu'au mode 6)",
      pont_passe({"hypotheses_reviewed": [hyp("H1")]}, 2))
check("mode 4 désignant une hypothèse inconnue REFUSÉ (même exigence référentielle)",
      pont_refuse({"hypotheses_impactees": ["H9"]}, 4))
check("mode 4 désignant une hypothèse figée PASSE",
      pont_passe({"hypotheses_impactees": ["H1"]}, 4))
check("source_entry_refs pointant une entry ABSENTE du contexte REFUSÉ (A2 : statut fondé sur rien)",
      pont_refuse({"hypotheses_reviewed": [hyp("H1", refs=[{"entry_id": 999, "version": 1}]),
                                           hyp("H2")]}, 6))
check("refs pointant les entries réellement envoyées PASSE",
      pont_passe({"hypotheses_reviewed": [hyp("H1", refs=[{"entry_id": 513, "version": 1}]),
                                          hyp("H2")]}, 6))
check("mode 1 (aucune hypothèse citée) PASSE sans exiger de revue",
      pont_passe({"checklist": ["a"]}, 1))


print("\n§4 — Champs dérivés : ce que l'appelant sait n'est pas demandé au modèle (#24/#36)")
d = _forcer_champs_derives(2, {"mode": 4, "thesis_id": 999}, thesis_v2_id=4,
                           peer_ticker=None, source_mode=None)
check("thesis_id erroné du modèle ÉCRASÉ par la valeur connue", d["thesis_id"] == 4, d)
check("mode erroné ÉCRASÉ (le discriminateur ne dépend pas du modèle)", d["mode"] == 2, d)
d4 = _forcer_champs_derives(4, {"pair_ticker": "INVENTE"}, thesis_v2_id=4,
                            peer_ticker="AMZN", source_mode=None)
check("pair_ticker imposé par l'événement de calendrier", d4["pair_ticker"] == "AMZN", d4)
d5 = _forcer_champs_derives(5, {}, thesis_v2_id=4, peer_ticker=None, source_mode=2)
check("source_mode imposé par la session d'origine", d5["source_mode"] == 2, d5)
d6 = _forcer_champs_derives(6, {}, thesis_v2_id=4, peer_ticker=None, source_mode=None)
check("schema_version constante, jamais demandée au modèle", d6["schema_version"] == "v2.0.0", d6)
check("pair_ticker NON injecté hors mode 4", "pair_ticker" not in d5, d5)


print("\n§5 — Colonnes lues par le routeur ↔ domaines de la migration 031")
c2 = _colonnes_routeur(2, {**M2, "alert_level": "CRITICAL", "seuils_franchis": ["H1"]})
check("mode 2 porte un alert_level", c2["alert_level"] == "CRITICAL", c2)
check("mode 2 ne porte AUCUN verdict (il flague, il ne juge pas)", c2["verdict"] is None, c2)
check("mode 2 en escalade suggère le routage mode 5", c2["routing_suggestion"] == "mode5", c2)
check("mode 2 RAS ne suggère aucun routage",
      _colonnes_routeur(2, M2)["routing_suggestion"] is None)
c4 = _colonnes_routeur(4, {**M4, "alert_level": "CRITICAL", "verdict": "SORTIR"})
check("mode 4 : alert_level et verdict FILTRÉS même si le payload en porte",
      c4["alert_level"] is None and c4["verdict"] is None, c4)
c6 = _colonnes_routeur(6, {**M6, "verdict": "SORTIR"})
check("mode 6 porte son verdict", c6["verdict"] == "SORTIR", c6)
check("mode 6 SORTIR pose la suggestion `exit_plan` (lot 9), sans prétendre l'exécuter",
      c6["routing_suggestion"] == "exit_plan", c6)
check("mode 6 CONFIRMER ne suggère rien",
      _colonnes_routeur(6, M6)["routing_suggestion"] is None)
c3 = _colonnes_routeur(3, {**M3, "decision": "RE_SYNTHESE"})
check("mode 3 : le verdict vient de `decision` (vocabulaire distinct du mode 6)",
      c3["verdict"] == "RE_SYNTHESE", c3)
check("mode 3 : aucun alert_level", c3["alert_level"] is None, c3)
check("mode 1 : ni alerte ni verdict",
      _colonnes_routeur(1, {"mode": 1})["alert_level"] is None
      and _colonnes_routeur(1, {"mode": 1})["verdict"] is None)
check("mode 5 : routing = la route décidée",
      _colonnes_routeur(5, M5)["routing_suggestion"] == "synthese")


print("\n§6 — Report des statuts : les seuils figés au validate sont EN LECTURE SEULE")
revues = [{"hypothese_id": "H1", "statut": "invalidee", "observation": "croissance à 18%",
           # sortie HOSTILE : le modèle « rappelle » un seuil plus bas que celui qu'il vient de franchir
           "seuil_invalidation": 5.0, "seuil_alerte": 8.0, "source_entry_refs": REFS}]
maj = _reporter_statuts(FIGEES, revues, __import__("datetime").date(2027, 8, 31))
h1 = next(h for h in maj if h["id"] == "H1")
h2 = next(h for h in maj if h["id"] == "H2")
check("le statut revu est bien reporté", h1["statut"] == "invalidee", h1)
check("seuil_invalidation FIGÉ conservé (25.0), pas celui rendu par le modèle (5.0)",
      h1["seuil_invalidation"] == 25.0, h1)
check("seuil_alerte FIGÉ conservé (30.0)", h1["seuil_alerte"] == 30.0, h1)
check("base_rate d'origine conservé", h1["base_rate"]["taux"] == 0.4, h1)
check("date de revue horodatée", h1["derniere_revue"] == "2027-08-31", h1)
check("hypothèse NON revue laissée intacte, sans horodatage trompeur",
      h2["statut"] == "active" and "derniere_revue" not in h2, h2)
check("aucune hypothèse figée ne disparaît du report",
      {h["id"] for h in maj} == {"H1", "H2"}, maj)
check("une hypothèse inventée ne s'ajoute PAS à la thèse figée",
      _reporter_statuts(FIGEES, [{"hypothese_id": "H7", "statut": "invalidee",
                                  "observation": "o", "source_entry_refs": REFS}],
                        __import__("datetime").date(2027, 8, 31)).__len__() == 2)


print("\n§7 — Surface HTTP : le corps de requête n'expose aucun champ de jugement (#36)")
champs = set(MonitoringRunBody.model_fields)
interdits = {"alert_level", "verdict", "decision", "hypotheses_reviewed", "seuils_franchis",
             "valuation_range_updated", "exit_trigger", "rendement_prospectif", "thermometer",
             "routing_suggestion", "result_json", "rationale"}
check("aucun champ de jugement dans MonitoringRunBody",
      not (champs & interdits), f"— fuite : {sorted(champs & interdits)}")
check("le corps ne porte que mode + contexte de déclenchement",
      champs <= {"mode", "trigger_label", "calendar_event_id", "peer_ticker", "source_mode"},
      f"— champs : {sorted(champs)}")


print("\n§8 — EventRouterV2 : le défaut V1 ne doit pas être reconduit")
# La docstring du module NOMME les défauts V1 (`LEFT JOIN`, `dust_auto_enabled`, `synced`) pour
# expliquer pourquoi ils sont écartés. Un grep brut lirait donc l'explication comme le défaut —
# et la seule façon de faire passer le check serait de retirer la justification du code. On
# inspecte le CODE, pas le commentaire : la docstring est retirée avant recherche.
_SRC_ROUTER = Path("app/calendar/event_router_v2.py").read_text(encoding="utf-8")
_DOC_ROUTER = ast.get_docstring(ast.parse(_SRC_ROUTER)) or ""
ROUTER = _SRC_ROUTER.replace(_DOC_ROUTER, "", 1) if _DOC_ROUTER else _SRC_ROUTER
check("la docstring du routeur documente bien l'écart au V1 (retirée avant grep)",
      "LEFT JOIN" in _DOC_ROUTER and "dust_auto_enabled" in _DOC_ROUTER)
check("jointure INNER sur theses_v2 (pas de LEFT JOIN)",
      "JOIN theses_v2 tv" in ROUTER and "LEFT JOIN" not in ROUTER)
check("la jointure filtre sur status='active'", "tv.status = 'active'" in ROUTER)
check("filtre explicite thesis_v2_id IS NOT NULL (pendant du filtre V1)",
      "ce.thesis_v2_id IS NOT NULL" in ROUTER)
check("interrupteur v2_auto_enabled, pas dust_auto_enabled",
      "v2_auto_enabled" in ROUTER and "dust_auto_enabled" not in ROUTER)
check("aucune garde `synced` (notion Dust, sans objet en V2)", "synced" not in ROUTER)
check("le mode 6 se rattrape (scheduled_date <= today)", "ce.scheduled_date <= $1" in ROUTER)
check("les modes trimestriels restent sur une date EXACTE",
      ROUTER.count("ce.scheduled_date = $1") >= 1 and "INTERVAL '2 days'" in ROUTER
      and "INTERVAL '1 day'" in ROUTER)
check("les 5 déclencheurs calendaires sont câblés",
      all(f"_trigger_{n}" in ROUTER for n in
          ("pre_event_briefs", "quarterly_reviews", "sector_pulses",
           "decision_reviews", "annual_reviews")))
check("une échéance non jouée est TRACÉE (pending_manual), pas perdue", "pending_manual" in ROUTER)
check("le mode 1 consomme brief_triggered, les autres triggered",
      'flag = "brief_triggered" if mode == 1 else "triggered"' in ROUTER)

MAIN = Path("app/main.py").read_text(encoding="utf-8")
check("le job V2 est SÉPARÉ du job V1 dans le scheduler",
      'id="daily_check_v2"' in MAIN and 'id="daily_check_v1"' in MAIN)


print("\n§9 — Migration 031 ↔ code : les domaines écrits en base sont ceux que le code produit")
MIG = Path("app/db/migrations/031_v2_monitoring_flow.sql").read_text(encoding="utf-8")
check("alert_level contraint au seul mode 2",
      "mode = 2 AND alert_level IN ('RAS', 'REVIEW_REQUIRED', 'CRITICAL')" in MIG)
check("verdict mode 6 : vocabulaire de revue",
      "mode = 6 AND verdict IN ('CONFIRMER', 'RENFORCER', 'REDUIRE', 'SORTIR')" in MIG)
check("verdict mode 3 : vocabulaire de décision (RE_SYNTHESE n'existe qu'ici)",
      "mode = 3 AND verdict IN ('MAINTENIR', 'REDUIRE', 'SORTIR', 'RE_SYNTHESE')" in MIG)
check("exclusivité de flux sur calendar_events", "ce_session_flow_exclusif" in MIG)
check("analysis_kind ouvert à 'monitoring' (snapshot des refs de suivi)",
      "'monitoring'" in MIG and "analysis_refs_kind_domain" in MIG)
check("v2_auto_enabled par défaut FALSE (pas de dépense automatique non supervisée)",
      "v2_auto_enabled BOOLEAN NOT NULL DEFAULT FALSE" in MIG)
# Le code ne doit jamais tenter d'écrire une valeur que le CHECK rejettera.
for mode, vocab in ((6, ("CONFIRMER", "RENFORCER", "REDUIRE", "SORTIR")),
                    (3, ("MAINTENIR", "REDUIRE", "SORTIR", "RE_SYNTHESE"))):
    cle = "verdict" if mode == 6 else "decision"
    check(f"mode {mode} : tout le vocabulaire du contrat passe le CHECK",
          all(f"'{v}'" in MIG for v in vocab)
          and all(_colonnes_routeur(mode, {cle: v})["verdict"] == v for v in vocab))
check("aucun mode hors 2 ne peut poser d'alert_level (le CHECK ne sera jamais violé)",
      all(_colonnes_routeur(m, {"alert_level": "CRITICAL"})["alert_level"] is None
          for m in (1, 3, 4, 5, 6)))
check("aucun mode hors 3/6 ne peut poser de verdict",
      all(_colonnes_routeur(m, {"verdict": "SORTIR", "decision": "SORTIR"})["verdict"] is None
          for m in (1, 2, 4, 5)))


print("\n§10 — Règle #19 : contrat figé ↔ copie runtime")
FROZEN = Path("/contract_frozen")
if (FROZEN / "monitoring_mode6_schema.py").exists():
    src6 = (FROZEN / "monitoring_mode6_schema.py").read_text(encoding="utf-8")
    src15 = (FROZEN / "monitoring_modes_1_5_schema.py").read_text(encoding="utf-8")
    for nom in ("class Mode6Review", "class ValuationThermometer", "class HypothesisReview",
                "class RendementProspectif", "contraignant", "next_review_date"):
        check(f"contrat figé mode 6 porte `{nom}`", nom in src6)
    for nom in ("class Mode1PreEvent", "class Mode2QuarterlyReview", "class Mode3DecisionReview",
                "class Mode4SectorPulse", "class Mode5Routing", "MonitoringSession"):
        check(f"contrat figé modes 1-5 porte `{nom}`", nom in src15)
    ecart6 = {c for c in Mode6Review.model_fields if f"{c}:" not in src6}
    check("aucun champ runtime absent du contrat figé mode 6", not ecart6, f"— écart : {sorted(ecart6)}")
    for modele, src in ((Mode1PreEvent, src15), (Mode2QuarterlyReview, src15),
                        (Mode3DecisionReview, src15), (Mode4SectorPulse, src15),
                        (Mode5Routing, src15)):
        ecart = {c for c in modele.model_fields if f"{c}:" not in src}
        check(f"aucun champ runtime absent du figé ({modele.__name__})", not ecart,
              f"— écart : {sorted(ecart)}")
else:
    print("  ---- contrat figé non monté (/contract_frozen) : comparaison NON faite.")
    print("       monter avec -v <repo>/roadmap/provenance-cards:/contract_frozen:ro")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
