"""
Décision & validation de thèse V2 (§9, lot 7, migration 030) — le point où G2 s'exerce le plus fort.

CE MODULE N'APPELLE AUCUN MODÈLE, et c'est exactement le point. Tout le flux V2 en amont produit du
jugement (research → bull/bear → synthèse) ; ici on ne juge plus, on **acquitte**. L'utilisateur ne
« saisit » pas une position : il accuse réception d'une analyse, et le contrat vérifie que son acte
est cohérent avec le verdict, le sizing capé et les risques de cette analyse. Un `PROCEED` sur des
risques non acquittés, ou un sizing au-dessus du cap Kelly, est refusé AVANT toute écriture.

D'où vient chaque champ figé — la question décisive (G2) :
  - `synthesis`, `hypotheses`, `conditions_entree`, `position_sizing_pct` viennent de la **BASE**
    (l'analyse persistée), JAMAIS du corps de la requête. Les accepter du client rendrait le contrat
    décoratif : il suffirait d'envoyer une synthèse complaisante pour valider n'importe quoi.
  - L'utilisateur ne fournit QUE ses acquittements (`risk_acks`, `pre_mortem_acked`) et les faits
    d'exécution (combien de titres, à quel prix, quand) — qui ne sont pas des objets de décision.
  - Un sizing différent du recommandé n'est PAS un paramètre du validate : il se trace en amont,
    dans la synthèse (`position_sizing.override_utilisateur`, A7 — édition tracée avec motif). Le
    validate ne fait que constater. C'est ce qui rend l'override auditable au lieu d'être un
    argument d'appel qu'on peut passer en douce.
  - `risk_matrix_acked` est DÉRIVÉ (la bijection risk_acks ↔ risques_acceptes vaut acquittement) et
    non demandé au client : on ne fait pas déclarer ce qui est calculable (même esprit que #24).

Atomicité (§9) : `get_db_session()` n'ouvre AUCUNE transaction — il ne fait qu'acquérir une
connexion du pool, chaque `execute` est en autocommit. L'atomicité est donc explicite ici, via
`async with conn.transaction()`. Sans elle, une panne au milieu laisserait une thèse `active` sans
position, ou une position sans mouvement de trésorerie. Les appels réseau (FX, calendrier) sont
faits AVANT d'ouvrir la transaction : on ne tient pas des verrous pendant un aller-retour yfinance.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Optional

from pydantic import ValidationError

from app.contracts import RiskMatrix, ThesisValidation
from app.db.database import get_db_session

logger = logging.getLogger(__name__)

# Le flux V2 signe ses événements de calendrier : le scheduler V1 les filtre sur `thesis_v2_id IS
# NULL` (migration 030), cette valeur sert à la lecture humaine et au futur routeur V2 (lot 8).
CALENDAR_SOURCE_V2 = "thesis_agent_v2"


class DecisionRefused(ValueError):
    """Le contrat de décision refuse l'acte — AUCUNE écriture n'a eu lieu.

    Distincte d'une erreur technique : c'est un refus *métier* (verdict non actionnable, risque non
    acquitté, sizing hors cap…). Se traduit en HTTP 400 avec le motif du contrat, pour que l'UX
    puisse l'afficher tel quel plutôt que de le reformuler à sa façon."""


class ThesisNotFound(LookupError):
    pass


class AlreadyValidated(RuntimeError):
    """Thèse déjà `active` — la validation n'est pas rejouable (elle a créé une position réelle)."""


