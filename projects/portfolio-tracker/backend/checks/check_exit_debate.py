"""Vérification de la SORTIE / CALIBRATION / DÉBAT V2 (§11/§12/A5 + §9-C, lot 9) — pur, hors ligne.

Le lot 9 est le seul du système où une sortie de modèle se traduit en **vente d'actions réelles**
puis en **mémoire longue** : le post-mortem alimente `knowledge_entries`, la calibration alimente
`calibration_registry`, et c'est ce registre qu'on relira dans deux ans pour juger nos propres
biais. Un chiffre approximatif écrit ici n'est pas une erreur d'affichage, c'est une fausse leçon
apprise — et elle sera relue comme un fait.

Trois modes de panne, aucun visible depuis un contrat Pydantic :

  • **la sortie habillée** — un plan de sortie déclare `origine='hypothese_invalidee'` alors
    qu'aucune hypothèse figée n'est invalidée. Contrat parfaitement satisfait, `extra='forbid'`
    satisfait : le contrat ne voit pas `theses_v2.hypotheses`. On vend sur une impression de prix
    en la faisant passer pour une décision de thèse.
  • **la complaisance armée par le seuil** — c'est le trou H7 du lot 8 transposé à l'endroit où sa
    conséquence est de GARDER une position qu'il fallait vendre. `ConvictionChallenge._anti_
    complaisance` ne mord que sur `seuil_franchi == "invalidation"`, or les deux seuils ET le
    franchissement sont DÉCLARÉS par le modèle : recopier `seuil_invalidation: 5.0` là où la thèse
    figée dit `25.0` désarme le garde-fou le plus important du lot, en restant parfaitement valide.
  • **le compliment de calibration** — `predite` rapproché de `realisee`, ou lu dans le
    `valuation_range` COURANT (que chaque revue annuelle réactualise) au lieu du figé au validate.
    On mesurerait alors notre erreur contre notre dernière opinion, c'est-à-dire rien.

Ce qu'on éprouve :

  §1     contrat ExitPlan — Σ tranches ≤ 100, ordres 1..n consécutifs, sortie accélérée motivée.
  §2     contrats PostMortem / CalibrationEntry + `valider_postmortem_couvre` (bijection).
  §3     contrat ConvictionChallenge — anti-complaisance, débat non décoratif, sourçage.
  §4     `_deriver_franchissement` — la direction se DÉDUIT de l'ordre des deux seuils figés, dans
         les deux sens ; le cas dégénéré (seuils égaux) conserve la déclaration au lieu d'inventer.
  §5     `_forcer_seuils_figes` — LES DEUX MOITIÉS DU TROU : le contrat ACCEPTE le seuil falsifié
         avec `closed_proceed`, et la revalidation après rétablissement le REFUSE. Montrer le seul
         refus ne prouverait pas que le trou existait.
  §6     `_valider_pont_debat` — hypothèse inventée, entry fantôme.
  §7     `_valider_pont_sortie` — antécédent opposable à chaque origine, position réelle, Σ des
         tranches confrontée à ce qui a DÉJÀ été vendu (le contrat ne voit que le nouveau plan).
  §8/§9  `_valider_pont_postmortem` / `_valider_pont_calibration` — histoire terminée, bilan avant
         mesure d'écart.
  §10    `_forcer_champs_derives` — durée, performance et `predite` sont CALCULÉES, jamais reçues.
  §11    `_verifier_etat` — les refus qui doivent tomber AVANT la dépense de tokens.
  §12    arithmétique de position — `shares` est décrémenté à chaque vente : l'assiette initiale se
         reconstitue, elle ne se lit pas.
  §13    surface HTTP — aucun corps n'expose de champ de jugement (#36), sauf la clôture de débat,
         qui est l'acte souverain de l'utilisateur.
  §14    migration 032 ↔ code — les valeurs que le code écrit passent les CHECKs de la base.
  §15    règle #19 — copie runtime `app/contracts/` ↔ contrat figé `roadmap/provenance-cards/`.
"""
import sys
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from app.agents.v2.debate import (
    DebateRefused,
    _deriver_franchissement,
    _forcer_seuils_figes,
    _valider_pont_debat,
)
from app.agents.v2.exit import (
    ExitRefused,
    ThesisNotExitable,
    _cout_de_revient_eur,
    _forcer_champs_derives,
    _pct_execute,
    _shares_initiales,
    _valider_pont_calibration,
    _valider_pont_postmortem,
    _valider_pont_sortie,
    _verifier_etat,
)
from app.api.analysis_v2 import (
    CloseDebateBody,
    DebateRunBody,
    ExecuteTrancheBody,
    ExitAlertBody,
)
from app.contracts import (
    CalibrationEntry,
    ConvictionChallenge,
    ExitPlan,
    PostMortem,
    valider_postmortem_couvre,
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


def refuse(fn, *args, exc=ExitRefused):
    """True si l'appel lève l'exception de refus attendue (le PONT, pas le contrat)."""
    try:
        fn(*args)
        return False
    except exc:
        return True


def passe(fn, *args):
    try:
        fn(*args)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"       (refus inattendu : {e})")
        return False


# ── Fixtures ─────────────────────────────────────────────────────────────────
REFS = [{"entry_id": 512, "version": 1}]
ENTRIES = [{"id": 512}, {"id": 513}]

