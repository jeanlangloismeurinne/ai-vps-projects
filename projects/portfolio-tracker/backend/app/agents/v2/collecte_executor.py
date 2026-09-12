"""L'EXÉCUTEUR RÉEL du collecteur (chantier v3, lot 2c — le maillon réseau, #58).

`collecteur.aiguiller_plan` est une orchestration PURE à exécuteur INJECTÉ : elle éprouve la logique
d'aiguillage (trois états, question-aveuglement, couverture = sous-produit déterministe) sans réseau,
avec un exécuteur factice. Ce module fournit l'exécuteur RÉEL — celui qui touche EDGAR et le
search-worker — et le branche sur `aiguiller_plan` **SANS le modifier** :

  · `aiguiller_plan` reste sync, sans IO, et appelle `collecter(ligne)` une fois par ligne `traduit` ;
  · on PRÉ-EXÉCUTE chaque ligne aveugle DISTINCTE (une passe async, réseau), puis on injecte dans
    `aiguiller_plan` une fonction de LOOKUP sync. La frontière réseau vit donc ici, entière, et la
    logique d'aiguillage reste la fonction pure déjà éprouvée (`feedback_frontiere_gratuite...`).

Pré-exécuter par LIGNE AVEUGLE distincte (et non par ligne de plan) n'est pas qu'une économie : deux
ingrédients qui demandent EXACTEMENT la même chose (même métrique, même source, même ancre) sont
collectés une fois, et l'aiguilleur rattache l'unique entry à leurs DEUX couples (question,
ingrédient) — ce qui est la bonne sémantique (`question_coverage` en `ON CONFLICT DO NOTHING`).

DISPATCH, ET POURQUOI IL EST AVEUGLE (#58) : le collecteur ne voit qu'une `LigneAveugle`. Il route
sur la `source_pressentie` (+ la métrique) :
  · un dépôt réglementaire (10-K/10-Q/…) DONT la métrique correspond à l'un des 8 POSTES du socle
    EDGAR → chemin EDGAR (déterministe, tier A, zéro modèle). Le lien pointe vers l'entry du socle ;
  · tout le reste → search-worker (web), qui CHERCHE sans jamais connaître la question. L'entry qu'il
    écrit ne peut donc porter aucun vocabulaire de framework (principe 2, structurel).

TROIS ÉTATS, JAMAIS UN SILENCE (#25/#44) — une collecte qui ne rend rien est un `echec` MOTIVÉ, que
l'aiguilleur transforme en mandat `echec_collecte`, jamais une entry vide ni un `entry_id` inventé :
  · EDGAR : poste non fondé (aucun concept XBRL exploitable) → `echec` ;
  · EDGAR indisponible (ticker privé / sans symbole) → `echec` sur toutes ses lignes EDGAR ;
  · web : recherche non configurée (`SearchUnavailable`) ou `status=not_found` → `echec` ;
  · web : un `entry_type` mal deviné fait REJETER les entries par le worker (une entry du mauvais
    type répond à une autre question) → `status` sans entry → `echec`. Le mauvais pari coûte un
    appel, jamais une donnée hors mandat ni un faux vert.

LE COLLECTEUR NE JUGE PAS LA VALEUR D'UNE SOURCE (#59) : la requête web part avec un plancher de
fiabilité PERMISSIF (0.40, le plancher `llm_memory`). Exiger un tier ici serait « combien de preuve
suffit ? », une question du FRAMEWORK et de lui seul — c'est le manager (lot 4) qui tranchera la
suffisance, pas l'ouvrier qui ramène la matière.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Collection
from typing import Any, Literal, Optional

import asyncpg

from app.agents.v2.collecteur import (
    LigneAveugle,
    ResultatAiguillage,
    ResultatCollecte,
    aiguiller_plan,
    ligne_aveugle,
)
from app.agents.v2.traducteur import traduire
from app.agents.v2.worker import WORKER_NAME, persist_worker_entries, run_search_worker
from app.contracts.collection_plan_schema import CollectionPlan
from app.contracts.worker_delegation_schema import EntryType, OutputSchema, WorkerRequest
from app.db.database import get_db_session
from app.knowledge.edgar_feed import POSTES, EdgarFeedUnavailable, run_edgar_feed
from app.knowledge.websearch import SearchUnavailable

from .collecte_persist import persist_aiguillage, persist_plan

logger = logging.getLogger(__name__)

__all__ = [
    "router_source",
    "poste_pour_metrique",
    "entry_type_pour_metrique",
    "construire_requete_web",
    "collecter_un",
    "postes_edgar_du_plan",
    "executer_plan_reel",
    "executer_collecte_framework",
]


# ─────────────────────────── frontière DÉTERMINISTE (pure, hors réseau) ───────────────────────────

def _norm(s: str) -> str:
    """Minuscule sans accents, apostrophes → espace — pour comparer « Chiffre d'affaires » à
    « chiffre d affaires ». Les TIRETS sont conservés : `_FORME_SEC` lit « 10-k » (dash optionnel)."""
    sans_accent = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    for apo in ("'", "’", "ʼ", "`"):  # droite, typographique, modificatrice, accent grave
        sans_accent = sans_accent.replace(apo, " ")
    return " ".join(sans_accent.lower().split())


# Formes de dépôts réglementaires SEC : 10-K, 10-Q, 8-K, 6-K, 20-F, 40-F (tiret optionnel). On NE
# détecte PAS « communiqué », « call », « transcript », « presse », « site », « données de marché »
# — tout cela part au web. `\bsec\b`/`\bedgar\b` en mots pleins (jamais « second », « secteur »).
_FORME_SEC = re.compile(r"\b(?:10|8|6|20|40)-?[kqf]\b|\bedgar\b|\bsec\b")

# Alias par POSTE, en forme normalisée (sans accents). DÉTENTEUR de la correspondance métrique→poste ;
# l'ENSEMBLE des postes, lui, est importé de `edgar_feed.POSTES` (#46 : un seul détenteur du socle —
# un assert positif du check vérifie que ce tableau couvre EXACTEMENT les 8 metric de POSTES).
_ALIAS_POSTE: dict[str, tuple[str, ...]] = {
    "revenue": ("chiffre d affaires", "revenu", "revenue", "revenues",
                "sales", "ventes", "turnover", "produit des activites"),
    "net_income": ("resultat net", "benefice net", "net income", "profit net", "perte nette",
                   "resultat de l exercice"),
    "gross_profit": ("marge brute", "gross profit", "gross margin", "benefice brut"),
    "operating_cash_flow": ("cash-flow operationnel", "cash flow operationnel",
                            "flux de tresorerie operationnel", "operating cash flow",
                            "tresorerie generee par l exploitation", "tresorerie d exploitation",
                            "flux de tresorerie lies a l exploitation"),
    "total_assets": ("total actif", "total des actifs", "actif total", "total assets",
                     "total de l actif"),
    "capital_expenditure": ("capex", "capital expenditure", "depenses d investissement",
                            "investissements corporels", "acquisitions d immobilisations"),
    "stockholders_equity": ("capitaux propres", "fonds propres", "stockholders equity",
                            "shareholders equity", "total equity"),
    "cash_and_lt_debt": ("tresorerie et dette", "dette long terme", "dette a long terme",
                         "long term debt", "endettement", "cash and debt", "dette financiere"),
}

# Un poste du socle est un NIVEAU BRUT (« Net income (GAAP) »). Une métrique qui CONTIENT le nom d'un
# poste peut pourtant en être une transformation — et la lier au nombre brut écrirait un lien vers le
# MAUVAIS nombre (#43, « tous les nombres justes, le fait faux »). Mesuré sur le plan réel NVDA : sur
# 6 lignes routées EDGAR, 5 étaient des dérivées (capital employé = actifs − trésorerie − passifs ;
# croissance du CA ; maintenance/growth capex ; rapprochement GAAP/non-GAAP). D'où deux familles de
# marqueurs qui forcent None → web : (a) des OPÉRATEURS (la métrique est un calcul) ; (b) des
# métriques nommées qui sont des ratios/taux/variations connus. Au moindre doute → None : une manque
# (niveau brut parti au web) est sûr, un faux match EDGAR est une corruption silencieuse.
# (a) OPÉRATEURS : la métrique est une EXPRESSION (un calcul), pas un poste. Recherche par substring
# (ce sont des symboles, pas des mots). « Total assets − cash − ... » porte le « − » (U+2212).
_OPERATEURS_DERIVATION = ("−", " - ", " / ", " + ", " x ")
# (b) MOTS de transformation (ratios, taux, variations, rapprochements). Recherche à la FRONTIÈRE DE
# MOT : « ratio » ne doit PAS matcher « opéRATIOnnel » (faux positif mesuré), ni « net » matcher
# « Net income ». Un poste est un NIVEAU brut ; ces mots en signalent une dérivée.
_MOTS_DERIVATION = (
    "minus", "moins", "net of", "net des",
    "free cash flow", "fcf", "flux de tresorerie disponible", "tresorerie disponible",
    "roic", "roce", "rentabilite du capital", "retour sur capital", "wacc", "cout du capital",
    "levier", "endettement net", "net debt", "dette nette", "besoin en fonds de roulement",
    "croissance", "growth", "cagr", "taux de croissance", "variation", "change in",
    "maintenance", "estimation", "reconciliation", "rapprochement", "reconcil",
    "ratio", "coverage", "couverture", "adjusted", "ajuste", "conversion", "burn", "runway",
    "marge operationnelle", "decomposition", "vs", "versus", "comparaison", "comparable",
)
_RE_MOTS_DERIVATION = re.compile(
    r"\b(?:" + "|".join(re.escape(m) for m in _MOTS_DERIVATION) + r")\b")


def _est_derivee(n: str) -> bool:
    """Vrai si la métrique normalisée `n` est une TRANSFORMATION (expression ou ratio/taux/variation)
    plutôt qu'un niveau brut — auquel cas elle ne peut pas se lier à un poste du socle (#43)."""
    return any(op in n for op in _OPERATEURS_DERIVATION) or bool(_RE_MOTS_DERIVATION.search(n))


