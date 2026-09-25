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
    check("§6 cause d'une collecte web qui LÈVE = `source_indisponible` (notre outil a cassé : on "
          "relance, on ne conclut pas que la donnée n'existe pas)",
          _rc.cause == "source_indisponible", f"→ {_rc.cause!r}")
except Exception as e:
    check("une collecte web qui LÈVE → echec motivé (jamais une exception qui tue le lot, #25)",
          False, f"→ a PROPAGÉ {type(e).__name__} au lieu de rendre un echec")


# ── §6bis une collecte web qui SE BLOQUE devient un mandat borné, jamais un silence infini (#25) ───
# §6 couvre l'exception ; le blocage est le mode de panne SYMÉTRIQUE et plus dangereux — il ne LÈVE
# pas, donc l'`except` de §6 ne le voit jamais : il fige toute la collecte (mesuré >18 min sur RVMD).
# Le garde est un `asyncio.wait_for` dans `collecter_un` ; on le prouve en substituant un worker QUI
# NE REND JAMAIS. L'assert discriminant : le check s'entoure lui-même d'un `wait_for(5 s)`, donc si la
# mutation RETIRE le garde de production, ce n'est plus borné → le wait_for du check LÈVE → FAIL.
# Une garde de comportement (« ça a rendu un echec ») ne suffirait pas : sans borne, on n'obtient
# jamais de retour à tester.
print("\n[6bis] une collecte web qui SE BLOQUE → mandat borné et NOMMÉ, jamais un silence infini (#25)")
from app.config import settings as _settings

_budget_avant = _settings.WEB_LINE_BUDGET_S
_orig_worker = _mod.run_search_worker


async def _hang(_req, **_kw):
    await asyncio.sleep(30)          # ne rend jamais dans le temps du test : simule le pair qui traîne


async def _mesure_blocage():
    _settings.WEB_LINE_BUDGET_S = 0.3     # le garde de PROD doit couper bien avant les 30 s du hang
    _mod.run_search_worker = _hang
    # wait_for du CHECK : si le garde de prod a sauté, `collecter_un` ne rend jamais → on LÈVE ici,
    # au lieu de figer le check comme la prod figeait la collecte. C'est ce qui rend la mutation rouge.
    return await asyncio.wait_for(
        _mod.collecter_un(_ligne_web, conn=None, socle=_mod._SocleEdgar(frozenset())), timeout=5)


try:
    _rc_b = asyncio.run(_mesure_blocage())
    check("un worker qui SE BLOQUE est BORNÉ par le garde de prod : `collecter_un` REND (le check "
          "ne fige pas) — sans `asyncio.wait_for`, la ligne bloquerait indéfiniment",
          _rc_b.echec is not None, f"→ {_rc_b!r}")
    check("le mandat NOMME la cause (budget dépassé) et non un « échec » générique (#25) : un motif "
          "muet se lit comme « le dépôt ne porte pas ce nombre »",
          _rc_b.echec is not None and "budget" in _rc_b.echec
          and str(int(_settings.WEB_LINE_BUDGET_S)) in _rc_b.echec, f"→ {_rc_b.echec!r}")
    check("§6bis cause d'un temps épuisé = `source_indisponible`, JAMAIS `recherche_epuisee` : "
          "l'analyste coupé en route n'a pas conclu que la donnée n'est pas publiée",
          _rc_b.cause == "source_indisponible", f"→ {_rc_b.cause!r}")
except (asyncio.TimeoutError, TimeoutError):
    check("un worker qui SE BLOQUE est BORNÉ par le garde de prod : `collecter_un` REND (le check "
          "ne fige pas) — sans `asyncio.wait_for`, la ligne bloquerait indéfiniment",
          False, "→ NON BORNÉ : `collecter_un` n'a pas rendu en 5 s (le garde de prod est absent)")
    check("le mandat NOMME la cause (budget dépassé) et non un « échec » générique (#25)",
          False, "→ non mesurable : la ligne n'a jamais rendu")
finally:
    _settings.WEB_LINE_BUDGET_S = _budget_avant
    _mod.run_search_worker = _orig_worker


# ── §7 router_source lit la carte d'appariement (câblage lot 3 maillon 4bis étape 2c) ──────────────
# La carte REMPLACE `poste_retenu()` comme décideur EDGAR/web. Sans carte, l'ancienne logique tient.
# ⚠️ Le paramètre `carte_statut` n'est pas dans LigneAveugle (le collecteur reste AVEUGLE, #58) : il
# est passé au moment de l'appel, par le niveau qui dispose de la carte, sans piercer l'enveloppe.
def _l(metrique, source, poste=None):
    """Raccourci local §7 — `_ligne` est une instance LigneAveugle depuis §5 et ne s'appelle plus."""
    return LigneAveugle(ticker_id="NVDA", metrique=metrique, source_pressentie=source,
                        ancre="clôture de l'exercice", poste=poste)


# ── §6ter le search-worker va AU BOUT et ne retient rien → `recherche_epuisee` ─────────────────────
print("\n[6ter] un search-worker qui répond `not_found` → cause `recherche_epuisee` (le seul « rien de publié » du web)")


async def _worker_not_found(req, **_kw):
    from app.contracts.worker_delegation_schema import (
        ExecutionDeclaration, WorkerExchange, WorkerResponse)
    return WorkerExchange(
        request=req,
        response=WorkerResponse(
            request_hash="mock", worker=req.worker, status="not_found", entries=[],
            execution=ExecutionDeclaration(model_used="mock")),
    )


