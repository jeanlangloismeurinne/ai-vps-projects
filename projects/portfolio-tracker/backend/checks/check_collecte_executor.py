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
check("'10-K' + poste INVENTÉ non-dérivé (`gross_revenue_net`, hors catalogue) → web — "
      "le filtre catalogue est distinct du véto dérivée (#60)",
      router_source(_ligne("chiffre d'affaires net", "10-K", "gross_revenue_net")) == "web")
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


# ── §7 router_source lit la carte d'appariement (câblage lot 3 maillon 4bis étape 2c) ──────────────
# La carte REMPLACE `poste_retenu()` comme décideur EDGAR/web. Sans carte, l'ancienne logique tient.
# ⚠️ Le paramètre `carte_statut` n'est pas dans LigneAveugle (le collecteur reste AVEUGLE, #58) : il
# est passé au moment de l'appel, par le niveau qui dispose de la carte, sans piercer l'enveloppe.
def _l(metrique, source, poste=None):
    """Raccourci local §7 — `_ligne` est une instance LigneAveugle depuis §5 et ne s'appelle plus."""
    return LigneAveugle(ticker_id="NVDA", metrique=metrique, source_pressentie=source,
                        ancre="clôture de l'exercice", poste=poste)


print("\n[7] router_source lit la carte d'appariement (câblage maillon 4bis — §2c)")
check("carte `exact` + source réglementaire SEC → edgar (la carte court-circuite poste_retenu)",
      router_source(_l("résultat net", "10-K (Income Statement)"), carte_statut="exact") == "edgar")
check("carte `approximation` + source réglementaire SEC → edgar (formule connue, EDGAR a les termes)",
      router_source(_l("capital employé", "10-K"), carte_statut="approximation") == "edgar")
check("carte `indisponible` + source SEC + poste valide → web (l'inventaire n'a pas le concept)",
      router_source(_l("coûts fixes décaissables", "10-K", "revenue"),
                    carte_statut="indisponible") == "web")
check("carte `exact` + source NON-SEC → web (la source ne nomme pas un dépôt réglementaire)",
      router_source(_l("résultat net", "communiqué de presse"), carte_statut="exact") == "web")
check("sans carte (repli) : logique antérieure préservée — poste valide + SEC → edgar",
      router_source(_l("résultat net", "10-K", "net_income"), carte_statut=None) == "edgar")
check("sans carte (repli) : logique antérieure préservée — pas de poste → web",
      router_source(_l("résultat net", "10-K"), carte_statut=None) == "web")


# ── §8 le CHEMIN D'EXÉCUTION RÉEL consulte la carte — pas seulement `router_source` en isolation ─────
# C'est L'ASSERT QUI DISTINGUE LE CÂBLAGE DE L'AFFICHAGE (convention #54 / demande du lot 2c).
# §7 ci-dessus prouve que `router_source` PEUT lire `carte_statut` si on le lui passe.
# §8 prouve que `collecter_un` — la fonction qui contient les appels `router_source` dans le chemin de
# production (lignes 317 et 359 de `collecte_executor.py`) — LE PASSE RÉELLEMENT à partir de son
# propre paramètre `carte_statut`, et que ce paramètre change l'issue observable.
#
# CAS DISCRIMINANT : une ligne avec source SEC + poste VALIDE (`net_income` / `10-K`).
#   · sans carte (repli) → `poste_retenu` renvoie `net_income` → chemin EDGAR → `socle.entry_id` appelé
#   · avec `carte_statut="indisponible"` → `router_source` retourne "web" → `run_search_worker` appelé
# Si le câblage manque, les deux cas prennent le même chemin — et l'assert « web avec indisponible »
# rougit, parce que `socle.entry_id` est appelé à la place de `run_search_worker`.
#
# MUTATION ATTENDUE : retirer le passage de `carte_statut` à `router_source` dans `collecter_un`
# (remplacer `router_source(ligne, carte_statut=carte_statut)` par `router_source(ligne)`) → l'assert
# « indisponible → web (run_search_worker) » rougit car `socle.entry_id` est appelé à la place.
print("\n[8] le chemin d'exécution réel (`collecter_un`) consulte la carte — pas seulement router_source")

