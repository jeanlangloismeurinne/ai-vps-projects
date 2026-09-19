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

import asyncio
import logging
import re
import unicodedata
from collections.abc import Collection
from typing import Any, Literal, NamedTuple, Optional

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
from app.config import settings
from app.contracts.worker_delegation_schema import EntryType, OutputSchema, WorkerRequest
from app.db.database import get_db_session
from app.knowledge.appariement_feed import (
    AppariementInexecutable,
    ConsigneAppariement,
    executer_appariement,
)
from app.knowledge.edgar_facts import EdgarUnavailable, fetch_company_facts
from app.knowledge.edgar_feed import (
    POSTES,
    EdgarFeedUnavailable,
    resolve_cik,
    run_edgar_feed,
    symbole_de_marche,
)
from app.knowledge.websearch import SearchUnavailable

from .appariement_persist import lire_carte, persister_carte
from .apparieur import (
    AppariementRefuse,
    AppariementSansObjet,
    apparier,
    dernier_depot_vu,
)
from .collecte_persist import persist_aiguillage, persist_plan

logger = logging.getLogger(__name__)

__all__ = [
    "router_source",
    "poste_retenu",
    "entry_type_pour_metrique",
    "construire_requete_web",
    "collecter_un",
    "postes_edgar_du_plan",
    "CarteCourante",
    "InventaireTicker",
    "assurer_carte",
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

# L'ENSEMBLE des postes vient de `edgar_feed.POSTES`, détenteur unique du socle (#46).
_TOUS_POSTES = frozenset(p.metric for p in POSTES)

# ⚠️ CE QUI A ÉTÉ SUPPRIMÉ ICI, ET POURQUOI (2026-09-14, lot 3 maillon 4).
# Une table `_ALIAS_POSTE` associait à chaque poste une liste de SOUS-CHAÎNES (« ventes », « dette à
# long terme », « capex »…), cherchées dans la `metrique` du plan. Elle a été mesurée sur les 3 plans
# réels de `qualite_financiere` : sur 7 lignes routées vers EDGAR, **5 l'étaient à tort** —
#
#   · « clauses de sauvegarde en cas de cession d'actifs »      → `revenue`   (« ventes »)
#   · « charges fixes décaissables, hors dépenses
#      d'investissement minimales »                             → `capex`     (dans une énumération)
#   · « capex de maintien (estimation) »                        → `capex`     (≠ capex total)
#   · « capex de croissance »                                   → `capex`     (≠ capex total)
#   · « dette à court terme, incluant la part courante
#      de la dette à long terme »                               → `cash_and_lt_debt`
#
# Les 2 appariements JUSTES étaient exactement les 2 réponses à nom court (« Net income (GAAP) »).
# Le défaut n'était donc pas dans la liste d'alias — il était dans l'idée de chercher un nom de compte
# dans une phrase écrite pour un humain. Aiguiser la table aurait déplacé les faux positifs, pas
# supprimé la classe : c'est une règle recopiée qui re-diverge au correctif suivant
# (`feedback_correctif_regle_jumeaux`).
#
# Désormais le traducteur NOMME le poste (`CollectionPlanItem.poste`, vocabulaire fermé) et l'aval
# ne fait qu'une ÉGALITÉ. Un poste inconnu du catalogue ne lève pas : il route au web, le défaut sûr
# (#60). La garde `_est_derivee` ci-dessous, elle, RESTE — elle est le seul contrôle déterministe
# qui survit au fait que le poste soit nommé par un modèle.

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


def poste_retenu(poste: Optional[str], metrique: str) -> Optional[str]:
    """Le poste du socle EDGAR à interroger pour cette ligne — ou None, qui route au web.

    Le poste n'est plus DEVINÉ depuis la métrique : il est NOMMÉ par le traducteur, dans le
    vocabulaire fermé `edgar_feed.POSTES`, et persisté avec le plan. Cette fonction ne fait donc plus
    d'appariement ; elle fait deux VÉTOS déterministes sur ce que le modèle a nommé :

      1. le poste doit EXISTER au catalogue. Un poste inventé (`ebitda`, `free_cash_flow`) route au
         web au lieu de lever : une manque coûte un appel web, un faux appariement corrompt (#60) ;
      2. la métrique ne doit pas être une DÉRIVÉE. C'est le garde-fou qui survit au fait que le poste
         soit choisi par un modèle : « capex de maintien (estimation) » a beau désigner du capex, ce
         n'est PAS le capex déposé — le lier au nombre brut écrirait le bon libellé en face du mauvais
         nombre (#43). Le véto est déterministe, donc il ne peut pas être desserré par un prompt (#59).

    Le véto 2 est volontairement plus large que le besoin : il retient aussi des lignes qu'un poste
    fonderait peut-être. C'est le sens du conservatisme — on préfère payer une recherche web qu'écrire
    un lien de couverture vers un nombre qui répond à une autre question.
    """
    if not poste or poste not in _TOUS_POSTES:
        if poste:
            logger.warning(
                "poste « %s » hors du catalogue EDGAR (%d postes) — ligne routée au web. "
                "C'est un défaut du traducteur, pas un cas nominal : son prompt énumère le "
                "vocabulaire fermé.", poste, len(_TOUS_POSTES))
        return None
    if _est_derivee(_norm(metrique)):
        logger.info(
            "poste « %s » nommé pour une métrique DÉRIVÉE (« %s ») — ligne routée au web : un poste "
            "est un niveau brut, pas son transformé (#43).", poste, metrique)
        return None
    return poste


def router_source(
    ligne: LigneAveugle,
    *,
    carte_statut: Optional[Literal["exact", "approximation", "indisponible"]] = None,
) -> Literal["edgar", "web"]:
    """Où exécuter cette ligne aveugle.

    AVEC CARTE (`carte_statut` non None — câblage lot 3 maillon 4bis) :
      · `indisponible` → web immédiatement, quel que soit le poste ou la source.
      · `exact` / `approximation` → edgar SI la source pressentie nomme un dépôt réglementaire.
        La vérification de source (b) est conservée : un appariement valide sur un inventaire EDGAR
        ne change pas le fait qu'un agrégat ajusté du « communiqué trimestriel » porte parfois le
        même nom que le poste GAAP — la source que le traducteur a nommée reste le tiebreaker.
        Le véto `poste_retenu()` est COURT-CIRCUITÉ : la carte a déjà décidé que le concept existe.

    SANS CARTE (repli, `carte_statut=None`) :
      EDGAR SEULEMENT si (a) le traducteur a nommé un poste du catalogue qui survit aux vétos,
      ET (b) la source pressentie nomme un dépôt réglementaire.

    La condition (b) SURVIT à l'enrichissement du catalogue, et ce n'est pas une inertie : un poste
    cité depuis un « communiqué trimestriel » ou un « call » n'est pas forcément le poste DÉPOSÉ —
    les entreprises y publient des agrégats ajustés qui portent le même nom. Aller quand même chez
    EDGAR livrerait le chiffre GAAP en réponse à une question posée sur le chiffre ajusté. Le
    collecteur ne juge pas la VALEUR d'une source (#59), mais il respecte celle que le plan a nommée.
    """
    if not _FORME_SEC.search(_norm(ligne.source_pressentie)):
        return "web"
    if carte_statut is not None:
        # La carte a déjà décidé : `indisponible` → web ; `exact`/`approximation` → edgar.
        # Le véto `poste_retenu()` est court-circuité — le concept existe dans l'inventaire.
        return "web" if carte_statut == "indisponible" else "edgar"
    return "edgar" if poste_retenu(ligne.poste, ligne.metrique) is not None else "web"


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
    ligne: LigneAveugle,
    *,
    conn: asyncpg.Connection,
    socle: _SocleEdgar,
    carte_statut: Optional[Literal["exact", "approximation", "indisponible"]] = None,
    consigne: Optional[ConsigneAppariement] = None,
    inventaire: Optional[InventaireTicker] = None,
) -> ResultatCollecte:
    """Exécute UNE ligne aveugle. Dispatch déterministe, puis réseau. Rend un XOR (entry OU echec),
    jamais un silence (#25) : c'est `aiguiller_plan` qui transformera un echec en mandat motivé.

    `carte_statut` (fourni par `executer_plan_reel`, jamais par `LigneAveugle` — #58) court-circuite
    `poste_retenu()` pour la décision EDGAR/web lorsque la carte l'a déjà tranché.

    TROIS chemins EDGAR, et le deuxième est ce que le maillon 4 ajoute (#72) :
      1. une RECETTE du catalogue (`poste_retenu` résout) → `_SocleEdgar`, inchangé ;
      2. sinon une CONSIGNE d'appariement (`exact` ou `approximation`) → `executer_appariement`,
         qui évalue l'expression sur l'inventaire DÉJÀ LU. C'est le cas NOMINAL d'une approximation :
         une formule sur des concepts XBRL nus n'a pas de recette, et jusqu'ici elle repartait au web
         chercher chez un tiers, en tier B, un nombre dont tous les termes étaient déposés en tier A ;
      3. ni l'un ni l'autre → repli web NOMMÉ, journalisé (le repli reste distinct du câblage réussi).

    ⚠️ L'ordre 1 avant 2 n'est pas un goût : une recette du catalogue choisit son concept par
    FRAÎCHEUR parmi des candidats (#30), ce qu'une expression figée ne fait pas. Doubler le chemin
    écrirait en plus deux entries actives pour le même fait (#43).

    ⚠️ Un appariement qui ne s'exécute pas devient un `echec` MOTIVÉ, donc un mandat — jamais un
    nombre approché, et jamais un repli web muet : la ligne repartant au web sans le dire ferait
    lire « le dépôt ne porte pas ce nombre » là où la cause est « l'ancre commune manque »."""
    route = router_source(ligne, carte_statut=carte_statut)
    if route == "edgar":
        poste = poste_retenu(ligne.poste, ligne.metrique)
        if poste is not None:
            return await socle.entry_id(ligne.ticker_id, poste)
        if consigne is not None and inventaire is not None:
            try:
                async with conn.transaction():
                    entry_id = await executer_appariement(
                        conn,
                        ticker_id=ligne.ticker_id,
                        symbole=inventaire.symbole,
                        cik=inventaire.cik,
                        libelle=ligne.metrique,
                        consigne=consigne,
                        facts=inventaire.facts,
                    )
            except AppariementInexecutable as e:
                return ResultatCollecte(
                    echec=f"appariement « {consigne.expression} » inexécutable sur le dépôt : {e}")
            except Exception as e:  # écriture/DB/contrat → #25, jamais un crash qui perd le lot
                return ResultatCollecte(
                    echec=f"appariement « {consigne.expression} » échoué "
                          f"({type(e).__name__}) : {e}")
            return ResultatCollecte(entry_id=entry_id)
        # Repli NOMMÉ : la carte a dit « edgar » mais il n'y a ni recette ni consigne exécutable
        # (carte absente, statut hérité de `poste_retenu` seul, ou inventaire injoignable).
        logger.info(
            "carte_statut=%s, poste_retenu()=None et %s pour « %s » — repli web (repli nommé)",
            carte_statut,
            "aucune consigne d'appariement" if consigne is None else "aucun inventaire en main",
            ligne.metrique,
        )

    # chemin web : le search-worker CHERCHE (sans connaître la question), puis on persiste ses entries.
    req = construire_requete_web(ligne)
    try:
        # Chien de garde par ligne (#25/#46) : `run_search_worker` peut enchaîner jusqu'à
        # `max_iterations` appels modèle à 720 s — une ligne bloquée figeait TOUTE la collecte (mesuré
        # >18 min sur RVMD). `wait_for` cap la ligne ENTIÈRE à `WEB_LINE_BUDGET_S` et ANNULE la
        # coroutine au dépassement (tous ses appels internes sont `await`, donc l'annulation les
        # traverse) ; comme la persistance a lieu APRÈS (plus bas), une ligne annulée n'écrit rien —
        # elle devient un mandat MOTIVÉ, jamais une entry partielle. Le garde borne la ligne SANS
        # imposer une signature aux appelants/substituts du worker : il n'y a qu'un détenteur du plafond.
        exchange = await asyncio.wait_for(
            run_search_worker(req), timeout=settings.WEB_LINE_BUDGET_S)
    except SearchUnavailable as e:
        return ResultatCollecte(echec=f"recherche web indisponible : {e}")
    except (asyncio.TimeoutError, TimeoutError):
        # Un blocage n'est pas une exception « naturelle » : sans ce garde il ne devient JAMAIS un
        # echec, il bloque. Le motif NOMME la cause (#25) pour que le mandat soit lisible.
        return ResultatCollecte(
            echec=f"collecte web abandonnée : budget de {settings.WEB_LINE_BUDGET_S} s dépassé "
                  f"pour « {ligne.metrique} » (ligne convertie en mandat, aucune donnée écrite)")
    except Exception as e:  # sortie non conforme / réseau → #25, jamais un crash
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