# Hypothèses FIGÉES au validate. Les deux sens de surveillance sont représentés :
# H1/H2 à la BAISSE (invalidation < alerte), H3 à la HAUSSE (alerte < invalidation).
FIGEES = [
    {"id": "H1", "enonce": "croissance cloud", "kpi": "croissance Azure", "unite": "%",
     "statut": "active", "seuil_alerte": 30.0, "seuil_invalidation": 25.0},
    {"id": "H2", "enonce": "marge tenue", "kpi": "marge opérationnelle", "unite": "%",
     "statut": "active", "seuil_alerte": 42.0, "seuil_invalidation": 38.0},
    {"id": "H3", "enonce": "capex maîtrisé", "kpi": "capex / CA", "unite": "%",
     "statut": "active", "seuil_alerte": 20.0, "seuil_invalidation": 28.0},
]

THESE = {
    "id": 5, "ticker_id": "MSFT", "status": "active", "verdict": "PROCEED",
    "position_sizing_pct": 6.0, "validated_at": "2026-01-15",
    # RÉACTUALISÉE par la revue annuelle — ce n'est PAS la prédiction d'origine.
    "valuation_range": {"low": 300.0, "base": 380.0, "high": 460.0},
    "hypotheses": FIGEES, "research_memo_id": None,
}
# Figée au validate (G3) : c'est ELLE que la calibration doit relire.
VALIDATION_JSON = {"valuation_range": {"low": 250.0, "base": 320.0, "high": 400.0}}

POSITION_OUVERTE = {"id": 8, "ticker_id": "MSFT", "shares": 40.0, "status": "open",
                    "purchase_price_eur": 300.0, "purchase_date": date(2026, 1, 15)}
POSITION_SOLDEE = {**POSITION_OUVERTE, "shares": 0.0, "status": "closed"}

EXECUTIONS = [
    {"ordre": 1, "pct_a_vendre": 40.0, "shares_sold": 40.0, "proceeds_eur": 14000.0,
     "executed_at": date(2026, 7, 14)},
    {"ordre": 2, "pct_a_vendre": 60.0, "shares_sold": 60.0, "proceeds_eur": 21600.0,
     "executed_at": date(2026, 8, 20)},
]


def session(sid=91, mode=6, alert=None, verdict=None, routing=None, result=None):
    return {"id": sid, "mode": mode, "alert_level": alert, "verdict": verdict,
            "routing_suggestion": routing, "result_json": result or {},
            "created_at": date(2026, 8, 1)}


def inputs(*, hypotheses=None, position=POSITION_OUVERTE, executions=(), sessions=(),
           plan=None, post_mortem=None, thesis=None):
    return {
        "thesis": {**THESE, **(thesis or {})},
        "hypotheses": [dict(h) for h in (hypotheses if hypotheses is not None else FIGEES)],
        "validation_json": VALIDATION_JSON,
        "position": position, "plan": plan, "executions": list(executions),
        "post_mortem": post_mortem, "sessions": list(sessions), "memo_json": {},
        "entries": ENTRIES,
    }


PLAN = {"schema_version": "v2.0.0", "thesis_id": 5, "origine": "hypothese_invalidee",
        "tranches": [{"ordre": 1, "pct_a_vendre": 40.0, "declencheur": "immédiat"},
                     {"ordre": 2, "pct_a_vendre": 60.0, "declencheur": "prix > 400"}],
        "exit_status": "plan_created"}

PM = {"schema_version": "v2.0.0", "thesis_id": 5, "duree_jours": 217, "performance_pct": 18.7,
      "hypotheses_finales": [
          {"hypothese_id": "H1", "statut_final": "invalidee", "predite_vs_realisee": "25 % vs 19 %"},
          {"hypothese_id": "H2", "statut_final": "confirmee", "predite_vs_realisee": "42 % vs 44 %"},
          {"hypothese_id": "H3", "statut_final": "non_concluante", "predite_vs_realisee": "capex opaque"}],
      "decision_sortie": "sortie sur invalidation de H1",
      "lecons": [{"lecon": "les seuils de croissance cloud étaient trop hauts",
                  "tags": ["hyperscaler", "seuil"]}]}

CALIB = {"schema_version": "v2.0.0", "thesis_id": 5,
         "paires": [{"metric": "iv_base", "predite": 320.0, "realisee": 355.0}]}


def tension(hid="H1", alerte=30.0, invalidation=25.0, valeur=19.0, franchi="invalidation"):
    return {"hypothese_id": hid, "seuil_alerte": alerte, "seuil_invalidation": invalidation,
            "valeur_observee": valeur, "seuil_franchi": franchi,
            "observation": f"{hid} observé à {valeur}", "source_entry_refs": REFS}


CONTRE = [{"titre": "la croissance décélère structurellement",
           "explication": "le mix bascule vers des charges moins margées",
           "probabilite": 0.55,
           "base_rate": {"taux": 0.4, "reference_class": "hyperscalers en phase de capex lourd"},
           "source_entry_refs": REFS}]

DEBAT = {"schema_version": "v2.0.0", "thesis_id": 5,
         "hypotheses_sous_tension": [tension()],
         "cas_contre_maintien": CONTRE,
         "biais_a_surveiller": ["ancrage_prix_entree", "cout_irrecuperable"],
         "cout_opportunite": "vs le renforcement de la ligne la mieux notée du portefeuille",
         "resolution_suggeree": "closed_pass",
         "resolution_rationale": "l'invalidation de H1 n'est pas compensée",
         "escalade_recommandee": False}


