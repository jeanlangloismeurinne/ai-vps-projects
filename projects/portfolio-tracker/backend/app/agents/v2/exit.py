"""
Sortie / post-mortem / calibration (§11, §12, A5 — lot 9, migration 032) : le dernier maillon.

C'est ici que la boucle se ferme. Le monitoring (lot 8) pose `routing_suggestion='exit_plan'` quand
un mode 3/6 rend REDUIRE ou SORTIR ; ce module transforme cette suggestion en plan de sortie
thèse-driven, exécute les tranches sur l'argent réel, puis — au dernier lot vendu — juge la thèse et
en tire ce que le système gardera : des leçons retrouvables et un registre de calibration.

Trois choses que ni le contrat Pydantic ni la base ne peuvent tenir seuls.

1. LE PONT INTER-OBJETS (`_valider_pont_sortie`, `_valider_pont_postmortem`). Convention #37 : un
   contrat valide UN objet, jamais la cohérence entre deux. `ExitPlan` accepte parfaitement
   `origine='hypothese_invalidee'` sur une thèse dont les quatre hypothèses sont `confirmee` — les
   statuts vivent dans `theses_v2.hypotheses`, hors payload. Or l'`origine` n'est pas décorative :
   c'est elle qui rend la sortie THÈSE-DRIVEN plutôt que mécanique (§11). Une origine invérifiée,
   c'est la sortie au feeling avec une étiquette de thèse dessus. Chaque origine exige donc ici son
   antécédent factuel, et le message de refus dit lequel.

2. CE QUI SE CALCULE NE SE DEMANDE PAS AU MODÈLE (`_forcer_champs_derives`, conventions #24/#36).
   `duree_jours` et `performance_pct` se déduisent des dates et du cash réellement encaissé ; les
   `predite` de la calibration sont dans la thèse FIGÉE au validate. Les faire produire par le
   modèle, c'est accepter qu'un chiffre inventé entre dans le registre A5 — et le registre A5 n'a
   qu'une seule utilité : mesurer notre erreur. Un registre flatté ne mesure plus rien. C'est le
   seul endroit du système où une hallucination ne se verrait jamais : personne ne recompte une
   performance passée deux ans plus tard.

3. L'EXÉCUTION EST UN FAIT DU MONDE, PAS UN JUGEMENT (`execute_tranche`). Vendre appelle ZÉRO
   modèle : le plan a déjà été jugé, l'exécution n'est que de l'arithmétique sur de l'argent réel.
   Elle est atomique (position, cash, exécution, statut du plan) et l'unicité `(exit_plan_id, ordre)`
   de la migration 032 la protège du double POST.

Atomicité (convention #35) : `get_db_session()` n'ouvre AUCUNE transaction. L'appel modèle et les
appels réseau (FX, embeddings des leçons) se font HORS transaction ; l'écriture est ensuite
explicitement atomique.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from app.agents.providers import get_agent_provider
from app.agents.v2.common import format_entries_for_prompt
from app.agents.v2.runner import run_json_agent
from app.contracts import (
    CalibrationEntry,
    ExitPlan,
    PostMortem,
    valider_postmortem_couvre,
)
from app.db.database import get_db_session
from app.knowledge import get_current_entries, store_knowledge

logger = logging.getLogger(__name__)

AGENT_NAME = "postmortem-agent"

MODES = ("exit_plan", "post_mortem", "calibration")
MODE_SCHEMAS: dict[str, Any] = {
    "exit_plan": ExitPlan,
    "post_mortem": PostMortem,
    "calibration": CalibrationEntry,
}

# Une leçon est une interprétation de faits observés par nos propres agents : `agent_synthesis`
# (tier B-) est sa source honnête. Elle n'est ni un document officiel, ni de la mémoire modèle.
LESSON_SOURCE_TYPE = "agent_synthesis"
LESSON_ENTRY_TYPE = "lesson_learned"

# Métriques de calibration dont la valeur PRÉDITE est dans la thèse figée : elles ne sont pas à
# la discrétion du modèle (voir `_forcer_predites`).
_METRIQUES_IV = {"iv_low": "low", "iv_base": "base", "iv_high": "high"}


class ThesisNotExitable(RuntimeError):
    """La thèse n'est pas dans un état où l'acte demandé a un sens (pas de position, déjà close…)."""


class ExitRefused(ValueError):
    """Sortie formellement conforme mais incohérente avec l'état réel de la thèse ou du portefeuille.

    Le JSON est valide, le contrat est satisfait, et pourtant l'objet ment sur le monde : une origine
    sans antécédent, un post-mortem sur une position encore ouverte, une calibration sans bilan.
    Se traduit en HTTP 422 — l'échec est persisté pour rester auditable."""


class ExitPlanNotFound(LookupError):
    """Aucun plan de sortie exploitable pour cette thèse / cet identifiant."""


class TrancheConflict(RuntimeError):
    """L'exécution demandée contredit l'état du plan (tranche déjà vendue, ordre sauté, sur-vente)."""


# ── Chargement des intrants ──────────────────────────────────────────────────
async def _load_exit_inputs(conn, thesis_v2_id: int) -> dict[str, Any]:
    """Thèse figée + position réelle + plan en cours + historique de suivi + corpus courant.

    Tout vient de la base : la sortie se juge sur ce qui a été FIGÉ à l'entrée et sur ce qui s'est
    RÉELLEMENT passé, jamais sur ce que le modèle se rappelle avoir dit.
    """
    thesis = await conn.fetchrow("SELECT * FROM theses_v2 WHERE id = $1", thesis_v2_id)
    if thesis is None:
        raise LookupError(f"Thèse V2 #{thesis_v2_id} introuvable.")

    position = await conn.fetchrow(
        "SELECT * FROM portfolio_positions WHERE thesis_v2_id = $1 ORDER BY id LIMIT 1", thesis_v2_id
    )

    plan = await conn.fetchrow(
        "SELECT * FROM exit_plans WHERE thesis_v2_id = $1 AND status = 'completed' "
        "ORDER BY id DESC LIMIT 1",
        thesis_v2_id,
    )
    executions: list[dict[str, Any]] = []
    if plan is not None:
        executions = [
            dict(r) for r in await conn.fetch(
                "SELECT * FROM exit_executions WHERE exit_plan_id = $1 ORDER BY ordre",
                plan["id"],
            )
        ]

    post_mortem = await conn.fetchrow(
        "SELECT * FROM post_mortems_v2 WHERE thesis_v2_id = $1 AND status = 'completed' "
        "ORDER BY id DESC LIMIT 1",
        thesis_v2_id,
    )

    sessions = [
        dict(r) for r in await conn.fetch(
            "SELECT id, mode, alert_level, verdict, routing_suggestion, result_json, created_at "
            "FROM monitoring_sessions_v2 WHERE thesis_v2_id = $1 AND status = 'completed' "
            "ORDER BY id DESC LIMIT 10",
            thesis_v2_id,
        )
    ]

    memo_json: dict[str, Any] = {}
    if thesis["research_memo_id"] is not None:
        memo = await conn.fetchrow(
            "SELECT memo_json FROM research_memos WHERE id = $1", thesis["research_memo_id"]
        )
        memo_json = (memo["memo_json"] if memo else None) or {}

    entries = await get_current_entries(conn, thesis["ticker_id"], limit=500)

    return {
        "thesis": thesis,
        "hypotheses": list(thesis["hypotheses"] or []),
        "validation_json": dict(thesis["validation_json"] or {}),
        "position": position,
        "plan": plan,
        "executions": executions,
        "post_mortem": post_mortem,
        "sessions": sessions,
        "memo_json": memo_json,
        "entries": entries,
    }