_mod.run_search_worker = _worker_not_found
try:
    _rc_nf = asyncio.run(_mod.collecter_un(_ligne_web, conn=None, socle=_mod._SocleEdgar(frozenset())))
    check("§6ter `not_found` → echec de cause `recherche_epuisee`",
          _rc_nf.echec is not None and _rc_nf.cause == "recherche_epuisee", f"→ {_rc_nf!r}")
finally:
    _mod.run_search_worker = _orig_worker


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
        return _mod.ResultatCollecte(echec="mock edgar — pas de réseau dans le check",
                                     cause="source_indisponible")


async def _mock_web(req):
    """Enregistre les appels web (sans réseau), et rend un `WorkerExchange` VALIDE.

    ⚠️ Il ne l'était pas jusqu'au 2026-09-18 : `WorkerResponse` était construite sans `request_hash`,
    `worker` ni `execution`, donc ce mock LEVAIT une `ValidationError` à chaque appel. Les cas de §8
    l'avalaient dans un `except Exception: pass` et restaient verts — un mock qui échoue à répondre
    mesurait le chemin web. Le défaut ne s'est vu que par le test négatif : la mutation §6 (la porte
    d'erreur générique restreinte) a cessé de rougir et a tué le script à la place
    (`feedback_fixture_copiee_du_reel` — une fixture qui ne tient pas la forme du réel est aveugle)."""
    _web_calls.append(req.ticker_id)
    from app.contracts.worker_delegation_schema import (
        ExecutionDeclaration, WorkerExchange, WorkerResponse)
    # `not_found` : le chemin web est bien emprunté, mais rien n'est persisté par le check.
    return WorkerExchange(
        request=req,
        response=WorkerResponse(
            request_hash="mock", worker=req.worker, status="not_found", entries=[],
            execution=ExecutionDeclaration(model_used="mock")),
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
# ⚠️ CE QUE CETTE SECTION GARDE DEPUIS LE 2026-09-18, ET POURQUOI C'EST PLUS FORT QU'AVANT.
# La version précédente exigeait UN SEUL appel à `lire_carte`, avec la sentinelle en `depot_courant`.
# C'était l'interdit juste, adossé au mauvais invariant : il tenait parce que l'exécuteur n'avait
# AUCUNE date à opposer — et donc il tenait aussi, sans rien dire, pendant que la table restait vide
# et que la carte ne décidait jamais rien. L'interdit survit ici sous une forme qui ne peut plus se
# satisfaire de l'inaction : le chemin NOMINAL passe une date, et cette date doit venir du producteur
# `dernier_depot_vu(...)` — jamais d'une valeur relue en base.
#
# Ces asserts sont structurels, lus sur l'AST et non sur le texte : la prose de ce fichier et celle
# de l'exécuteur PARLENT toutes deux de `dernier_depot_vu` pour expliquer l'interdit, et un grep brut
# rougirait sur sa propre énonciation (`feedback_grep_interdit_lit_sa_propre_enonciation`).
print("\n[9] la référence de revérification ne peut pas venir de la carte elle-même")
import ast  # noqa: E402
from pathlib import Path  # noqa: E402

_ARBRE = ast.parse(Path(_mod.__file__).read_text(encoding="utf-8"))


def _appels(nom):
    return [n for n in ast.walk(_ARBRE)
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == nom]


_appels_lire = _appels("lire_carte")
check("§9 l'exécuteur appelle `lire_carte` — le câblage existe dans le code de production, pas "
      "seulement dans son test",
      len(_appels_lire) >= 1, f"→ {len(_appels_lire)} appel(s)")

# LE PRODUCTEUR EXISTE. Sans lui, tous les asserts d'âge ci-dessous sont vrais sur une table vide :
# `lire_carte` renvoie None, l'exécuteur retombe sur `poste_retenu()`, et rien ne rougit. C'est
# exactement l'état mesuré en base le 2026-09-18 (0 ligne, 0 appelant de `persister_carte` en
# production) — un décideur sans producteur ne décide jamais.
check("§9 l'exécuteur PRODUIT la carte quand elle manque : `apparier` puis `persister_carte` sont "
      "appelés dans le code de production (sans quoi la garde d'âge porte sur une table vide)",
      len(_appels("apparier")) >= 1 and len(_appels("persister_carte")) >= 1,
      f"→ apparier={len(_appels('apparier'))}, persister_carte={len(_appels('persister_carte'))}")

# Chaque `depot_courant` est un NOM (jamais une expression inline qu'on ne pourrait pas remonter).
_noms_depot = []
_non_nom = 0
for _a in _appels_lire:
    _v = {k.arg: k.value for k in _a.keywords}.get("depot_courant")
    if isinstance(_v, ast.Name):
        _noms_depot.append(_v.id)
    else:
        _non_nom += 1
check("§9 chaque appel à `lire_carte` passe `depot_courant` par un NOM — une expression inline "
      "rendrait sa provenance illisible à l'AST, donc l'interdit ingardable",
      _non_nom == 0 and len(_noms_depot) == len(_appels_lire),
      f"→ {_non_nom} appel(s) sans nom, {len(_noms_depot)}/{len(_appels_lire)}")

# La sentinelle reste un emploi LÉGITIME (inventaire injoignable), mais elle n'est plus le seul.
check("§9 la sentinelle `_SANS_REVERIFICATION` est encore employée — servir une carte sans pouvoir "
      "la dater reste un état NOMMÉ, pas un silence",
      "_SANS_REVERIFICATION" in _noms_depot, f"→ {sorted(set(_noms_depot))}")
check("§9 au moins un appel oppose une AUTRE référence que la sentinelle : le chemin nominal "
      "revérifie réellement l'âge (sans cela, la branche « périmée » reste inatteignable)",
      any(n != "_SANS_REVERIFICATION" for n in _noms_depot), f"→ {sorted(set(_noms_depot))}")

# L'INTERDIT, sous sa forme forte : toute référence autre que la sentinelle doit être PRODUITE par
# `dernier_depot_vu(...)`. Une réassignation depuis `carte.dernier_depot_vu` ou depuis un `row[...]`
# recréerait `X < X` — et cette fois-ci elle ne se verrait pas non plus.
for _nom in sorted({n for n in _noms_depot if n != "_SANS_REVERIFICATION"}):
    _rhs = [n.value for n in ast.walk(_ARBRE) if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == _nom for t in n.targets)]
    check(f"§9 `{_nom}` est PRODUIT par `dernier_depot_vu(...)`, et par rien d'autre : la date "
          "opposée à la carte est mesurée sur l'inventaire, jamais relue depuis la carte",
          len(_rhs) >= 1 and all(isinstance(r, ast.Call)
                                 and getattr(r.func, "id", None) == "dernier_depot_vu"
                                 for r in _rhs),
          f"→ {len(_rhs)} affectation(s) : "
          f"{[type(r).__name__ + ':' + str(getattr(getattr(r, 'func', None), 'id', '?')) for r in _rhs]}")