print("§1 — Contrat ExitPlan : la sortie est un PLAN, pas une intention")
check("plan nominal accepté", accepte(ExitPlan, PLAN))
check("Σ pct_a_vendre > 100 REFUSÉ (on ne vend pas 130 % d'une ligne)",
      rejette(ExitPlan, {**PLAN, "tranches": [{"ordre": 1, "pct_a_vendre": 70.0, "declencheur": "d"},
                                              {"ordre": 2, "pct_a_vendre": 60.0, "declencheur": "d"}]}))
check("Σ = 100 exactement ACCEPTÉ (sortie totale planifiée)", accepte(ExitPlan, PLAN))
check("Σ < 100 ACCEPTÉ (réduction, pas sortie)",
      accepte(ExitPlan, {**PLAN, "tranches": [{"ordre": 1, "pct_a_vendre": 30.0, "declencheur": "d"}]}))
check("ordres non consécutifs (1,3) REFUSÉS",
      rejette(ExitPlan, {**PLAN, "tranches": [{"ordre": 1, "pct_a_vendre": 40.0, "declencheur": "d"},
                                              {"ordre": 3, "pct_a_vendre": 60.0, "declencheur": "d"}]}))
check("ordres dupliqués (1,1) REFUSÉS",
      rejette(ExitPlan, {**PLAN, "tranches": [{"ordre": 1, "pct_a_vendre": 40.0, "declencheur": "d"},
                                              {"ordre": 1, "pct_a_vendre": 60.0, "declencheur": "d"}]}))
check("tranche à 0 % REFUSÉE (une tranche qui ne vend rien n'est pas une tranche)",
      rejette(ExitPlan, {**PLAN, "tranches": [{"ordre": 1, "pct_a_vendre": 0.0, "declencheur": "d"}]}))
check("déclencheur vide REFUSÉ (une tranche sans condition d'exécution est un ordre au marché)",
      rejette(ExitPlan, {**PLAN, "tranches": [{"ordre": 1, "pct_a_vendre": 40.0, "declencheur": ""}]}))
check("aucune tranche REFUSÉE", rejette(ExitPlan, {**PLAN, "tranches": []}))
check("exit_status='accelerated_exit' SANS condition REFUSÉ",
      rejette(ExitPlan, {**PLAN, "exit_status": "accelerated_exit"}))
check("exit_status='accelerated_exit' AVEC condition ACCEPTÉ",
      accepte(ExitPlan, {**PLAN, "exit_status": "accelerated_exit",
                         "conditions_accelerees": [{"type": "hypothese_invalidee",
                                                    "seuil": "H1 < 20 %"}]}))
check("type de condition accélérée hors domaine REFUSÉ (§11 n'en prévoit que deux)",
      rejette(ExitPlan, {**PLAN, "exit_status": "accelerated_exit",
                         "conditions_accelerees": [{"type": "prix_en_baisse", "seuil": "-15 %"}]}))
check("origine hors domaine REFUSÉE (la sortie est thèse-driven)",
      rejette(ExitPlan, {**PLAN, "origine": "prix_trop_haut"}))
check("champ hors contrat REFUSÉ (extra='forbid')",
      rejette(ExitPlan, {**PLAN, "recommandation": "tout vendre"}))


print("\n§2 — Contrats PostMortem / CalibrationEntry et bijection des hypothèses")
check("post-mortem nominal accepté", accepte(PostMortem, PM))
check("post-mortem sans leçon REFUSÉ (un bilan sans leçon ne laisse rien)",
      rejette(PostMortem, {**PM, "lecons": []}))
check("leçon sans tag REFUSÉE (elle serait irrécupérable dans la KB)",
      rejette(PostMortem, {**PM, "lecons": [{"lecon": "l", "tags": []}]}))
check("hypotheses_finales vide REFUSÉ", rejette(PostMortem, {**PM, "hypotheses_finales": []}))
check("statut final hors domaine REFUSÉ",
      rejette(PostMortem, {**PM, "hypotheses_finales": [
          {"hypothese_id": "H1", "statut_final": "ratee", "predite_vs_realisee": "x"}]}))
check("decision_sortie vide REFUSÉE", rejette(PostMortem, {**PM, "decision_sortie": ""}))

pm_ok = PostMortem(**PM)
check("bijection exacte acceptée", passe(valider_postmortem_couvre, pm_ok, ["H1", "H2", "H3"]))
check("hypothèse OMISE refusée (c'est celle qui gênait)",
      refuse(valider_postmortem_couvre, pm_ok, ["H1", "H2", "H3", "H4"], exc=ValueError))
check("hypothèse INVENTÉE refusée (un verdict sur rien)",
      refuse(valider_postmortem_couvre, pm_ok, ["H1", "H2"], exc=ValueError))

check("calibration nominale acceptée", accepte(CalibrationEntry, CALIB))
check("calibration sans paire REFUSÉE", rejette(CalibrationEntry, {**CALIB, "paires": []}))
check("metric vide REFUSÉE",
      rejette(CalibrationEntry, {**CALIB, "paires": [{"metric": "", "predite": 1.0, "realisee": 2.0}]}))


print("\n§3 — Contrat ConvictionChallenge : le maintien doit être MÉRITÉ")
check("débat nominal (invalidation → closed_pass) accepté", accepte(ConvictionChallenge, DEBAT))
check("closed_proceed SOUS invalidation REFUSÉ (on ne maintient pas avec conviction)",
      rejette(ConvictionChallenge, {**DEBAT, "resolution_suggeree": "closed_proceed"}))
check("closed_monitor sous invalidation SANS escalade REFUSÉ",
      rejette(ConvictionChallenge, {**DEBAT, "resolution_suggeree": "closed_monitor"}))
