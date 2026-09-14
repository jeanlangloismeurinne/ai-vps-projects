"""Vérification de la FRONTIÈRE DÉTERMINISTE de l'exécuteur réel (chantier v3, lot 2c —
`app/agents/v2/collecte_executor.py`).

Sans réseau ni modèle ni base. L'exécution réelle (EDGAR / search-worker) est hors de portée d'un
check hors ligne ; mais la CORRECTION vit dans la frontière déterministe — quelle source ? quel poste
EDGAR ? quel type d'entry ? quelle requête ? — et elle, on l'éprouve ici, entièrement.

  • §1 LE DISPATCH EST AVEUGLE ET CONSERVATEUR — EDGAR seulement si la source nomme un dépôt
       réglementaire ET le poste nommé par le plan survit aux vétos ; au moindre doute → web.
  • §2 LE VÉTO DÉTERMINISTE SURVIT AU FAIT QUE LE POSTE SOIT NOMMÉ PAR UN MODÈLE — un poste posé sur
       une métrique DÉRIVÉE est refusé ; un faux appariement écrirait un lien vers le mauvais nombre
       (#43). C'est le seul contrôle que le prompt ne peut pas desserrer (#59).
  • §3 DÉTENTEUR UNIQUE DU SOCLE (#46) — le vocabulaire fermé montré au traducteur est RENDU depuis
       `edgar_feed.POSTES`, jamais recopié : un poste ajouté au socle apparaît dans le prompt, sinon
       le modèle ne peut pas le nommer et la ligne part au web sans que rien ne le signale.
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
    poste_retenu,
    postes_edgar_du_plan,
    router_source,
)
from app.agents.v2.traducteur import _TRADUCTEUR_SYSTEM_PROMPT, _catalogue_postes
from app.contracts.collection_plan_schema import CollectionPlan, CollectionPlanItem
from app.knowledge.edgar_feed import POSTES


def _ligne(metrique, source, poste=None, ticker="NVDA", ancre="clôture de l'exercice"):
    """Raccourci de fixture : une ligne aveugle telle que l'aiguilleur la construit."""
    return LigneAveugle(ticker_id=ticker, metrique=metrique, source_pressentie=source,
                        ancre=ancre, poste=poste)

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
print("[1] le dispatch EDGAR exige source réglementaire ET poste nommé survivant aux vétos")
check("'10-Q' + poste `revenue` → edgar",
      router_source(_ligne("chiffre d'affaires", "10-Q", "revenue")) == "edgar")
check("'rapport annuel (10-K) EDGAR' + poste `net_income` → edgar",
      router_source(_ligne("résultat net", "rapport annuel (10-K) EDGAR", "net_income")) == "edgar")
check("'10-K' SANS poste nommé → web (le plan n'a rien désigné : on ne devine plus)",
      router_source(_ligne("chiffre d'affaires", "10-K")) == "web",
      "→ un appariement deviné a ressuscité")
check("'communiqué + call trimestriel' + poste `operating_cash_flow` → web "
      "(le poste est juste, mais la source pressentie n'est pas un dépôt — un agrégat ajusté du "
      "communiqué porte souvent le même nom que le poste GAAP)",
      router_source(_ligne("trésorerie d'exploitation", "communiqué + call trimestriel",
                           "operating_cash_flow")) == "web")
check("'données de marché' + aucun poste → web",
      router_source(_ligne("coût du capital (WACC)", "données de marché")) == "web")
check("'10-K' + poste `operating_cash_flow` sur « free cash flow » → web "
      "(dépôt SEC et poste existant, mais métrique DÉRIVÉE : le véto prime)",
      router_source(_ligne("free cash flow", "10-K", "operating_cash_flow")) == "web")
check("'10-K' + poste INVENTÉ (`ebitda`, hors catalogue) → web, jamais une levée (#60)",
      router_source(_ligne("EBITDA ajusté", "10-K", "ebitda")) == "web")
check("'10-K (Income Statement)' + poste `net_income` sur « Net income (GAAP) » → edgar",
      router_source(_ligne("Net income (GAAP)", "10-K (Income Statement)", "net_income")) == "edgar")

# ── §2 le véto déterministe, dernier rempart derrière un poste nommé par un modèle ────────────────
print("\n[2] un poste posé sur une métrique DÉRIVÉE est refusé (le prompt ne peut pas desserrer ça)")
check("poste `net_income` sur « Net income (GAAP) » → retenu (c'est le NIVEAU brut)",
      poste_retenu("net_income", "Net income (GAAP)") == "net_income",
      f"→ {poste_retenu('net_income', 'Net income (GAAP)')}")