# LE MÊME INTERDIT, UN CRAN PLUS BAS : D'OÙ VIENT LE SYMBOLE OPPOSÉ À EDGAR.
# `plan.ticker_id` est un identifiant INTERNE — `PUB-XXXXXXXX` pour un titre coté ajouté sans
# symbole, `PRIV-…` pour une société non cotée. Il n'a coïncidé avec le symbole de marché que tant
# qu'on n'exerçait que RVMD/NVDA/MSFT, où les deux se ressemblent. Un assert de COMPORTEMENT ne peut
# pas tenir cet interdit : il resterait vert sur tout ticker où l'id EST le symbole, c'est-à-dire
# exactement sur les tickers qu'on teste (#71 — l'interdit juste adossé au mauvais invariant).
_appels_cik = _appels("resolve_cik")
_args_cik = [(_a.args[0] if _a.args else
              {k.arg: k.value for k in _a.keywords}.get("ticker")) for _a in _appels_cik]
check("§9 l'exécuteur résout le CIK, et il passe son argument par un NOM — une expression inline "
      "(`plan.ticker_id`) rendrait la provenance du symbole ingardable à l'AST",
      len(_appels_cik) >= 1 and all(isinstance(v, ast.Name) for v in _args_cik),
      f"→ {len(_appels_cik)} appel(s) : {[type(v).__name__ for v in _args_cik]}")
for _nom in sorted({v.id for v in _args_cik if isinstance(v, ast.Name)}):
    _rhs = [n.value for n in ast.walk(_ARBRE) if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == _nom for t in n.targets)]
    _prod = [r.value if isinstance(r, ast.Await) else r for r in _rhs]
    check(f"§9 `{_nom}` est PRODUIT par `symbole_de_marche(...)`, et par rien d'autre : le symbole "
          "de marché se LIT dans `tickers.ticker_symbol` (#11), il ne se devine pas depuis l'id",
          len(_prod) >= 1 and all(isinstance(r, ast.Call)
                                  and getattr(r.func, "id", None) == "symbole_de_marche"
                                  for r in _prod),
          f"→ {len(_prod)} affectation(s) : "
          f"{[getattr(getattr(r, 'func', None), 'id', type(r).__name__) for r in _prod]}")

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


# ── §10 LES QUATRE ÉTATS DE LA CARTE SONT OBSERVABLES, ET LA RECONSTRUCTION EST UNE RECONSTRUCTION ──
# §9 lit le code ; §10 le FAIT TOURNER. Sans réseau, sans modèle, sans base : on substitue les quatre
# frontières externes de `assurer_carte` (`resolve_cik`, `fetch_company_facts`, `lire_carte`,
# `apparier`/`persister_carte`) et on COMPTE ce qui est appelé. `dernier_depot_vu` reste le VRAI —
# c'est précisément ce que §9 exige comme source de la date, et le substituer mesurerait le mock.
#
# CE QUE CHAQUE CAS FERME :
#   · carte fraîche        → ZÉRO appel modèle. Sans cet assert, une implémentation qui reconstruit à
#                            chaque exécution serait verte partout ailleurs et coûterait une carte
#                            par run.
#   · carte périmée        → `apparier` appelé ET `persister_carte` appelé. C'est la branche que #70
#                            rendait inatteignable ; qu'elle mène à une RECONSTRUCTION et non à un
#                            repli est ce qui distingue le correctif d'un simple aveu.
#   · inventaire injoignable → carte STOCKÉE servie, état `non_reverifiable`, et `depot_courant` None.
#                            Un None se lit comme une absence ; une date recopiée se lirait comme une
#                            mesure (c'est la faute de #70, transposée d'un cran).
#   · rien du tout         → `aucune` + `statuts is None` → l'aval retombe sur `poste_retenu()`.
print("\n[10] les quatre états de la carte, observés sur `assurer_carte` (sans réseau ni modèle)")
from app.contracts.appariement_schema import AppariementCarte, AppariementItem  # noqa: E402

_journal = {"apparier": 0, "persiste": 0, "depots_opposes": [],
            "symbole_pour": [], "cik_pour": []}