check("closed_monitor sous invalidation AVEC escalade ACCEPTÉ",
      accepte(ConvictionChallenge, {**DEBAT, "resolution_suggeree": "closed_monitor",
                                    "escalade_recommandee": True}))
check("closed_proceed sur simple ALERTE ACCEPTÉ (l'alerte n'est pas une invalidation)",
      accepte(ConvictionChallenge, {**DEBAT, "resolution_suggeree": "closed_proceed",
                                    "hypotheses_sous_tension": [tension(franchi="alerte", valeur=28.0)]}))
check("aucun cas contre REFUSÉ (un débat sans meilleur cas CONTRE est du théâtre)",
      rejette(ConvictionChallenge, {**DEBAT, "cas_contre_maintien": []}))
check("contre-argument sans source_entry_refs REFUSÉ (A2)",
      rejette(ConvictionChallenge, {**DEBAT, "cas_contre_maintien": [
          {**CONTRE[0], "source_entry_refs": []}]}))
check("contre-argument sans base_rate REFUSÉ (règle 2 : probabilité ancrée)",
      rejette(ConvictionChallenge, {**DEBAT, "cas_contre_maintien": [
          {k: v for k, v in CONTRE[0].items() if k != "base_rate"}]}))
check("resolution_rationale vide REFUSÉE (pendant du NO-GO muet interdit)",
      rejette(ConvictionChallenge, {**DEBAT, "resolution_rationale": ""}))
check("cout_opportunite vide REFUSÉ (maintenir se juge contre des alternatives)",
      rejette(ConvictionChallenge, {**DEBAT, "cout_opportunite": ""}))
check("biais_a_surveiller vide REFUSÉ", rejette(ConvictionChallenge, {**DEBAT, "biais_a_surveiller": []}))
check("hypotheses_sous_tension vide REFUSÉ",
      rejette(ConvictionChallenge, {**DEBAT, "hypotheses_sous_tension": []}))
check("resolution hors domaine REFUSÉE (pas de verdict d'exécution)",
      rejette(ConvictionChallenge, {**DEBAT, "resolution_suggeree": "PROCEED"}))
check("sizing dans le débat REFUSÉ (extra='forbid' — le débat ne dimensionne rien)",
      rejette(ConvictionChallenge, {**DEBAT, "position_sizing_pct": 4.0}))


print("\n§4 — `_deriver_franchissement` : la direction se DÉDUIT de l'ordre des seuils figés")
# Surveillance à la BAISSE (invalidation 25 < alerte 30) : la grandeur descend.
check("baisse — valeur sous l'invalidation → invalidation",
      _deriver_franchissement(19.0, 30.0, 25.0, "aucun") == "invalidation")
check("baisse — valeur ENTRE les deux seuils → alerte",
      _deriver_franchissement(27.0, 30.0, 25.0, "aucun") == "alerte")
check("baisse — valeur au-dessus de l'alerte → aucun",
      _deriver_franchissement(34.0, 30.0, 25.0, "invalidation") == "aucun")
check("baisse — valeur PILE sur l'invalidation → invalidation (le seuil est atteint, pas frôlé)",
      _deriver_franchissement(25.0, 30.0, 25.0, "aucun") == "invalidation")
check("baisse — valeur PILE sur l'alerte → alerte",
      _deriver_franchissement(30.0, 30.0, 25.0, "aucun") == "alerte")
# Surveillance à la HAUSSE (alerte 20 < invalidation 28) : la grandeur monte (capex, dette…).
check("hausse — valeur au-dessus de l'invalidation → invalidation",
      _deriver_franchissement(31.0, 20.0, 28.0, "aucun") == "invalidation")
check("hausse — valeur ENTRE les deux seuils → alerte",
      _deriver_franchissement(24.0, 20.0, 28.0, "aucun") == "alerte")
check("hausse — valeur sous l'alerte → aucun",
      _deriver_franchissement(12.0, 20.0, 28.0, "invalidation") == "aucun")
check("dégénéré (seuils égaux) → la déclaration du modèle est CONSERVÉE, rien n'est inventé",
      _deriver_franchissement(5.0, 10.0, 10.0, "alerte") == "alerte"
      and _deriver_franchissement(5.0, 10.0, 10.0, "aucun") == "aucun")


print("\n§5 — Le trou H7 transposé : LES DEUX MOITIÉS")
# Moitié 1 — le contrat, seul, accepte parfaitement la falsification.
FALSIFIE = {**DEBAT, "resolution_suggeree": "closed_proceed",
            "hypotheses_sous_tension": [
                # H1 est réellement invalidée (19 < 25) ; le modèle recopie 5.0 et déclare "aucun".
                tension(invalidation=5.0, valeur=19.0, franchi="aucun")]}
check("le CONTRAT accepte un seuil_invalidation falsifié (5.0 au lieu de 25.0) + closed_proceed "
      "— LE TROU EXISTE", accepte(ConvictionChallenge, FALSIFIE))
check("le contrat accepte aussi un `seuil_franchi` sous-déclaré sur des seuils justes",
      accepte(ConvictionChallenge, {**DEBAT, "resolution_suggeree": "closed_proceed",
                                    "hypotheses_sous_tension": [tension(franchi="alerte")]}))