def postes_edgar_du_plan(
    plan: CollectionPlan,
    *,
    carte_statuts: Optional[dict[tuple[str, str], Literal["exact", "approximation", "indisponible"]]] = None,
) -> frozenset[str]:
    """Les postes du socle EDGAR que CE plan réclame (maillon 5 / §3.6) : l'union des postes canoniques
    des lignes traduites routées vers EDGAR. C'est exactement ce que le socle collectera — « un poste
    que nul plan ne réclame ne se collecte plus ». Détenteur unique du dispatch : `router_source` +
    `poste_retenu`, jamais une seconde liste (#46).

    `carte_statuts` (dict `(question_id, ingredient_id) → statut`) est fourni par `executer_plan_reel`
    lorsqu'une carte est disponible — il est transmis à `router_source` pour que les lignes `indisponible`
    soient exclues du socle EDGAR, même si leur source pressentie nomme un dépôt réglementaire."""
    postes: set[str] = set()
    for item in plan.items:
        if item.statut != "traduit":
            continue
        ligne = ligne_aveugle(item, plan.ticker_id)
        statut = carte_statuts.get((item.question_id, item.ingredient_id)) if carte_statuts else None
        if router_source(ligne, carte_statut=statut) == "edgar":
            poste = poste_retenu(ligne.poste, ligne.metrique)
            if poste is None:
                continue  # approximation sans poste catalogue : exclue du socle, partira au web
            postes.add(poste)
    return frozenset(postes)