# ── Chargement des intrants de la décision ───────────────────────────────────
async def _load_decision_inputs(conn, thesis_id: int) -> dict[str, Any]:
    """Charge la thèse + l'analyse dont elle procède. Tout vient d'ici, rien du client."""
    thesis = await conn.fetchrow("SELECT * FROM theses_v2 WHERE id = $1", thesis_id)
    if thesis is None:
        raise ThesisNotFound(f"Thèse V2 #{thesis_id} introuvable.")
    if thesis["status"] == "active":
        raise AlreadyValidated(
            f"Thèse V2 #{thesis_id} déjà validée le {thesis['validated_at']} — "
            "une validation crée une position réelle, elle ne se rejoue pas."
        )
    if thesis["synthesis_analysis_id"] is None:
        raise DecisionRefused(
            f"Thèse V2 #{thesis_id} sans synthèse rattachée : il n'y a pas d'analyse à acquitter. "
            "Lance la chaîne research → bull/bear → synthèse avant de décider (G2)."
        )

    synth = await conn.fetchrow(
        "SELECT id, result_json, research_memo_id FROM investment_analyses "
        "WHERE id = $1 AND analysis_type = 'synthesis'",
        thesis["synthesis_analysis_id"],
    )
    if synth is None:
        raise DecisionRefused(
            f"Analyse de synthèse #{thesis['synthesis_analysis_id']} introuvable "
            "(ou d'un autre type) — décision impossible."
        )

    memo_id = thesis["research_memo_id"] or synth["research_memo_id"]
    if memo_id is None:
        raise DecisionRefused(
            "Aucun research_memo rattaché : la fourchette de valorisation en dérive (lignée "
            "d'auditabilité §9)."
        )
    memo = await conn.fetchrow("SELECT id, memo_json FROM research_memos WHERE id = $1", memo_id)
    if memo is None:
        raise DecisionRefused(f"Research memo #{memo_id} introuvable — décision impossible.")

    # Symbole boursier réel (convention #11) — peut être NULL : non coté, ou coté ajouté sans symbole.
    symbol = await conn.fetchval("SELECT ticker_symbol FROM tickers WHERE id = $1", thesis["ticker_id"])

    return {"thesis": thesis, "synthesis": synth, "memo": memo, "symbol": symbol}


def _valuation_range_from_memo(memo_json: dict[str, Any]) -> dict[str, float]:
    """Fourchette de valeur intrinsèque figée à l'entrée, DÉRIVÉE du research memo (§8.0).

    `iv_range` donne les bornes, `dcf_scenarios.base` le scénario central — on ne fabrique pas la
    base par moyenne des bornes : ce serait inventer une donnée que l'analyse n'a pas produite. Si
    la base tombe hors des bornes, le contrat rejette (low ≤ base ≤ high) et c'est le comportement
    voulu : une valorisation incohérente doit bloquer la décision, pas être figée en silence.
    """
    val = (memo_json or {}).get("valuation") or {}
    iv = val.get("iv_range")
    base = ((val.get("dcf_scenarios") or {}).get("base"))
    if not iv or len(iv) != 2 or base is None:
        raise DecisionRefused(
            "research_memo.valuation incomplet (iv_range + dcf_scenarios.base requis) — "
            "impossible de figer la fourchette de valorisation à l'entrée."
        )
    return {"low": float(iv[0]), "base": float(base), "high": float(iv[1])}


def build_validation(
    inputs: dict[str, Any],
    risk_acks: list[dict[str, Any]],
    pre_mortem_acked: bool,
) -> ThesisValidation:
    """Construit et VALIDE le contrat. Lève DecisionRefused — jamais d'écriture avant ce passage."""
    thesis, synth, memo = inputs["thesis"], inputs["synthesis"], inputs["memo"]
    result = synth["result_json"] or {}

    if "risk_matrix" not in result or "hypotheses" not in result:
        raise DecisionRefused(
            "result_json de la synthèse sans `risk_matrix`/`hypotheses` — contrat §8.4 non respecté."
        )

    try:
        rm = RiskMatrix.model_validate(result["risk_matrix"])
    except ValidationError as e:
        raise DecisionRefused(f"La synthèse ne satisfait plus son propre contrat (§8.4) : {e}") from e

    # Sizing : dérivé de l'analyse, jamais du client (override tracé A7 = dans la synthèse).
    ps = rm.position_sizing
    sizing = ps.override_utilisateur.valeur_pct if ps.override_utilisateur else ps.pct_recommande

    try:
        return ThesisValidation(
            schema_version="v2.0.0",
            thesis_id=thesis["id"],
            research_memo_id=memo["id"],
            synthesis_analysis_id=synth["id"],
            synthesis=rm,
            hypotheses=result["hypotheses"],
            risk_acks=risk_acks,
            pre_mortem_acked=pre_mortem_acked,
            position_sizing_pct=sizing,
            valuation_range=_valuation_range_from_memo(memo["memo_json"]),
            conditions_entree=list(rm.conditions_entree),
        )
    except ValidationError as e:
        raise DecisionRefused(str(e)) from e