# Moitié 2 — après rétablissement depuis la thèse figée, la revalidation le refuse.
inp = inputs()
restaure = _forcer_seuils_figes(dict(FALSIFIE), inp)
h0 = restaure["hypotheses_sous_tension"][0]
check("seuil_invalidation RÉÉCRIT depuis la thèse figée (5.0 → 25.0)", h0["seuil_invalidation"] == 25.0)
check("seuil_alerte réécrit depuis la thèse figée", h0["seuil_alerte"] == 30.0)
check("seuil_franchi RECALCULÉ ('aucun' → 'invalidation')", h0["seuil_franchi"] == "invalidation")
check("valeur_observee LAISSÉE au modèle (c'est sa lecture des entries, pas la métrique du garde-fou)",
      h0["valeur_observee"] == 19.0)
check("observation laissée au modèle", h0["observation"].startswith("H1 observé"))
check("le contrat REVALIDÉ refuse le closed_proceed — LE TROU EST BOUCHÉ",
      rejette(ConvictionChallenge, restaure))
check("thesis_id et schema_version forcés depuis la base (#24)",
      restaure["thesis_id"] == 5 and restaure["schema_version"] == "v2.0.0")

# Le rétablissement ne doit pas non plus DURCIR à tort : une tension réelle reste ce qu'elle est.
honnete = _forcer_seuils_figes(dict(DEBAT), inputs())
check("un débat honnête traverse le rétablissement sans changer",
      honnete["hypotheses_sous_tension"][0]["seuil_franchi"] == "invalidation"
      and accepte(ConvictionChallenge, honnete))
# Sens inverse : un modèle qui SUR-déclare une invalidation est corrigé aussi.
sur = _forcer_seuils_figes(
    {**DEBAT, "hypotheses_sous_tension": [tension(valeur=34.0, franchi="invalidation")]}, inputs())
check("sur-déclaration corrigée vers le bas (34 % > alerte 30 % → 'aucun')",
      sur["hypotheses_sous_tension"][0]["seuil_franchi"] == "aucun")
check("une hypothèse INVENTÉE traverse `_forcer_seuils_figes` intacte (c'est le pont qui la refuse)",
      _forcer_seuils_figes({**DEBAT, "hypotheses_sous_tension": [tension(hid="H9")]},
                           inputs())["hypotheses_sous_tension"][0]["seuil_invalidation"] == 25.0)


print("\n§6 — `_valider_pont_debat` : référentiel figé et entries réellement envoyées")
check("débat nominal accepté par le pont",
      passe(_valider_pont_debat, ConvictionChallenge(**DEBAT), inputs()))
check("hypothèse H9 inconnue de la thèse figée REFUSÉE",
      refuse(_valider_pont_debat, ConvictionChallenge(**{**DEBAT, "hypotheses_sous_tension": [
          tension(hid="H9")]}), inputs(), exc=DebateRefused))
check("source_entry_refs pointant une entry absente du contexte REFUSÉE (A2)",
      refuse(_valider_pont_debat, ConvictionChallenge(**{**DEBAT, "cas_contre_maintien": [
          {**CONTRE[0], "source_entry_refs": [{"entry_id": 999, "version": 1}]}]}),
             inputs(), exc=DebateRefused))
check("entry 513 (envoyée mais non citée ailleurs) ACCEPTÉE",
      passe(_valider_pont_debat, ConvictionChallenge(**{**DEBAT, "cas_contre_maintien": [
          {**CONTRE[0], "source_entry_refs": [{"entry_id": 513, "version": 1}]}]}), inputs()))


print("\n§7 — `_valider_pont_sortie` : une origine déclarée doit correspondre à un FAIT")
plan_ok = ExitPlan(**PLAN)
INVALIDEES = [{**FIGEES[0], "statut": "invalidee"}, FIGEES[1], FIGEES[2]]
ALERTE = [{**FIGEES[0], "statut": "alerte"}, FIGEES[1], FIGEES[2]]

check("origine='hypothese_invalidee' SANS hypothèse invalidée REFUSÉE — la sortie habillée",
      refuse(_valider_pont_sortie, plan_ok, inputs()))
check("origine='hypothese_invalidee' AVEC H1 invalidée ACCEPTÉE",
      passe(_valider_pont_sortie, plan_ok, inputs(hypotheses=INVALIDEES)))
check("une hypothèse en simple ALERTE ne suffit pas à 'hypothese_invalidee'",
      refuse(_valider_pont_sortie, plan_ok, inputs(hypotheses=ALERTE)))

deg = ExitPlan(**{**PLAN, "origine": "thesis_degradation"})
check("origine='thesis_degradation' sans aucun signe de dégradation REFUSÉE (anti-churn §10)",
      refuse(_valider_pont_sortie, deg, inputs()))
check("'thesis_degradation' justifiée par une hypothèse en alerte ACCEPTÉE",
      passe(_valider_pont_sortie, deg, inputs(hypotheses=ALERTE)))
check("'thesis_degradation' justifiée par une session escaladée ACCEPTÉE",
      passe(_valider_pont_sortie, deg, inputs(sessions=[session(alert="CRITICAL")])))
check("une session RAS ne justifie pas une dégradation",
      refuse(_valider_pont_sortie, deg, inputs(sessions=[session(alert="RAS")])))

rdt = ExitPlan(**{**PLAN, "origine": "rendement_insuffisant"})
check("origine='rendement_insuffisant' sans arbitrage prospectif REFUSÉE (§11 anti-ratio mécanique)",
      refuse(_valider_pont_sortie, rdt, inputs()))
check("'rendement_insuffisant' justifiée par un mode 6 `suffisant=false` ACCEPTÉE",
      passe(_valider_pont_sortie, rdt,
            inputs(sessions=[session(result={"rendement_prospectif": {"suffisant": False}})])))