# ────────────────────────── la carte d'appariement : la PRODUIRE, pas seulement la lire ──────────────
#
# CE QUI A CHANGÉ ICI, ET POURQUOI (2026-09-18, lot 3 — la garde #70 fermée par le haut).
#
# La version précédente ne faisait que LIRE la carte, avec une sentinelle qui avouait n'avoir aucune
# date de dépôt à lui opposer. L'aveu était juste ; ce qu'il ne disait pas, c'est que la table était
# VIDE — mesuré en base : 0 ligne dans `appariement_cartes`, 0 appelant de `persister_carte` en
# production (les checks écrivent en ROLLBACK), 0 appelant de `apparier()` hors d'un outil
# d'acceptation qui ne persiste rien. `lire_carte` renvoyait donc TOUJOURS None, et l'exécuteur
# retombait TOUJOURS sur `poste_retenu()` — celui-là même dont la mesure du 2026-09-14 a montré que
# 5 appariements sur 7 étaient faux. Un décideur sans producteur ne décide jamais : c'est la même
# famille que #70 (`feedback_controle_au_point_de_lecture`), un cran plus haut — non pas une garde
# nourrie de sa propre valeur, mais une garde qu'aucune donnée n'atteint.
#
# Le correctif ne muscle pas la garde, il lui donne une matière : l'exécuteur LIT L'INVENTAIRE
# (`fetch_company_facts`, gratuit, un appel) AVANT de router. Il en tire la date du dépôt courant par
# le détenteur unique qui existe déjà (`apparieur.dernier_depot_vu`, #46) — donc AUCUNE nouvelle
# règle de décision n'est introduite, et la date retenue est par construction celle de la dernière
# mise à jour de l'entrée EDGAR, qu'elle vienne d'un dépôt trimestriel ou d'un rectificatif ultérieur
# (c'est un `max(filed)` sur TOUT l'inventaire, jamais un `max(end)` : un 10-K/A peut AJOUTER des
# concepts sans déplacer la clôture).
#
# La branche « périmée » de `lire_carte` devient alors ATTEIGNABLE, et ce qu'elle déclenche est une
# RECONSTRUCTION, pas un repli dégradé : une carte périmée est une carte à refaire, et l'inventaire
# qui a servi à la déclarer périmée est précisément celui qu'il faut pour la refaire.
#
# QUATRE ÉTATS NOMMÉS, JAMAIS UN SILENCE (#25/#44). Trois servent une carte, le quatrième est le
# repli :
#   · `fraiche`          — carte persistée, âge REVÉRIFIÉ contre une date mesurée. Zéro appel modèle.
#   · `reconstruite`     — absente ou périmée : `apparier()` + `persister_carte()`. Une dépense.
#   · `non_reverifiable` — inventaire injoignable : on sert la carte STOCKÉE en le DISANT. C'est le
#                          seul emploi légitime de `_SANS_REVERIFICATION`, et il est désormais
#                          l'exception (panne SEC) au lieu d'être le seul chemin.
#   · `aucune`           — ni inventaire ni carte : repli nommé sur `poste_retenu()`, journalisé.