def poste_pour_metrique(metrique: str) -> Optional[str]:
    """La métrique (vocabulaire de l'entreprise, texte libre) correspond-elle à l'un des 8 POSTES du
    socle EDGAR ? Rend le `metric` canonique, ou None. CONSERVATEUR par conception : au moindre doute
    (métrique dérivée, formulation inconnue) → None, jamais un poste deviné — un faux match EDGAR est
    une corruption silencieuse (lien vers le mauvais nombre), un None route simplement vers le web."""
    n = _norm(metrique)
    if _est_derivee(n):
        return None
    for metric, alias in _ALIAS_POSTE.items():
        if any(a in n for a in alias):
            return metric
    return None


def router_source(source_pressentie: str, metrique: str) -> Literal["edgar", "web"]:
    """Où exécuter cette ligne aveugle. EDGAR SEULEMENT si (a) la source pressentie nomme un dépôt
    réglementaire ET (b) la métrique correspond à un poste du socle. Les deux conditions, parce qu'un
    « 10-K » pour une métrique dérivée (free cash flow) n'est pas dans le socle, et une métrique de
    poste citée depuis un « communiqué » se cherche quand même au web. Tout le reste → web."""
    if _FORME_SEC.search(_norm(source_pressentie)) and poste_pour_metrique(metrique) is not None:
        return "edgar"
    return "web"