check("un mode 6 `suffisant=true` ne justifie PAS 'rendement_insuffisant'",
      refuse(_valider_pont_sortie, rdt,
             inputs(sessions=[session(result={"rendement_prospectif": {"suffisant": True}})])))
check("origine='reallocation' n'exige AUCUN antécédent (choix d'allocation, décision légitime)",
      passe(_valider_pont_sortie, ExitPlan(**{**PLAN, "origine": "reallocation"}), inputs()))

check("plan sans position ouverte REFUSÉ (tranches vides sur des titres inexistants)",
      refuse(_valider_pont_sortie, ExitPlan(**{**PLAN, "origine": "reallocation"}),
             inputs(position=None)))
check("plan sur position déjà clôturée REFUSÉ",
      refuse(_valider_pont_sortie, ExitPlan(**{**PLAN, "origine": "reallocation"}),
             inputs(position=POSITION_SOLDEE)))
# Le contrat voit Σ=100 et l'accepte ; seul le pont sait que 40 % ont déjà été vendus.
check("Σ tranches + DÉJÀ EXÉCUTÉ > 100 % REFUSÉ (le contrat ne voit que le nouveau plan)",
      refuse(_valider_pont_sortie, ExitPlan(**{**PLAN, "origine": "reallocation"}),
             inputs(executions=[EXECUTIONS[0]])))
check("le même plan reste ACCEPTÉ par le contrat seul — les deux moitiés, à nouveau",
      accepte(ExitPlan, {**PLAN, "origine": "reallocation"}))
check("Σ compatible avec le déjà-vendu ACCEPTÉ",
      passe(_valider_pont_sortie,
            ExitPlan(**{**PLAN, "origine": "reallocation",
                        "tranches": [{"ordre": 1, "pct_a_vendre": 60.0, "declencheur": "d"}]}),
            inputs(executions=[EXECUTIONS[0]])))


print("\n§8 — `_valider_pont_postmortem` : un bilan juge une histoire TERMINÉE")
check("post-mortem sur position encore ouverte REFUSÉ",
      refuse(_valider_pont_postmortem, pm_ok, inputs()))
check("post-mortem sur position soldée (status='closed') ACCEPTÉ",
      passe(_valider_pont_postmortem, pm_ok, inputs(position=POSITION_SOLDEE)))
check("post-mortem sur position à 0 titre ACCEPTÉ (soldée de fait)",
      passe(_valider_pont_postmortem, pm_ok,
            inputs(position={**POSITION_OUVERTE, "shares": 0.0})))
check("post-mortem qui OMET une hypothèse figée REFUSÉ",
      refuse(_valider_pont_postmortem,
             PostMortem(**{**PM, "hypotheses_finales": PM["hypotheses_finales"][:2]}),
             inputs(position=POSITION_SOLDEE)))
check("post-mortem qui INVENTE une hypothèse REFUSÉ",
      refuse(_valider_pont_postmortem,
             PostMortem(**{**PM, "hypotheses_finales": PM["hypotheses_finales"] + [
                 {"hypothese_id": "H9", "statut_final": "confirmee", "predite_vs_realisee": "x"}]}),
             inputs(position=POSITION_SOLDEE)))


print("\n§9 — `_valider_pont_calibration` : pas d'écart à mesurer sans bilan")
check("calibration sans post-mortem abouti REFUSÉE",
      refuse(_valider_pont_calibration, CalibrationEntry(**CALIB), inputs(position=POSITION_SOLDEE)))
check("calibration après post-mortem ACCEPTÉE",
      passe(_valider_pont_calibration, CalibrationEntry(**CALIB),
            inputs(position=POSITION_SOLDEE, post_mortem={"id": 3})))


print("\n§10 — `_forcer_champs_derives` : ce que le code calcule n'est jamais reçu (#24)")
d = _forcer_champs_derives("exit_plan", {**PLAN, "thesis_id": 999, "exit_status": "closed"}, inputs())
check("`exit_status='closed'` déclaré à la CRÉATION ramené à 'plan_created' "
      "(clôturer est un fait d'exécution)", d["exit_status"] == "plan_created")
check("thesis_id écrasé par celui de la base", d["thesis_id"] == 5)
d2 = _forcer_champs_derives("exit_plan", {**PLAN, "exit_status": "accelerated_exit",
                                          "conditions_accelerees": [{"type": "iv_revisee_baisse",
                                                                     "seuil": "-20 %"}]}, inputs())
check("'accelerated_exit' AVEC conditions conservé (c'est une intention, pas un fait d'exécution)",
      d2["exit_status"] == "accelerated_exit")
check("'accelerated_exit' SANS condition ramené à 'plan_created'",
      _forcer_champs_derives("exit_plan", {**PLAN, "exit_status": "accelerated_exit"},
                             inputs())["exit_status"] == "plan_created")

inp_pm = inputs(position=POSITION_SOLDEE, executions=EXECUTIONS)
dpm = _forcer_champs_derives("post_mortem", {**PM, "duree_jours": 10, "performance_pct": 99.0}, inp_pm)
# 100 titres à 300 € = 30 000 € engagés ; 14 000 + 21 600 = 35 600 € encaissés → +18,666 %.
check("performance_pct RECALCULÉE sur les faits (99 % annoncés → 18.67 % réels)",
      abs(dpm["performance_pct"] - 18.6667) < 0.01, f"— reçu {dpm['performance_pct']}")