# Plus petite que toute date ISO (« 0 » < « 1 »… < « 9 »), donc `dernier_depot_vu < depot_courant`
# est faux quelle que soit la carte. Ce n'est PAS une date par défaut : c'est l'aveu, écrit dans le
# code, que CE chemin-là n'a pas de dépôt courant à opposer. Une date plausible (`1970-01-01`, ou la
# date stockée elle-même) aurait eu le même effet en se lisant comme une mesure.
_SANS_REVERIFICATION = "0000-00-00 (aucune date de dépôt courante : âge non revérifié ici)"

EtatCarte = Literal["fraiche", "reconstruite", "non_reverifiable", "aucune"]


class InventaireTicker(NamedTuple):
    """L'inventaire XBRL lu UNE FOIS par `assurer_carte`, et de quoi en écrire la provenance.

    `facts` est le `companyfacts` complet (1 à 5 Mo, 269 à 627 concepts) : le RE-télécharger par
    ligne serait un appel réseau par ingrédient là où un seul suffit pour tout le plan. C'est ce qui
    rend l'exécution d'un appariement GRATUITE — la dépense a déjà eu lieu pour produire la carte.

    `symbole` vient de `tickers.ticker_symbol` (#11) et non de `tickers.id` ; `cik` en est résolu.
    Les deux ne servent qu'à la PROVENANCE du fait produit (titre, URL de dépôt) — aucun des deux
    n'entre dans une décision."""
    symbole: str
    cik: int
    facts: dict[str, list[dict[str, Any]]]