# L'ID DU PLAN N'EST PAS SON SYMBOLE, et c'est délibéré : sur « NVDA »/« NVDA » les deux asserts de
# provenance ci-dessous seraient verts quoi que fasse le code (`feedback_fixture_copiee_du_reel` —
# une fixture plus favorable que la prod est un check aveugle).
_TICKER_ID = "PUB-4F2A9C10"
_SYMBOLE = "NVDA"

# Un inventaire minimal mais de la MÊME FORME que le réel : `fetch_company_facts` rend
# {concept → [points]} et chaque point porte `filed` (copié de la forme EDGAR, pas inventé plus
# commode — une fixture plus favorable que la prod est un check aveugle, `feedback_fixture_copiee`).
_FACTS = {"Assets": [{"end": "2026-01-26", "val": 1.0, "filed": "2026-02-26", "form": "10-K"}],
          "Revenues": [{"end": "2026-01-26", "val": 2.0, "filed": "2026-06-30", "form": "10-Q/A"}]}
_DEPOT_REEL = "2026-06-30"   # le max(filed) de _FACTS — et non le max(end), qui vaudrait 2026-01-26


def _carte_stockee(depot):
    return AppariementCarte(
        ticker_id=_TICKER_ID, framework_id="qualite_financiere", framework_version="v3.0.0",
        dernier_depot_vu=depot,
        items=[AppariementItem(question_id="qf_1", ingredient_id="resultat_net",
                               statut="exact", concepts=["NetIncomeLoss"])])


async def _fake_cik(ticker):
    _journal["cik_pour"].append(ticker)
    return "0001045810"


async def _fake_facts(cik):
    return _FACTS


def _installer(*, facts_ok=True, en_base=None, symbole_ok=True):
    """Substitue les CINQ frontières externes. `en_base` = la carte stockée (ou None).

    ⚠️ `symbole_de_marche` est la cinquième, arrivée avec le maillon 4 : elle touche la BASE (elle
    lit `tickers`), donc elle passe la frontière au même titre que le réseau. L'oublier n'a pas rendu
    un assert faux — le script est mort sur un `AttributeError` avant d'atteindre son bilan, ce qui
    se lit comme une absence de mesure et non comme un vert (`feedback_bilan_par_sa_forme`)."""
    _journal["apparier"] = _journal["persiste"] = 0
    _journal["depots_opposes"] = []
    _journal["symbole_pour"] = []
    _journal["cik_pour"] = []

    async def _symbole(conn, ticker_id):
        _journal["symbole_pour"].append(ticker_id)
        if not symbole_ok:
            raise _mod.EdgarFeedUnavailable(
                f"{ticker_id} : pas de symbole de marché (privé/PUB-/PRIV-) — aucun dépôt EDGAR")
        return _SYMBOLE
    _mod.symbole_de_marche = _symbole

    _mod.resolve_cik = _fake_cik
    if facts_ok:
        _mod.fetch_company_facts = _fake_facts
    else:
        async def _ko(cik):
            raise _mod.EdgarUnavailable("SEC injoignable (simulé)")
        _mod.fetch_company_facts = _ko

    async def _lire(conn, *, ticker_id, framework_id, framework_version, depot_courant):
        _journal["depots_opposes"].append(depot_courant)
        if en_base is None:
            return None
        # LA VRAIE RÈGLE DE `lire_carte`, recopiée et non contournée : périmée ⟹ None (#54).
        return None if en_base.dernier_depot_vu < depot_courant else en_base
    _mod.lire_carte = _lire

    async def _apparier(plan, facts):
        _journal["apparier"] += 1
        return _mod_apparieur.Appariement(
            run=_RunFactice(), carte=_carte_stockee(_mod.dernier_depot_vu(facts)),
            refus_repares=[], mandats=[])
    _mod.apparier = _apparier

    async def _persister(conn, carte):
        _journal["persiste"] += 1
        return 1
    _mod.persister_carte = _persister


class _RunFactice:
    cost_usd = 0.0012


import app.agents.v2.apparieur as _mod_apparieur  # noqa: E402

_plan_carte = CollectionPlan(ticker_id=_TICKER_ID, framework_id="qualite_financiere",
                             framework_version="v3.0.0", archetype="rentable",
                             items=[_it_rev, _it_ni])

# ── cas 1 : carte à jour (stockée sur le dépôt courant) → FRAÎCHE, zéro appel modèle ──────────────
_installer(en_base=_carte_stockee(_DEPOT_REEL))
_c1 = asyncio.run(_mod.assurer_carte(_plan_carte, conn=None))
check("§10 carte à jour → état `fraiche`, AUCUN appel modèle (une carte valide ne se repaie pas)",
      _c1.etat == "fraiche" and _journal["apparier"] == 0 and _journal["persiste"] == 0
      and _c1.cout_usd == 0.0,
      f"→ etat={_c1.etat}, apparier={_journal['apparier']}, persiste={_journal['persiste']}")
check("§10 la date opposée à la carte est le `max(filed)` de l'inventaire (2026-06-30), pas le "
      "`max(end)` (2026-01-26) : un rectificatif qui AJOUTE des concepts sans bouger la clôture "
      "doit périmer la carte",
      _journal["depots_opposes"] == [_DEPOT_REEL] and _c1.depot_courant == _DEPOT_REEL,
      f"→ {_journal['depots_opposes']}, depot_courant={_c1.depot_courant}")
