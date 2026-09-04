"""
Alimentateur `financials` (V2) — fonde les RATIOS DÉRIVÉS depuis les faits EDGAR déjà en base.

Motif (00-REPRISE, étape 1 post-valorisation) : la dimension MVDD `financials` exige quatre champs —
`roic_pct`, `fcf_conversion_pct`, `intensite_capex_pct`, `levier` — au tier plancher **A**. Aucun n'est
une donnée que la recherche web fonde honnêtement, et le quant (yfinance/FMP) est tier B+, donc SOUS le
plancher : un ratio quant ne fonderait pas le champ. Ce sont des **ratios**, pas des mesures : ils se
CALCULENT à partir des postes comptables. Or ces postes sont déjà en base, en tier A, issus du 10-K
EDGAR (CA, résultat net, cash-flow opérationnel, capitaux propres, dette, trésorerie). Un ratio calculé
**uniquement** à partir de faits tier A est lui-même un fait tier A : sa provenance est EDGAR, donc
`source_type='edgar_official'`. Aucun intrant non-EDGAR n'entre — sinon on retomberait à B+.

Le seul poste manquant au seed est le **capex** (nécessaire à `fcf_conversion_pct` et
`intensite_capex_pct`). Il n'est pas fabriqué ni emprunté au quant : il est **mesuré à la source** via
`edgar_facts.fetch_annual_value()` (concept us-gaap `PaymentsToAcquirePropertyPlantAndEquipment`), puis
persisté comme fait EDGAR tier A réutilisable. Si EDGAR est indisponible, les deux champs qui en
dépendent restent **non fondés** — un trou honnête, jamais un chiffre inventé (#25).

Garde-fous (mêmes que valuation_feed / base_rate_corpus) :
  • `source_type` connu et mesuré ici, pas déclaré par un modèle (#24) ; score recalculé par
    `store_knowledge` (tier A fixe, le score décroît un peu avec l'âge du dépôt mais pas le tier).
  • Append-only avec supersede par tags : re-calculer un ratio supersede l'entrée courante du même champ.
  • La transformation `build_financials_entries()` est **pure** (facts dict → specs), vérifiable
    hors-ligne (`backend/checks/check_financials_feed.py`). L'IO (KB + EDGAR + écriture) vit dans
    `run_financials_feed()`.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from app.data_collection.data_service import DataService  # noqa: F401  (parité d'accès quant, non requis ici)
from app.db.database import get_db_session
from app.knowledge.edgar_facts import EdgarUnavailable, cik_from_url, fetch_annual_value
# L'identité d'un fait EDGAR (quelle entrée courante un nouveau fait remplace) est une règle
# UNIQUE, tenue par edgar_feed. Ce module écrit lui aussi un `capital_expenditure` : lui donner
# son propre appariement, c'est écrire deux fois le même fait sous deux jeux de tags — cf. F6.
from app.knowledge.edgar_feed import _current_fact_ids
from app.knowledge.service import get_current_entries, store_knowledge
from app.knowledge.units import montant

logger = logging.getLogger(__name__)

# Ratios dérivés de faits EDGAR seuls → provenance EDGAR → tier A (0.95 dans RELIABILITY_TABLE).
_SOURCE_TYPE = "edgar_official"
# On ne consomme QUE des faits tier A pour que le ratio reste tier A (cf. docstring).
_CONSUMED_SOURCE_TYPES = {"edgar_official"}
# Concept XBRL du capex — ordre d'essai (NVDA déclare le premier).
_CAPEX_TAGS = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"]

# metric du content_structured → poste interne. `cash_and_lt_debt` porte deux nombres.
_SIMPLE_METRICS = {
    "revenue": "revenue",
    "net_income": "net_income",
    "gross_profit": "gross_profit",
    "operating_cash_flow": "operating_cash_flow",
    "stockholders_equity": "stockholders_equity",
    "total_assets": "total_assets",
    "capital_expenditure": "capex",
}


class FinancialsUnavailable(Exception):
    """Les ratios `financials` ne sont pas fondables (ticker sans symbole, ou aucun fait EDGAR en base).
    Distinct d'un résultat vide : l'appelant DOIT le remonter (#25)."""


@dataclass
class FinancialsEntrySpec:
    field: str            # 'roic_pct' | 'fcf_conversion_pct' | 'intensite_capex_pct' | 'levier'
    entry_type: str
    title: str
    content: str
    content_structured: dict[str, Any]
    fiscal_period: Optional[str] = None
    source_url: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    source_type: str = _SOURCE_TYPE


def _pct(v: Optional[float], nd: int = 1) -> str:
    if v is None:
        return "n/d"
    return f"{v:.{nd}f}".replace(".", ",") + " %"


def _md(v: Optional[float], devise: str = "") -> str:
    """Montant en format FR, unité choisie par l'ordre de grandeur (règle : `knowledge/units.py`).

    ⚠️ La devise est passée ICI, plus concaténée par l'appelant : un vrai zéro s'écrit « 0 » sans
    palier (#45), donc `f"{_md(v, cur)}"` produirait « 0USD ». Ce module écrivait `/1e9` en dur —
    le capex FY2025 de RVMD (15,99 M$) sortait « 0,0 MdUSD », et l'entry `fcf_conversion_pct`
    publiait « FCF -0,9 Md = CFO -0,9 Md − capex 0,0 Md » : une soustraction qui paraît juste
    seulement parce que ses deux termes sont écrasés à la même unité (F10).
    """
    return montant(v, devise)


def _as_dict(cs: Any) -> dict[str, Any]:
    """content_structured est un dict (codec JSONB) — mais tolère une str JSON par sécurité."""
    if isinstance(cs, dict):
        return cs
    if isinstance(cs, str):
        try:
            return json.loads(cs)
        except ValueError:
            return {}
    return {}


def _parse_end(v: Any) -> Optional[date]:
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            return None
    return None


# Postes de BILAN, pour les entries LEGACY qui ne portent pas encore `poste_kind` (seed NVDA écrit
# à la main, entries antérieures au split flux/bilan). Repli explicite et borné — la nature d'un
# poste se lit dans le fait lui-même dès qu'elle y est écrite.
_STOCK_METRICS_LEGACY = {"stockholders_equity", "total_assets", "cash_and_lt_debt"}


def _poste_kind(metric: str, cs: dict[str, Any]) -> str:
    return cs.get("poste_kind") or ("stock" if metric in _STOCK_METRICS_LEGACY else "flow")


def extract_edgar_facts(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Faits `fact_financial` EDGAR (tier A) → dict plat. Pur, sans IO.

    DEUX ancres, parce qu'il y a deux natures de poste et que les confondre est un défaut de sens :
      • **flux** (CA, résultat, OCF, capex) → dernière clôture d'exercice ; les mélanger entre
        exercices fabriquerait des ratios faux tout en restant « tier A » ;
      • **bilan** (capitaux propres, actif, trésorerie/dette) → dernier INSTANT publié, qui est
        typiquement un trimestre PLUS RÉCENT que la clôture. Les forcer sur la clôture annuelle
        rendait le levier d'un émetteur aveugle à toute levée de fonds postérieure — mesuré sur
        RVMD : 487,4 M$ de convertibles invisibles, capitaux propres sous-évalués de 60 %.

    `periods_mixed` dit si les deux ancres diffèrent, pour que les ratios qui croisent un flux et un
    stock (ROIC) le DÉCLARENT au lieu de le taire. Postes absents = None (jamais un zéro, #25).
    """
    by_metric: dict[str, dict[date, dict[str, Any]]] = {}
    currency = "USD"
    for e in entries:
        if e.get("entry_type") != "fact_financial":
            continue
        if e.get("source_type") not in _CONSUMED_SOURCE_TYPES:
            continue
        cs = _as_dict(e.get("content_structured"))
        metric = cs.get("metric")
        end = _parse_end(cs.get("period_end")) or _parse_end(e.get("source_date"))
        if not metric or end is None:
            continue
        currency = cs.get("currency") or currency
        rec = {"period": cs.get("period") or e.get("fiscal_period"),
               "source_url": e.get("source_url"), "entry_id": e.get("id"),
               "kind": _poste_kind(metric, cs), "cs": cs}
        by_metric.setdefault(metric, {})[end] = rec

    def _latest(metric: str) -> Optional[date]:
        dates = sorted((by_metric.get(metric) or {}).keys())
        return dates[-1] if dates else None

    stock_target = _latest("stockholders_equity") or _latest("total_assets")
    # L'ancre de flux ne peut pas être celle du bilan : sur un socle post-split elles diffèrent, et
    # y apparier les flux les viderait tous silencieusement (chaque ratio deviendrait non fondé).
    flow_target = _latest("net_income") or _latest("revenue") or _latest("operating_cash_flow")

    facts: dict[str, Any] = {
        "period_end": flow_target or stock_target, "balance_end": stock_target,
        "currency": currency, "period": None, "source_url": None,
        "periods_mixed": bool(stock_target and flow_target and stock_target != flow_target),
        "jours_entre_ancres": ((stock_target - flow_target).days
                               if stock_target and flow_target else None),
    }
    if flow_target is None and stock_target is None:
        return facts

    def _at(metric: str) -> Optional[dict[str, Any]]:
        at_date = by_metric.get(metric) or {}
        kind = next((r["kind"] for r in at_date.values()), None)
        target = stock_target if kind == "stock" else flow_target
        if target is None:
            return None
        return at_date.get(target)

    # période lisible + URL de provenance (celle du CA, à défaut de l'ancre bilan)
    anchor = _at("revenue") or _at("net_income") or _at("stockholders_equity")
    if anchor:
        facts["period"] = anchor["period"]
        facts["source_url"] = anchor["source_url"]

    for metric, key in _SIMPLE_METRICS.items():
        rec = _at(metric)
        facts[key] = (rec["cs"].get("value") if rec else None)

    cash_rec = _at("cash_and_lt_debt")
    if cash_rec:
        facts["cash"] = cash_rec["cs"].get("cash")
        facts["long_term_debt"] = cash_rec["cs"].get("long_term_debt")
    else:
        facts["cash"] = facts.get("cash")
        facts["long_term_debt"] = facts.get("long_term_debt")
    return facts


def build_financials_entries(
    ticker_id: str, symbol: str, facts: dict[str, Any], *, as_of: date
) -> tuple[list[FinancialsEntrySpec], list[dict[str, str]]]:
    """facts (sortie d'extract_edgar_facts, capex éventuellement injecté) → specs des ratios fondables.

    Pur, sans IO. Ne produit une entry QUE si tous les intrants du ratio sont présents ; sinon le champ
    est reporté dans `unfounded` avec la raison — jamais une entrée avec un chiffre fabriqué (#25).
    Retour : (specs, unfounded=[{field, reason}]).
    """
    period = facts.get("period")
    period_end = facts.get("period_end")
    cur = facts.get("currency") or "USD"
    fy = period or (f"FY{period_end.year}" if isinstance(period_end, date) else "dernier exercice")
    src = facts.get("source_url")

    # ── Datation : un ratio se date par les POSTES qui le composent (F6) ──────
    # `levier` n'est fait que de postes de bilan ; l'annoncer « FY2025 » alors que ses trois
    # chiffres datent du 2026-06-30 produit un fait FAUX dont tous les nombres sont justes — le
    # pire genre, puisque aucun contrôle arithmétique ne peut le voir. Un ratio MIXTE (ROIC : un
    # flux au numérateur, un bilan au dénominateur) est licite, mais il doit le DIRE.
    balance_end = facts.get("balance_end")
    au_bilan = f"AU {balance_end}" if balance_end else fy
    ancres_mixtes = bool(facts.get("periods_mixed"))
    ecart_ancres = facts.get("jours_entre_ancres")
    mention_mixte = (
        f" ⚠️ Ancres MIXTES : numérateur de l'exercice clos le {period_end}, dénominateur du bilan "
        f"au {balance_end} — {ecart_ancres} jours d'écart. "
        if ancres_mixtes else ""
    )

    def _dater(structured: dict[str, Any], *, mixte: bool) -> dict[str, Any]:
        """Ajoute la traçabilité des ancres à un ratio mixte. Un ratio mono-ancre n'en porte pas :
        la déclarer partout la rendrait invisible là où elle compte."""
        if mixte and ancres_mixtes:
            structured |= {"periods_mixed": True, "balance_end": str(balance_end),
                           "jours_entre_ancres": ecart_ancres}
        return structured

    revenue = facts.get("revenue")
    net_income = facts.get("net_income")
    ocf = facts.get("operating_cash_flow")
    equity = facts.get("stockholders_equity")
    cash = facts.get("cash")
    debt = facts.get("long_term_debt")
    capex = facts.get("capex")

    specs: list[FinancialsEntrySpec] = []
    unfounded: list[dict[str, str]] = []

    def _tags(f: str) -> list[str]:
        return ["financials", f, "derived_ratio", "edgar"]

    def _miss(f: str, need: str) -> None:
        unfounded.append({"field": f, "reason": f"intrant manquant en base EDGAR : {need}"})

    def _absents(**intrants: Any) -> str:
        """Nomme les intrants RÉELLEMENT absents, jamais la liste entière de la formule.

        Énumérer les quatre intrants quand un seul manque envoie chercher trois données déjà
        présentes — et masque lequel bloque. `0` compte comme présent : c'est une valeur, pas un
        trou (cf. le CA nul de RVMD).
        """
        manquants = [nom for nom, v in intrants.items() if v is None]
        return ", ".join(manquants) if manquants else "aucun (valeur nulle rendant le ratio indéfini)"

    # ── levier : dette / capitaux propres + dette nette (tous EDGAR) ──────────
    if debt is not None and equity and cash is not None:
        net_debt = debt - cash
        d2e = debt / equity * 100
        nd2e = net_debt / equity * 100
        net_cash = net_debt < 0
        structured = {
            "metric": "levier", "field": "levier",
            "long_term_debt": debt, "cash": cash, "net_debt": net_debt,
            "stockholders_equity": equity, "currency": cur,
            "debt_to_equity_pct": round(d2e, 2), "net_debt_to_equity_pct": round(nd2e, 2),
            "net_cash_position": net_cash, "period": au_bilan,
            "period_end": str(balance_end) if balance_end else None,
            "poste_kind": "stock",
            "method": "dette LT (non courante) / capitaux propres ; dette nette = dette LT − trésorerie",
        }
        content = (
            f"Levier de {ticker_id} ({symbol}) — {au_bilan} : dette LT {_md(debt, cur)}, trésorerie "
            f"{_md(cash, cur)} → dette nette {_md(net_debt, cur)}. Gearing (`levier`, dette/capitaux "
            f"propres) = {_pct(d2e)} ; dette nette/capitaux propres = {_pct(nd2e)}. "
        )
        if net_cash:
            content += (
                "Position de trésorerie NETTE POSITIVE : dette nette négative, donc dette nette/EBITDA "
                "négatif — le gearing (dette/capitaux propres) est ici la lecture pertinente du levier. "
            )
        content += "Calculé depuis les postes de bilan déposés chez EDGAR (tier A)."
        specs.append(FinancialsEntrySpec(
            field="levier", entry_type="fact_financial",
            title=f"Financials — levier (dette nette / gearing) {au_bilan}",
            content=content, content_structured=structured,
            fiscal_period=au_bilan, source_url=src, tags=_tags("levier"),
        ))
    else:
        _miss("levier", _absents(**{"dette LT": debt, "trésorerie": cash,
                                    "capitaux propres": equity}))

    # ── roic_pct : NOPAT / capital investi (NOPAT ≈ résultat net, société en trésorerie nette) ──
    if net_income and equity and debt is not None and cash is not None:
        invested = equity + debt - cash
        roic = net_income / invested * 100 if invested else None
        if roic is not None:
            structured = _dater({
                "metric": "roic", "field": "roic_pct",
                "roic_pct": round(roic, 2), "net_income": net_income,
                "invested_capital": invested, "stockholders_equity": equity,
                "long_term_debt": debt, "cash": cash, "currency": cur, "period": period,
                "nopat_approx": "net_income",
                "method": ("NOPAT ≈ résultat net (charge d'intérêts nette négligeable en position de "
                           "trésorerie nette) ; capital investi = capitaux propres + dette LT − trésorerie"),
            }, mixte=True)
            content = (
                f"ROIC de {ticker_id} ({symbol}) — {fy} : {_pct(roic)} (`roic_pct`). Capital investi "
                f"{_md(invested, cur)} (capitaux propres {_md(equity, cur)} + dette LT {_md(debt, cur)} − trésorerie "
                f"{_md(cash, cur)}), NOPAT approché par le résultat net {_md(net_income, cur)}. "
                f"Approximation NOPAT ≈ résultat net justifiée par la position de trésorerie nette "
                f"(intérêts nets négligeables) — elle peut LÉGÈREMENT majorer le ROIC si le résultat "
                f"non opérationnel est significatif.{mention_mixte} Calculé depuis les dépôts EDGAR "
                f"(tier A)."
            )
            specs.append(FinancialsEntrySpec(
                field="roic_pct", entry_type="fact_financial",
                title=f"Financials — ROIC {fy}",
                content=content, content_structured=structured,
                fiscal_period=period, source_url=src, tags=_tags("roic_pct"),
            ))
        else:
            _miss("roic_pct", "capital investi nul")
    else:
        _miss("roic_pct", _absents(**{"résultat net": net_income, "capitaux propres": equity,
                                      "dette LT": debt, "trésorerie": cash}))

    # ── fcf_conversion_pct : FCF / résultat net, FCF = OCF − capex ────────────
    if ocf is not None and net_income and capex is not None:
        fcf = ocf - capex
        # ⚠️ LE PIÈGE : un quotient de deux négatifs est POSITIF. Mesuré sur RVMD FY2025 —
        # FCF −913,7 M$ / résultat net −1 131,3 M$ = **+80,8 %**, publié tier A comme une
        # « conversion FCF de 80,8 % » par une société qui brûle 914 M$ par an. Arithmétique exacte,
        # contrat satisfait, fondation légitime, sens inversé : c'est #37 d'un cran plus haut — un
        # ratio valide un CALCUL, jamais sa signification. La conversion du résultat en cash n'a de
        # sens que si le résultat est un profit ; sinon on publie le fait qui compte vraiment, la
        # consommation de trésorerie, et on laisse `fcf_conversion_pct` à None plutôt qu'à un
        # nombre flatteur.
        significatif = net_income > 0
        conv = (fcf / net_income * 100) if significatif else None
        structured = {
            "metric": "fcf_conversion", "field": "fcf_conversion_pct",
            "fcf_conversion_pct": round(conv, 2) if conv is not None else None,
            "free_cash_flow": fcf,
            "operating_cash_flow": ocf, "capex": capex, "net_income": net_income,
            "currency": cur, "period": period,
            "significatif": significatif,
            "method": "FCF = flux de trésorerie opérationnel − capex ; conversion = FCF / résultat net",
        }
        if significatif:
            content = (
                f"Conversion FCF de {ticker_id} ({symbol}) — {fy} : {_pct(conv)} (`fcf_conversion_pct`). "
                f"FCF {_md(fcf, cur)} = cash-flow opérationnel {_md(ocf, cur)} − capex {_md(capex, cur)}, rapporté au "
                f"résultat net {_md(net_income, cur)}. Tous les postes proviennent du 10-K EDGAR (tier A ; "
                f"capex = us-gaap PaymentsToAcquirePropertyPlantAndEquipment)."
            )
            titre = f"Financials — conversion FCF {fy}"
        else:
            structured["metric"] = "cash_burn"
            structured["cash_burn_annuel"] = -fcf if fcf < 0 else 0
            structured["method"] = (
                "résultat net négatif → la conversion FCF n'est pas définie (un quotient de deux "
                "négatifs serait positif et se lirait comme une bonne conversion) ; on publie la "
                "consommation de trésorerie, qui est le fait pertinent"
            )
            content = (
                f"Trésorerie consommée par {ticker_id} ({symbol}) — {fy} : FCF {_md(fcf, cur)} "
                f"= cash-flow opérationnel {_md(ocf, cur)} − capex {_md(capex, cur)}, pour un résultat net "
                f"{_md(net_income, cur)}. ⚠️ `fcf_conversion_pct` est **non défini** ici et vaut None : "
                f"le résultat net étant négatif, le quotient FCF/résultat net serait POSITIF "
                f"({_pct(fcf / net_income * 100)}) et se lirait à tort comme une bonne conversion du "
                f"résultat en cash. L'émetteur ne convertit pas un bénéfice en trésorerie, il "
                f"consomme de la trésorerie. Postes du 10-K EDGAR (tier A ; capex = us-gaap "
                f"PaymentsToAcquirePropertyPlantAndEquipment)."
            )
            titre = f"Financials — consommation de trésorerie {fy} (conversion FCF non définie)"
        specs.append(FinancialsEntrySpec(
            field="fcf_conversion_pct", entry_type="fact_financial",
            title=titre,
            content=content, content_structured=structured,
            fiscal_period=period, source_url=src, tags=_tags("fcf_conversion_pct"),
        ))
    else:
        need = "capex (EDGAR indisponible)" if capex is None else "cash-flow opérationnel, résultat net"
        _miss("fcf_conversion_pct", need)

    # ── intensite_capex_pct : capex / CA ─────────────────────────────────────
    if capex is not None and revenue:
        inten = capex / revenue * 100
        structured = {
            "metric": "intensite_capex", "field": "intensite_capex_pct",
            "intensite_capex_pct": round(inten, 2), "capex": capex, "revenue": revenue,
            "currency": cur, "period": period,
            "method": "capex / chiffre d'affaires",
        }
        content = (
            f"Intensité capitalistique de {ticker_id} ({symbol}) — {fy} : {_pct(inten)} "
            f"(`intensite_capex_pct`). Capex {_md(capex, cur)} / CA {_md(revenue, cur)}. "
            f"Modèle {'peu' if inten < 10 else 'assez'} capitalistique. Postes du 10-K EDGAR (tier A)."
        )
        specs.append(FinancialsEntrySpec(
            field="intensite_capex_pct", entry_type="fact_financial",
            title=f"Financials — intensité capex {fy}",
            content=content, content_structured=structured,
            fiscal_period=period, source_url=src, tags=_tags("intensite_capex_pct"),
        ))
    else:
        # « CA absent » et « CA nul » ne sont PAS le même monde. RVMD dépose
        # `RevenueFromContractWithCustomerExcludingAssessedTax = 0` : la donnée est là, c'est le
        # ratio qui n'existe pas. Écrire « intrant manquant » sur une donnée présente envoie la
        # chaîne chercher une source qu'elle ne trouvera jamais, et fait passer pour une lacune de
        # collecte ce qui est un fait d'entreprise (pré-commercialisation).
        if capex is None:
            need = "capex (EDGAR indisponible)"
        elif revenue == 0:
            need = ("chiffre d'affaires NUL (déposé, pas manquant) — l'intensité capitalistique "
                    "n'est pas définie sans base de CA ; émetteur en pré-commercialisation")
        else:
            need = "chiffre d'affaires"
        _miss("intensite_capex_pct", need)

    return specs, unfounded


async def _current_tagged_entry_id(conn, ticker_id: str, tags: list[str]) -> Optional[int]:
    """Id de l'entrée COURANTE portant tous les `tags` (à superseder). Ce feed est le seul producteur
    de ces tags dérivés → pas de collision avec une entry EDGAR brute ou de recherche."""
    row = await conn.fetchrow(
        """
        SELECT id FROM knowledge_entries
        WHERE ticker_id = $1 AND superseded_by IS NULL AND is_deleted = FALSE
          AND tags @> $2
        ORDER BY id DESC LIMIT 1
        """,
        ticker_id, tags,
    )
    return row["id"] if row else None


async def _persist_capex_fact(
    conn, ticker_id: str, symbol: str, point: dict[str, Any], *, currency: str,
    fiscal_period: Optional[str], source_url: Optional[str], tag_used: str,
) -> dict[str, Any]:
    """Écrit le capex fetché comme fait EDGAR tier A réutilisable (supersede l'ancien s'il existe).

    ⚠️ L'appariement se fait sur le POSTE (`metric` + exercice), jamais sur les tags. Le tag `fact`
    séparait ce capex de celui du socle (`{financials, capex, edgar}` contre
    `{financials, capex, fact, edgar}`) : deux entrées `capital_expenditure` FY2025 courantes en
    même temps pour RVMD, un seul mot d'écart, aucun signal. Un fait vaut par ce qu'il mesure, pas
    par le vocabulaire du module qui l'a écrit.
    """
    val = point["val"]
    period_end = point["end"]
    structured = {
        "metric": "capital_expenditure", "value": val, "currency": currency,
        "period": fiscal_period, "period_end": period_end, "poste_kind": "flow",
        "xbrl_tag": f"us-gaap:{tag_used}", "accn": point.get("accn"), "form": point.get("form"),
    }
    content = (
        f"Capex (dépenses d'investissement) de {ticker_id} ({symbol}) — exercice clos le {period_end} : "
        f"{_md(val, currency)}. Source : {point.get('form','10-K')} EDGAR, concept XBRL "
        f"us-gaap:{tag_used} (accession {point.get('accn')})."
    )
    prevs = await _current_fact_ids(
        conn, ticker_id, "capital_expenditure", period_end, flow=True
    )
    stored = await store_knowledge(
        conn, ticker_id=ticker_id, entry_type="fact_financial", content=content,
        source_type=_SOURCE_TYPE, title=f"Capex {fiscal_period or period_end} ({symbol})",
        content_structured=structured, tags=["financials", "capex", "fact", "edgar"],
        lang="fr", source_url=source_url, source_date=_parse_end(period_end),
        fiscal_period=fiscal_period, supersedes_entry_id=prevs[0] if prevs else None,
    )
    if len(prevs) > 1:
        await conn.execute(
            "UPDATE knowledge_entries SET superseded_by = $1 WHERE id = ANY($2::int[])",
            stored["id"], prevs[1:],
        )
    return stored


async def run_financials_feed(
    ticker_id: str, *, persist: bool = True, refresh: bool = False
) -> dict[str, Any]:
    """Fonde `financials.{roic_pct,fcf_conversion_pct,intensite_capex_pct,levier}` depuis les faits
    EDGAR en base, en récupérant le capex manquant à la source (EDGAR).

    `persist=False` = dry-run (base append-only : on regarde avant d'écrire). `refresh` re-tente le
    fetch capex EDGAR même si un capex figure déjà en base.
    """
    async with get_db_session() as conn:
        row = await conn.fetchrow(
            "SELECT ticker_symbol, company_type FROM tickers WHERE id = $1", ticker_id
        )
        if row is None:
            raise FinancialsUnavailable(f"ticker inconnu : {ticker_id}")
        if (row["company_type"] or "") == "private" or not row["ticker_symbol"]:
            raise FinancialsUnavailable(
                f"{ticker_id} : pas de symbole de marché (privé/PUB-/PRIV-) — pas de dépôt EDGAR ; "
                f"financials à fonder depuis des documents uploadés, pas depuis EDGAR"
            )
        symbol = row["ticker_symbol"]
        entries = await get_current_entries(
            conn, ticker_id, entry_types=["fact_financial"], include_sector=False, limit=500
        )

    facts = extract_edgar_facts(entries)
    if facts.get("period_end") is None:
        raise FinancialsUnavailable(
            f"{ticker_id} : aucun fait financier EDGAR (tier A) en base — lancer l'ingestion EDGAR "
            f"(10-K) avant de dériver les ratios `financials`"
        )

    # CIK depuis la provenance réelle d'un dépôt EDGAR en base (aucune table de correspondance).
    cik = cik_from_url(facts.get("source_url"))
    if cik is None:
        for e in entries:
            cik = cik_from_url(e.get("source_url"))
            if cik:
                break

    # ── Capex : fondation depuis EDGAR si absent de la base (ou refresh) ──────
    capex_source = "kb" if facts.get("capex") is not None else "absent"
    capex_point: Optional[dict[str, Any]] = None
    capex_tag_used: Optional[str] = None
    if (facts.get("capex") is None or refresh) and cik is not None:
        for tag in _CAPEX_TAGS:
            try:
                capex_point = await fetch_annual_value(cik, tag, period_end=facts["period_end"])
                capex_tag_used = tag
                facts["capex"] = capex_point["val"]
                capex_source = "edgar_fetched"
                break
            except EdgarUnavailable as e:
                logger.info("financials_feed %s : capex %s indisponible (%s)", ticker_id, tag, e)
        if capex_point is None and facts.get("capex") is None:
            capex_source = "edgar_unavailable"
    elif facts.get("capex") is None and cik is None:
        capex_source = "cik_introuvable"

    as_of = date.today()
    specs, unfounded = build_financials_entries(ticker_id, symbol, facts, as_of=as_of)

    created: list[dict[str, Any]] = []
    capex_entry: Optional[dict[str, Any]] = None
    if persist:
        async with get_db_session() as conn:
            async with conn.transaction():
                if capex_point is not None:
                    stored = await _persist_capex_fact(
                        conn, ticker_id, symbol, capex_point, currency=facts.get("currency") or "USD",
                        fiscal_period=facts.get("period"), source_url=facts.get("source_url"),
                        tag_used=capex_tag_used or _CAPEX_TAGS[0],
                    )
                    capex_entry = dict(stored) | {"metric": "capital_expenditure"}
                for spec in specs:
                    prev = await _current_tagged_entry_id(
                        conn, ticker_id, ["financials", spec.field, "derived_ratio"]
                    )
                    stored = await store_knowledge(
                        conn, ticker_id=ticker_id, entry_type=spec.entry_type, content=spec.content,
                        source_type=spec.source_type, title=spec.title,
                        content_structured=spec.content_structured, tags=spec.tags, lang="fr",
                        source_url=spec.source_url, source_date=facts.get("period_end"),
                        fiscal_period=spec.fiscal_period, supersedes_entry_id=prev,
                        covers=[f"financials.{spec.field}"],   # index 029 : chemin complet
                    )
                    created.append(dict(stored) | {"field": spec.field, "supersedes": prev})
        logger.info(
            "financials_feed %s (%s) → %d ratio(s) [%s] · capex=%s · non fondés: %s",
            ticker_id, symbol, len(created), ", ".join(f"{c['field']}#{c['id']}" for c in created),
            capex_source, ", ".join(u["field"] for u in unfounded) or "aucun",
        )

    return {
        "ticker_id": ticker_id,
        "symbol": symbol,
        "period": facts.get("period"),
        "as_of": as_of.isoformat(),
        "source_type": _SOURCE_TYPE,
        "capex_source": capex_source,
        "entries": [
            {
                "field": s.field, "title": s.title, "content": s.content,
                "content_structured": s.content_structured, "tags": s.tags,
                "source_type": s.source_type,
            }
            for s in specs
        ],
        "unfounded": unfounded,
        "capex_entry": capex_entry,
        "persisted": created,
        "dry_run": not persist,
    }