class CarteCourante(NamedTuple):
    """La carte dont dispose UNE exécution, et COMMENT elle a été obtenue.

    `etat` n'est pas de la décoration : sans lui, « carte servie parce qu'elle est à jour » et
    « carte servie parce qu'on n'a pas pu vérifier qu'elle l'est » sont indiscernables en aval — et
    c'est exactement la confusion que #70 a produite une fois. `depot_courant` est None quand
    l'inventaire n'a pas pu être lu : un None se lit comme une absence, une date recopiée se lirait
    comme une mesure.

    `consignes` et `inventaire` sont ce que le maillon 4 ajoute : le premier dit QUOI calculer, le
    second CONTRE QUOI. Les deux sont None quand la carte est servie sans inventaire en main
    (`non_reverifiable` sur panne SEC, `aucune`) — et `collecter_un` retombe alors sur le repli web
    NOMMÉ, jamais sur un calcul contre un inventaire qu'il aurait re-téléchargé pour l'occasion."""
    statuts: Optional[dict[tuple[str, str], Literal["exact", "approximation", "indisponible"]]]
    etat: EtatCarte
    depot_courant: Optional[str]
    cout_usd: float = 0.0
    consignes: Optional[dict[tuple[str, str], ConsigneAppariement]] = None
    inventaire: Optional[InventaireTicker] = None


def _statuts(carte) -> dict[tuple[str, str], Literal["exact", "approximation", "indisponible"]]:
    """`(question_id, ingredient_id) → statut`. Le COUPLE, jamais l'ingrédient nu : un même
    ingrédient peut exister sous deux questions (contrat `CollectionPlanItem`)."""
    return {(it.question_id, it.ingredient_id): it.statut for it in carte.items}


def _consignes(carte) -> dict[tuple[str, str], ConsigneAppariement]:
    """`(question_id, ingredient_id) → ConsigneAppariement`, pour les seules lignes EXÉCUTABLES.

    C'EST ICI QUE LE VOCABULAIRE DE FRAMEWORK S'ARRÊTE. La CLEF le porte — elle sert à retrouver la
    ligne du plan — mais la VALEUR ne le porte pas : une `ConsigneAppariement` n'a ni `question_id`
    ni `ingredient_id` ni `framework_id`. `collecter_un` ne reçoit que la valeur, donc il reste
    aussi aveugle qu'avec une `LigneAveugle` (#58), et le fait produit ne PEUT pas nommer la
    question. L'aveuglement est une propriété du type, pas une discipline d'écriture (#57).

    Un `exact` devient une expression à UN terme (le concept nu) : la grammaire l'admet tel quel, et
    cela évite une seconde branche d'évaluation dont la seule différence serait de ne rien calculer.
    Un `indisponible` n'a pas de consigne — c'est exactement là, et seulement là, que le web
    intervient (#67).
    """
    out: dict[tuple[str, str], ConsigneAppariement] = {}
    for it in carte.items:
        if it.statut == "exact":
            expression = str(it.concepts[0])      # le contrat garantit qu'il y en a exactement un
        elif it.statut == "approximation":
            expression = str(it.formule)          # le contrat garantit qu'elle est présente
        else:
            continue
        out[(it.question_id, it.ingredient_id)] = ConsigneAppariement(
            statut=it.statut,
            expression=expression,
            hypotheses=tuple(str(h) for h in it.hypotheses),
            deterministe=it.deterministe,
            termes_web=tuple(str(t) for t in it.termes_web),
        )
    return out