check("§10 la carte fraîche fournit bien les statuts au routage (couple question×ingrédient)",
      _c1.statuts == {("qf_1", "resultat_net"): "exact"}, f"→ {_c1.statuts}")
# §9 lit que le symbole VIENT de `symbole_de_marche` ; ici on lit ce qui ARRIVE à EDGAR. Les deux
# ensemble ferment le trou : le CIK était résolu depuis `plan.ticker_id`, ce qui ne marchait que
# tant que l'id était le symbole — silencieux sur tout titre `PUB-…`.
check("§10 `symbole_de_marche` est interrogé avec l'ID DU PLAN, et c'est le SYMBOLE qu'il rend qui "
      "part chez EDGAR : l'id interne n'atteint jamais la SEC (#11)",
      _journal["symbole_pour"] == [_TICKER_ID] and _journal["cik_pour"] == [_SYMBOLE],
      f"→ symbole_de_marche({_journal['symbole_pour']}), resolve_cik({_journal['cik_pour']})")
check("§10 l'inventaire remonté porte le symbole et le CIK résolus — l'exécution d'un appariement "
      "écrit sa provenance (`sec.gov/…/CIK…`) sans re-résoudre quoi que ce soit",
      _c1.inventaire is not None and _c1.inventaire.symbole == _SYMBOLE
      and _c1.inventaire.facts == _FACTS,
      f"→ {None if _c1.inventaire is None else (_c1.inventaire.symbole, _c1.inventaire.cik)}")

# ── cas 2 : carte PÉRIMÉE → RECONSTRUCTION (pas un repli dégradé) ─────────────────────────────────
_installer(en_base=_carte_stockee("2026-02-26"))   # antérieure au dépôt courant
_c2 = asyncio.run(_mod.assurer_carte(_plan_carte, conn=None))
check("§10 carte PÉRIMÉE → `reconstruite` : `apparier` ET `persister_carte` appelés une fois. "
      "C'est la branche que #70 rendait inatteignable, et elle RECONSTRUIT au lieu de dégrader",
      _c2.etat == "reconstruite" and _journal["apparier"] == 1 and _journal["persiste"] == 1,
      f"→ etat={_c2.etat}, apparier={_journal['apparier']}, persiste={_journal['persiste']}")
check("§10 la carte reconstruite est datée du dépôt COURANT (elle ne renaît pas périmée) et son "
      "coût modèle est remonté, pas absorbé",
      _c2.depot_courant == _DEPOT_REEL and _c2.cout_usd > 0,
      f"→ depot_courant={_c2.depot_courant}, cout={_c2.cout_usd}")

# ── cas 3 : aucune carte en base → production initiale ────────────────────────────────────────────
_installer(en_base=None)
_c3 = asyncio.run(_mod.assurer_carte(_plan_carte, conn=None))
check("§10 aucune carte en base → `reconstruite` : le premier passage PRODUIT la carte au lieu de "
      "retomber silencieusement sur `poste_retenu()` (l'état mesuré en prod le 2026-09-18)",
      _c3.etat == "reconstruite" and _journal["apparier"] == 1 and _journal["persiste"] == 1,
      f"→ etat={_c3.etat}, apparier={_journal['apparier']}, persiste={_journal['persiste']}")

# ── cas 4 : inventaire injoignable + carte en base → servie SANS revérification, et c'est DIT ─────
_installer(facts_ok=False, en_base=_carte_stockee("2026-02-26"))
_c4 = asyncio.run(_mod.assurer_carte(_plan_carte, conn=None))
check("§10 inventaire injoignable → `non_reverifiable` : la carte stockée est servie, mais l'état "
      "le DIT — « à jour » et « pas vérifiable » ne se confondent plus en aval",
      _c4.etat == "non_reverifiable" and _c4.statuts is not None
      and _journal["apparier"] == 0,
      f"→ etat={_c4.etat}, statuts={_c4.statuts}, apparier={_journal['apparier']}")
check("§10 dans cet état, `depot_courant` est None et la sentinelle est ce qui a été opposé : "
      "aucune date n'est inventée pour faire croire à une mesure",
      _c4.depot_courant is None
      and _journal["depots_opposes"] == [_mod._SANS_REVERIFICATION],
      f"→ depot_courant={_c4.depot_courant}, opposés={_journal['depots_opposes']}")

# ── cas 4bis : société SANS symbole de marché → même repli nommé, et zéro appel réseau ────────────
# L'absence de symbole n'est pas une panne, c'est une propriété de l'émetteur (`PRIV-…`, ou un titre
# coté ajouté sans symbole). Elle doit se comporter comme une frontière indisponible — pas remonter
# en exception qui tue le lot, pas non plus partir interroger la SEC avec un id interne.
_installer(en_base=_carte_stockee("2026-02-26"), symbole_ok=False)
_c4b = asyncio.run(_mod.assurer_carte(_plan_carte, conn=None))
check("§10 société sans symbole de marché → `non_reverifiable` sur le stock, et `resolve_cik` n'est "
      "JAMAIS appelé : on n'interroge pas EDGAR avec un identifiant interne",
      _c4b.etat == "non_reverifiable" and _c4b.statuts is not None
      and _journal["cik_pour"] == [] and _journal["apparier"] == 0,
      f"→ etat={_c4b.etat}, resolve_cik={_journal['cik_pour']}, apparier={_journal['apparier']}")
check("§10 sans symbole, aucun inventaire n'est remonté : `consignes` et `inventaire` restent None, "
      "donc l'aval ne peut pas croire qu'il a de quoi exécuter un appariement",
      _c4b.inventaire is None and _c4b.consignes is None,
      f"→ inventaire={_c4b.inventaire}, consignes={_c4b.consignes}")

