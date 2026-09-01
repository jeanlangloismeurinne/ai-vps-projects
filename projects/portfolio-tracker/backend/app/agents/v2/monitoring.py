"""
Monitoring V2 (§10/§11, lot 8, migration 031) — le suivi anti-churn d'une thèse figée.

Ce module est le SEUL point où les modes 1 à 6 appellent un modèle. Il tient trois choses que ni le
contrat Pydantic ni la base ne peuvent tenir seuls :

1. LE PONT INTER-OBJETS (`_valider_pont_hypotheses`). Le garde-fou 7 de la carte mode 6
   (« hypotheses_reviewed[] couvre les hypothèses figées de la thèse ») est INVÉRIFIABLE dans le
   contrat : celui-ci ne voit que le payload du modèle, jamais `theses_v2.hypotheses`. Ici on a les
   deux en main. Deux contrôles distincts, pour deux pannes distinctes :
     * RÉFÉRENTIEL (tous les modes qui citent des hypothèses) — un `hypothese_id` absent de la thèse
       figée est une hypothèse INVENTÉE. C'est le trou exact de l'anti-churn : le contrat mode 2
       impose « escalade ⇔ seuil franchi », mais un modèle qui hallucine `H7 en alerte` satisfait
       parfaitement cette équivalence et escalade sur un seuil qui n'a JAMAIS été pré-enregistré.
       L'anti-churn exige que le seuil soit pré-enregistré ; seul ce contrôle-là le vérifie.
     * EXHAUSTIVITÉ (mode 6 seulement, comme la carte le demande) — sans lui, un modèle passe le
       contrat en ne revoyant qu'une hypothèse sur quatre, et les trois autres dérivent un an de
       plus sans que rien ne le signale. C'est précisément ce que la revue annuelle doit empêcher.
     * CITATIONS RÉELLES — un `source_entry_ref` qui ne figure pas dans le contexte envoyé est un
       statut fondé sur rien : `snapshot_refs` se contenterait de logguer et de passer, laissant une
       hypothèse changée de statut sans aucune trace opposable (A2).

2. CE QUE L'APPELANT SAIT, ON NE LE DEMANDE PAS AU MODÈLE (`_forcer_champs_derives`, conventions #24
   et #36). `thesis_id`, `mode`, `pair_ticker`, `source_mode`, `schema_version` sont connus du code
   qui déclenche la session. Les faire produire par le modèle ajoute des modes d'échec sans ajouter
   d'information — pire, un `thesis_id` erroné ferait persister un jugement sous la mauvaise thèse.

3. LES SEUILS FIGÉS SONT EN LECTURE SEULE. Le mode 6 reporte les `statut` revus sur
   `theses_v2.hypotheses`, mais JAMAIS les `seuil_alerte`/`seuil_invalidation` : ils ont été figés au
   validate (G3). Si le monitoring pouvait les réécrire, un modèle pourrait abaisser le seuil qu'il
   vient de franchir — l'anti-churn s'annulerait lui-même, silencieusement, et l'historique ne
   garderait aucune trace du seuil d'origine.

Atomicité (convention #35) : `get_db_session()` n'ouvre AUCUNE transaction. L'appel modèle se fait
HORS transaction (on ne tient pas de verrou pendant 12 minutes d'inférence) ; l'écriture session +
effets de bord (calendrier, thèse) est ensuite explicitement atomique.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Optional

from app.agents.providers import get_agent_provider
from app.agents.v2.common import format_entries_for_prompt
from app.agents.v2.runner import run_json_agent
from app.contracts import (
    Mode1PreEvent,
    Mode2QuarterlyReview,
    Mode3DecisionReview,
    Mode4SectorPulse,
    Mode5Routing,
    Mode6Review,
)
from app.db.database import get_db_session
from app.knowledge import collect_refs, get_current_entries, snapshot_refs

logger = logging.getLogger(__name__)

AGENT_NAME = "monitoring-agent"
CALENDAR_SOURCE_V2 = "monitoring_agent_v2"

MODE_SCHEMAS: dict[int, Any] = {
    1: Mode1PreEvent,
    2: Mode2QuarterlyReview,
    3: Mode3DecisionReview,
    4: Mode4SectorPulse,
    5: Mode5Routing,
    6: Mode6Review,
}

# Modes dont la sortie porte `hypotheses_reviewed[]` (donc soumis au pont inter-objets).
_MODES_AVEC_HYPOTHESES = {2, 3, 6}
# Seul le mode 6 exige la couverture COMPLÈTE des hypothèses figées (carte, garde-fou 7).
_MODES_EXHAUSTIFS = {6}
# Le routeur lit ces colonnes dénormalisées ; la migration 031 en contraint le domaine par mode.
_MODES_ALERT_LEVEL = {2}
_MODES_VERDICT = {3, 6}


class ThesisNotActive(RuntimeError):
    """Le monitoring suit une position réelle : une thèse `draft`/`superseded` n'a rien à suivre."""