async def _servir_le_stock(
    conn: asyncpg.Connection, plan: CollectionPlan, *, motif: str,
    inventaire: Optional[InventaireTicker] = None,
) -> CarteCourante:
    """Dernier recours : servir la carte STOCKÉE sans pouvoir revérifier son âge, ou avouer qu'il n'y
    en a aucune. La sentinelle rend la comparaison `<` fausse par construction — on ne prétend pas
    revérifier, on sert ce qui est là et le log le dit.

    `inventaire` n'est fourni que lorsqu'on l'a RÉELLEMENT lu (le modèle apparieur a échoué, mais
    `companyfacts` était bien en main). Il est alors transmis : les consignes de la carte stockée
    restent exécutables, et renoncer à les exécuter enverrait au web des lignes dont tous les termes
    sont déposés. Sur une panne SEC il reste None — on ne calcule pas contre un inventaire absent."""
    try:
        carte = await lire_carte(
            conn,
            ticker_id=plan.ticker_id,
            framework_id=plan.framework_id,
            framework_version=plan.framework_version,
            depot_courant=_SANS_REVERIFICATION,
        )
    except Exception as e:
        logger.warning(
            "lecture carte %s/%s %s échouée (%s: %s) — repli sur poste_retenu() (repli nommé)",
            plan.ticker_id, plan.framework_id, plan.framework_version, type(e).__name__, e)
        return CarteCourante(None, "aucune", None)
    if carte is None:
        logger.info(
            "aucune carte d'appariement pour %s/%s %s (%s) — repli sur poste_retenu() (repli nommé)",
            plan.ticker_id, plan.framework_id, plan.framework_version, motif)
        return CarteCourante(None, "aucune", None)
    logger.warning(
        "carte %s/%s %s servie SANS revérification d'âge (%s) — %d ligne(s), depot_vu=%s : le "
        "verdict servi reste celui d'un dépôt réel, seulement peut-être plus ancien",
        plan.ticker_id, plan.framework_id, plan.framework_version, motif,
        len(carte.items), carte.dernier_depot_vu)
    return CarteCourante(_statuts(carte), "non_reverifiable", None,
                         consignes=_consignes(carte) if inventaire else None,
                         inventaire=inventaire)