# ── cas 5 : ni inventaire ni carte → repli NOMMÉ vers `poste_retenu()` ────────────────────────────
_installer(facts_ok=False, en_base=None)
_c5 = asyncio.run(_mod.assurer_carte(_plan_carte, conn=None))
check("§10 ni inventaire ni carte → `aucune` + `statuts is None` : l'aval retombe sur "
      "`poste_retenu()`, et ce repli porte un nom (#25/#44)",
      _c5.etat == "aucune" and _c5.statuts is None and _c5.depot_courant is None,
      f"→ {_c5}")

# ── cas 6 : le modèle REFUSE deux fois → on ne tue pas le lot, on sert le stock en le disant ──────
_installer(en_base=_carte_stockee("2026-02-26"))


async def _apparier_refuse(plan, facts):
    _journal["apparier"] += 1
    raise _mod.AppariementRefuse("concepts inventés deux fois de suite (simulé)")


_mod.apparier = _apparier_refuse
_c6 = asyncio.run(_mod.assurer_carte(_plan_carte, conn=None))
check("§10 appariement REFUSÉ après réparation → `non_reverifiable` sur le stock, jamais une "
      "exception qui tue toute la collecte (#25) — et rien n'est persisté",
      _c6.etat == "non_reverifiable" and _journal["persiste"] == 0 and _journal["apparier"] == 1,
      f"→ etat={_c6.etat}, persiste={_journal['persiste']}")

# ── LE CÂBLAGE : `executer_plan_reel` OBTIENT la carte, il ne se contente pas de l'accepter ───────
# Sans ces deux asserts, `assurer_carte` pourrait être parfaite et n'être appelée par personne — ce
# qui est EXACTEMENT l'état dans lequel `apparier()` et `persister_carte()` ont vécu tout le maillon
# 4bis. Plan tout-`inobtenable` : l'aiguillage se fait sans une seule ligne à collecter, donc sans
# réseau, et ce qu'on observe est le câblage nu.
_plan_inob = CollectionPlan(ticker_id="NVDA", framework_id="qualite_financiere",
                            framework_version="v3.0.0", archetype="rentable", items=[_it_inob])
_assure = {"n": 0}


async def _fake_assurer(plan, *, conn):
    _assure["n"] += 1
    return _mod.CarteCourante(None, "aucune", None)


_mod.assurer_carte = _fake_assurer
asyncio.run(_mod.executer_plan_reel(_plan_inob, conn=None))
check("§10 `executer_plan_reel` OBTIENT la carte quand l'appelant n'en fournit pas : le producteur "
      "est branché sur le chemin d'exécution, pas seulement écrit à côté",
      _assure["n"] == 1, f"→ {_assure['n']} appel(s) à assurer_carte")

_assure["n"] = 0
asyncio.run(_mod.executer_plan_reel(
    _plan_inob, conn=None, carte=_mod.CarteCourante(None, "aucune", None)))
check("§10 une carte FOURNIE court-circuite la production : l'appelant qui en détient déjà une "
      "(`executer_collecte_framework`) ne la repaie pas une seconde fois",
      _assure["n"] == 0, f"→ {_assure['n']} appel(s) à assurer_carte")

check("§10 `executer_plan_reel` expose le paramètre `carte` — un appelant qui en détient une "
      "(ou qui n'en veut aucune) ne repaie pas la production",
      "carte" in __import__("inspect").signature(_mod.executer_plan_reel).parameters,
      f"→ {list(__import__('inspect').signature(_mod.executer_plan_reel).parameters)}")


# ── §11 UNE CONSIGNE D'APPARIEMENT S'EXÉCUTE, ET ELLE RESTE AVEUGLE À LA QUESTION ─────────────────
# CE QUE CE MAILLON DÉBLOQUE, ET CE QUI LE MESURE. La carte disait déjà « edgar » pour 9 lignes de
# RVMD ; l'exécuteur, lui, n'avait AUCUN moyen d'exécuter autre chose qu'une RECETTE du catalogue —
# donc ces 9 lignes repartaient au web. C'est la moitié manquante : la carte routait, personne ne
# collectait. Le chiffre à suivre est « lignes COLLECTÉES depuis le dépôt », jamais « lignes ROUTÉES
# vers EDGAR » (#71) — et il se mesure à l'acceptation, pas ici. Ici on garde la MÉCANIQUE.
#
# ⚠️ LA DISTRIBUTION RÉELLE INTERDIT DE N'EXÉCUTER QUE LES `exact` : sur RVMD la carte porte
# 10 `approximation` · 3 `indisponible` · 0 `exact`. Chez une biotech pré-revenus, TOUTE ligne ancrée
# passe par une formule. Un chemin qui ne saurait exécuter que le concept nu ne débloquerait rien.
print("\n[11] une consigne d'appariement s'exécute (et l'ordre recette-puis-consigne est tenu)")

_carte_mixte = AppariementCarte(
    ticker_id=_TICKER_ID, framework_id="qualite_financiere", framework_version="v3.0.0",
    dernier_depot_vu=_DEPOT_REEL,
    items=[
        AppariementItem(question_id="qf_1", ingredient_id="resultat_net",
                        statut="exact", concepts=["NetIncomeLoss"]),
        AppariementItem(question_id="qf_2", ingredient_id="tresorerie_par_action",
                        statut="approximation",
                        concepts=["CashAndCashEquivalentsAtCarryingValue", "Shares"],
                        formule="CashAndCashEquivalentsAtCarryingValue / Shares",
                        hypotheses=["les actions dilutives ne sont pas retirées"],
                        deterministe=True),
        AppariementItem(question_id="qf_3", ingredient_id="part_de_marche",
                        statut="indisponible",
                        motif="aucun concept XBRL ne porte une part de marché"),
    ])