# ── Faits d'exécution (hors contrat de décision) ─────────────────────────────
async def _resolve_execution_price(
    symbol: Optional[str], purchase_price_eur: float, purchase_date: str
) -> tuple[float, str]:
    """Convertit le prix EUR saisi vers la devise native, comme le fait le flux V1.

    `portfolio_positions` est une table de FAITS DU MONDE, partagée par les deux flux (migration
    030) : elle doit rester homogène. Deux conventions de devise dans la même table donneraient un
    portefeuille faux, silencieusement. On réutilise donc LE helper FX existant plutôt que d'en
    écrire un second — deux implémentations = deux vérités sur le taux de change. Import tardif :
    le helper vit dans un module d'API V1, on ne veut pas de cette dépendance au chargement.
    Best-effort, comme en V1 : un échec FX ne doit pas empêcher d'enregistrer une position réelle.

    `symbol` est `tickers.ticker_symbol`, JAMAIS `tickers.id` (convention #11) : depuis la migration
    018 l'id peut être `PUB-XXXXXXXX`/`PRIV-XXXXXXXX`, qui n'existe chez aucun fournisseur. Symbole
    absent ⇒ on n'interroge pas DataService (non coté ou ajouté sans symbole) et on reste en EUR.
    """
    if not symbol:
        return purchase_price_eur, "EUR"

    from app.api.thesis_v2 import _get_fx_rate
    from app.config import settings
    from app.data_collection.data_service import DataService

    currency = "EUR"
    try:
        m1 = await DataService().get_m1(symbol, settings.FMP_API_KEY)
        currency = (m1.get("price") or {}).get("currency", "EUR") or "EUR"
    except Exception:  # noqa: BLE001 — API muette, rate-limit yfinance…
        logger.info("decision: devise native indisponible pour %s, EUR retenu", symbol)

    if currency == "EUR":
        return purchase_price_eur, "EUR"
    try:
        rate = await _get_fx_rate("EUR", currency, purchase_date)
        return round(purchase_price_eur * rate, 4), currency
    except Exception as e:  # noqa: BLE001
        logger.warning("decision: conversion FX EUR→%s échouée (%s), prix conservé en EUR", currency, e)
        return purchase_price_eur, "EUR"


async def _next_earnings_date(symbol: Optional[str]) -> Optional[date]:
    """Prochaine publication de résultats, pour armer les modes 1 (J-2) et 2 (J+1).

    Best-effort et hors transaction. Un calendrier absent ne doit pas bloquer une entrée en
    position : l'événement sera posé plus tard par le rafraîchissement de calendrier. Comme
    ci-dessus, on part du `ticker_symbol` (convention #11) et on s'abstient s'il est absent.
    """
    if not symbol:
        return None
    try:
        from app.data_collection.data_service import DataService

        cal = await DataService().get_calendar(symbol)
        raw = (cal or {}).get("next_earnings_date")
        if isinstance(raw, str) and raw:
            return date.fromisoformat(raw[:10])
    except Exception as e:  # noqa: BLE001
        logger.info("decision: date de résultats indisponible pour %s (%s)", symbol, e)
    return None