async def assurer_carte(plan: CollectionPlan, *, conn: asyncpg.Connection) -> CarteCourante:
    """Rend la carte d'appariement de CE plan, à jour — en la RECONSTRUISANT si elle ne l'est pas.

    Ordre, et il n'est pas arbitraire : la frontière GRATUITE d'abord, la dépense ensuite (#63).
      1. `fetch_company_facts` — un appel réseau gratuit, AVANT tout routage et toute dépense modèle ;
      2. `dernier_depot_vu(facts)` — la date de la dernière mise à jour de l'entrée EDGAR, par le
         détenteur unique qui existe déjà (#46). Aucune règle de décision nouvelle n'est écrite ici ;
      3. `lire_carte(..., depot_courant=<cette date>)` — la revérification de #54 devient RÉELLE ;
      4. None (absente OU périmée) → `apparier()` sur LES MÊMES `facts`, puis `persister_carte()`.
         L'inventaire n'est lu qu'une fois et sert aux deux emplois.

    LIT LA CARTE UNE SEULE FOIS par exécution — jamais une requête par ligne (#61 transposé au réseau
    DB) — et n'appelle le modèle QUE si la carte manque ou a vieilli : une carte `fraiche` coûte zéro.

    ⚠️ DÉPENSE. Cette fonction peut appeler le modèle apparieur (≈ $0.001 par carte, deux tours au
    pire). C'est le prix d'une carte par (ticker × framework × version) et par dépôt, pas par
    exécution : l'UPSERT de `persister_carte` fait qu'une deuxième exécution sur le même dépôt relit.

    Aucun refus ne tue le lot : un `AppariementRefuse` (le modèle invente des noms de concepts deux
    fois de suite) ou un `AppariementSansObjet` (rien de traduit à apparier) retombe sur le stock,
    puis sur `poste_retenu()` — en le DISANT à chaque marche."""
    # ── (1) la frontière gratuite : l'inventaire réel, avant toute dépense ────────────────────────
    # ⚠️ Le symbole passe par `symbole_de_marche` (#11/#46) et non par `plan.ticker_id` : l'id peut
    # être `PUB-XXXXXXXX`. Résoudre le CIK depuis l'id ne marchait que tant que les deux coïncidaient.
    try:
        symbole = await symbole_de_marche(conn, plan.ticker_id)
        cik = await resolve_cik(symbole)
        facts = await fetch_company_facts(cik)
    except (EdgarFeedUnavailable, EdgarUnavailable) as e:
        return await _servir_le_stock(conn, plan, motif=f"inventaire EDGAR injoignable : {e}")
    inventaire = InventaireTicker(symbole=symbole, cik=cik, facts=facts)

    # ── (2) la date opposable — `max(filed)` sur TOUT l'inventaire, détenteur unique (#46) ────────
    try:
        depot_courant = dernier_depot_vu(facts)
    except AppariementSansObjet as e:
        return await _servir_le_stock(conn, plan, motif=f"inventaire non datable : {e}",
                                      inventaire=inventaire)

    # ── (3) la revérification d'âge, contre une date MESURÉE cette fois ───────────────────────────
    try:
        carte = await lire_carte(
            conn,
            ticker_id=plan.ticker_id,
            framework_id=plan.framework_id,
            framework_version=plan.framework_version,
            depot_courant=depot_courant,
        )
    except Exception as e:
        logger.warning(
            "lecture carte %s/%s %s échouée (%s: %s) — on tente la reconstruction",
            plan.ticker_id, plan.framework_id, plan.framework_version, type(e).__name__, e)
        carte = None
    if carte is not None:
        logger.info(
            "carte %s/%s %s FRAÎCHE — %d ligne(s), depot_vu=%s ≥ dépôt courant %s : aucun appel "
            "modèle", plan.ticker_id, plan.framework_id, plan.framework_version,
            len(carte.items), carte.dernier_depot_vu, depot_courant)
        return CarteCourante(_statuts(carte), "fraiche", depot_courant,
                             consignes=_consignes(carte), inventaire=inventaire)

    # ── (4) absente ou PÉRIMÉE → reconstruction sur le même inventaire, pas un repli dégradé ──────
    logger.info(
        "carte %s/%s %s absente ou périmée contre le dépôt du %s — reconstruction (%d concepts "
        "déposés)", plan.ticker_id, plan.framework_id, plan.framework_version,
        depot_courant, len(facts))
    try:
        res = await apparier(plan, facts)
    except AppariementSansObjet as e:
        return await _servir_le_stock(conn, plan, motif=f"rien à apparier dans ce plan : {e}",
                                      inventaire=inventaire)
    except AppariementRefuse as e:
        return await _servir_le_stock(conn, plan, motif=f"appariement REFUSÉ après réparation : {e}",
                                      inventaire=inventaire)
    except Exception as e:  # modèle indisponible / timeout / sortie non conforme → #25, jamais un crash
        return await _servir_le_stock(
            conn, plan, motif=f"appariement échoué ({type(e).__name__}) : {e}",
            inventaire=inventaire)
    row_id = await persister_carte(conn, res.carte)
    logger.info(
        "carte %s/%s %s RECONSTRUITE et persistée (#%d) — %d ligne(s), depot_vu=%s, "
        "%d réparation(s), $%.4f",
        plan.ticker_id, plan.framework_id, plan.framework_version, row_id,
        len(res.carte.items), res.carte.dernier_depot_vu, len(res.refus_repares),
        getattr(res.run, "cost_usd", 0.0) or 0.0)
    return CarteCourante(_statuts(res.carte), "reconstruite", depot_courant,
                         getattr(res.run, "cost_usd", 0.0) or 0.0,
                         consignes=_consignes(res.carte), inventaire=inventaire)