check("duree_jours RECALCULÉE (entrée 2026-01-15 → dernière vente 2026-08-20 = 217 j)",
      dpm["duree_jours"] == 217, f"— reçu {dpm['duree_jours']}")
check("post-mortem SANS exécution de sortie REFUSÉ (pas de perf sur une intention de vendre)",
      refuse(_forcer_champs_derives, "post_mortem", dict(PM), inputs(position=POSITION_SOLDEE)))
check("post-mortem sans purchase_price_eur REFUSÉ (perf sans assiette = chiffre inventé)",
      refuse(_forcer_champs_derives, "post_mortem", dict(PM),
             inputs(position={**POSITION_SOLDEE, "purchase_price_eur": None},
                    executions=EXECUTIONS)))

# Le point central de la calibration : `predite` vient du FIGÉ AU VALIDATE (320), pas du
# `valuation_range` courant (380) que la revue annuelle a réactualisé, ni du modèle (350).
dc = _forcer_champs_derives("calibration", {**CALIB, "paires": [
    {"metric": "iv_base", "predite": 350.0, "realisee": 355.0}]}, inputs())
check("`predite` réécrite depuis validation_json FIGÉ (350 déclaré → 320), pas depuis le "
      "valuation_range courant (380)", dc["paires"][0]["predite"] == 320.0,
      f"— reçu {dc['paires'][0]['predite']}")
check("`realisee` laissée intacte (c'est le fait mesuré)", dc["paires"][0]["realisee"] == 355.0)
check("iv_low / iv_high réécrites elles aussi",
      [p["predite"] for p in _forcer_champs_derives("calibration", {**CALIB, "paires": [
          {"metric": "iv_low", "predite": 1.0, "realisee": 2.0},
          {"metric": "iv_high", "predite": 1.0, "realisee": 2.0}]}, inputs())["paires"]]
      == [250.0, 400.0])
check("une métrique hors IV (`risque:H3`) est laissée au modèle — rien à réécrire en base",
      _forcer_champs_derives("calibration", {**CALIB, "paires": [
          {"metric": "risque:H3", "predite": 0.3, "realisee": 0.0}]},
          inputs())["paires"][0]["predite"] == 0.3)


print("\n§11 — `_verifier_etat` : les refus qui tombent AVANT la dépense de tokens")
check("plan de sortie sur thèse non active REFUSÉ",
      refuse(_verifier_etat, "exit_plan", inputs(thesis={"status": "draft"}), exc=ThesisNotExitable))
check("plan de sortie sur thèse active ACCEPTÉ", passe(_verifier_etat, "exit_plan", inputs()))
check("second plan alors qu'un plan est EN COURS REFUSÉ (deux séries de tranches sur les mêmes titres)",
      refuse(_verifier_etat, "exit_plan",
             inputs(plan={"id": 2, "exit_status": "partially_exited"}), exc=ThesisNotExitable))
check("nouveau plan après un plan CLÔTURÉ accepté",
      passe(_verifier_etat, "exit_plan", inputs(plan={"id": 2, "exit_status": "closed"})))
check("post-mortem déjà établi → second bilan REFUSÉ (il dupliquerait les paires A5)",
      refuse(_verifier_etat, "post_mortem",
             inputs(position=POSITION_SOLDEE, post_mortem={"id": 3}), exc=ThesisNotExitable))
check("post-mortem sur thèse 'closed' accepté (le bilan vient APRÈS la clôture)",
      passe(_verifier_etat, "post_mortem",
            inputs(position=POSITION_SOLDEE, thesis={"status": "closed"})))
check("calibration sans post-mortem REFUSÉE avant tout appel",
      refuse(_verifier_etat, "calibration", inputs(), exc=ThesisNotExitable))


print("\n§12 — Arithmétique de position : `shares` est DÉCRÉMENTÉ à chaque vente")
inp_arith = inputs(position={**POSITION_OUVERTE, "shares": 40.0}, executions=[EXECUTIONS[0]])
check("assiette initiale = restants + vendus (40 + 40 = 100 ≠ 40)",
      _shares_initiales(inp_arith) == 80.0, f"— reçu {_shares_initiales(inp_arith)}")
check("coût de revient calculé sur l'assiette reconstituée (80 × 300 = 24 000 €)",
      _cout_de_revient_eur(inp_arith) == 24000.0)
check("coût de revient None si purchase_price_eur absent (pas d'invention)",
      _cout_de_revient_eur(inputs(position={**POSITION_OUVERTE, "purchase_price_eur": None})) is None)
check("coût de revient None sans position", _cout_de_revient_eur(inputs(position=None)) is None)
check("% exécuté = Σ des tranches vendues", _pct_execute(inputs(executions=EXECUTIONS)) == 100.0)
check("% exécuté = 0 sans exécution", _pct_execute(inputs()) == 0.0)


print("\n§13 — Surface HTTP : aucun corps n'expose de champ de JUGEMENT (#36)")
# Les trois POST d'agent n'ont PAS de corps du tout : rien à inspecter, c'est le but.
JUGEMENT = {"origine", "tranches", "exit_status", "conditions_accelerees", "performance_pct",
            "duree_jours", "hypotheses_finales", "lecons", "predite", "paires",
            "resolution_suggeree", "escalade_recommandee", "seuil_alerte", "seuil_invalidation",
            "seuil_franchi", "hypotheses_sous_tension", "cas_contre_maintien", "verdict"}