class MonitoringRefused(ValueError):
    """La sortie du modèle est formellement conforme mais incohérente avec la thèse figée.

    Distincte d'une erreur technique et d'un échec de contrat : le JSON est valide, le contrat est
    satisfait, et pourtant le jugement porte sur des hypothèses qui n'existent pas ou en oublie.
    Se traduit en HTTP 422 — la session est persistée en `failed` pour rester auditable."""


# ── Chargement des intrants ──────────────────────────────────────────────────
async def _load_monitoring_inputs(conn, thesis_v2_id: int) -> dict[str, Any]:
    """Thèse V2 active + memo de recherche + entries courantes. Tout vient de la base."""
    thesis = await conn.fetchrow("SELECT * FROM theses_v2 WHERE id = $1", thesis_v2_id)
    if thesis is None:
        raise LookupError(f"Thèse V2 #{thesis_v2_id} introuvable.")
    if thesis["status"] != "active":
        raise ThesisNotActive(
            f"Thèse V2 #{thesis_v2_id} au statut '{thesis['status']}' — le monitoring ne suit que "
            "les thèses actives (une thèse non validée ne porte aucune position à surveiller)."
        )

    memo_json: dict[str, Any] = {}
    if thesis["research_memo_id"] is not None:
        memo = await conn.fetchrow(
            "SELECT memo_json FROM research_memos WHERE id = $1", thesis["research_memo_id"]
        )
        memo_json = (memo["memo_json"] if memo else None) or {}

    entries = await get_current_entries(conn, thesis["ticker_id"], limit=500)

    derniere = await conn.fetchval(
        "SELECT MAX(created_at) FROM monitoring_sessions_v2 "
        "WHERE thesis_v2_id = $1 AND status = 'completed'",
        thesis_v2_id,
    )
    return {
        "thesis": thesis,
        "hypotheses": list(thesis["hypotheses"] or []),
        "memo_json": memo_json,
        "entries": entries,
        "derniere_revue": derniere or thesis["validated_at"],
    }


def _format_hypotheses(hypotheses: list[dict[str, Any]]) -> str:
    """Injecte les hypothèses AVEC leurs seuils pré-enregistrés.

    Sans les seuils chiffrés dans le contexte, la règle « on n'escalade que sur franchissement d'un
    seuil pré-enregistré » n'est pas applicable par le modèle : il escaladerait à l'impression, et le
    contrat — qui vérifie la cohérence interne statut ⇔ seuils_franchis ⇔ alert_level, pas le fond —
    laisserait passer. Les seuils sont donnés en LECTURE : ils ne sont jamais réécrits par le suivi.
    """
    if not hypotheses:
        return "(aucune hypothèse figée — anomalie : une thèse active en porte toujours)"
    lignes = []
    for h in hypotheses:
        unite = h.get("unite") or ""
        lignes.append(
            f"- {h.get('id')} [{h.get('statut', 'active')}] {h.get('enonce', '')}\n"
            f"    KPI suivi : {h.get('kpi', '?')} — seuil_alerte {h.get('seuil_alerte')}{unite} · "
            f"seuil_invalidation {h.get('seuil_invalidation')}{unite} · horizon {h.get('horizon', '?')}"
        )
    return "\n".join(lignes)