_cons = _mod._consignes(_carte_mixte)

check("§11 `exact` → l'expression EST le concept nu ; `approximation` → l'expression EST la formule. "
      "Les deux s'exécutent par le même chemin, sans que l'aval ait à retrancher le statut",
      _cons[("qf_1", "resultat_net")].expression == "NetIncomeLoss"
      and _cons[("qf_2", "tresorerie_par_action")].expression
      == "CashAndCashEquivalentsAtCarryingValue / Shares",
      f"→ {[(k, v.expression) for k, v in _cons.items()]}")
check("§11 `indisponible` ne produit AUCUNE consigne : le seul chemin qui lui reste est le web, et "
      "c'est déjà ce que `router_source` décide (§7) — les deux ne peuvent pas diverger",
      ("qf_3", "part_de_marche") not in _cons and len(_cons) == 2, f"→ {sorted(_cons)}")
check("§11 l'approximation transporte ses HYPOTHÈSES et son caractère déterministe — sans eux le "
      "tier ne peut pas se dériver, et un calcul non déterministe passerait pour un relevé (#67)",
      _cons[("qf_2", "tresorerie_par_action")].hypotheses
      == ("les actions dilutives ne sont pas retirées",)
      and _cons[("qf_2", "tresorerie_par_action")].deterministe is True,
      f"→ {_cons[('qf_2', 'tresorerie_par_action')]}")

# L'AVEUGLEMENT EST UNE PROPRIÉTÉ DU TYPE, PAS UNE DISCIPLINE D'ÉCRITURE (#57/#58). Le couple
# question×ingrédient est la CLEF du dictionnaire ; il n'entre dans aucune VALEUR. Un collecteur qui
# reçoit la valeur nue ne peut donc pas écrire la question dans l'entry, même par inadvertance.
_champs_consigne = set(_mod.ConsigneAppariement._fields)
check("§11 `ConsigneAppariement` ne porte AUCUN champ de question : l'aveuglement du collecteur (#58) "
      "tient à la forme du type, il ne dépend pas de la vigilance de l'appelant",
      not (_champs_consigne & {"question_id", "ingredient_id", "question", "framework_id"}),
      f"→ {sorted(_champs_consigne)}")
_vocab = {"qf_1", "qf_2", "resultat_net", "tresorerie_par_action", "qualite_financiere"}
_fuite = [(k, c, v) for k, v in _cons.items() for c in v
          if isinstance(c, str) and any(j in c for j in _vocab)]
check("§11 aucune VALEUR de consigne ne contient un fragment du vocabulaire de framework : le "
      "couple reste une clef, il ne voyage pas avec la consigne",
      _fuite == [], f"→ {_fuite}")

# ── LE CHEMIN D'EXÉCUTION : trois issues, et l'ordre entre les deux premières ─────────────────────
# `args` démarre à {} et non à None : un assert qui EXPLOSE au lieu de rougir tue le script avant son
# bilan, et une absence de bilan se lit comme une absence de mesure, pas comme un échec nommé
# (`feedback_bilan_par_sa_forme`). C'est exactement ce qu'a montré la mutation « consigne jamais
# exécutée » : la garde suivante doit ROUGIR, pas mourir.
_appar: dict = {"n": 0, "args": {}}


class _ConnFactice:
    """De quoi ouvrir une transaction, et rien de plus : ce que l'appariement ÉCRIT est éprouvé par
    `check_appariement_feed` (la règle) et par l'acceptation réelle (l'état). Ici on mesure le
    CÂBLAGE — qui appelle quoi, avec quels arguments."""
    class _Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *a):
            return False

    def transaction(self):
        return self._Tx()


async def _fake_executer(conn, *, ticker_id, symbole, cik, libelle, consigne, facts):
    _appar["n"] += 1
    _appar["args"] = dict(ticker_id=ticker_id, symbole=symbole, cik=cik, libelle=libelle,
                          consigne=consigne, facts=facts)
    return 9001


_mod.executer_appariement = _fake_executer
_inv = _mod.InventaireTicker(symbole=_SYMBOLE, cik=1045810, facts=_FACTS)
_consigne_approx = _cons[("qf_2", "tresorerie_par_action")]

# Une ligne SANS recette du catalogue : c'est le cas nominal d'une approximation. `poste` est None et
# la métrique n'est pas un poste — seule la carte la route chez EDGAR.
_ligne_sans_recette = LigneAveugle(
    ticker_id=_TICKER_ID, metrique="trésorerie par action",
    source_pressentie="10-Q (Balance Sheet)", ancre="clôture du trimestre", poste=None)

check("§11 (préalable) cette ligne n'a AUCUNE recette du catalogue — sans quoi le cas ci-dessous "
      "mesurerait le chemin 1 en croyant mesurer le chemin 2",
      _mod.poste_retenu(_ligne_sans_recette.poste, _ligne_sans_recette.metrique) is None,
      f"→ {_mod.poste_retenu(_ligne_sans_recette.poste, _ligne_sans_recette.metrique)}")