_edgar_calls = []
_web_calls = []


class _MockSocle:
    """Enregistre les appels EDGAR (sans réseau)."""
    async def entry_id(self, ticker_id, poste_metric):
        _edgar_calls.append((ticker_id, poste_metric))
        return _mod.ResultatCollecte(echec="mock edgar — pas de réseau dans le check")


async def _mock_web(req):
    """Enregistre les appels web (sans réseau)."""
    _web_calls.append(req.ticker_id)
    from app.contracts.worker_delegation_schema import WorkerExchange, WorkerResponse
    # On retourne une réponse "not_found" pour que le check reste un echec propre — pas de persistence.
    return WorkerExchange(
        request=req,
        response=WorkerResponse(status="not_found", entries=[]),
    )


# Ligne EDGAR par `poste_retenu` (SEC source + poste `net_income` valide non dérivé)
_ligne_edgar = LigneAveugle(
    ticker_id="NVDA", metrique="Net income (GAAP)",
    source_pressentie="10-K (Income Statement)",
    ancre="clôture de l'exercice", poste="net_income",
)

# ── cas 1 : sans carte → chemin EDGAR (poste_retenu décide) ──────────────────────────────────────────
_edgar_calls.clear(); _web_calls.clear()
_mod.run_search_worker = _mock_web
try:
    asyncio.run(_mod.collecter_un(_ligne_edgar, conn=None, socle=_MockSocle(), carte_statut=None))
except Exception:
    pass  # le mock edgar retourne un echec propre — la levée éventuelle ne nous intéresse pas
check("§8 sans carte : une ligne SEC+poste valide prend le chemin EDGAR (socle.entry_id appelé)",
      len(_edgar_calls) == 1 and _edgar_calls[0][1] == "net_income",
      f"→ edgar_calls={_edgar_calls}, web_calls={_web_calls}")

# ── cas 2 : carte `indisponible` → chemin WEB (carte décide, poste_retenu court-circuité) ────────────
_edgar_calls.clear(); _web_calls.clear()
try:
    asyncio.run(_mod.collecter_un(
        _ligne_edgar, conn=None, socle=_MockSocle(), carte_statut="indisponible"))
except Exception:
    pass
check("§8 carte `indisponible` : la même ligne prend le chemin WEB (run_search_worker appelé)",
      len(_web_calls) == 1 and len(_edgar_calls) == 0,
      f"→ edgar_calls={_edgar_calls}, web_calls={_web_calls}")

# ── cas 3 : carte `exact` → chemin EDGAR (carte dit que le concept est déposé) ──────────────────────
_edgar_calls.clear(); _web_calls.clear()
try:
    asyncio.run(_mod.collecter_un(
        _ligne_edgar, conn=None, socle=_MockSocle(), carte_statut="exact"))
except Exception:
    pass
check("§8 carte `exact` : la même ligne prend le chemin EDGAR (la carte confirme le concept)",
      len(_edgar_calls) == 1 and len(_edgar_calls) > 0,
      f"→ edgar_calls={_edgar_calls}, web_calls={_web_calls}")

# ── cas 4 : sans carte mais poste None (dérivée) → chemin WEB comme avant (repli inchangé) ──────────
_ligne_derivee = LigneAveugle(
    ticker_id="NVDA", metrique="free cash flow",
    source_pressentie="10-K", ancre="clôture de l'exercice", poste="operating_cash_flow",
)
_edgar_calls.clear(); _web_calls.clear()
try:
    asyncio.run(_mod.collecter_un(_ligne_derivee, conn=None, socle=_MockSocle(), carte_statut=None))