def _head(inputs: dict[str, Any]) -> str:
    """Bloc front-loadé déterministe : thèse figée + hypothèses + corpus courant (cache §5.3)."""
    t = inputs["thesis"]
    val = t["valuation_range"] or {}
    conditions = list(t["conditions_entree"] or [])
    valo = (inputs["memo_json"] or {}).get("valuation") or {}
    reverse = valo.get("reverse_dcf") or {}

    return (
        f"## Thèse V2 #{t['id']} — {t['ticker_id']} (figée au validate)\n"
        f"Verdict d'entrée : {t['verdict']} · sizing {t['position_sizing_pct']}%\n"
        f"Fourchette de valeur intrinsèque FIGÉE À L'ENTRÉE : "
        f"low {val.get('low')} · base {val.get('base')} · high {val.get('high')}\n"
        f"Conditions d'entrée : {'; '.join(conditions) if conditions else '(aucune)'}\n"
        f"Validée le : {t['validated_at']} · dernière revue : {inputs['derniere_revue']}\n\n"
        f"## Hypothèses figées et leurs seuils PRÉ-ENREGISTRÉS (lecture seule)\n"
        f"{_format_hypotheses(inputs['hypotheses'])}\n\n"
        f"## Valorisation du research memo d'origine (référence de réactualisation)\n"
        f"prix_actuel à l'analyse : {valo.get('prix_actuel')} · iv_range {valo.get('iv_range')} · "
        f"marge de sécurité base {valo.get('marge_securite_base_pct')}%\n"
        f"reverse-DCF d'origine : croissance implicite "
        f"{reverse.get('croissance_implicite_prix_actuel_pct')}% — {reverse.get('verdict', '')}\n\n"
        f"## knowledge_entries courantes (cite par entry_id — un statut sans ref n'est pas recevable)\n"
        f"{format_entries_for_prompt(inputs['entries'])}"
    )


# ── Tâche du tour, par mode ──────────────────────────────────────────────────
def _tache(mode: int, inputs: dict[str, Any], *, trigger_label: str,
           peer_ticker: Optional[str], source_mode: Optional[int]) -> str:
    tid = inputs["thesis"]["id"]
    ids = ", ".join(str(h.get("id")) for h in inputs["hypotheses"]) or "(aucune)"
    if mode == 1:
        return (
            f"Événement à venir (J-2) : {trigger_label}\n"
            f"Produis la checklist de lecture (contrat Mode1PreEvent) : AU PLUS 3 points à surveiller "
            f"dans la publication, dérivés des hypothèses figées. AUCUN verdict, aucune décision."
        )
    if mode == 2:
        return (
            f"Publication parue (J+1) : {trigger_label}\n"
            f"Produis la revue trimestrielle (contrat Mode2QuarterlyReview). Revois les hypothèses "
            f"{ids} : pour chacune, `statut` étayé par des `source_entry_refs` pris dans les entries "
            f"ci-dessus. ANTI-CHURN : ne passe une hypothèse en `alerte`/`invalidee` QUE si le KPI "
            f"observé franchit son seuil pré-enregistré ci-dessus. `seuils_franchis` = exactement les "
            f"ids en alerte/invalidee. Sous les seuils → alert_level 'RAS', même si le cours a bougé. "
            f"`valuation_status` est contextuel : ce n'est jamais un ordre de vente."
        )
    if mode == 3:
        return (
            f"Escalade — motif : {trigger_label}\n"
            f"Produis la décision review (contrat Mode3DecisionReview) : `diagnostic`, test "
            f"d'inversion de Munger (`munger_inversion` : qu'est-ce qui tuerait cette thèse ?), "
            f"statut des hypothèses {ids}, puis `decision` motivée. REDUIRE/SORTIR exige un "
            f"`exit_trigger` (pas de sortie muette) ; MAINTENIR/RE_SYNTHESE n'en porte aucun."
        )
    if mode == 4:
        return (
            f"Résultats d'un pair : {peer_ticker} — {trigger_label}\n"
            f"Produis le sector pulse (contrat Mode4SectorPulse) : `sector_score` de -5 à +5 et les "
            f"hypothèses de {ids} impactées. CONTEXTUEL : ce mode n'escalade JAMAIS seul — il ne "
            f"produit ni verdict ni niveau d'alerte."
        )
    if mode == 5:
        return (
            f"Routage d'une alerte issue du mode {source_mode} — motif : {trigger_label}\n"
            f"Produis le routing (contrat Mode5Routing) : `route`='synthese' si la dégradation est "
            f"matérielle et impose de refaire l'analyse, 'debate' si la conviction doit être "
            f"challengée (option C). Routing PUR : aucune donnée nouvelle, aucun verdict."
        )
    return (
        f"Revue annuelle de la thèse #{tid} — {trigger_label}\n"
        f"Produis la revue (contrat Mode6Review). Tu DOIS revoir TOUTES les hypothèses figées "
        f"({ids}) — une hypothèse non revue dérive un an de plus. Réactualise "
        f"`valuation_range_updated` et le `thermometer` (contextuel : `contraignant` reste false — "
        f"tu peux être en zone `surevalue` et CONFIRMER si la thèse tient). Une sortie/réduction "
        f"motivée par la valorisation exige un `rendement_prospectif` avec `suffisant=false` : "
        f"c'est un arbitrage rendement/risque prospectif, JAMAIS un ratio prix/IV mécanique."
    )