check("poste `operating_cash_flow` sur « free cash flow » → None (FCF ≠ OCF, #43)",
      poste_retenu("operating_cash_flow", "free cash flow") is None)
check("poste `revenue` sur « conversion du chiffre d'affaires en trésorerie » → None (ratio)",
      poste_retenu("revenue", "conversion du chiffre d'affaires en trésorerie") is None)
check("poste `total_assets` sur « Total assets − cash − ... » → None (soustraction, pas le brut)",
      poste_retenu("total_assets",
                   "Total assets − cash and marketable securities − "
                   "non-interest-bearing current liabilities") is None)
check("poste inventé hors catalogue → None (route au web, ne lève pas — #60)",
      poste_retenu("free_cash_flow", "free cash flow") is None)
check("poste absent (None) → None", poste_retenu(None, "chiffre d'affaires") is None)

# Les 5 faux appariements MESURÉS le 2026-09-14 sur les 3 plans réels, et le remède de CHACUN. Les
# écrire ici nommément est ce qui empêche la classe de revenir : trois remèdes différents, et les
# confondre ferait croire qu'un seul correctif suffisait.
print("\n[2bis] les 5 faux appariements mesurés, et le remède de chacun")
# (a) deux étaient de purs ARTEFACTS de la recherche par sous-chaînes — la métrique ne parle même pas
#     du poste. Ils disparaissent avec la recherche elle-même : plus personne ne lit `metrique` pour
#     en déduire un poste. Ce qu'on vérifie, c'est qu'un poste NON NOMMÉ ne s'invente pas.
check("(a) « clauses de sauvegarde en cas de cession d'actifs » sans poste → web "
      "(matché `revenue` sur « ventes » — l'artefact meurt avec la recherche par sous-chaînes)",
      router_source(_ligne("clauses de sauvegarde en cas de cession d'actifs", "10-K")) == "web")
check("(a) « charges fixes décaissables, hors dépenses d'investissement minimales » sans poste → web "
      "(matché `capital_expenditure` dans une énumération)",
      router_source(_ligne("charges fixes décaissables, hors dépenses d'investissement minimales",
                           "10-K")) == "web")
# (b) deux étaient des TRANSFORMATIONS d'un poste réel. Là le traducteur PEUT légitimement nommer le
#     poste voisin, et c'est le véto déterministe qui doit tenir — d'où le poste passé explicitement.
check("(b) poste `capital_expenditure` sur « capex de maintien (estimation) » → véto",
      poste_retenu("capital_expenditure", "capex de maintien (estimation)") is None)
check("(b) poste `capital_expenditure` sur « capex de croissance » → véto",
      poste_retenu("capital_expenditure", "capex de croissance") is None)
# (c) le cinquième n'était NI un artefact NI une dérivée : le bon poste n'existait pas au catalogue,
#     et l'appariement est retombé sur le voisin. Le remède est l'ENRICHISSEMENT, et il se vérifie
#     par la présence du poste — pas par un véto, qui laisserait la ligne partir au web pour rien.
check("(c) « échéances à douze mois » a désormais SON poste au catalogue (`long_term_debt_current`) "
      "— faute de quoi l'appariement retombait sur la dette à LONG terme (#43)",
      "long_term_debt_current" in {p.metric for p in POSTES})
check("(c) … et il est retenu sur la métrique mesurée, sans véto",
      poste_retenu("long_term_debt_current",
                   "Dette à court terme (échéances dans les 12 mois), incluant la part courante "
                   "de la dette à long terme") == "long_term_debt_current")

# ── §3 détenteur unique du socle (#46) ────────────────────────────────────────────────────────────
print("\n[3] le vocabulaire fermé montré au traducteur EST `edgar_feed.POSTES` (#46)")
metrics_socle = {p.metric for p in POSTES}
_catalogue = _catalogue_postes()
check("chaque poste du socle est énuméré au traducteur (sinon il ne peut pas le nommer, "
      "et la ligne part au web sans que rien ne le signale)",
      all(m in _catalogue for m in metrics_socle),
      f"→ absents du prompt : {sorted(m for m in metrics_socle if m not in _catalogue)}")
check("chaque poste énuméré porte son libellé humain (un identifiant nu ne se reconnaît pas)",
      all(p.label in _catalogue for p in POSTES),
      f"→ sans libellé : {sorted(p.metric for p in POSTES if p.label not in _catalogue)}")