except Exception:
    pass
check("§8 repli (sans carte, poste dérivée) : chemin WEB préservé — le repli est inchangé",
      len(_web_calls) == 1 and len(_edgar_calls) == 0,
      f"→ edgar_calls={_edgar_calls}, web_calls={_web_calls}")

# ── invariant de non-régression : §7 reste intact au niveau `router_source` ──────────────────────────
check("§8 invariant §7 intact : carte `indisponible`+SEC → web ; `exact`+SEC → edgar ; repli tient",
      all([
          router_source(_l("résultat net", "10-K (Income Statement)"),
                        carte_statut="indisponible") == "web",
          router_source(_l("résultat net", "10-K (Income Statement)"),
                        carte_statut="exact") == "edgar",
          router_source(_l("résultat net", "10-K"), carte_statut=None) == "web",  # repli sans poste
      ]))


# ── §9 LA RÉFÉRENCE DE REVÉRIFICATION NE VIENT JAMAIS DE LA CARTE ELLE-MÊME ─────────────────────
# `lire_carte` tranche l'âge de la carte en comparant son `dernier_depot_vu` à un `depot_courant`
# que l'APPELANT fournit (#54). La première version du câblage puisait ce `depot_courant` dans la
# table de la carte : la comparaison devenait `X < X`, donc toujours fausse, et la branche
# « périmée » journalisait `depot_vu=X < depot_courant=X` — un log qui ne peut jamais être vrai. La
# garde n'était pas absente, elle était NOURRIE DE SA PROPRE VALEUR, et c'est la seule des deux
# formes qui ne se voit pas à la lecture (`feedback_controle_au_point_de_lecture`).
#
# Cet assert est structurel, lu sur l'AST et non sur le texte : la prose de ce fichier et celle de
# l'exécuteur PARLENT toutes deux de `dernier_depot_vu` pour expliquer l'interdit, et un grep brut
# rougirait sur sa propre énonciation (`feedback_grep_interdit_lit_sa_propre_enonciation`).
print("\n[9] la référence de revérification ne peut pas venir de la carte elle-même")
import ast  # noqa: E402
from pathlib import Path  # noqa: E402

_ARBRE = ast.parse(Path(_mod.__file__).read_text(encoding="utf-8"))

_appels_lire = [n for n in ast.walk(_ARBRE)
                if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "lire_carte"]
check("§9 l'exécuteur appelle `lire_carte` — le câblage existe dans le code de production, pas "
      "seulement dans son test",
      len(_appels_lire) == 1, f"→ {len(_appels_lire)} appel(s)")
_kw = {k.arg: k.value for a in _appels_lire for k in a.keywords}
check("§9 `depot_courant` est la SENTINELLE nommée, jamais une date lue en base : l'exécuteur avoue "
      "dans son code qu'il n'a pas de dépôt courant à opposer",
      isinstance(_kw.get("depot_courant"), ast.Name)
      and _kw["depot_courant"].id == "_SANS_REVERIFICATION",
      f"→ {ast.dump(_kw['depot_courant'])[:90] if 'depot_courant' in _kw else 'absent'}")
_sql = [n.value for n in ast.walk(_ARBRE)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
        and "SELECT" in n.value and "appariement_cartes" in n.value]
check("§9 l'exécuteur n'émet AUCUN `SELECT` sur `appariement_cartes` : il ne peut donc pas y "
      "repuiser la date qu'il oppose à la carte — la boucle est coupée à la source, pas gardée",
      _sql == [], f"→ {len(_sql)} requête(s)")
check("§9 la sentinelle est plus petite que toute date ISO : la comparaison `<` est fausse par "
      "CONSTRUCTION, elle ne dépend pas d'un `if` qu'un correctif pourrait retourner",
      _mod._SANS_REVERIFICATION < "0001-01-01",
      f"→ {_mod._SANS_REVERIFICATION!r}")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