# ── Champs dérivés : l'appelant les connaît, on ne les demande pas ───────────
def _forcer_champs_derives(
    mode: int, data: dict[str, Any], *, thesis_v2_id: int,
    peer_ticker: Optional[str], source_mode: Optional[int],
) -> dict[str, Any]:
    """Écrase les champs que le code connaît AVANT validation (conventions #24, #36).

    On loggue les divergences plutôt que de les taire : un `thesis_id` qui ne correspond pas est le
    signe que le modèle a perdu le fil de son contexte, information utile même si sans conséquence.
    """
    for champ, attendu in (
        ("mode", mode),
        ("thesis_id", thesis_v2_id),
        ("pair_ticker", peer_ticker if mode == 4 else None),
        ("source_mode", source_mode if mode == 5 else None),
        ("schema_version", "v2.0.0" if mode == 6 else None),
    ):
        if attendu is None:
            continue
        rendu = data.get(champ)
        if rendu is not None and rendu != attendu:
            logger.warning(
                "monitoring mode %s: `%s` rendu par le modèle (%r) ≠ valeur connue (%r) — écrasé",
                mode, champ, rendu, attendu,
            )
        data[champ] = attendu
    return data


# ── Le pont inter-objets : ce que le contrat ne peut pas voir ────────────────
def _valider_pont_hypotheses(
    data: dict[str, Any], hypotheses_figees: list[dict[str, Any]],
    entries: list[dict[str, Any]], *, mode: int,
) -> None:
    """Confronte la sortie du modèle à la thèse figée et au corpus réellement envoyé.

    Lève MonitoringRefused. N'est PAS un doublon du contrat : le contrat vérifie la cohérence
    interne du payload, ceci vérifie son ancrage dans des objets qu'il ne voit pas.
    """
    ids_figes = {str(h.get("id")) for h in hypotheses_figees if h.get("id")}
    reviewed = data.get("hypotheses_reviewed") or []
    cites = {str(h.get("hypothese_id")) for h in reviewed if h.get("hypothese_id")}

    # Le mode 4 ne « revoit » pas d'hypothèses mais en désigne — même exigence référentielle.
    if mode == 4:
        cites = {str(x) for x in (data.get("hypotheses_impactees") or [])}

    inventees = sorted(cites - ids_figes)
    if inventees:
        raise MonitoringRefused(
            f"Hypothèses inconnues de la thèse figée : {inventees} (figées : {sorted(ids_figes)}). "
            "Un seuil qui n'a pas été pré-enregistré au validate ne peut pas être « franchi » — "
            "l'anti-churn (§10) l'interdit."
        )

    if mode in _MODES_EXHAUSTIFS:
        oubliees = sorted(ids_figes - cites)
        if oubliees:
            raise MonitoringRefused(
                f"Revue annuelle incomplète : hypothèses non revues {oubliees}. La revue annuelle "
                "est la colonne vertébrale du suivi long terme — une hypothèse qu'elle omet dérive "
                "une année de plus sans contrôle (garde-fou 7 de la carte mode 6)."
            )

    # A2 : un statut se fonde sur une entry REÇUE, pas sur un identifiant plausible.
    ids_entries = {e["id"] for e in entries}
    fantomes = sorted(
        {r["entry_id"] for r in collect_refs(data)} - ids_entries
    )
    if fantomes:
        raise MonitoringRefused(
            f"source_entry_refs pointant des entries absentes du contexte envoyé : {fantomes}. "
            "Un statut d'hypothèse doit s'étayer sur une entry réellement fournie (A2) — sinon "
            "le snapshot est vide et le changement de statut n'est opposable à rien."
        )