# ── Arithmétique de la position (aucun modèle n'y touche) ────────────────────
def _shares_initiales(inputs: dict[str, Any]) -> float:
    """Titres détenus à l'entrée = restants + déjà vendus.

    `portfolio_positions.shares` est DÉCRÉMENTÉ à chaque vente (convention du portefeuille partagé,
    cf. `portfolio_v2.reduce_position`). Lire `shares` après une vente partielle et l'appeler
    « position initiale » donnerait une performance calculée sur une assiette fausse.
    """
    pos = inputs["position"]
    restants = float(pos["shares"]) if pos is not None else 0.0
    vendus = sum(float(e["shares_sold"]) for e in inputs["executions"])
    return restants + vendus


def _cout_de_revient_eur(inputs: dict[str, Any]) -> Optional[float]:
    """Cash réellement débité à l'entrée. `None` si la base ne le porte pas (pas d'invention)."""
    pos = inputs["position"]
    if pos is None or pos["purchase_price_eur"] is None:
        return None
    return float(pos["purchase_price_eur"]) * _shares_initiales(inputs)


def _pct_execute(inputs: dict[str, Any]) -> float:
    """Pourcentage du plan déjà exécuté (somme des tranches vendues)."""
    return sum(float(e["pct_a_vendre"]) for e in inputs["executions"])


def _position_soldee(inputs: dict[str, Any]) -> bool:
    pos = inputs["position"]
    return pos is not None and (pos["status"] == "closed" or float(pos["shares"]) <= 0)


# ── Contexte envoyé au modèle ────────────────────────────────────────────────
def _format_hypotheses(hypotheses: list[dict[str, Any]]) -> str:
    """Hypothèses figées AVEC leurs seuils et leur statut courant (celui reporté par le monitoring).

    Les seuils sont donnés en LECTURE : la sortie ne les réécrit jamais (corollaire de #37 — sinon
    on pourrait ajuster après coup le seuil qu'on est en train de déclarer franchi).
    """
    if not hypotheses:
        return "(aucune hypothèse figée — anomalie : une thèse validée en porte toujours)"
    lignes = []
    for h in hypotheses:
        unite = h.get("unite") or ""
        lignes.append(
            f"- {h.get('id')} [statut courant : {h.get('statut', 'active')}] {h.get('enonce', '')}\n"
            f"    KPI {h.get('kpi', '?')} — seuil_alerte {h.get('seuil_alerte')}{unite} · "
            f"seuil_invalidation {h.get('seuil_invalidation')}{unite}"
            + (f"\n    dernière observation : {h['derniere_observation']}"
               if h.get("derniere_observation") else "")
        )
    return "\n".join(lignes)


def _format_sessions(sessions: list[dict[str, Any]]) -> str:
    """Historique de suivi : c'est lui qui FONDE l'origine de la sortie."""
    if not sessions:
        return "(aucune session de monitoring aboutie)"
    lignes = []
    for s in sessions:
        res = s.get("result_json") or {}
        extra = ""
        rp = res.get("rendement_prospectif") or {}
        if rp:
            extra = (f" · rendement prospectif suffisant={rp.get('suffisant')} "
                     f"({rp.get('rendement_annualise_pct')}%/an)")
        if res.get("exit_trigger"):
            extra += f" · exit_trigger : {res['exit_trigger']}"
        lignes.append(
            f"- session #{s['id']} (mode {s['mode']}, {str(s['created_at'])[:10]}) : "
            f"alerte={s['alert_level']} verdict={s['verdict']} routage={s['routing_suggestion']}{extra}"
        )
    return "\n".join(lignes)


def _format_executions(inputs: dict[str, Any]) -> str:
    """Ce qui a RÉELLEMENT été vendu — la matière du post-mortem."""
    if not inputs["executions"]:
        return "(aucune tranche exécutée)"
    return "\n".join(
        f"- tranche {e['ordre']} le {e['executed_at']} : {e['shares_sold']} titres @ "
        f"{e['sell_price_eur']} € ({e['pct_a_vendre']}% du plan) → {e['proceeds_eur']} € encaissés"
        for e in inputs["executions"]
    )


def _head(inputs: dict[str, Any]) -> str:
    """Bloc front-loadé déterministe (discipline de cache §5.3 : aucun champ volatil)."""
    t = inputs["thesis"]
    pos = inputs["position"]
    val_figee = (inputs["validation_json"].get("valuation_range")
                 or t["valuation_range"] or {})
    val_courante = t["valuation_range"] or {}

    if pos is None:
        bloc_position = "(aucune position enregistrée pour cette thèse)"
    else:
        bloc_position = (
            f"{_shares_initiales(inputs)} titres à l'entrée · PRU {pos['purchase_price_eur']} € "
            f"({pos['purchase_price']} {pos['purchase_currency']}) · achetés le {pos['purchase_date']}\n"
            f"Restant en portefeuille : {pos['shares']} titres · statut {pos['status']} · "
            f"exit_status {pos['exit_status']}"
        )

    return (
        f"## Thèse V2 #{t['id']} — {t['ticker_id']} (figée au validate)\n"
        f"Verdict d'entrée : {t['verdict']} · sizing {t['position_sizing_pct']}% · "
        f"validée le {t['validated_at']} · statut {t['status']}\n"
        f"Fourchette de valeur intrinsèque FIGÉE À L'ENTRÉE (référence de calibration) : "
        f"low {val_figee.get('low')} · base {val_figee.get('base')} · high {val_figee.get('high')}\n"
        f"Fourchette courante (réactualisée par les revues annuelles) : "
        f"low {val_courante.get('low')} · base {val_courante.get('base')} · high {val_courante.get('high')}\n\n"
        f"## Position réelle\n{bloc_position}\n\n"
        f"## Hypothèses figées, seuils PRÉ-ENREGISTRÉS et statut courant (lecture seule)\n"
        f"{_format_hypotheses(inputs['hypotheses'])}\n\n"
        f"## Historique de suivi (ce qui fonde l'origine d'une sortie)\n"
        f"{_format_sessions(inputs['sessions'])}\n\n"
        f"## Tranches déjà exécutées\n{_format_executions(inputs)}\n\n"
        f"## knowledge_entries courantes (le réalisé s'y lit)\n"
        f"{format_entries_for_prompt(inputs['entries'])}"
    )