async def executer_plan_reel(
    plan: CollectionPlan, *, conn: asyncpg.Connection, carte: Optional[CarteCourante] = None,
) -> ResultatAiguillage:
    """Exécute un plan RÉELLEMENT (EDGAR + web), puis aiguille. `aiguiller_plan` reste intact : on
    pré-exécute chaque ligne aveugle distincte, puis on lui injecte un lookup sync.

    Le socle EDGAR ne collecte que les postes RÉCLAMÉS par ce plan (`postes_edgar_du_plan`) : la
    collecte data-first des 8 postes en bloc a disparu avec le maillon 5 (§3.6).

    CARTE D'APPARIEMENT (maillon 4bis) : obtenue UNE FOIS en début d'exécution (#61) par
    `assurer_carte` — produite si elle manque, reconstruite si elle a vieilli. Elle fournit le
    `carte_statut` de chaque ligne à `router_source` : le décideur réel devient la carte, et non plus
    `poste_retenu` seul. Le repli (`etat="aucune"`) est NOMMÉ et journalisé — sans ce log il serait
    indiscernable du câblage réussi, et il l'a été pendant tout le maillon 4bis.

    `carte` permet à un appelant qui en détient déjà une (ou qui veut explicitement n'en avoir
    aucune : `CarteCourante(None, "aucune", None)`) de court-circuiter la production, donc la
    dépense. Par défaut, l'exécuteur la PRODUIT — un décideur sans producteur ne décide jamais.

    EXÉCUTION DE L'APPARIEMENT (maillon 4, #72) : la carte ne fait plus que router, elle fournit
    aussi la CONSIGNE de chaque couple et l'INVENTAIRE contre lequel l'exécuter. Le chiffre à suivre
    est « lignes COLLECTÉES depuis le dépôt », jamais « lignes routées vers EDGAR » (#71) : il se
    lit sur l'état écrit (les entries taguées `appariement`), pas sur une intention de routage.

    ⚠️ La déduplication « deux ingrédients, une collecte » se fait sur la ligne AVEUGLE. Deux
    couples qui produisent la même ligne aveugle (même métrique, même source, même ancre) partagent
    donc aussi la consigne du premier — ce qui est cohérent : c'est la même demande, l'appariement
    ne peut pas légitimement en différer."""
    # ── Obtention de la carte : UNE fois, avant la boucle, et avant tout routage ─────────────────────
    if carte is None:
        carte = await assurer_carte(plan, conn=conn)
    carte_statuts = carte.statuts

    socle = _SocleEdgar(postes_edgar_du_plan(plan, carte_statuts=carte_statuts))
    resultats: dict[tuple[str, str, str, str], ResultatCollecte] = {}
    for item in plan.items:
        if item.statut != "traduit":
            continue  # `inobtenable` : aucune collecte, aiguiller_plan en fera un mandat
        ligne = ligne_aveugle(item, plan.ticker_id)
        cle = (ligne.ticker_id, ligne.metrique, ligne.source_pressentie, ligne.ancre)
        if cle in resultats:
            continue  # même ligne aveugle déjà collectée (deux ingrédients, une collecte)
        couple = (item.question_id, item.ingredient_id)
        statut = carte_statuts.get(couple) if carte_statuts else None
        # La consigne est résolue ICI, sur le couple, puis passée NUE : `collecter_un` ne reçoit
        # jamais le couple lui-même (#58 — voir `_consignes`).
        consigne = carte.consignes.get(couple) if carte.consignes else None
        resultats[cle] = await collecter_un(
            ligne, conn=conn, socle=socle, carte_statut=statut,
            consigne=consigne, inventaire=carte.inventaire)

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
    framework_mandates / appariement_cartes) + dépense réseau (modèle traducteur, modèle apparieur
    si la carte manque ou a vieilli, appels search-worker par ligne web).

    La carte est obtenue AVANT le routage et son état est REMONTÉ dans le compte rendu : « d'où
    venait la décision de routage » se lit sur le résultat, pas seulement dans un log.
    """
    run, plan = await traduire(ticker_id, framework_id, archetype)  # modèle + contrat + pont

    async with get_db_session() as conn:
        async with conn.transaction():
            plan_id = await persist_plan(conn, plan)

    async with get_db_session() as conn:
        carte = await assurer_carte(plan, conn=conn)         # inventaire + carte (modèle si besoin)
        result = await executer_plan_reel(plan, conn=conn, carte=carte)  # réseau + entries
        async with conn.transaction():
            ecrits = await persist_aiguillage(conn, result, plan_id=plan_id)

    logger.info(
        "collecte %s/%s (%s) : plan #%d · carte %s · %d ligne(s) · %d lien(s) · %d mandat(s)",
        ticker_id, framework_id, archetype, plan_id, carte.etat, result.lignes_vues,
        len(result.liens), len(result.mandats),
    )
    return {
        "ticker_id": ticker_id,
        "framework_id": framework_id,
        "framework_version": plan.framework_version,
        "archetype": archetype,
        "plan_id": plan_id,
        "carte_etat": carte.etat,
        "carte_depot_courant": carte.depot_courant,
        "carte_lignes": len(carte.statuts) if carte.statuts else 0,
        "lignes_vues": result.lignes_vues,
        "liens": [l.model_dump() for l in result.liens],
        "mandats": [m.model_dump() for m in result.mandats],
        "ecrits": ecrits,
        "traducteur_cost_usd": getattr(run, "cost_usd", None),
        "apparieur_cost_usd": carte.cout_usd,
    }