# ── Dénormalisations lues par le routeur ─────────────────────────────────────
def _colonnes_routeur(mode: int, data: dict[str, Any]) -> dict[str, Optional[str]]:
    """alert_level / verdict / routing_suggestion — bornés par mode (CHECKs de la migration 031).

    Le routeur décide d'escalader en lisant ces colonnes, sans reparser `result_json` : elles ne
    peuvent donc porter que ce que la carte autorise pour ce mode-là.
    """
    alert = data.get("alert_level") if mode in _MODES_ALERT_LEVEL else None
    verdict = (data.get("verdict") if mode == 6 else data.get("decision")) if mode in _MODES_VERDICT else None

    routing: Optional[str] = None
    if mode == 5:
        routing = data.get("route")
    elif mode == 2 and alert in ("REVIEW_REQUIRED", "CRITICAL"):
        routing = "mode5"                     # à router : le mode 5 tranchera synthèse vs debate
    elif mode in (3, 6) and (verdict in ("REDUIRE", "SORTIR")):
        # Le plan de sortie (calibration, exécution) est le lot 9 : on POSE la suggestion sans
        # prétendre l'exécuter — un verdict SORTIR qui ne laisserait aucune trace actionnable
        # serait pire qu'une suggestion explicitement en attente.
        routing = "exit_plan"
    return {"alert_level": alert, "verdict": verdict, "routing_suggestion": routing}


# ── Effets du mode 6 : report des statuts, réactualisation, replanification ──
def _reporter_statuts(
    hypotheses_figees: list[dict[str, Any]], reviewed: list[dict[str, Any]], jour: date,
) -> list[dict[str, Any]]:
    """Reporte les `statut` revus sur les hypothèses figées, seuils INTACTS.

    Fusion par id : on ne remplace pas la liste par celle du modèle. Sinon les `seuil_alerte`/
    `seuil_invalidation`, le `base_rate` et les `source_entry_refs` d'origine — tout ce qui a été
    figé au validate (G3) — seraient réécrits à chaque revue par ce que le modèle a bien voulu
    répéter. Le seuil qu'on vient de franchir deviendrait négociable.
    """
    par_id = {str(h.get("hypothese_id")): h for h in reviewed}
    sortie = []
    for h in hypotheses_figees:
        copie = dict(h)
        revue = par_id.get(str(h.get("id")))
        if revue is not None:
            copie["statut"] = revue.get("statut", copie.get("statut"))
            copie["derniere_revue"] = jour.isoformat()
            copie["derniere_observation"] = revue.get("observation")
        sortie.append(copie)
    return sortie


async def _appliquer_effets_mode6(
    conn, *, thesis_v2_id: int, ticker_id: str, data: dict[str, Any], jour: date,
) -> dict[str, Any]:
    """Réactualise la thèse et replanifie la revue suivante. Appelé DANS la transaction."""
    hyps = list(await conn.fetchval("SELECT hypotheses FROM theses_v2 WHERE id = $1", thesis_v2_id) or [])
    maj = _reporter_statuts(hyps, data.get("hypotheses_reviewed") or [], jour)

    await conn.execute(
        "UPDATE theses_v2 SET valuation_range = $2, hypotheses = $3, updated_at = NOW() WHERE id = $1",
        thesis_v2_id, data["valuation_range_updated"], maj,
    )

    # La date de la prochaine revue est DÉRIVÉE (+365j), pas celle rendue par le modèle. C'est un
    # calcul, donc ce n'est pas à lui de le faire (#24) — et une date de replanification hallucinée
    # ne se voit pas : elle produit un trou de suivi qu'on ne découvrirait qu'un an plus tard.
    # `next_review_date` du contrat reste dans result_json : on garde ce que le modèle a dit.
    prochaine = jour + timedelta(days=365)
    if data.get("next_review_date") and data["next_review_date"][:10] != prochaine.isoformat():
        logger.info(
            "monitoring mode 6: next_review_date du modèle (%s) ignorée au profit de la date "
            "dérivée %s", data["next_review_date"], prochaine,
        )
    ev = await conn.fetchrow(
        """
        INSERT INTO calendar_events
            (thesis_v2_id, ticker_id, event_type, label, scheduled_date, monitoring_mode, source)
        VALUES ($1, $2, 'annual_review', $3, $4, 6, $5)
        RETURNING id, event_type, scheduled_date, monitoring_mode
        """,
        thesis_v2_id, ticker_id, f"Revue annuelle {ticker_id}", prochaine, CALENDAR_SOURCE_V2,
    )
    return {"valuation_range": data["valuation_range_updated"], "hypotheses": maj,
            "next_event": dict(ev)}