def _tache(mode: str, inputs: dict[str, Any]) -> str:
    t = inputs["thesis"]
    ids = ", ".join(str(h.get("id")) for h in inputs["hypotheses"]) or "(aucune)"

    if mode == "exit_plan":
        restant = 100 - _pct_execute(inputs)
        return (
            f"Produis le plan de sortie de la thèse #{t['id']} (contrat ExitPlan).\n"
            f"`origine` est OBLIGATOIRE et THÈSE-DRIVEN : la sortie a une cause de thèse, jamais un "
            f"pur seuil de prix. Elle doit être ÉTAYÉE par l'état réel ci-dessus — "
            f"`hypothese_invalidee` exige une hypothèse effectivement au statut `invalidee` ; "
            f"`thesis_degradation` exige une dégradation constatée (hypothèse en alerte/invalidée ou "
            f"session de suivi escaladée) ; `rendement_insuffisant` exige un arbitrage rendement/"
            f"risque prospectif déjà établi par le suivi (mode 6 `suffisant=false`, ou verdict "
            f"REDUIRE/SORTIR). Une origine non étayée par ce qui précède sera REFUSÉE.\n"
            f"Les tranches sont l'EXÉCUTION de cette décision : ordres 1..n consécutifs, "
            f"Σ pct_a_vendre ≤ {restant:g} (le reste du plan disponible), chaque `declencheur` "
            f"explicite et vérifiable. `conditions_accelerees` si une invalidation critique ou une "
            f"IV révisée de −20 % doit précipiter la sortie."
        )

    if mode == "post_mortem":
        return (
            f"La position est soldée. Produis le bilan de la thèse #{t['id']} (contrat PostMortem).\n"
            f"`hypotheses_finales` doit couvrir EXACTEMENT les hypothèses figées ({ids}) — aucune "
            f"oubliée, aucune inventée : chacune reçoit un `statut_final` et un `predite_vs_realisee` "
            f"chiffré, lu dans les entries ci-dessus.\n"
            f"`duree_jours` et `performance_pct` sont RECALCULÉS par le système à partir des dates et "
            f"du cash réellement encaissé : donne ce que tu lis, ils seront écrasés — ne bâtis aucun "
            f"raisonnement dessus.\n"
            f"≥1 `lecon`, chacune TAGUÉE : ces leçons deviennent des knowledge_entries réutilisables "
            f"par les futurs bull-agents sur des comparables. Une leçon sans tag est irrécupérable. "
            f"Sois factuel et impitoyable : une leçon qui ménage la décision passée ne sert à rien."
        )

    return (
        f"Produis le registre de calibration de la thèse #{t['id']} (contrat CalibrationEntry).\n"
        f"≥1 paire prédit/réalisé. Le PRÉDIT se lit dans la thèse FIGÉE À L'ENTRÉE ci-dessus (les "
        f"`iv_low`/`iv_base`/`iv_high` seront de toute façon repris de la thèse figée) ; le RÉALISÉ "
        f"se lit dans le bilan et les entries. Métriques utiles : `iv_base`, `risque:H3`, "
        f"`rendement_5ans`, tout KPI d'hypothèse chiffrable.\n"
        f"Ce registre n'a qu'un usage : mesurer notre erreur systématique sur 15-20 positions. "
        f"Une calibration flattée détruit sa propre utilité."
    )