for corps in (ExecuteTrancheBody, ExitAlertBody, DebateRunBody):
    fuite = set(corps.model_fields) & JUGEMENT
    check(f"{corps.__name__} n'expose aucun champ de jugement", not fuite, f"— fuite : {sorted(fuite)}")
check("ExecuteTrancheBody n'expose ni `pct_a_vendre` ni `declencheur` (recopiés du plan figé)",
      not {"pct_a_vendre", "declencheur"} & set(ExecuteTrancheBody.model_fields))
check("ExecuteTrancheBody n'expose que des FAITS d'exécution",
      set(ExecuteTrancheBody.model_fields) == {"ordre", "shares", "sell_price_eur", "sell_date", "note"})
check("ExitAlertBody n'expose pas `label` (le motif vient du déclencheur figé)",
      "label" not in ExitAlertBody.model_fields)
check("DebateRunBody n'expose que le CONTEXTE du déclenchement",
      set(DebateRunBody.model_fields) == {"motif", "monitoring_session_v2_id"})
# La seule exception assumée : la clôture est l'acte souverain de l'utilisateur.
check("CloseDebateBody porte `resolution` — jugement de L'UTILISATEUR, pas de l'agent",
      "resolution" in CloseDebateBody.model_fields
      and set(CloseDebateBody.model_fields) == {"resolution", "note"})


print("\n§14 — Migration 032 ↔ code : ce que le code écrit passe les CHECKs")
MIG = Path("app/db/migrations/032_v2_exit_calibration_debate.sql").read_text(encoding="utf-8")
for table in ("exit_plans", "exit_executions", "post_mortems_v2", "calibration_registry",
              "conviction_debates_v2"):
    check(f"table `{table}` créée par la migration", f"CREATE TABLE IF NOT EXISTS {table}" in MIG)
for garde in ("uq_exit_plan_actif", "uq_exit_execution_tranche", "uq_post_mortem_v2_thesis",
              "uq_calibration_metric", "cd_v2_anti_complaisance", "pp_exit_status_flux_v2",
              "pa_alert_type_coherent"):
    check(f"garde-fou `{garde}` posé", garde in MIG)
check("`theses_v2` ouverte au statut terminal 'closed' (sinon on écrirait un faux 'invalidated')",
      "'closed'" in MIG and "theses_v2_status_check" in MIG)
check("`analysis_kind` ouvert à 'debate' (le snapshot des refs du débat)",
      "'debate'" in MIG and "analysis_refs_kind_domain" in MIG)
check("`exit_executions` distingue prix natif et prix EUR (V1 nomme `sell_price` en EUR)",
      "sell_price_native" in MIG and "sell_price_eur" in MIG)
check("`proceeds_eur` est GÉNÉRÉE, pas écrite (une trésorerie ne se déclare pas)",
      "proceeds_eur" in MIG and "GENERATED ALWAYS AS" in MIG)
check("`ecart` du registre est GÉNÉRÉ (realisee - predite)",
      "ecart" in MIG and "realisee - predite" in MIG)
# Tout le vocabulaire que le code peut écrire doit exister dans les CHECKs de la base.
for valeur in ("plan_created", "partially_exited", "accelerated_exit", "closed"):
    check(f"exit_status '{valeur}' accepté par la base", f"'{valeur}'" in MIG)
for valeur in ("hypothese_invalidee", "thesis_degradation", "rendement_insuffisant", "reallocation"):
    check(f"origine '{valeur}' acceptée par la base", f"'{valeur}'" in MIG)
for valeur in ("closed_pass", "closed_monitor", "closed_proceed", "open"):
    check(f"statut de débat '{valeur}' accepté par la base", f"'{valeur}'" in MIG)
for valeur in ("exit_tranche", "exit_accelere", "manual"):
    check(f"alert_type '{valeur}' accepté par la base", f"'{valeur}'" in MIG)
check("`post_mortem` ABSENT du domaine analysis_kind (aucun chemin ne peut le remplir — #32)",
      "'post_mortem'" not in MIG.split("analysis_refs_kind_domain")[-1][:400])


print("\n§15 — Règle #19 : contrat figé ↔ copie runtime")
FROZEN = Path("/contract_frozen")
if (FROZEN / "exit_calibration_schema.py").exists():
    src_exit = (FROZEN / "exit_calibration_schema.py").read_text(encoding="utf-8")
    src_deb = (FROZEN / "debate_conviction_schema.py").read_text(encoding="utf-8")
    for nom in ("class ExitPlan", "class ExitTranche", "class ConditionAcceleree",
                "class PostMortem", "class HypothesisOutcome", "class Lecon",
                "class CalibrationEntry", "class CalibrationPair", "valider_postmortem_couvre"):
        check(f"contrat figé sortie/calibration porte `{nom}`", nom in src_exit)
    for nom in ("class ConvictionChallenge", "class HypotheseSousTension", "class ContreArgument",
                "_anti_complaisance", "SeuilFranchi", "ResolutionDebat"):
        check(f"contrat figé débat porte `{nom}`", nom in src_deb)
    for modele, src in ((ExitPlan, src_exit), (PostMortem, src_exit), (CalibrationEntry, src_exit),
                        (ConvictionChallenge, src_deb)):
        ecart = {c for c in modele.model_fields if f"{c}:" not in src}
        check(f"aucun champ runtime absent du figé ({modele.__name__})", not ecart,
              f"— écart : {sorted(ecart)}")
else:
    print("  ---- contrat figé non monté (/contract_frozen) : comparaison NON faite.")
    print("       monter avec -v <repo>/roadmap/provenance-cards:/contract_frozen:ro")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