# ── cas 1 : consigne + inventaire, pas de recette → L'APPARIEMENT S'EXÉCUTE ───────────────────────
_appar["n"] = 0; _edgar_calls.clear(); _web_calls.clear()
_r1 = asyncio.run(_mod.collecter_un(
    _ligne_sans_recette, conn=_ConnFactice(), socle=_MockSocle(), carte_statut="approximation",
    consigne=_consigne_approx, inventaire=_inv))
check("§11 consigne + inventaire, aucune recette → `executer_appariement` est appelé UNE fois et son "
      "entry est rendue : la ligne est COLLECTÉE depuis le dépôt, elle ne repart plus au web",
      _appar["n"] == 1 and _r1.entry_id == 9001 and _r1.echec is None and _web_calls == [],
      f"→ n={_appar['n']}, resultat={_r1}, web={_web_calls}")
check("§11 l'appariement reçoit le SYMBOLE et l'inventaire DÉJÀ LU (aucune seconde lecture EDGAR), "
      "et le LIBELLÉ de la ligne — jamais le couple question×ingrédient (#58)",
      _appar["args"].get("symbole") == _SYMBOLE and _appar["args"].get("facts") is _FACTS
      and _appar["args"].get("libelle") == "trésorerie par action"
      and _appar["args"].get("ticker_id") == _TICKER_ID,
      f"→ {({k: v for k, v in _appar['args'].items() if k != 'facts'})}")

# ── cas 2 : une RECETTE existe → elle passe DEVANT la consigne ────────────────────────────────────
# Doubler les deux chemins écrirait deux entries actives pour le même fait (#43) ; et la recette
# choisit son concept par FRAÎCHEUR parmi des candidats (#30), ce qu'une expression figée ne fait pas.
_appar["n"] = 0; _edgar_calls.clear(); _web_calls.clear()
asyncio.run(_mod.collecter_un(
    _ligne_edgar, conn=_ConnFactice(), socle=_MockSocle(), carte_statut="exact",
    consigne=_cons[("qf_1", "resultat_net")], inventaire=_inv))
check("§11 quand une RECETTE du catalogue résout, elle passe devant la consigne : le socle est "
      "appelé, l'appariement NON — un même fait n'a pas deux producteurs actifs (#30/#43)",
      len(_edgar_calls) == 1 and _appar["n"] == 0,
      f"→ edgar={_edgar_calls}, appariement={_appar['n']}")

# ── cas 3 : consigne SANS inventaire → repli web, et il reste distinct d'une exécution ────────────
_appar["n"] = 0; _edgar_calls.clear(); _web_calls.clear()
_mod.run_search_worker = _mock_web
asyncio.run(_mod.collecter_un(
    _ligne_sans_recette, conn=_ConnFactice(), socle=_MockSocle(), carte_statut="approximation",
    consigne=_consigne_approx, inventaire=None))
check("§11 consigne mais aucun inventaire (EDGAR injoignable) → repli WEB, et l'appariement n'est "
      "pas tenté à vide : le repli reste un état distinct du câblage réussi",
      _appar["n"] == 0 and len(_web_calls) == 1,
      f"→ appariement={_appar['n']}, web={_web_calls}")

# ── cas 4 : l'appariement REFUSE → echec MOTIVÉ, jamais un repli web muet ─────────────────────────
# C'est le cœur du refus nommé (#25) : un web silencieux ferait lire « le dépôt ne porte pas ce
# nombre » là où la cause est « l'ancre commune manque à ±20 jours ».
_appar["n"] = 0; _edgar_calls.clear(); _web_calls.clear()


async def _executer_refuse(conn, **kw):
    _appar["n"] += 1
    raise _mod.AppariementInexecutable("aucune ancre commune à ±20 j (simulé)")


_mod.executer_appariement = _executer_refuse
_r4 = asyncio.run(_mod.collecter_un(
    _ligne_sans_recette, conn=_ConnFactice(), socle=_MockSocle(), carte_statut="approximation",
    consigne=_consigne_approx, inventaire=_inv))
check("§11 appariement INEXÉCUTABLE → `echec` motivé qui NOMME la cause et l'expression, jamais une "
      "exception qui tue le lot, jamais un nombre approché, jamais un repli web muet (#25)",
      _r4.entry_id is None and _r4.echec is not None
      and "ancre commune" in _r4.echec and _consigne_approx.expression in _r4.echec
      and _web_calls == [],
      f"→ {_r4}")
check("§11 cause d'un appariement inexécutable = `recherche_epuisee` (le dépôt a été lu, il ne porte "
      "pas le concept sous une forme calculable)", _r4.cause == "recherche_epuisee", f"→ {_r4.cause!r}")


# ── LE CÂBLAGE AMONT : la consigne ARRIVE jusqu'à `collecter_un` ──────────────────────────────────
# Sans cet assert, tout §11 pourrait être vert alors qu'`executer_plan_reel` n'y passe jamais ni
# `consigne` ni `inventaire` — une capacité parfaite et sans appelant, exactement l'état dans lequel
# `apparier()` a vécu tout le maillon 4bis.
_passes = [n for n in ast.walk(_ARBRE) if isinstance(n, ast.Call)
           and getattr(n.func, "id", None) == "collecter_un"]
_kw = [{k.arg for k in n.keywords} for n in _passes]
check("§11 le code de production APPELLE `collecter_un` en lui passant `consigne` ET `inventaire` : "
      "le chemin d'exécution est branché, pas seulement écrit à côté",
      len(_passes) >= 1 and any({"consigne", "inventaire"} <= s for s in _kw),
      f"→ {len(_passes)} appel(s), kwargs={_kw}")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