# Jetons financiers : une métrique chiffrable → `fact_financial`. Sinon `fact_qualitative`. Un mauvais
# pari n'écrit rien de faux (le worker rejette l'entry du mauvais type → echec → mandat), il coûte au
# pire un appel. On ne tente pas `fact_statistical` (taux de base) : il relève d'un producteur dédié.
_JETONS_FINANCIERS = (
    "chiffre d affaires", "revenu", "revenue", "sales", "ventes", "resultat", "benefice", "profit",
    "perte", "marge", "cash flow", "cash-flow", "tresorerie", "capex", "investissement", "actif",
    "passif", "capitaux propres", "fonds propres", "dette", "endettement", "ebitda", "ebit",
    "free cash flow", "fcf", "burn", "runway", "roic", "roce", "wacc", "levier", "multiple",
    "valorisation", "per", "price", "cours", "dividende", "montant", "usd", "eur", "milliard",
    "million", "ratio", "taux",
)


def entry_type_pour_metrique(metrique: str) -> EntryType:
    """Type d'entry attendu par le worker pour cette métrique (il REJETTE tout autre type, #web).
    Heuristique : jeton financier → `fact_financial`, sinon `fact_qualitative`. Le worker étant
    aveugle à la question, c'est la seule indication disponible ; un faux pari dégrade en mandat."""
    n = _norm(metrique)
    if any(j in n for j in _JETONS_FINANCIERS):
        return "fact_financial"
    return "fact_qualitative"