# ── L'acte : contrat d'abord, puis transaction atomique ──────────────────────
async def validate_thesis(
    thesis_id: int,
    risk_acks: list[dict[str, Any]],
    pre_mortem_acked: bool,
    shares: float,
    purchase_price: float,
    purchase_date: str,
) -> dict[str, Any]:
    """POST /v2/theses/{id}/validate — fige la décision puis exécute l'entrée en position (§9).

    `purchase_price` est en EUR (le cash réellement débité) ; la conversion vers la devise native
    suit la convention du portefeuille partagé.
    """
    async with get_db_session() as conn:
        inputs = await _load_decision_inputs(conn, thesis_id)

    # 1) Le contrat AVANT tout — un refus ici n'écrit rien (G2).
    validation = build_validation(inputs, risk_acks, pre_mortem_acked)

    ticker_id = inputs["thesis"]["ticker_id"]
    symbol = inputs["symbol"]

    # 2) Aller-retours réseau HORS transaction (pas de verrou tenu pendant un appel externe).
    price_native, currency = await _resolve_execution_price(symbol, purchase_price, purchase_date)
    earnings = await _next_earnings_date(symbol)

    purchase_day = date.fromisoformat(purchase_date)
    payload = validation.model_dump(mode="json")

    # 3) Transaction atomique : tout ou rien (§9, convention #13).
    async with get_db_session() as conn:
        async with conn.transaction():
            thesis_row = await conn.fetchrow(
                """
                UPDATE theses_v2 SET
                    status='active', validation_json=$2, verdict=$3, position_sizing_pct=$4,
                    valuation_range=$5, conditions_entree=$6, hypotheses=$7, risk_acks=$8,
                    pre_mortem_acked=TRUE, risk_matrix_acked=TRUE,
                    research_memo_id=$9, synthesis_analysis_id=$10,
                    validated_at=NOW(), updated_at=NOW()
                WHERE id=$1 AND status <> 'active'
                RETURNING *
                """,
                thesis_id, payload, validation.synthesis.verdict, validation.position_sizing_pct,
                payload["valuation_range"], list(validation.conditions_entree),
                payload["hypotheses"], payload["risk_acks"],
                validation.research_memo_id, validation.synthesis_analysis_id,
            )
            if thesis_row is None:
                # Course entre deux validations concurrentes : la garde `status <> 'active'` a mordu.
                raise AlreadyValidated(f"Thèse V2 #{thesis_id} validée entre-temps.")

            await conn.execute(
                "UPDATE tickers SET status='portfolio', updated_at=NOW() WHERE id=$1", ticker_id
            )

            position = await conn.fetchrow(
                """
                INSERT INTO portfolio_positions
                    (ticker_id, shares, purchase_price, purchase_currency, purchase_date,
                     thesis_v2_id, status, purchase_price_eur)
                VALUES ($1, $2, $3, $4, $5, $6, 'open', $7)
                RETURNING id, shares, purchase_price, purchase_currency, purchase_price_eur
                """,
                ticker_id, shares, price_native, currency, purchase_day, thesis_id, purchase_price,
            )

            await conn.execute(
                "INSERT INTO cash_movements (type, amount, label, ticker_id) "
                "VALUES ('buy', $1, $2, $3)",
                shares * purchase_price,   # cash réel débité, toujours en EUR
                f"Achat {ticker_id} — thèse V2 #{thesis_id}",
                ticker_id,
            )

            events: list[dict[str, Any]] = []
            if earnings is not None:
                # UN seul événement sert les modes 1 (J-2, brief_triggered) et 2 (J+1, triggered) :
                # le routeur calcule le décalage depuis la date de l'événement.
                ev = await conn.fetchrow(
                    """
                    INSERT INTO calendar_events
                        (thesis_v2_id, ticker_id, event_type, label, scheduled_date,
                         monitoring_mode, source)
                    VALUES ($1, $2, 'quarterly_results', $3, $4, 2, $5)
                    RETURNING id, event_type, scheduled_date, monitoring_mode
                    """,
                    thesis_id, ticker_id, f"Résultats {ticker_id}", earnings, CALENDAR_SOURCE_V2,
                )
                events.append(dict(ev))

            ev6 = await conn.fetchrow(
                """
                INSERT INTO calendar_events
                    (thesis_v2_id, ticker_id, event_type, label, scheduled_date,
                     monitoring_mode, source)
                VALUES ($1, $2, 'annual_review', $3, $4, 6, $5)
                RETURNING id, event_type, scheduled_date, monitoring_mode
                """,
                thesis_id, ticker_id, f"Revue annuelle {ticker_id}",
                purchase_day + timedelta(days=365), CALENDAR_SOURCE_V2,
            )
            events.append(dict(ev6))

    logger.info(
        "decision: thèse V2 #%s validée (%s, %s%% du portefeuille, %s risque(s) acquitté(s))",
        thesis_id, validation.synthesis.verdict, validation.position_sizing_pct,
        len(validation.risk_acks),
    )
    return {
        "thesis": dict(thesis_row),
        "position": dict(position),
        "calendar_events": events,
        "validation": payload,
        # Ces événements ne sont pas encore ROUTÉS : le scheduler V1 les filtre volontairement
        # (migration 030) et le routeur V2 arrive au lot 8. Annoncé pour ne pas se lire comme un bug.
        "note": "Événements planifiés ; le routeur de monitoring V2 (modes 1/2/6) arrive au lot 8.",
    }


async def create_thesis_draft(
    ticker_id: str, research_memo_id: int, synthesis_analysis_id: int
) -> dict[str, Any]:
    """Ouvre la thèse V2 en `draft` à partir d'une synthèse — l'objet qu'on validera ensuite."""
    async with get_db_session() as conn:
        row = await conn.fetchrow(
            "INSERT INTO theses_v2 (ticker_id, research_memo_id, synthesis_analysis_id, status) "
            "VALUES ($1, $2, $3, 'draft') RETURNING *",
            ticker_id, research_memo_id, synthesis_analysis_id,
        )
    return dict(row)