check("le catalogue est bien INCLUS dans le prompt système (rendu, pas seulement calculable)",
      _catalogue in _TRADUCTEUR_SYSTEM_PROMPT)
check("le prompt n'énumère AUCUN poste hors catalogue (une liste recopiée divergerait, #46)",
      not [l for l in _catalogue.splitlines()
           if l.strip().lstrip("· ").split(" — ")[0].strip() not in metrics_socle])

# ── §3bis le catalogue est présenté comme un TEST à passer, jamais comme un menu ──────────────────
# MESURE DU 2026-09-14, et c'est elle qui justifie ces asserts. Premier prompt : le catalogue était
# rendu avec une consigne du type « si l'ingrédient EST l'un des postes, nomme-le », suivie d'une
# liste d'interdits. Sur 3 plans réels, le modèle a nommé un poste sur 34 lignes dont ~22 FAUX — il
# lit une liste de 33 entrées comme un menu et la remplit par voisinage thématique (« clauses
# restrictives des contrats de dette » → `total_liabilities`, « politique de capitalisation » →
# `capital_expenditure`). Une liste d'interdits ne ferme rien : elle se contourne par un cas non
# listé. Un CRITÈRE, lui, se transporte — d'où la question de complétude/exactitude ci-dessous,
# qui a fait retomber les 3 plans à 11 lignes EDGAR toutes justes.
# ⚠️ Ces asserts gardent l'ÉNONCÉ, pas le comportement : le modèle reste instable d'un passage à
# l'autre (MSFT rejoué deux fois : 5 lignes puis 15). Ce qui garantira l'appariement est une garde
# EN CODE (le modèle propose, le code vérifie — #24/#28/#29) ; elle n'existe pas encore, et c'est
# pourquoi la collecte RÉELLE ne doit pas partir sur ce chemin. Ne pas lire ces asserts comme une
# garantie d'appariement : ils garantissent seulement que le durcissement ne se perd pas en route.
check("le prompt pose le critère de COMPLÉTUDE/EXACTITUDE (le test que le poste doit passer)",
      "COMPLÈTEMENT et EXACTEMENT" in _TRADUCTEUR_SYSTEM_PROMPT)
check("le prompt dit explicitement que le catalogue n'est PAS un menu à remplir",
      "CE N'EST PAS UN MENU À REMPLIR" in _TRADUCTEUR_SYSTEM_PROMPT)
check("le prompt nomme les opérations qui DISQUALIFIENT un poste (ajouter/diviser/part/période)",
      all(op in _TRADUCTEUR_SYSTEM_PROMPT
          for op in ("ADDITIONNER", "SOUSTRAIRE", "DIVISER", "PART", "AUTRE PÉRIODE",
                     "LIRE DU TEXTE")))
# Les contre-exemples ne sont pas décoratifs : chacun est un faux appariement MESURÉ sur un plan
# réel. Les retirer du prompt, c'est retirer la seule instruction que le modèle a sur ces cas.
check("le prompt porte les contre-exemples mesurés (covenant, politique, ligne non tirée)",
      all(ce in _TRADUCTEUR_SYSTEM_PROMPT
          for ce in ("covenants", "politique de capitalisation", "NON UTILISÉES")))
check("le prompt dit que l'ABSENCE de poste est le cas normal (sinon le défaut reste « remplir »)",
      "la plupart des lignes n'ont pas de `poste`" in _TRADUCTEUR_SYSTEM_PROMPT)

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
                             ancre="clôture de l'exercice", poste="revenue")
_it_ni = CollectionPlanItem(question_id="qf_2", ingredient_id="resultat_net_2", statut="traduit",
                            metrique="Net income (GAAP)", source_pressentie="10-K (Income Statement)",
                            ancre="clôture de l'exercice", poste="net_income")
# Dépôt SEC, poste NOMMÉ et existant — mais métrique dérivée : le véto renvoie au web. C'est le cas
# qui distingue « le plan a désigné un poste » de « ce poste est légitime pour cette métrique ».
_it_web_derivee = CollectionPlanItem(question_id="qf_7", ingredient_id="fcf", statut="traduit",
                                     metrique="free cash flow", source_pressentie="10-K",
                                     ancre="clôture du trimestre", poste="operating_cash_flow")
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
                                   ancre="clôture du trimestre", poste="gross_profit")
_it_rev_bis = CollectionPlanItem(question_id="qf_3", ingredient_id="croissance", statut="traduit",
                                 metrique="chiffre d'affaires", source_pressentie="10-Q",
                                 ancre="clôture du trimestre", poste="revenue")  # dédup sur 'revenue'
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