def construire_requete_web(ligne: LigneAveugle) -> WorkerRequest:
    """Construit la requête du search-worker depuis la ligne AVEUGLE — sans jamais nommer la question.

    `requester='knowledge-curator'` : le collecteur s'exécute dans le flux de constitution de
    connaissance (le `Requester` est de la traçabilité pure, sans consommateur en aval — réutiliser
    le plus proche évite une modification de contrat fermé pour un champ décoratif).
    `reliability_min=0.40` : plancher permissif — le collecteur ne juge pas la valeur d'une source
    (#59), il ramène la matière ; la suffisance est jugée plus tard par le manager du framework."""
    return WorkerRequest(
        requester="knowledge-curator",
        worker=WORKER_NAME,
        ticker_id=ligne.ticker_id,
        query=(
            f"Pour l'entreprise {ligne.ticker_id}, trouve la donnée suivante : {ligne.metrique}. "
            f"Cherche en priorité dans : {ligne.source_pressentie}. "
            f"Date le fait par rapport à l'événement : {ligne.ancre}."
        ),
        output_schema=OutputSchema(entry_type=entry_type_pour_metrique(ligne.metrique)),
        reliability_min=0.40,
        max_entries=3,
    )


# ─────────────────────────────── exécuteur RÉEL (async, réseau + DB) ───────────────────────────────

class _SocleEdgar:
    """Mémoïse le socle EDGAR d'un ticker sur la durée d'UN aiguillage : on ne rejoue pas la collecte
    à chaque ligne EDGAR. Trois états possibles par ticker (jamais deux confondus, #25) : un dict
    {metric → entry_id} des postes fondés, OU un motif d'indisponibilité (ticker sans symbole).

    ⚠️ On ne collecte QUE les postes RÉCLAMÉS par le plan (`metrics`, maillon 5 / §3.6) — la collecte
    data-first des 8 postes en bloc a disparu. Un poste que nul plan ne réclame n'est jamais interrogé
    chez EDGAR."""

    def __init__(self, metrics: Collection[str]) -> None:
        self._metrics = frozenset(metrics)
        self._par_ticker: dict[str, dict[str, int]] = {}
        self._indispo: dict[str, str] = {}

    async def entry_id(self, ticker_id: str, poste_metric: str) -> ResultatCollecte:
        if ticker_id not in self._par_ticker and ticker_id not in self._indispo:
            await self._collecter(ticker_id)
        if ticker_id in self._indispo:
            return ResultatCollecte(echec=self._indispo[ticker_id])
        par_metric = self._par_ticker[ticker_id]
        entry_id = par_metric.get(poste_metric)
        if entry_id is None:
            return ResultatCollecte(
                echec=f"poste EDGAR '{poste_metric}' non fondé pour {ticker_id} "
                      "(aucun concept XBRL exploitable dans les dépôts)")
        return ResultatCollecte(entry_id=entry_id)

    async def _collecter(self, ticker_id: str) -> None:
        try:
            res = await run_edgar_feed(ticker_id, persist=True, metrics=self._metrics)
        except EdgarFeedUnavailable as e:
            self._indispo[ticker_id] = f"socle EDGAR indisponible pour {ticker_id} : {e}"
            return
        # `created` ne porte que les postes effectivement fondés+écrits (les absents sont en
        # `unfounded`, qu'on laisse retomber sur le « poste non fondé » ci-dessus).
        self._par_ticker[ticker_id] = {c["metric"]: c["id"] for c in res.get("created", [])}


