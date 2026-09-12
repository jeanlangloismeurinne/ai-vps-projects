"""Vérification de la FRONTIÈRE DÉTERMINISTE de l'exécuteur réel (chantier v3, lot 2c —
`app/agents/v2/collecte_executor.py`).

Sans réseau ni modèle ni base. L'exécution réelle (EDGAR / search-worker) est hors de portée d'un
check hors ligne ; mais la CORRECTION vit dans la frontière déterministe — quelle source ? quel poste
EDGAR ? quel type d'entry ? quelle requête ? — et elle, on l'éprouve ici, entièrement.

  • §1 LE DISPATCH EST AVEUGLE ET CONSERVATEUR — EDGAR seulement si la source nomme un dépôt
       réglementaire ET la métrique correspond à un poste du socle ; au moindre doute → web.
  • §2 LA CORRESPONDANCE MÉTRIQUE→POSTE REFUSE LES MÉTRIQUES DÉRIVÉES — « free cash flow » n'est PAS
       le cash-flow opérationnel ; un faux match écrirait un lien vers le mauvais nombre (#43).
  • §3 DÉTENTEUR UNIQUE DU SOCLE (#46) — le tableau d'alias couvre EXACTEMENT les 8 `metric` de
       `edgar_feed.POSTES`, importés et non recopiés : un poste ajouté au socle sans alias se voit.
  • §4 LE TYPE D'ENTRY SE DÉDUIT DE LA MÉTRIQUE — un mauvais pari dégrade en mandat, jamais en donnée
       fausse ; mais le pari nominal doit être juste (financier → fact_financial).
  • §5 LA REQUÊTE WEB EST AVEUGLE À LA QUESTION ET NE JUGE PAS LA SOURCE (#59) — plancher permissif
       0.40, aucun `field_path` (qui ré-ancrerait la question), worker et ticker corrects.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
import sys

from app.agents.v2.collecteur import LigneAveugle
from app.agents.v2.collecte_executor import (
    construire_requete_web,
    entry_type_pour_metrique,
    poste_pour_metrique,
    postes_edgar_du_plan,
    router_source,
    _ALIAS_POSTE,
)
from app.contracts.collection_plan_schema import CollectionPlan, CollectionPlanItem
from app.knowledge.edgar_feed import POSTES

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


# ── §1 dispatch aveugle et conservateur ──────────────────────────────────────────────────────────
print("[1] le dispatch EDGAR exige source réglementaire ET poste du socle")
check("'10-Q' + 'chiffre d'affaires' → edgar",
      router_source("10-Q", "chiffre d'affaires") == "edgar",
      f"→ {router_source('10-Q', 'chiffre d''affaires')}")
check("'rapport annuel (10-K) EDGAR' + 'résultat net' → edgar",
      router_source("rapport annuel (10-K) EDGAR", "résultat net") == "edgar")
check("'communiqué + call trimestriel' + 'consommation de trésorerie' → web",
      router_source("communiqué + call trimestriel", "consommation de trésorerie trimestrielle") == "web")
check("'données de marché' + 'coût du capital (WACC)' → web",
      router_source("données de marché", "coût du capital (WACC)") == "web")
check("'10-K' + 'free cash flow' → web (dépôt SEC mais métrique DÉRIVÉE, pas un poste socle)",
      router_source("10-K", "free cash flow") == "web",
      f"→ {router_source('10-K', 'free cash flow')}")
check("'10-K (Income Statement)' + 'Net income (GAAP)' → edgar (niveau brut = poste socle)",
      router_source("10-K (Income Statement)", "Net income (GAAP)") == "edgar")
check("'10-K' + 'Croissance du chiffre d'affaires' → web (dérivée malgré le dépôt SEC)",
      router_source("10-K (données financières sélectionnées)", "Croissance du chiffre d'affaires (revenue) d'un exercice à l'autre") == "web")

# ── §2 correspondance métrique→poste, conservatrice ───────────────────────────────────────────────
print("\n[2] métrique→poste refuse les dérivées (un faux match = un lien vers le mauvais nombre)")
check("'Chiffre d'affaires' (accent/casse) → revenue",
      poste_pour_metrique("Chiffre d'affaires") == "revenue",
      f"→ {poste_pour_metrique('Chiffre d''affaires')}")
check("'capitaux propres' → stockholders_equity",
      poste_pour_metrique("capitaux propres") == "stockholders_equity")
check("'flux de trésorerie opérationnel' → operating_cash_flow",
      poste_pour_metrique("flux de trésorerie opérationnel") == "operating_cash_flow")
check("'free cash flow' → None (dérivé, surtout PAS operating_cash_flow)",
      poste_pour_metrique("free cash flow") is None,
      f"→ {poste_pour_metrique('free cash flow')}")
check("'conversion du chiffre d'affaires en trésorerie' → None — contient l'alias revenue, mais "
      "la garde prime sur l'alias (sinon un ratio dérivé serait lié au nombre brut, #43)",
      poste_pour_metrique("conversion du chiffre d'affaires en trésorerie") is None,
      f"→ {poste_pour_metrique('conversion du chiffre d''affaires en trésorerie')}")
# Les 5 faux matchs MESURÉS sur le plan réel NVDA (lus avant toute écriture) : chacun CONTIENT un
# alias de poste mais est une transformation → doit rendre None, surtout pas le nombre brut.
check("'Net income (GAAP)' → net_income (NIVEAU brut, lui, se lie au socle)",
      poste_pour_metrique("Net income (GAAP)") == "net_income",
      f"→ {poste_pour_metrique('Net income (GAAP)')}")
check("capital employé ('Total assets − cash − ...') → None (soustraction, pas total_assets brut)",
      poste_pour_metrique("Total assets − cash and marketable securities − non-interest-bearing current liabilities") is None)
check("'Croissance du chiffre d'affaires d'un exercice à l'autre' → None (growth, pas le CA brut)",
      poste_pour_metrique("Croissance du chiffre d'affaires (revenue) d'un exercice à l'autre") is None)
check("'Maintenance capex (estimation interne)' → None (split dérivé, pas le capex brut)",
      poste_pour_metrique("Maintenance capex (estimation interne)") is None)
check("'Reconciliation GAAP net income vs non-GAAP' → None (rapprochement, pas le résultat net brut)",
      poste_pour_metrique("Reconciliation GAAP net income vs non-GAAP net income (poste par poste)") is None)
check("'ROIC' → None (métrique dérivée)", poste_pour_metrique("ROIC") is None)
check("'coût du capital' → None (dérivé — WACC n'est pas un poste socle)",
      poste_pour_metrique("coût du capital") is None)
check("une formulation inconnue → None (pas de poste deviné)",
      poste_pour_metrique("part de marché sur le segment datacenter") is None)

# ── §3 détenteur unique du socle (#46) ────────────────────────────────────────────────────────────
print("\n[3] le tableau d'alias couvre EXACTEMENT les 8 postes de edgar_feed.POSTES (#46)")
metrics_socle = {p.metric for p in POSTES}
check("alias ⟺ POSTES : aucun poste sans alias, aucun alias orphelin",
      set(_ALIAS_POSTE) == metrics_socle,
      f"→ manquants={metrics_socle - set(_ALIAS_POSTE)} orphelins={set(_ALIAS_POSTE) - metrics_socle}")

# ── §4 type d'entry déduit de la métrique ─────────────────────────────────────────────────────────
print("\n[4] le type d'entry se déduit de la métrique (mauvais pari → mandat, jamais donnée fausse)")
check("'chiffre d'affaires' → fact_financial",
      entry_type_pour_metrique("chiffre d'affaires") == "fact_financial")
check("'consommation de trésorerie trimestrielle (cash burn)' → fact_financial",
      entry_type_pour_metrique("consommation de trésorerie trimestrielle (cash burn)") == "fact_financial")
check("'durabilité de l'avantage concurrentiel' → fact_qualitative",
      entry_type_pour_metrique("durabilité de l'avantage concurrentiel") == "fact_qualitative",
      f"→ {entry_type_pour_metrique('durabilité de l''avantage concurrentiel')}")
check("'type de barrière à l'entrée (moat)' → fact_qualitative",
      entry_type_pour_metrique("type de barrière à l'entrée (moat)") == "fact_qualitative")

# ── §5 la requête web est aveugle à la question et ne juge pas la source (#59) ─────────────────────
print("\n[5] la requête web est AVEUGLE à la question et ne juge pas la valeur de la source (#59)")
_ligne = LigneAveugle(ticker_id="NVDA", metrique="free cash flow",
                      source_pressentie="10-K + communiqué", ancre="clôture du trimestre")
req = construire_requete_web(_ligne)
check("reliability_min permissif = 0.40 (le collecteur ne juge pas la valeur d'une source, #59)",
      req.reliability_min == 0.40, f"→ {req.reliability_min}")
check("aucun `field_path` dans la requête (un field_path ré-ancrerait la question — #58)",
      req.output_schema.field_path is None, f"→ {req.output_schema.field_path}")
check("worker = search-worker, ticker repris de la ligne",
      req.worker == "search-worker" and req.ticker_id == "NVDA")
check("la requête porte la métrique, la source ET l'ancre de la ligne",
      all(x in req.query for x in (_ligne.metrique, _ligne.source_pressentie, _ligne.ancre)))
check("le type d'entry de la requête suit la déduction (#4) : 'free cash flow' → fact_financial",
      req.output_schema.entry_type == entry_type_pour_metrique(_ligne.metrique))


# ── §5bis POSTES dérivé du plan : le socle ne collecte QUE les postes réclamés (maillon 5, §3.6) ──
print("\n[5bis] `postes_edgar_du_plan` : un poste que nul plan ne réclame ne se collecte plus (§3.6)")
# Le socle EDGAR data-first (8 postes en bloc) a disparu : `_SocleEdgar` ne collecte que l'union des
# postes des lignes traduites routées EDGAR. Détenteur unique du dispatch (`router_source` +
# `poste_pour_metrique`), jamais une seconde liste (#46).
_it_rev = CollectionPlanItem(question_id="qf_2", ingredient_id="resultat_net", statut="traduit",
                             metrique="chiffre d'affaires", source_pressentie="10-K",
                             ancre="clôture de l'exercice")
_it_ni = CollectionPlanItem(question_id="qf_2", ingredient_id="resultat_net_2", statut="traduit",
                            metrique="Net income (GAAP)", source_pressentie="10-K (Income Statement)",
                            ancre="clôture de l'exercice")
_it_web_derivee = CollectionPlanItem(question_id="qf_7", ingredient_id="fcf", statut="traduit",
                                     metrique="free cash flow", source_pressentie="10-K",
                                     ancre="clôture du trimestre")  # dépôt SEC mais DÉRIVÉE → web
_it_web_marche = CollectionPlanItem(question_id="qf_1", ingredient_id="cout_du_capital",
                                    statut="traduit", metrique="coût du capital (WACC)",
                                    source_pressentie="données de marché", ancre="aujourd'hui")
# ⚠️ Le cas DISCRIMINANT du routing : une métrique qui EST un poste (`marge brute` → gross_profit),
# mais annoncée depuis un COMMUNIQUÉ (pas un dépôt SEC) → router = web. Correctement routée, elle ne
# réclame PAS le poste EDGAR ; ignorer le routing ajouterait `gross_profit` (qui n'apparaît nulle part
# ailleurs) et ferait rougir l'assert. Sans ce cas, un `postes_edgar_du_plan` aveugle au routing
# passerait au vert (les autres lignes web portent des métriques dérivées, déjà exclues par le poste).
_it_web_poste = CollectionPlanItem(question_id="qf_4", ingredient_id="marge", statut="traduit",
                                   metrique="marge brute", source_pressentie="communiqué de presse",
                                   ancre="clôture du trimestre")
_it_rev_bis = CollectionPlanItem(question_id="qf_3", ingredient_id="croissance", statut="traduit",
                                 metrique="chiffre d'affaires", source_pressentie="10-Q",
                                 ancre="clôture du trimestre")  # même poste 'revenue' → dédup
_it_inob = CollectionPlanItem(question_id="qf_1", ingredient_id="autre", statut="inobtenable",
                              motif="aucune source connue")
_plan_mix = CollectionPlan(ticker_id="NVDA", framework_id="qualite_financiere",
                           framework_version="v3.0.0", archetype="rentable",
                           items=[_it_rev, _it_ni, _it_web_derivee, _it_web_marche,
                                  _it_web_poste, _it_rev_bis, _it_inob])
_reclames = postes_edgar_du_plan(_plan_mix)
check("seuls les postes des lignes EDGAR traduites sont réclamés (dérivées/marché/inobtenable exclus)",
      _reclames == frozenset({"revenue", "net_income"}), f"→ {sorted(_reclames)}")
check("un plan SANS ligne EDGAR ne réclame aucun poste (rien à collecter, aucun appel réseau)",
      postes_edgar_du_plan(CollectionPlan(
          ticker_id="RVMD", framework_id="qualite_financiere", framework_version="v3.0.0",
          archetype="pre_revenus", items=[_it_web_marche, _it_inob])) == frozenset(),
      "→ un plan tout-web/inobtenable déclencherait quand même le socle data-first")


# ── §6 une collecte web qui LÈVE devient un echec, jamais une exception qui tue le lot (#25) ───────
print("\n[6] une collecte web qui LÈVE → echec motivé, jamais une exception qui tue le lot (#25)")
import asyncio
import app.agents.v2.collecte_executor as _mod


async def _failing(_req):
    raise RuntimeError("provider timeout simulé")


_mod.run_search_worker = _failing  # monkeypatch : le modèle/réseau échoue
_ligne_web = LigneAveugle(ticker_id="RVMD", metrique="analyse qualitative du moat",
                          source_pressentie="communiqué", ancre="dernière lecture clinique")
try:
    _rc = asyncio.run(_mod.collecter_un(_ligne_web, conn=None, socle=_mod._SocleEdgar(frozenset())))
    check("une collecte web qui LÈVE → echec motivé (jamais une exception qui tue le lot, #25)",
          _rc.echec is not None and "provider timeout simulé" in _rc.echec, f"→ {_rc!r}")
except Exception as e:
    check("une collecte web qui LÈVE → echec motivé (jamais une exception qui tue le lot, #25)",
          False, f"→ a PROPAGÉ {type(e).__name__} au lieu de rendre un echec")


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