# ── Préparation du contexte (partagée avec le routeur) ───────────────────────
async def _preparer(
    thesis_v2_id: int, mode: int, *, trigger_label: str,
    peer_ticker: Optional[str], source_mode: Optional[int],
) -> tuple[dict[str, Any], str]:
    async with get_db_session() as conn:
        inputs = await _load_monitoring_inputs(conn, thesis_v2_id)
    contexte = (
        f"{_head(inputs)}\n\n---\n[mode: {mode}]\n"
        f"{_tache(mode, inputs, trigger_label=trigger_label, peer_ticker=peer_ticker, source_mode=source_mode)}"
    )
    return inputs, contexte


async def build_monitoring_context(
    thesis_v2_id: int, mode: int, *, trigger_label: str = "",
    peer_ticker: Optional[str] = None, source_mode: Optional[int] = None,
) -> str:
    """Le contexte EXACT qui serait envoyé au modèle, sans l'envoyer.

    Utilisé par le routeur quand `v2_auto_enabled` est FALSE : la session est enregistrée
    `pending_manual` avec son contexte déjà construit. Sans ça, « échéance en attente » se réduirait
    à une ligne vide dont personne ne saurait quoi faire — et le déclenchement manuel repartirait
    d'un contexte reconstruit plus tard, donc différent de celui de l'échéance.
    """
    _, contexte = await _preparer(
        thesis_v2_id, mode, trigger_label=trigger_label,
        peer_ticker=peer_ticker, source_mode=source_mode,
    )
    return contexte