async def collecter_un(
    ligne: LigneAveugle, *, conn: asyncpg.Connection, socle: _SocleEdgar
) -> ResultatCollecte:
    """Exécute UNE ligne aveugle. Dispatch déterministe, puis réseau. Rend un XOR (entry OU echec),
    jamais un silence (#25) : c'est `aiguiller_plan` qui transformera un echec en mandat motivé."""
    if router_source(ligne.source_pressentie, ligne.metrique) == "edgar":
        poste = poste_pour_metrique(ligne.metrique)
        assert poste is not None  # garanti par router_source
        return await socle.entry_id(ligne.ticker_id, poste)

    # chemin web : le search-worker CHERCHE (sans connaître la question), puis on persiste ses entries.
    req = construire_requete_web(ligne)
    try:
        exchange = await run_search_worker(req)
    except SearchUnavailable as e:
        return ResultatCollecte(echec=f"recherche web indisponible : {e}")
    except Exception as e:  # timeout fournisseur / sortie non conforme / réseau → #25, jamais un crash
        # Une collecte qui ÉCHOUE pour QUELQUE raison que ce soit devient un mandat MOTIVÉ (cause
        # nommée), jamais une exception qui fait perdre tout le lot et empêche de persister les liens
        # déjà acquis. Le plan est persisté et la couverture est idempotente : la ligne se re-collecte
        # à un prochain run. Portée au SEUL `run_search_worker` (appel externe, modèle/recherche) — un
        # bug de dispatch en amont, lui, continue de remonter, jamais masqué en mandat.
        return ResultatCollecte(echec=f"collecte web échouée ({type(e).__name__}) : {e}")
    if exchange.response.status == "not_found" or not exchange.response.entries:
        return ResultatCollecte(
            echec=f"search-worker n'a rien retenu pour « {ligne.metrique} » "
                  f"(status={exchange.response.status})")
    async with conn.transaction():
        created = await persist_worker_entries(conn, exchange)
    if not created:
        return ResultatCollecte(
            echec=f"search-worker: aucune entry persistée pour « {ligne.metrique} »")
    # Une ligne → un lien. Le worker peut retenir plusieurs entries (Pareto) ; elles entrent toutes au
    # corpus, mais la couverture de CET ingrédient est adossée à la première (la mieux classée).
    return ResultatCollecte(entry_id=created[0]["id"])


def postes_edgar_du_plan(plan: CollectionPlan) -> frozenset[str]:
    """Les postes du socle EDGAR que CE plan réclame (maillon 5 / §3.6) : l'union des postes canoniques
    des lignes traduites routées vers EDGAR. C'est exactement ce que le socle collectera — « un poste
    que nul plan ne réclame ne se collecte plus ». Détenteur unique du dispatch : `router_source` +
    `poste_pour_metrique`, jamais une seconde liste (#46)."""
    postes: set[str] = set()
    for item in plan.items:
        if item.statut != "traduit":
            continue
        ligne = ligne_aveugle(item, plan.ticker_id)
        if router_source(ligne.source_pressentie, ligne.metrique) == "edgar":
            poste = poste_pour_metrique(ligne.metrique)
            assert poste is not None  # garanti par router_source
            postes.add(poste)
    return frozenset(postes)