# ── Champs dérivés : ce que le code sait, on ne le demande pas (#24) ─────────
def _forcer_champs_derives(mode: str, data: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    """Écrase AVANT validation les champs que le code connaît ou calcule. Divergences logguées."""
    thesis_v2_id = inputs["thesis"]["id"]
    for champ, attendu in (("schema_version", "v2.0.0"), ("thesis_id", thesis_v2_id)):
        rendu = data.get(champ)
        if rendu is not None and rendu != attendu:
            logger.warning("exit %s: `%s` rendu (%r) ≠ valeur connue (%r) — écrasé",
                           mode, champ, rendu, attendu)
        data[champ] = attendu

    if mode == "exit_plan":
        # À la CRÉATION du plan, aucune tranche n'est vendue : `partially_exited` et `closed` sont
        # des faits d'exécution, que seul `execute_tranche` peut constater. Les laisser au modèle,
        # c'est laisser un JSON déclarer close une position qui ne l'est pas.
        rendu = data.get("exit_status")
        attendu = ("accelerated_exit"
                   if rendu == "accelerated_exit" and data.get("conditions_accelerees")
                   else "plan_created")
        if rendu != attendu:
            logger.info("exit_plan: exit_status rendu (%r) ramené à %r (état d'exécution réel)",
                        rendu, attendu)
        data["exit_status"] = attendu

    elif mode == "post_mortem":
        derives = _derives_postmortem(inputs)
        for champ, attendu in derives.items():
            rendu = data.get(champ)
            if rendu is not None and abs(float(rendu) - attendu) > 0.01:
                logger.warning(
                    "post_mortem: `%s` rendu par le modèle (%r) ≠ valeur calculée (%r) — écrasé. "
                    "C'est exactement ce que le calcul protège : ce chiffre part dans le registre A5.",
                    champ, rendu, attendu)
            data[champ] = attendu

    elif mode == "calibration":
        data["paires"] = _forcer_predites(data.get("paires") or [], inputs)

    return data


def _derives_postmortem(inputs: dict[str, Any]) -> dict[str, float]:
    """`duree_jours` et `performance_pct`, calculés sur les faits. Lève ExitRefused si incalculables.

    Refuser plutôt que laisser passer le chiffre du modèle : une performance approximative écrite
    une fois dans le registre de calibration y reste, et c'est elle qu'on relira dans deux ans pour
    juger nos propres biais.
    """
    pos = inputs["position"]
    execs = inputs["executions"]
    if pos is None or not execs:
        raise ExitRefused(
            "Post-mortem impossible : aucune exécution de sortie enregistrée. La durée et la "
            "performance se calculent sur des ventes réelles, pas sur une intention de vendre."
        )
    cout = _cout_de_revient_eur(inputs)
    if not cout:
        raise ExitRefused(
            f"Post-mortem impossible : le coût de revient EUR de la position #{pos['id']} est "
            "inconnu (`purchase_price_eur` vide). Une performance sans assiette d'achat est un "
            "chiffre inventé — et il alimenterait le registre de calibration."
        )

    derniere = max(e["executed_at"] for e in execs)
    duree = (derniere - pos["purchase_date"]).days
    produit = sum(float(e["proceeds_eur"]) for e in execs)
    return {"duree_jours": max(0, duree), "performance_pct": round((produit - cout) / cout * 100, 4)}


def _forcer_predites(paires: list[dict[str, Any]], inputs: dict[str, Any]) -> list[dict[str, Any]]:
    """Réécrit les `predite` des métriques d'IV depuis la thèse FIGÉE AU VALIDATE.

    Deux raisons de ne pas croire le modèle ici. D'abord `theses_v2.valuation_range` est RÉACTUALISÉ
    par chaque revue annuelle (mode 6) : la fourchette d'aujourd'hui n'est plus celle qu'on avait
    prédite, et calibrer sur elle reviendrait à mesurer notre erreur contre notre dernière opinion —
    autrement dit à ne mesurer rien. La prédiction d'origine vit dans `validation_json`, figée (G3).
    Ensuite, un `predite` rapproché du `realisee` transforme le registre en compliment.
    """
    figee = (inputs["validation_json"].get("valuation_range")
             or inputs["thesis"]["valuation_range"] or {})
    sortie = []
    for p in paires:
        copie = dict(p)
        cle = _METRIQUES_IV.get(str(copie.get("metric", "")).strip())
        if cle is not None and figee.get(cle) is not None:
            attendu = float(figee[cle])
            rendu = copie.get("predite")
            if rendu is not None and abs(float(rendu) - attendu) > 1e-6:
                logger.warning(
                    "calibration: `predite` de %s rendu (%r) ≠ valeur figée au validate (%r) — "
                    "écrasé (le prédit se lit dans la thèse figée, pas dans le souvenir du modèle)",
                    copie.get("metric"), rendu, attendu)
            copie["predite"] = attendu
        sortie.append(copie)
    return sortie


# ── Les ponts inter-objets : ce que le contrat ne peut pas voir (#37) ────────
def _antecedents(inputs: dict[str, Any]) -> dict[str, Any]:
    """Faits opposables à une origine de sortie, lus dans la thèse et le suivi."""
    hyps = inputs["hypotheses"]
    sessions = inputs["sessions"]
    invalidees = [str(h.get("id")) for h in hyps if h.get("statut") == "invalidee"]
    en_alerte = [str(h.get("id")) for h in hyps if h.get("statut") in ("alerte", "invalidee")]
    escalades = [
        s["id"] for s in sessions
        if s["alert_level"] in ("REVIEW_REQUIRED", "CRITICAL")
        or s["verdict"] in ("REDUIRE", "SORTIR")
    ]
    rendement_insuffisant = [
        s["id"] for s in sessions
        if ((s.get("result_json") or {}).get("rendement_prospectif") or {}).get("suffisant") is False
    ]
    return {
        "hypotheses_invalidees": invalidees,
        "hypotheses_en_alerte": en_alerte,
        "sessions_escaladees": escalades,
        "sessions_rendement_insuffisant": rendement_insuffisant,
    }


def _valider_pont_sortie(plan: ExitPlan, inputs: dict[str, Any]) -> None:
    """Confronte le plan à l'état réel de la thèse et du portefeuille. Lève ExitRefused.

    N'est PAS un doublon du contrat : celui-ci vérifie que les tranches sont cohérentes ENTRE ELLES
    (Σ ≤ 100, ordres consécutifs) ; ceci vérifie qu'elles portent sur des titres qui existent et que
    l'origine déclarée correspond à quelque chose qui s'est produit.
    """
    pos = inputs["position"]
    if pos is None or float(pos["shares"]) <= 0 or pos["status"] != "open":
        raise ExitRefused(
            "Aucune position ouverte sur cette thèse : un plan de sortie qui ne porte sur aucun "
            "titre est un document sans objet — et il rendrait exécutables des tranches vides."
        )

    deja = _pct_execute(inputs)
    total = sum(t.pct_a_vendre for t in plan.tranches)
    if deja + total > 100 + 1e-9:
        raise ExitRefused(
            f"Σ des tranches ({total:g}%) + déjà exécuté ({deja:g}%) = {deja + total:g}% > 100 %. "
            "Le contrat ne voit que le nouveau plan ; le portefeuille, lui, a déjà été entamé."
        )

    origine = plan.origine
    ant = _antecedents(inputs)
    if origine == "hypothese_invalidee" and not ant["hypotheses_invalidees"]:
        raise ExitRefused(
            "origine='hypothese_invalidee' mais aucune hypothèse figée n'est au statut `invalidee` "
            f"(statuts : {[(h.get('id'), h.get('statut')) for h in inputs['hypotheses']]}). "
            "Une invalidation se constate au monitoring (mode 2/3/6) et se reporte sur la thèse ; "
            "la déclarer ici sans qu'elle existe, c'est habiller une sortie de prix en sortie de thèse."
        )
    if origine == "thesis_degradation" and not (ant["hypotheses_en_alerte"] or ant["sessions_escaladees"]):
        raise ExitRefused(
            "origine='thesis_degradation' mais rien n'atteste d'une dégradation : aucune hypothèse "
            "en alerte ou invalidée, aucune session de suivi escaladée (alerte REVIEW_REQUIRED/"
            "CRITICAL ou verdict REDUIRE/SORTIR). Sortir « parce que la thèse se dégrade » sans "
            "dégradation constatée est précisément le churn que §10 interdit."
        )
    if origine == "rendement_insuffisant" and not (
        ant["sessions_rendement_insuffisant"] or ant["sessions_escaladees"]
    ):
        raise ExitRefused(
            "origine='rendement_insuffisant' mais aucun arbitrage rendement/risque prospectif n'a "
            "été établi par le suivi (aucune revue mode 6 avec `rendement_prospectif.suffisant=false`, "
            "aucun verdict REDUIRE/SORTIR). Sans cet antécédent, « rendement insuffisant » n'est "
            "qu'un ratio prix/IV mécanique — ce que §11 refuse explicitement comme cause de sortie."
        )
    # `reallocation` n'affirme rien sur la thèse : c'est un choix d'allocation de l'investisseur.
    # Rien à ponter — et lui inventer une condition serait refuser une décision légitime.


def _valider_pont_postmortem(pm: PostMortem, inputs: dict[str, Any]) -> None:
    """Bijection avec les hypothèses figées + position réellement soldée. Lève ExitRefused."""
    if not _position_soldee(inputs):
        pos = inputs["position"]
        restant = float(pos["shares"]) if pos is not None else 0
        raise ExitRefused(
            f"Position non soldée ({restant:g} titre(s) restant(s)) : le post-mortem juge une "
            "histoire terminée. Le produire maintenant figerait des statuts finaux d'hypothèses sur "
            "une thèse encore en cours — et bloquerait le vrai bilan (un seul par thèse)."
        )

    # Le helper de bijection vient du contrat FIGÉ : on lui passe l'objet validé et le référentiel.
    # C'est le seul contrôle inter-objets que le contrat porte lui-même — parce qu'on lui FOURNIT
    # le second objet (les ids figés) ; il ne va pas le chercher.
    ids_figes = [str(h.get("id")) for h in inputs["hypotheses"] if h.get("id")]
    try:
        valider_postmortem_couvre(pm, ids_figes)
    except ValueError as e:
        raise ExitRefused(
            f"{e} — le bilan doit juger EXACTEMENT les hypothèses figées au validate : une "
            "hypothèse omise est celle qui gênait, une hypothèse inventée est un verdict sur rien "
            "(pendant de la bijection des risk_acks à la décision)."
        ) from e


def _valider_pont_calibration(entry: CalibrationEntry, inputs: dict[str, Any]) -> None:
    """La calibration mesure un écart : sans bilan abouti, elle n'a rien à mesurer."""
    if inputs["post_mortem"] is None:
        raise ExitRefused(
            "Aucun post-mortem abouti pour cette thèse : la calibration confronte le prédit au "
            "réalisé, or le réalisé (statut final de chaque hypothèse, performance) est établi par "
            "le bilan. Produis le post-mortem d'abord."
        )


_PONTS = {
    "exit_plan": _valider_pont_sortie,
    "post_mortem": _valider_pont_postmortem,
    "calibration": _valider_pont_calibration,
}


# ── L'acte : appel modèle hors transaction, écriture atomique ────────────────
async def run_exit_agent(thesis_v2_id: int, mode: str) -> dict[str, Any]:
    """Exécute un des trois actes de sortie et le persiste. `mode` ∈ exit_plan|post_mortem|calibration."""
    if mode not in MODE_SCHEMAS:
        raise ValueError(f"mode '{mode}' inconnu — attendus : {', '.join(MODES)}.")

    async with get_db_session() as conn:
        inputs = await _load_exit_inputs(conn, thesis_v2_id)

    _verifier_etat(mode, inputs)

    thesis = inputs["thesis"]
    ticker_id = thesis["ticker_id"]
    contexte = f"{_head(inputs)}\n\n---\n[mode: {mode}]\n{_tache(mode, inputs)}"
    agent = await get_agent_provider(AGENT_NAME, "v2")

    # `json_object=False` : DeepSeek-V4-Flash est non fiable en mode json_object (mesuré 2026-08-26).
    # temperature basse : ce tour reporte des chiffres et des ids, il n'invente pas.
    try:
        run = await run_json_agent(
            agent, [{"role": "user", "content": contexte}], MODE_SCHEMAS[mode],
            json_object=False, temperature=0.2,
        )
    except RuntimeError as e:
        # ⚠️ `run_json_agent` ne remonte ni le texte brut fautif ni les tokens quand il abandonne :
        # l'échec est tracé mais la dépense de cette tentative n'est PAS comptabilisée. Limite
        # connue du runner, commune à tous les agents V2 (dette du lot 8, toujours ouverte).
        await _persister_echec(mode, inputs, contexte, agent, str(e))
        raise

    try:
        data = _forcer_champs_derives(mode, dict(run.data), inputs)
        # Revalidation APRÈS forçage : les champs écrasés doivent encore satisfaire le contrat
        # (`exit_status`, `paires`, `performance_pct` ont bougé). Sans ce tour, on persisterait un
        # objet que son propre schéma refuserait — et le pont travaillerait sur du non validé.
        parsed = MODE_SCHEMAS[mode].model_validate(data)
        _PONTS[mode](parsed, inputs)
    except (ExitRefused, ValueError) as e:
        motif = str(e)
        await _persister_echec(mode, inputs, contexte, agent, motif,
                               raw_content=run.raw_content, run=run)
        raise e if isinstance(e, ExitRefused) else ExitRefused(motif) from e

    if mode == "exit_plan":
        return await _persister_plan(inputs, data, contexte, agent, run)
    if mode == "post_mortem":
        return await _persister_postmortem(inputs, data, contexte, agent, run)
    return await _persister_calibration(inputs, data, contexte, agent, run)


def _verifier_etat(mode: str, inputs: dict[str, Any]) -> None:
    """Pré-conditions d'état, AVANT toute dépense de tokens.

    Ces refus-là ne sont pas des jugements sur la sortie du modèle : ils disent que la question
    n'avait pas lieu d'être posée. Les vérifier après l'appel coûterait un appel pour rien.
    """
    thesis = inputs["thesis"]
    if mode == "exit_plan":
        if thesis["status"] != "active":
            raise ThesisNotExitable(
                f"Thèse V2 #{thesis['id']} au statut '{thesis['status']}' — on ne planifie une "
                "sortie que sur une thèse active (validée, position ouverte)."
            )
        plan = inputs["plan"]
        if plan is not None and plan["exit_status"] != "closed":
            raise ThesisNotExitable(
                f"Un plan de sortie #{plan['id']} est déjà en cours (exit_status="
                f"'{plan['exit_status']}'). Deux plans ouverts, ce sont deux séries de tranches sur "
                "les mêmes titres : exécute ou clôture celui-ci d'abord."
            )
    elif mode == "post_mortem":
        if thesis["status"] not in ("active", "closed"):
            raise ThesisNotExitable(
                f"Thèse V2 #{thesis['id']} au statut '{thesis['status']}' — un bilan suppose une "
                "thèse qui a réellement porté une position."
            )
        if inputs["post_mortem"] is not None:
            raise ThesisNotExitable(
                f"Post-mortem #{inputs['post_mortem']['id']} déjà établi pour cette thèse. Un "
                "second bilan dupliquerait ses paires dans le registre de calibration."
            )
    elif mode == "calibration" and inputs["post_mortem"] is None:
        raise ThesisNotExitable(
            "Calibration demandée sans post-mortem abouti : le réalisé n'est pas encore établi."
        )


# ── Persistance, par acte ────────────────────────────────────────────────────
async def _persister_plan(inputs, data, contexte, agent, run) -> dict[str, Any]:
    thesis = inputs["thesis"]
    pos = inputs["position"]
    session_amont = next(
        (s["id"] for s in inputs["sessions"] if s["routing_suggestion"] == "exit_plan"), None
    )

    async with get_db_session() as conn:
        async with conn.transaction():
            plan = await conn.fetchrow(
                """
                INSERT INTO exit_plans
                    (thesis_v2_id, ticker_id, position_id, monitoring_session_v2_id, origine,
                     exit_status, plan_json, context_sent, raw_content, status,
                     provider_used, model_used, prompt_snapshot, tokens_in, tokens_out, cost_usd)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'completed',$10,$11,$12,$13,$14,$15)
                RETURNING *
                """,
                thesis["id"], thesis["ticker_id"], pos["id"] if pos is not None else None,
                session_amont, data["origine"], data["exit_status"], data, contexte,
                run.raw_content, agent.provider.name, agent.model, agent.system_prompt,
                run.tokens_in, run.tokens_out, run.cost_usd,
            )
            if pos is not None:
                await conn.execute(
                    "UPDATE portfolio_positions SET exit_status = $2, updated_at = NOW() WHERE id = $1",
                    pos["id"], data["exit_status"],
                )

    logger.info("exit_plan: thèse #%s (%s) → plan #%s, origine=%s, %s tranche(s), $%.4f",
                thesis["id"], thesis["ticker_id"], plan["id"], data["origine"],
                len(data.get("tranches") or []), run.cost_usd)
    return {"exit_plan": dict(plan), "result": data}


async def _persister_postmortem(inputs, data, contexte, agent, run) -> dict[str, Any]:
    """Écrit le bilan, publie les leçons, clôt la thèse — atomiquement.

    Les embeddings des leçons sont calculés AVANT la transaction (convention #35) : `store_knowledge`
    appelle sinon l'API d'embedding le verrou tenu. En cas d'échec on écrit quand même la leçon sans
    vecteur — `backfill_embeddings` rattrapera. Perdre la leçon serait bien pire que la retrouver tard.
    """
    thesis = inputs["thesis"]
    pos = inputs["position"]
    plan = inputs["plan"]
    lecons = data.get("lecons") or []

    vecteurs = await _embeddings_lecons(thesis["ticker_id"], lecons)

    async with get_db_session() as conn:
        async with conn.transaction():
            entry_ids: list[int] = []
            for i, lecon in enumerate(lecons):
                entry = await store_knowledge(
                    conn,
                    ticker_id=thesis["ticker_id"],
                    entry_type=LESSON_ENTRY_TYPE,
                    title=f"Leçon — {thesis['ticker_id']} (thèse V2 #{thesis['id']})",
                    content=lecon["lecon"],
                    source_type=LESSON_SOURCE_TYPE,
                    tags=list(lecon.get("tags") or []),
                    lang="fr",
                    source_date=date.today(),
                    embedding=vecteurs[i] if vecteurs else None,
                    embed=False,          # déjà calculé hors transaction (ou assumé absent)
                )
                entry_ids.append(entry["id"])

            derives = _derives_postmortem(inputs)
            pm = await conn.fetchrow(
                """
                INSERT INTO post_mortems_v2
                    (thesis_v2_id, ticker_id, exit_plan_id, position_id, duree_jours,
                     performance_pct, result_json, context_sent, raw_content, lesson_entry_ids,
                     status, provider_used, model_used, prompt_snapshot,
                     tokens_in, tokens_out, cost_usd)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,'completed',$11,$12,$13,$14,$15,$16)
                RETURNING *
                """,
                thesis["id"], thesis["ticker_id"], plan["id"] if plan is not None else None,
                pos["id"] if pos is not None else None,
                derives["duree_jours"], derives["performance_pct"], data, contexte,
                run.raw_content, entry_ids, agent.provider.name, agent.model, agent.system_prompt,
                run.tokens_in, run.tokens_out, run.cost_usd,
            )

            # La thèse a vécu : elle sort du radar du routeur (qui ne suit que `status='active'`).
            # Sans ce passage à 'closed', les échéances de revue annuelle continueraient de tomber
            # sur une position vendue.
            await conn.execute(
                "UPDATE theses_v2 SET status='closed', updated_at=NOW() WHERE id=$1", thesis["id"]
            )

    logger.info("post_mortem: thèse #%s clôturée — %s j, %.2f%%, %s leçon(s) publiée(s), $%.4f",
                thesis["id"], pm["duree_jours"], float(pm["performance_pct"]), len(entry_ids),
                run.cost_usd)
    return {"post_mortem": dict(pm), "result": data, "lesson_entry_ids": entry_ids}


async def _embeddings_lecons(ticker_id: str, lecons: list[dict[str, Any]]) -> list[Optional[list[float]]]:
    """Vecteurs des leçons, calculés hors transaction. Renvoie [] si indisponibles (non fatal)."""
    if not lecons:
        return []
    try:
        from app.knowledge import embed_texts, entry_text

        textes = [
            entry_text(f"Leçon — {ticker_id}", l["lecon"], list(l.get("tags") or []))
            for l in lecons
        ]
        return list(await embed_texts(textes))
    except Exception as e:  # noqa: BLE001 — l'API d'embedding n'est pas critique ici
        logger.warning("post_mortem: embeddings des leçons indisponibles (%s) — backfill plus tard", e)
        return []


async def _persister_calibration(inputs, data, contexte, agent, run) -> dict[str, Any]:
    """Écrit les paires dans le registre A5 et rattache la dépense au post-mortem.

    `ON CONFLICT DO NOTHING` sur (thesis_v2_id, metric) : rejouer une calibration est légitime (le
    premier passage a pu être partiel), dupliquer une paire ne l'est pas — la moyenne des écarts est
    LE produit du registre. On rapporte donc ce qui a été ignoré plutôt que d'échouer en bloc.
    """
    thesis = inputs["thesis"]
    pm = inputs["post_mortem"]
    paires = data.get("paires") or []

    inserees: list[dict[str, Any]] = []
    ignorees: list[str] = []
    async with get_db_session() as conn:
        async with conn.transaction():
            for p in paires:
                row = await conn.fetchrow(
                    """
                    INSERT INTO calibration_registry
                        (thesis_v2_id, ticker_id, post_mortem_id, metric, predite, realisee)
                    VALUES ($1,$2,$3,$4,$5,$6)
                    ON CONFLICT (thesis_v2_id, metric) DO NOTHING
                    RETURNING *
                    """,
                    thesis["id"], thesis["ticker_id"], pm["id"], p["metric"],
                    float(p["predite"]), float(p["realisee"]),
                )
                (inserees.append(dict(row)) if row is not None else ignorees.append(p["metric"]))

            await conn.execute(
                """
                UPDATE post_mortems_v2 SET
                    calibration_json = $2, calibration_raw = $3, calibration_tokens_in = $4,
                    calibration_tokens_out = $5, calibration_cost_usd = $6, calibration_at = NOW()
                WHERE id = $1
                """,
                pm["id"], data, run.raw_content, run.tokens_in, run.tokens_out, run.cost_usd,
            )

    if ignorees:
        logger.info("calibration: métriques déjà enregistrées pour la thèse #%s, ignorées : %s",
                    thesis["id"], ignorees)
    logger.info("calibration: thèse #%s → %s paire(s) enregistrée(s), $%.4f",
                thesis["id"], len(inserees), run.cost_usd)
    return {"calibration": inserees, "ignorees": ignorees, "result": data}


async def _persister_echec(mode, inputs, contexte, agent, motif, *, raw_content=None, run=None) -> None:
    """Trace l'échec dans la table de l'acte concerné. Un échec silencieux est un trou d'audit.

    La calibration n'a pas de table à elle : son échec ne peut être tracé que si un post-mortem
    existe (sa colonne `calibration_raw`). C'est assumé — sans post-mortem, la calibration est
    refusée avant tout appel modèle, donc sans dépense à tracer.
    """
    thesis = inputs["thesis"]
    trace = raw_content or f"[échec sans sortie exploitable] {motif}"
    tokens = (getattr(run, "tokens_in", 0) or 0, getattr(run, "tokens_out", 0) or 0,
              getattr(run, "cost_usd", 0) or 0)
    try:
        async with get_db_session() as conn:
            if mode == "exit_plan":
                await conn.execute(
                    """
                    INSERT INTO exit_plans
                        (thesis_v2_id, ticker_id, position_id, origine, context_sent, raw_content,
                         status, provider_used, model_used, prompt_snapshot,
                         tokens_in, tokens_out, cost_usd)
                    VALUES ($1,$2,$3,'reallocation',$4,$5,'failed',$6,$7,$8,$9,$10,$11)
                    """,
                    thesis["id"], thesis["ticker_id"],
                    inputs["position"]["id"] if inputs["position"] is not None else None,
                    contexte, trace, agent.provider.name, agent.model, agent.system_prompt, *tokens,
                )
            elif mode == "post_mortem":
                await conn.execute(
                    """
                    INSERT INTO post_mortems_v2
                        (thesis_v2_id, ticker_id, context_sent, raw_content, status,
                         provider_used, model_used, prompt_snapshot, tokens_in, tokens_out, cost_usd)
                    VALUES ($1,$2,$3,$4,'failed',$5,$6,$7,$8,$9,$10)
                    """,
                    thesis["id"], thesis["ticker_id"], contexte, trace,
                    agent.provider.name, agent.model, agent.system_prompt, *tokens,
                )
            elif inputs["post_mortem"] is not None:
                await conn.execute(
                    "UPDATE post_mortems_v2 SET calibration_raw = $2, calibration_tokens_in = $3, "
                    "calibration_tokens_out = $4, calibration_cost_usd = $5, calibration_at = NOW() "
                    "WHERE id = $1",
                    inputs["post_mortem"]["id"], trace, *tokens,
                )
    except Exception:  # noqa: BLE001 — journaliser l'échec ne doit jamais masquer l'échec initial
        logger.exception("exit: échec de la trace d'échec (thèse #%s, mode %s)", thesis["id"], mode)


# ── L'exécution : aucun modèle, de l'arithmétique sur de l'argent réel ───────
async def execute_tranche(
    exit_plan_id: int,
    ordre: int,
    shares: float,
    sell_price_eur: float,
    sell_date: Optional[str] = None,
    note: Optional[str] = None,
) -> dict[str, Any]:
    """Exécute UNE tranche du plan : vend, encaisse, met à jour position, plan et thèse.

    Zéro appel modèle : le jugement a eu lieu à la création du plan. Ici on ne fait qu'appliquer des
    faits fournis par l'investisseur (nombre de titres, prix réellement obtenu). `sell_price_eur` est
    le prix EN EUROS, comme `purchase_price` au validate et comme le formulaire de vente V1 : c'est
    lui qui fait foi pour la trésorerie.
    """
    jour = date.fromisoformat(sell_date) if sell_date else date.today()

    async with get_db_session() as conn:
        plan = await conn.fetchrow("SELECT * FROM exit_plans WHERE id = $1", exit_plan_id)
        if plan is None or plan["status"] != "completed":
            raise ExitPlanNotFound(f"Plan de sortie #{exit_plan_id} introuvable ou non abouti.")
        if plan["exit_status"] == "closed":
            raise TrancheConflict(f"Plan #{exit_plan_id} déjà clôturé : plus rien à exécuter.")
        inputs = await _load_exit_inputs(conn, plan["thesis_v2_id"])

    tranches = {int(t["ordre"]): t for t in ((plan["plan_json"] or {}).get("tranches") or [])}
    tranche = tranches.get(ordre)
    if tranche is None:
        raise TrancheConflict(
            f"Le plan #{exit_plan_id} ne comporte pas de tranche {ordre} (ordres : "
            f"{sorted(tranches)}). Vendre hors plan, c'est vendre sans la décision de thèse qui "
            "justifie la vente."
        )

    faites = {int(e["ordre"]) for e in inputs["executions"]}
    if ordre in faites:
        raise TrancheConflict(f"Tranche {ordre} du plan #{exit_plan_id} déjà exécutée.")
    manquantes = sorted(o for o in tranches if o < ordre and o not in faites)
    if manquantes:
        raise TrancheConflict(
            f"Tranches {manquantes} non exécutées : les ordres sont consécutifs par construction "
            "(chaque déclencheur suppose le précédent atteint). Exécuter la suivante d'abord "
            "inverserait la logique du plan."
        )

    pos = inputs["position"]
    if pos is None or pos["status"] != "open":
        raise TrancheConflict("Position absente ou déjà clôturée : rien à vendre.")
    restants = float(pos["shares"])
    if shares <= 0 or shares > restants + 1e-9:
        raise TrancheConflict(
            f"{shares:g} titre(s) demandés pour {restants:g} détenu(s) : on ne vend pas ce qu'on "
            "n'a pas (le portefeuille est de l'argent réel, pas un registre d'intentions)."
        )

    # Appel réseau (FX) HORS transaction — convention #35. On réutilise LE helper du flux décision :
    # deux implémentations du taux de change donneraient deux vérités sur la même vente.
    symbol = None
    async with get_db_session() as conn:
        symbol = await conn.fetchval("SELECT ticker_symbol FROM tickers WHERE id = $1", pos["ticker_id"])
    from app.agents.v2.decision import _resolve_execution_price

    prix_natif, devise = await _resolve_execution_price(symbol, sell_price_eur, jour.isoformat())
    fx = round(prix_natif / sell_price_eur, 8) if sell_price_eur else None

    restant_apres = round(restants - shares, 6)
    proceeds = round(shares * sell_price_eur, 4)

    async with get_db_session() as conn:
        async with conn.transaction():
            cash_id = await conn.fetchval(
                "INSERT INTO cash_movements (type, amount, label, ticker_id) "
                "VALUES ('sell', $1, $2, $3) RETURNING id",
                proceeds,
                f"Vente {pos['ticker_id']} — tranche {ordre} du plan de sortie #{exit_plan_id} "
                f"({shares:g} titres @ {sell_price_eur} €)",
                pos["ticker_id"],
            )

            execution = await conn.fetchrow(
                """
                INSERT INTO exit_executions
                    (exit_plan_id, ordre, pct_a_vendre, declencheur, shares_sold, sell_price_native,
                     sell_currency, fx_rate, sell_price_eur, executed_at, cash_movement_id, note)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                RETURNING *
                """,
                exit_plan_id, ordre, float(tranche.get("pct_a_vendre") or 0),
                str(tranche.get("declencheur") or ""), shares, prix_natif, devise, fx,
                sell_price_eur, jour, cash_id, note,
            )

            soldee = restant_apres <= 0
            await conn.execute(
                """
                UPDATE portfolio_positions SET
                    shares = $2, status = $3, sell_price = $4, sell_date = $5,
                    closed_at = CASE WHEN $3 = 'closed' THEN NOW() ELSE closed_at END,
                    exit_status = $6, updated_at = NOW()
                WHERE id = $1
                """,
                pos["id"], restant_apres, "closed" if soldee else "open",
                sell_price_eur, jour, "closed" if soldee else "partially_exited",
            )

            nouvel_etat = "closed" if soldee else "partially_exited"
            await conn.execute(
                "UPDATE exit_plans SET exit_status = $2, updated_at = NOW(), "
                "closed_at = CASE WHEN $2 = 'closed' THEN NOW() ELSE closed_at END WHERE id = $1",
                exit_plan_id, nouvel_etat,
            )

            if soldee:
                # Les alertes de ce plan n'ont plus d'objet : les laisser actives ferait sonner un
                # déclencheur de vente sur une position qui n'existe plus.
                await conn.execute(
                    "UPDATE price_alerts SET active = FALSE WHERE exit_plan_id = $1 AND active",
                    exit_plan_id,
                )

    logger.info("exit: tranche %s du plan #%s exécutée — %s titres @ %s € (%s € encaissés), "
                "reste %s titre(s), plan %s",
                ordre, exit_plan_id, shares, sell_price_eur, proceeds, restant_apres, nouvel_etat)
    return {
        "execution": dict(execution),
        "position_restante": restant_apres,
        "exit_status": nouvel_etat,
        "post_mortem_attendu": restant_apres <= 0,
    }


async def create_exit_alert(
    exit_plan_id: int, price: float, direction: str,
    ordre: Optional[int] = None, condition_index: Optional[int] = None,
) -> dict[str, Any]:
    """Arme une alerte de prix rattachée à une tranche ou à une condition accélérée du plan.

    Le `declencheur` produit par l'agent est de la PROSE (« prix > 135 (zone surévaluée) ») : en
    extraire un nombre par expression régulière ferait dépendre une vente réelle d'un parsing de
    texte libre. Le prix chiffré est donc fourni par l'investisseur ; l'agent fournit le libellé,
    c'est-à-dire la RAISON. Chacun ce qu'il sait faire (#24).
    """
    if direction not in ("above", "below"):
        raise ValueError("direction doit être 'above' ou 'below'.")
    if (ordre is None) == (condition_index is None):
        raise ValueError("Fournis exactement l'un de `ordre` (tranche) ou `condition_index`.")

    async with get_db_session() as conn:
        plan = await conn.fetchrow("SELECT * FROM exit_plans WHERE id = $1", exit_plan_id)
        if plan is None or plan["status"] != "completed":
            raise ExitPlanNotFound(f"Plan de sortie #{exit_plan_id} introuvable ou non abouti.")

        payload = plan["plan_json"] or {}
        if ordre is not None:
            source = {int(t["ordre"]): t for t in (payload.get("tranches") or [])}.get(ordre)
            if source is None:
                raise TrancheConflict(f"Le plan #{exit_plan_id} n'a pas de tranche {ordre}.")
            libelle = f"Tranche {ordre} — {source.get('declencheur', '')}"
            alert_type = "exit_tranche"
        else:
            conditions = payload.get("conditions_accelerees") or []
            if not 0 <= condition_index < len(conditions):
                raise TrancheConflict(
                    f"Le plan #{exit_plan_id} n'a pas de condition accélérée #{condition_index}."
                )
            cond = conditions[condition_index]
            libelle = f"Sortie accélérée ({cond.get('type')}) — {cond.get('seuil', '')}"
            alert_type = "exit_accelere"

        alerte = await conn.fetchrow(
            """
            INSERT INTO price_alerts (ticker_id, price, direction, label, active, alert_type, exit_plan_id)
            VALUES ($1, $2, $3, $4, TRUE, $5, $6)
            RETURNING *
            """,
            plan["ticker_id"], price, direction, libelle, alert_type, exit_plan_id,
        )
    return dict(alerte)


# ── Lecture du registre A5 ───────────────────────────────────────────────────
async def calibration_summary() -> dict[str, Any]:
    """Biais systématique par métrique : la question à laquelle le registre existe pour répondre.

    L'écart MOYEN SIGNÉ est l'indicateur utile (« mes IV hautes sont 20 % trop basses ») ; la moyenne
    des valeurs absolues, elle, mesurerait une dispersion et masquerait justement le biais — deux
    erreurs opposées se compenseraient dans l'une et pas dans l'autre. On rend les deux, et `n`,
    parce qu'un biais sur 2 positions n'est pas un biais.
    """
    async with get_db_session() as conn:
        lignes = await conn.fetch(
            """
            SELECT metric,
                   COUNT(*)                                   AS n,
                   ROUND(AVG(ecart)::numeric, 4)              AS ecart_moyen,
                   ROUND(AVG(ABS(ecart))::numeric, 4)         AS ecart_absolu_moyen,
                   ROUND(AVG(CASE WHEN predite <> 0
                                  THEN (realisee - predite) / ABS(predite) * 100 END)::numeric, 2)
                                                              AS biais_relatif_pct
            FROM calibration_registry
            GROUP BY metric
            ORDER BY n DESC, metric
            """
        )
        total = await conn.fetchval("SELECT COUNT(DISTINCT thesis_v2_id) FROM calibration_registry")
    return {
        "theses_calibrees": int(total or 0),
        "metriques": [dict(r) for r in lignes],
        # 15-20 positions : le seuil au-delà duquel la carte A5 considère le biais lisible. En
        # dessous, afficher une tendance serait donner du sens à du bruit.
        "lisible": int(total or 0) >= 15,
    }