# ── L'acte ───────────────────────────────────────────────────────────────────
async def run_monitoring(
    thesis_v2_id: int,
    mode: int,
    *,
    trigger_type: str = "manual",
    trigger_label: str = "",
    calendar_event_id: Optional[int] = None,
    peer_ticker: Optional[str] = None,
    source_mode: Optional[int] = None,
) -> dict[str, Any]:
    """Exécute une session de monitoring V2 et la persiste dans `monitoring_sessions_v2`.

    L'appel modèle est fait HORS transaction (convention #35) ; l'écriture de la session, le
    marquage de l'événement de calendrier et les effets du mode 6 sont ensuite atomiques.
    """
    if mode not in MODE_SCHEMAS:
        raise ValueError(f"mode {mode} inconnu — les modes V2 vont de 1 à 6 (§10).")

    inputs, contexte = await _preparer(
        thesis_v2_id, mode, trigger_label=trigger_label,
        peer_ticker=peer_ticker, source_mode=source_mode,
    )
    ticker_id = inputs["thesis"]["ticker_id"]
    agent = await get_agent_provider(AGENT_NAME, "v2")

    # `json_object=False` : DeepSeek-V4-Flash est non fiable en mode json_object (mesuré 2026-08-26).
    try:
        run = await run_json_agent(
            agent, [{"role": "user", "content": contexte}], MODE_SCHEMAS[mode], json_object=False,
            # Le modèle doit reproduire fidèlement des seuils chiffrés et des ids d'entries : on ne
            # veut pas de créativité sur ces reports-là.
            temperature=0.2,
        )
    except RuntimeError as e:
        # ⚠️ `run_json_agent` ne remonte ni le texte brut fautif ni les tokens consommés quand il
        # abandonne : on persiste le motif pour que l'échec reste visible, mais la dépense de cette
        # tentative n'est PAS comptabilisée. Limite connue du runner, commune à tous les agents V2.
        await _persister_echec(thesis_v2_id, ticker_id, mode, trigger_type, trigger_label,
                               calendar_event_id, contexte, agent, str(e))
        raise

    data = _forcer_champs_derives(
        mode, dict(run.data), thesis_v2_id=thesis_v2_id,
        peer_ticker=peer_ticker, source_mode=source_mode,
    )
    try:
        _valider_pont_hypotheses(data, inputs["hypotheses"], inputs["entries"], mode=mode)
    except MonitoringRefused as e:
        await _persister_echec(thesis_v2_id, ticker_id, mode, trigger_type, trigger_label,
                               calendar_event_id, contexte, agent, str(e),
                               raw_content=run.raw_content, run=run)
        raise

    cols = _colonnes_routeur(mode, data)
    jour = date.today()
    effets: dict[str, Any] = {}

    async with get_db_session() as conn:
        async with conn.transaction():
            session = await conn.fetchrow(
                """
                INSERT INTO monitoring_sessions_v2
                    (thesis_v2_id, ticker_id, mode, trigger_type, trigger_label, calendar_event_id,
                     result_json, context_sent, raw_content, alert_level, verdict, routing_suggestion,
                     status, provider_used, model_used, prompt_snapshot,
                     tokens_in, tokens_out, cost_usd, completed_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,'completed',$13,$14,$15,$16,$17,$18,NOW())
                RETURNING *
                """,
                thesis_v2_id, ticker_id, mode, trigger_type, trigger_label, calendar_event_id,
                data, contexte, run.raw_content,
                cols["alert_level"], cols["verdict"], cols["routing_suggestion"],
                agent.provider.name, agent.model, agent.system_prompt,
                run.tokens_in, run.tokens_out, run.cost_usd,
            )
            session_id = session["id"]

            refs = collect_refs(data)
            if refs:
                await snapshot_refs(
                    conn, analysis_id=session_id, analysis_kind="monitoring", refs=refs
                )

            if calendar_event_id is not None:
                # Le mode 1 consomme le drapeau de brief (J-2) ; les autres consomment l'événement.
                flag = "brief_triggered" if mode == 1 else "triggered"
                await conn.execute(
                    f"UPDATE calendar_events SET {flag} = TRUE, session_v2_id = $2 WHERE id = $1",
                    calendar_event_id, session_id,
                )

            if mode == 6:
                effets = await _appliquer_effets_mode6(
                    conn, thesis_v2_id=thesis_v2_id, ticker_id=ticker_id, data=data, jour=jour
                )

    logger.info(
        "monitoring V2 mode %s — %s thèse #%s → session #%s (alert=%s, verdict=%s, routing=%s, $%.4f)",
        mode, ticker_id, thesis_v2_id, session_id,
        cols["alert_level"], cols["verdict"], cols["routing_suggestion"], run.cost_usd,
    )
    return {"session": dict(session), "result": data, "effets": effets}


async def _persister_echec(
    thesis_v2_id: int, ticker_id: str, mode: int, trigger_type: str, trigger_label: str,
    calendar_event_id: Optional[int], contexte: str, agent, motif: str,
    *, raw_content: Optional[str] = None, run: Any = None,
) -> None:
    """Trace une session `failed`. Un échec silencieux est un trou de suivi.

    L'événement de calendrier n'est PAS marqué consommé : une session ratée ne doit pas faire
    disparaître l'échéance du radar du routeur — sinon la thèse cesse d'être suivie sans que
    personne ne l'ait décidé.
    """
    try:
        async with get_db_session() as conn:
            await conn.execute(
                """
                INSERT INTO monitoring_sessions_v2
                    (thesis_v2_id, ticker_id, mode, trigger_type, trigger_label, calendar_event_id,
                     context_sent, raw_content, status, provider_used, model_used, prompt_snapshot,
                     tokens_in, tokens_out, cost_usd)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'failed',$9,$10,$11,$12,$13,$14)
                """,
                thesis_v2_id, ticker_id, mode, trigger_type, trigger_label, calendar_event_id,
                contexte, raw_content or f"[échec sans sortie exploitable] {motif}",
                agent.provider.name, agent.model, agent.system_prompt,
                getattr(run, "tokens_in", 0) or 0, getattr(run, "tokens_out", 0) or 0,
                getattr(run, "cost_usd", 0) or 0,
            )
    except Exception:  # noqa: BLE001 — journaliser l'échec ne doit jamais masquer l'échec initial
        logger.exception("monitoring V2: échec de la trace d'échec (thèse #%s, mode %s)",
                         thesis_v2_id, mode)