async def executer_plan_reel(
    plan: CollectionPlan, *, conn: asyncpg.Connection
) -> ResultatAiguillage:
    """Exécute un plan RÉELLEMENT (EDGAR + web), puis aiguille. `aiguiller_plan` reste intact : on
    pré-exécute chaque ligne aveugle distincte, puis on lui injecte un lookup sync.

    Le socle EDGAR ne collecte que les postes RÉCLAMÉS par ce plan (`postes_edgar_du_plan`) : la
    collecte data-first des 8 postes en bloc a disparu avec le maillon 5 (§3.6)."""
    socle = _SocleEdgar(postes_edgar_du_plan(plan))
    resultats: dict[tuple[str, str, str, str], ResultatCollecte] = {}
    for item in plan.items:
        if item.statut != "traduit":
            continue  # `inobtenable` : aucune collecte, aiguiller_plan en fera un mandat
        ligne = ligne_aveugle(item, plan.ticker_id)
        cle = (ligne.ticker_id, ligne.metrique, ligne.source_pressentie, ligne.ancre)
        if cle in resultats:
            continue  # même ligne aveugle déjà collectée (deux ingrédients, une collecte)
        resultats[cle] = await collecter_un(ligne, conn=conn, socle=socle)

    def collecter(ligne: LigneAveugle) -> ResultatCollecte:
        cle = (ligne.ticker_id, ligne.metrique, ligne.source_pressentie, ligne.ancre)
        try:
            return resultats[cle]
        except KeyError:  # défensif : aiguiller_plan n'appelle `collecter` que sur des lignes traduites
            raise RuntimeError(f"ligne aveugle non pré-exécutée : {cle!r}")

    return aiguiller_plan(plan, collecter=collecter)


async def executer_collecte_framework(
    ticker_id: str, framework_id: str, archetype: str,
) -> dict[str, Any]:
    """Chaîne RUNTIME de bout en bout (spec §3.6) : traduire → persister le plan → collecter →
    persister liens + mandats. Le plan est persisté AVANT la collecte, pour que « mauvais plan ou
    mauvaise collecte ? » reste diagnosticable même si la collecte échoue en route (§3.6).

    ⚠️ Écritures PROD (knowledge_entries via les producteurs, collection_plans / question_coverage /
    framework_mandates) + dépense réseau (modèle traducteur, appels search-worker par ligne web).
    """
    run, plan = await traduire(ticker_id, framework_id, archetype)  # modèle + contrat + pont

    async with get_db_session() as conn:
        async with conn.transaction():
            plan_id = await persist_plan(conn, plan)

    async with get_db_session() as conn:
        result = await executer_plan_reel(plan, conn=conn)  # réseau + écritures d'entries
        async with conn.transaction():
            ecrits = await persist_aiguillage(conn, result, plan_id=plan_id)

    logger.info(
        "collecte %s/%s (%s) : plan #%d · %d ligne(s) · %d lien(s) · %d mandat(s)",
        ticker_id, framework_id, archetype, plan_id, result.lignes_vues,
        len(result.liens), len(result.mandats),
    )
    return {
        "ticker_id": ticker_id,
        "framework_id": framework_id,
        "framework_version": plan.framework_version,
        "archetype": archetype,
        "plan_id": plan_id,
        "lignes_vues": result.lignes_vues,
        "liens": [l.model_dump() for l in result.liens],
        "mandats": [m.model_dump() for m in result.mandats],
        "ecrits": ecrits,
        "traducteur_cost_usd": getattr(run, "cost_usd", None),
    }
