"""Vérification du recompute déterministe du curator — pur, sans réseau ni DB ni LLM.

Depuis la 029, la couverture est DÉRIVÉE DE LA BASE, plus des citations du LLM : pour chaque champ
requis, le backend cherche dans un INDEX de couverture une entry qui PORTE ce champ (chemin complet
`dimension.champ`) à un tier ≥ plancher.

⚠️ **D'où vient cet index a changé le 2026-09-10 (migration 036).** Il se construisait ici même,
depuis `knowledge_entries.covers` (`_covers_index`). La colonne est archivée : ce qu'une entry
couvre est une propriété de la RELATION entry ↔ question, pas de l'entry (#57). L'index est
désormais un **argument requis** de `recompute_coverage`, et `None` y déclare « aucun émetteur ».
Les fixtures de ce fichier le construisent donc elles-mêmes (`_index_fixture`) : ce que le lot 2c
lira dans `question_coverage`, elles le fournissent à la main, ce qui laisse intactes les 19
sections qui éprouvent la PORTE. L'écart entre les deux lots — la porte n'a réellement aucun
émetteur aujourd'hui — est déclaré en §4 et virera au vert de lui-même le jour du câblage (#52).

Ce qu'on éprouve ici :

  • le plancher mord (une entry sous plancher ne fonde pas — bug #54 : tier B compté pour un B+) ;
  • le plancher PAR CHAMP (dégradé `croissance_marche_historique=B`) est respecté ;
  • l'index DÉCOUVRE une entry que le LLM n'a pas citée (le faux creux qui faisait osciller le
    verdict à corpus figé — rapports NVDA #11/#13/#14) ;
  • le chemin complet discrimine `business_model.description` de `produits.description` ;
  • une entry non taguée ne fonde plus rien (fin du fallback tier-only de la 028) ;
  • le LLM ne peut plus DESSERRER champs_requis / tier_plancher, seulement les resserrer ;
  • les gaps restent en bijection avec les non-fondables, et le ReadinessReport final valide.
"""
import copy
import inspect
import sys

from datetime import date

from app.agents.v2.common import (
    FIELD_PROFILES, MVDD_FIELD_PATHS, MVDD_SPEC, format_entries_for_prompt,
)
from app.agents.v2.curator import (
    DECLARED_NONBLOCKING_GAPS,
    CouvertureSansEmetteur,
    MOTIF_SANS_EMETTEUR,
    nonblocking_gaps_for,
    index_couverture_pour,
    exiger_index_couverture,
    _apply_deterministic_overrides,
    _declare_nonblocking_gaps,
    _exigences,
    constrain_rationale,
    verdicts_nommes,
    _plancher_for,
    _tier_ge,
    recompute_coverage,
    reconcile_gaps,
)
from app.contracts import ReadinessReport, compute_cause_non_ready
from app.knowledge.material_events import (
    MaterialEvent, MaterialEventLookup, ancre_substantielle,
)

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


_SPEC = {s["dimension"]: s for s in MVDD_SPEC}


# Date par DÉFAUT des entries de fixture. Elle n'est pas décorative : une entry sans `source_date`
# est `indeterminable` (#53), et `indeterminable` n'est pas `courante` — sur un champ où l'actualité
# BLOQUE, elle ne fonde donc rien. Laisser le défaut à `None` transformait silencieusement les 14
# sections écrites avant la capacité 4 en tests d'actualité : elles mesuraient l'axe au lieu du
# plancher qu'elles nomment. Un cas qui VEUT l'indatabilité passe `source_date=None` explicitement.
_JADIS = date(2026, 1, 1)


# Clef de FIXTURE, jamais une colonne. Elle porte les chemins que cette entry couvre, pour que
# `_index_fixture` en bâtisse l'index. Le préfixe `_` et le suffixe `_fixture` sont là pour qu'une
# relecture ne la confonde pas avec l'ancienne colonne `covers` : la ligne rendue par `entry()` est
# une ligne de `knowledge_entries` telle que la 036 la laisse, et `_index_fixture` la retire avant
# de la passer à la porte — une entry ne doit pas pouvoir se fonder elle-même.
_LIENS = "_liens_fixture"


def entry(eid, tier, covers, source_type="edgar_official", source_date=_JADIS, cites=None):
    """Une entry de fixture, datée par défaut. `source_date`/`cites` portent l'axe actualité
    (capacité 4) : sous `_NEANT` toute date vaut `courante`, sous `_ancre(j)` une date antérieure à
    `j` vaut `perimee`.

    ⚠️ `covers` reste le nom du PARAMÈTRE — c'est ce que la fixture déclare — mais il ne va plus
    dans la ligne : il alimente l'index de couverture, qui est l'argument que la porte reçoit
    désormais (#57). Le garder dans la ligne rendrait ce fichier vert le jour où quelqu'un
    réintroduirait une lecture de colonne dans `recompute_coverage`.
    """
    e = {"id": eid, "reliability_tier": tier, "source_type": source_type,
         "source_date": source_date, _LIENS: covers}
    if cites is not None:
        e["content_structured"] = {"claims": [{"text": "x", "cited_entry_ids": list(cites)}]}
    return e


def _index_fixture(entries):
    """`(index, lignes)` — l'index que le dispatch du lot 2c produira, et les lignes sans la clef.

    Reprend les règles que `_covers_index` tenait jusqu'à la 036, parce qu'elles ne dépendaient pas
    de la colonne : une entry sans tier n'entre pas dans l'index (la porte n'aurait rien à comparer
    au plancher), une entry sans lien n'y entre pas non plus, et une chaîne nue vaut un chemin.
    Trié par id pour que `fondations` soit stable d'une exécution à l'autre.
    """
    index: dict[str, list[tuple[int, str]]] = {}
    lignes = []
    for e in entries:
        ligne = {k: v for k, v in e.items() if k != _LIENS}
        lignes.append(ligne)
        liens, tier = e.get(_LIENS), e.get("reliability_tier")
        if not liens or not tier:
            continue
        for path in ([liens] if isinstance(liens, str) else liens):
            index.setdefault(path, []).append((e["id"], tier))
    for path in index:
        index[path].sort()
    return index, lignes


# ── Ancres matérielles de fixture ────────────────────────────────────────────────────────────────
# `_NEANT` est l'ancre par défaut des sections 1-14, écrites AVANT la capacité 4 : `status="none"`
# signifie « l'émetteur n'a rien publié qui puisse périmer quoi que ce soit », donc toute entry y est
# `courante` et ces sections mesurent exactement ce qu'elles mesuraient. Ce n'est PAS un neutre
# commode : c'est un état connu, distinct de `unavailable` (#49). Prendre `unavailable` comme défaut
# aurait fait basculer les 14 sections en bloc, prendre `found` aurait rendu leur résultat dépendant
# d'une date arbitraire.
_NEANT = MaterialEventLookup(status="none")


def _ancre(jour, items=("8.01",), form="8-K"):
    """Ancre `found` datée. `items` porte les items EDGAR — c'est par eux que passe le filtre des
    dépôts purement formels."""
    ev = MaterialEvent(form=form, event_date=jour, filing_date=jour, items=tuple(items),
                       accession=f"acc-{jour.isoformat()}-{'_'.join(items) or 'none'}")
    return MaterialEventLookup(status="found", event=ev, cik=1, recents=(ev,))


def dim_cov(dimension, fondations=None):
    """Squelette de dimension tel que le LLM le rend (fondations ignorées : le backend les réécrit)."""
    s = _SPEC[dimension]
    return {"dimension": dimension, "tier_plancher": s["tier_plancher"],
            "champs_requis": list(s["champs_requis"]), "fondations": fondations or [],
            "champs_non_fondables": [], "champs_perimes": [], "tier_atteint": None, "ok": True}


def run(dims_qual, entries, dims_struct=None, ticker_id="NVDA", ancre=_NEANT, motifs=None):
    cov = {"structuree": {"dimensions": dims_struct or [], "bloc_ok": True},
           "qualitative_marche": {"dimensions": dims_qual, "bloc_ok": True}}
    index, lignes = _index_fixture(entries)
    recompute_coverage(cov, lignes, ancre=ancre, index_couverture=index,
                       ticker_id=ticker_id, motifs_out=motifs)
    return cov


def appliquer(rep, entries, *, ancre=_NEANT, ticker_id="NVDA"):
    """`_apply_deterministic_overrides` — la fonction de PRODUCTION — avec l'index de fixture.

    Un seul point de passage (#46) : l'index est un argument requis depuis la 036, et le poser sur
    les huit sites d'appel garantirait d'en oublier un au prochain changement de signature.
    """
    index, lignes = _index_fixture(entries)
    _apply_deterministic_overrides(rep, lignes, ancre=ancre, index_couverture=index,
                                   ticker_id=ticker_id)


print("\n1. _tier_ge — comparaison de plancher (A meilleur)")
check("A ≥ B+", _tier_ge("A", "B+"))
check("B+ ≥ B+", _tier_ge("B+", "B+"))
check("B NON ≥ B+ (le bug #54)", not _tier_ge("B", "B+"))
check("A- NON ≥ A", not _tier_ge("A-", "A"))
check("None ne satisfait jamais", not _tier_ge(None, "B"))

print("\n2. _plancher_for — plancher par champ, lu dans FIELD_PROFILES (#46)")
# Jusqu'au 2026-09-08 le dégradé vivait dans `curator.FIELD_PLANCHER_OVERRIDES`, une SECONDE table
# de planchers à côté de `FIELD_PROFILES`. Deux tables d'accord restent deux tables : c'est celle-ci
# qui a empêché le desserrage B+ → B de #50 d'atteindre la porte. Ce qui se vérifie désormais est que
# la porte applique la table de DOCTRINE, et que le champ y déclare son desserrage.
check("croissance_marche_historique → B (desserrage déclaré)",
      _plancher_for("marche", "croissance_marche_historique", "B+") == "B")
check("champ NON desserré → plancher de sa dimension",
      _plancher_for("produits", "description", "B+") == "B+")
# `marche.structure_5forces` tenait ce rôle jusqu'au 2026-09-08 : il est desserré à B lui aussi
# (#50), ce qui ne se voyait pas tant que la porte lisait la seconde table. Le contre-exemple doit
# donc venir d'un champ qui, lui, ne desserre rien — sinon les deux asserts disent la même chose.
check("un champ desserré ne desserre pas ses voisins",
      _plancher_for("produits", "unit_economics", "B+") == "B+")
check("le dégradé vient de FIELD_PROFILES, pas d'une seconde table",
      FIELD_PROFILES["marche.croissance_marche_historique"]["plancher"] == "B")
check("le desserrage est DÉCLARÉ, jamais tacite",
      bool((FIELD_PROFILES["marche.croissance_marche_historique"].get("desserrage") or "").strip()),
      "→ desserrage tacite : le trou de feedback_optional_schema_gate")

print("\n3. MVDD_FIELD_PATHS — vocabulaire fermé de l'index")
check("chemins complets uniquement", all("." in p for p in MVDD_FIELD_PATHS))
check("business_model.description présent", "business_model.description" in MVDD_FIELD_PATHS)
check("produits.description présent (homonyme distinct)", "produits.description" in MVDD_FIELD_PATHS)
check("nom nu absent", "description" not in MVDD_FIELD_PATHS)
check("un chemin par champ requis",
      len(MVDD_FIELD_PATHS) == sum(len(s["champs_requis"]) for s in MVDD_SPEC))

print("\n4. L'index n'a AUCUN ÉMETTEUR entre le lot 2b et le lot 2c — et la porte refuse de prononcer")
# _INDEX_SANS_EMETTEUR — écart déclaré, sur la forme de #52 : il vit dans le check du lot qui l'a
# créé et virera au vert de lui-même le jour du câblage, plutôt que dans un `TODO` que personne ne
# relit. Ce qui se garde ici n'est pas « l'index est vide » mais la DISTINCTION entre deux états qui
# se ressemblent et se lisent à l'opposé : « personne n'écrit les liens » (on ne SAIT pas ce que le
# corpus fonde) et « l'émetteur rend zéro lien » (on sait qu'il ne fonde rien). Confondre les deux
# ferait tomber les 19 champs en `non_couvert`, donc dériver `lacune`, donc prescrire 19 mandats de
# COLLECTE sur une base qui contient déjà la matière — un verdict faux se corrige, un REMÈDE faux
# fait dépenser.
_INDEX_SANS_EMETTEUR = index_couverture_pour("NVDA")
check("aujourd'hui, l'index n'a aucun émetteur (le dispatch du lot 2c n'existe pas)",
      _INDEX_SANS_EMETTEUR is None,
      "→ si ce n'est plus None, le câblage est fait : cette section doit être RETIRÉE, pas adaptée")
check("le détenteur du motif le NOMME (`covers` archivée, dispatch absent)",
      "aucun émetteur" in MOTIF_SANS_EMETTEUR and "question_coverage" in MOTIF_SANS_EMETTEUR,
      f"→ {MOTIF_SANS_EMETTEUR[:80]}")
try:
    exiger_index_couverture(None)
    check("sans émetteur, la porte LÈVE au lieu de prononcer", False, "→ aucune exception")
except CouvertureSansEmetteur:
    check("sans émetteur, la porte LÈVE au lieu de prononcer", True)
# … et le refus est prononcé AVANT toute dépense (#40) : c'est `recompute_coverage` elle-même qui
# exige, pas un appelant qui aurait pu l'oublier.
try:
    recompute_coverage({"structuree": {"dimensions": [], "bloc_ok": True},
                        "qualitative_marche": {"dimensions": [dim_cov("risques")], "bloc_ok": True}},
                       [entry(1, "A", ["risques.risques_cles"])],
                       ancre=_NEANT, index_couverture=None, ticker_id="NVDA")
    check("`recompute_coverage(index_couverture=None)` refuse", False, "→ elle a prononcé")
except CouvertureSansEmetteur:
    check("`recompute_coverage(index_couverture=None)` refuse", True)
# ZÉRO LIEN N'EST PAS L'ABSENCE D'ÉMETTEUR — l'autre moitié de la distinction. Un index vide mais
# PRÉSENT est un verdict légitime : le corpus ne fonde rien, et la porte le dit sans lever.
_vide = run([dim_cov("risques")], [entry(1, "A", None)])["qualitative_marche"]["dimensions"][0]
check("un émetteur qui rend zéro lien fait PRONONCER `non_couvert`, il ne fait pas lever",
      _vide["champs_non_fondables"] == list(_SPEC["risques"]["champs_requis"]),
      f"→ {_vide['champs_non_fondables']}")

# Les règles de construction de l'index, éprouvées AU POINT DE LECTURE (la porte), jamais sur le
# constructeur de fixture — ce dernier n'est pas du code de production, l'asserter serait tester le
# test. Ce qui compte est ce que la porte FAIT de chaque cas.
_cov4 = run([dim_cov("risques"), dim_cov("marche")], [
    entry(1, "A", ["risques.risques_cles", "marche.structure_5forces"]),
    entry(2, "B+", ["risques.risques_cles"]),
    entry(3, "A", None),                       # aucun lien : ne fonde rien
    entry(4, "A", "risques.risques_cles"),     # chaîne nue : un lien quand même
    entry(5, None, ["risques.risques_cles"]),  # sans tier : rien à comparer au plancher
    entry(6, "B", ["marche.croissance_marche_historique"], "web_search_reputable"),
])
_rq4 = _cov4["qualitative_marche"]["dimensions"][0]
_fond4 = {f["champ"]: f["entry_ids"] for f in _rq4["fondations"]}
check("multi-champ : la MÊME entry fonde deux dimensions",
      _rq4["ok"] is True and _cov4["qualitative_marche"]["dimensions"][1]["ok"] is True,
      f"→ {_rq4['champs_non_fondables']}")
check("agrégation par champ, triée par id, et rien d'autre",
      _fond4.get("risques_cles") == [1, 2, 4], f"→ {_fond4.get('risques_cles')}")
check("une entry sans lien ne fonde rien (fin du fallback tier-only de la 028)",
      3 not in _fond4.get("risques_cles", []))
check("une entry sans tier est écartée (aucun terme à comparer au plancher)",
      5 not in _fond4.get("risques_cles", []))

print("\n5. recompute_coverage — le plancher mord, et il est PAR CHAMP")
# MÊME TIER, DEUX SORTS. Une entry tier B fonde `marche.structure_5forces` (plancher de champ B,
# desserrage déclaré #50) et ne fonde PAS `produits.description` (plancher de champ B+). C'est bien
# le plancher par champ qu'on éprouve, pas celui de la dimension.
# ⚠️ Ce couple vivait auparavant à l'intérieur de `marche`, dont les deux champs avaient des
# planchers différents. Ils ne l'ont plus : la capacité 4 a fait descendre les DEUX à B en câblant
# `FIELD_PROFILES` (le desserrage de #50 n'atteignait pas la porte). Le contraste se prend donc
# désormais entre deux dimensions — sans quoi la section resterait verte en ne discriminant plus
# rien (`feedback_fixture_copiee_du_reel`, versant « non discriminante »).
cov = run([dim_cov("marche"), dim_cov("produits")], [
    entry(54, "B", ["marche.structure_5forces"], "agent_synthesis"),
    entry(55, "B", ["marche.croissance_marche_historique"], "web_search_reputable"),
    entry(56, "B", ["produits.description"], "web_search_reputable"),
    entry(57, "A", ["produits.unit_economics"]),
])
md, pd_ = cov["qualitative_marche"]["dimensions"]
check("marche : une entry B fonde structure_5forces (plancher de champ B)",
      md["champs_non_fondables"] == [], f"→ {md['champs_non_fondables']}")
check("produits : la MÊME entry B ne fonde pas description (plancher de champ B+)",
      pd_["champs_non_fondables"] == ["description"], f"→ {pd_['champs_non_fondables']}")
check("dimension produits ok=False", pd_["ok"] is False)
check("tier_atteint reflète la seule fondation qui tient (A)",
      pd_["tier_atteint"] == "A", f"→ {pd_['tier_atteint']}")
check("seule la fondation au-dessus du plancher est retenue",
      [f["champ"] for f in pd_["fondations"]] == ["unit_economics"], f"→ {pd_['fondations']}")

# Le plancher mord toujours SOUS le champ desserré : B est un plancher, pas une porte ouverte.
cov = run([dim_cov("marche")], [
    entry(58, "C+", ["marche.structure_5forces"], "web_search_generic"),
    entry(59, "B", ["marche.croissance_marche_historique"], "web_search_reputable"),
])
md = cov["qualitative_marche"]["dimensions"][0]
check("une entry C+ ne fonde pas un champ desserré à B",
      md["champs_non_fondables"] == ["structure_5forces"], f"→ {md['champs_non_fondables']}")

print("\n6. recompute_coverage — l'index DÉCOUVRE, il ne filtre plus des citations")
# LE cas qui faisait osciller le verdict : le LLM ne cite RIEN (fondations=[]), mais une entry
# taguée existe en base → le champ est fondé quand même.
cov = run([dim_cov("risques", fondations=[])], [entry(28, "A", ["risques.risques_cles"])])
rd = cov["qualitative_marche"]["dimensions"][0]
check("champ fondé SANS citation du LLM (fin du faux creux)", rd["ok"] is True, f"→ {rd}")
check("fondations RÉÉCRITES depuis l'index",
      rd["fondations"] == [{"champ": "risques_cles", "entry_ids": [28]}], f"→ {rd['fondations']}")
check("tier_atteint dérivé des entries retenues", rd["tier_atteint"] == "A")

# … et symétriquement : une citation LLM sans entry taguée derrière ne fonde plus rien.
cov = run([dim_cov("risques", fondations=[{"champ": "risques_cles", "entry_ids": [28]}])],
          [entry(28, "A", None)])
check("citation LLM sur entry NON taguée → non fondé (fin du fallback tier-only)",
      cov["qualitative_marche"]["dimensions"][0]["champs_non_fondables"] == ["risques_cles"])

print("\n7. Chemin complet — `description` ne traverse pas les dimensions")
cov = run([dim_cov("produits")],
          [entry(20, "A", ["produits.description"]), entry(53, "A-", ["produits.unit_economics"])],
          dims_struct=[dim_cov("business_model")])
bm = cov["structuree"]["dimensions"][0]
pr = cov["qualitative_marche"]["dimensions"][0]
check("produits.description fondé", "description" not in pr["champs_non_fondables"])
check("produits ok (description + unit_economics)", pr["ok"] is True, f"→ {pr['champs_non_fondables']}")
check("business_model.description NON fondé par le tag produits",
      "description" in bm["champs_non_fondables"], f"→ {bm['champs_non_fondables']}")

print("\n8. _exigences — le LLM peut RESSERRER, jamais DESSERRER")
r, p = _exigences("business_model", {"champs_requis": ["description"], "tier_plancher": "C"})
check("champ requis retiré par le LLM → réintroduit",
      set(r) >= set(_SPEC["business_model"]["champs_requis"]), f"→ {r}")
check("plancher assoupli (C) → ramené au socle B+", p == "B+", f"→ {p}")
r2, p2 = _exigences("business_model",
                    {"champs_requis": ["description", "part_recurrente_cloud"], "tier_plancher": "A"})
check("champ ajouté par le LLM → conservé", "part_recurrente_cloud" in r2)
check("socle en tête, ajouts ensuite (ordre stable)",
      r2[:3] == _SPEC["business_model"]["champs_requis"], f"→ {r2}")
check("plancher resserré (A) → conservé", p2 == "A", f"→ {p2}")
r3, p3 = _exigences("risques", {})
check("dimension sans proposition → socle MVDD", r3 == _SPEC["risques"]["champs_requis"] and p3 == "B")

print("\n9. reconcile_gaps — bijection champs_non_fondables ↔ gaps")
# croissance est fondée à son plancher B (desserrage déclaré) ; structure_5forces ne l'est pas (C+
# reste sous B). Le gap proposé par le modèle vise les deux : il doit être raboté.
cov = run([dim_cov("marche")], [
    entry(54, "C+", ["marche.structure_5forces"], "web_search_generic"),
    entry(55, "B", ["marche.croissance_marche_historique"], "web_search_reputable"),
])
report = {"gaps": [
    {"dimension": "marche", "champs_cibles": ["structure_5forces", "croissance_marche_historique"],
     "manque": "x", "queries_suggerees": [], "priorite": "haute", "coverage_actuelle": "B",
     "origine": "curator"}]}
reconcile_gaps(report, cov)
g = report["gaps"]
check("gap raboté aux non-fondables réels (croissance est fondée à son plancher B)",
      len(g) == 1 and g[0]["champs_cibles"] == ["structure_5forces"], f"→ {g}")
report2 = {"gaps": []}
reconcile_gaps(report2, cov)
check("gap synthétisé pour un non-fondable orphelin",
      any("structure_5forces" in x["champs_cibles"] for x in report2["gaps"]))

print("\n10. Dispense RETIRÉE — croissance_marche_historique se fonde désormais (2026-08-31)")
# La dispense disait « aucune source accessible à un tier suffisant ». C'était vrai de la table de
# domaines, pas du monde : depuis #32 les cabinets d'études sont `web_search_reputable` (plafond B),
# soit exactement le plancher dégradé du champ. Le retrait ne DESSERRE rien — il rend le champ
# bloquant, et c'est une entry réelle qui le fonde (NVDA 117-119 : Omdia, IDC, TechInsights).
check("croissance n'est PLUS une lacune déclarée pour NVDA",
      "marche.croissance_marche_historique" not in nonblocking_gaps_for("NVDA"))
check("business_model.recurrence_pct reste dispensé (fait NVIDIA, lui, toujours vrai)",
      "business_model.recurrence_pct" in nonblocking_gaps_for("NVDA"))

cov9 = run([dim_cov("marche")], [entry(56, "A-", ["marche.structure_5forces"], "agent_synthesis")])
md9 = cov9["qualitative_marche"]["dimensions"][0]
check("croissance non portée → comptée comme non fondable (elle BLOQUE)",
      "croissance_marche_historique" in md9["champs_non_fondables"], f"→ {md9}")
check("marche ok=False tant qu'elle manque", md9["ok"] is False, f"→ {md9}")

cov10 = run([dim_cov("marche")], [
    entry(57, "A-", ["marche.structure_5forces"], "agent_synthesis"),
    entry(58, "B", ["marche.croissance_marche_historique"], "web_search_reputable"),
])
md10 = cov10["qualitative_marche"]["dimensions"][0]
check("un cabinet d'études tier B fonde croissance (plancher B, desserrage déclaré)",
      "croissance_marche_historique" not in md10["champs_non_fondables"], f"→ {md10}")
check("marche ok=True une fois les deux champs fondés", md10["ok"] is True, f"→ {md10}")

# Le plancher mord toujours : si C+ passait, le retrait de la dispense aurait desserré le gate au
# lieu de le rendre exigeant.
cov11 = run([dim_cov("marche")], [
    entry(59, "A-", ["marche.structure_5forces"], "agent_synthesis"),
    entry(60, "C+", ["marche.croissance_marche_historique"], "web_search_generic"),
])
check("une entry C+ ne fonde PAS croissance (le plancher B tient)",
      "croissance_marche_historique"
      in cov11["qualitative_marche"]["dimensions"][0]["champs_non_fondables"])

rep9 = {"incertitudes_investissables": []}
_declare_nonblocking_gaps(rep9, cov9, "NVDA")
check("plus aucune incertitude « croissance » déclarée (la dispense n'existe plus)",
      not any("croissance" in u["question"].lower() for u in rep9["incertitudes_investissables"]))

print("\n11. format_entries_for_prompt — le listing ne montre QUE la ligne")
# ⚠️ Cette section éprouvait « l'index est visible au modèle » : chaque ligne annonçait « · couvre
# business_model.drivers_revenus », lu sur `e["covers"]`. La mention est partie avec la colonne
# (036). Ce qui la remplace n'est PAS un grep d'absence — il se met en défaut sur la prose (#56) —
# mais l'assert POSITIF que le listing est une fonction des seules colonnes de la ligne : deux
# entries identiques à la couverture près y sont indiscernables, ce qui est exactement ce que « la
# couverture n'est pas une propriété de l'entry » veut dire (#57). Le jour où le lot 2c la rendra
# visible, elle viendra par JOINTURE au site qui construit le contexte, et cet assert devra être
# retiré sciemment plutôt que contourné.
_ligne_19 = {"id": 19, "title": "Data Center", "content": "x", "reliability_tier": "A",
             "source_type": "company_ir_official", "version": 1}
listing = format_entries_for_prompt([
    dict(_ligne_19),
    {"id": 25, "title": "Buybacks", "content": "y", "reliability_tier": "A",
     "source_type": "edgar_official", "version": 1},
])
check("le listing rend une ligne par entry, triée par id",
      [l.split()[0] for l in listing.split("\n")] == ["#19", "#25"], f"→ {listing}")
check("il porte les trois axes lisibles sur la ligne (tier, source, contenu)",
      "A · company_ir_official" in listing and "Data Center" in listing, f"→ {listing}")
# La preuve par indiscernabilité : la MÊME entry, à qui l'on ajoute un lien de couverture, produit
# le MÊME texte. Un `not in` seul serait vert sur un listing vide.
_avec_lien = dict(_ligne_19, **{_LIENS: ["business_model.drivers_revenus"]})
check("deux entries qui ne diffèrent que par leur couverture sont indiscernables au modèle",
      format_entries_for_prompt([_avec_lien]) == format_entries_for_prompt([dict(_ligne_19)]),
      "→ le listing lit encore un champ de couverture sur la ligne")

print("\n12. Intégration — ReadinessReport valide, verdict = fonction du corpus")


def full_report(coverage, verdict="not_ready"):
    return {"schema_version": "v2.0.0", "verdict": verdict, "coverage": coverage,
            "entries_par_tier": {"tier_A": 0, "tier_B": 0, "tier_C_llm_memory": 0, "total": 0},
            "indicateurs": {"qualite_info": 0.6, "conviction": 0.9, "marge_securite": 0.1},
            "incertitudes_bloquantes": [], "incertitudes_investissables": [],
            "gaps": [], "arret_pareto_recommande": False, "rationale": "test"}


def corpus_complet():
    """Une entry tier A par champ requis (hors lacune déclarée) — le cas `ready`."""
    ents, eid = [], 100
    for s in MVDD_SPEC:
        for champ in s["champs_requis"]:
            path = f"{s['dimension']}.{champ}"
            if path in nonblocking_gaps_for("NVDA"):
                continue
            ents.append(entry(eid, "A", [path]))
            eid += 1
    return ents


ents = corpus_complet()
cov_ready = {"structuree": {"dimensions": [dim_cov(d) for d in
                                           ("business_model", "financials", "valorisation")], "bloc_ok": True},
             "qualitative_marche": {"dimensions": [dim_cov(d) for d in
                                                   ("produits", "positionnement", "marche",
                                                    "management_allocation", "risques")], "bloc_ok": True}}
rep = full_report(cov_ready)
appliquer(rep, ents, ancre=_NEANT, ticker_id="NVDA")
check("verdict recalculé = ready", rep["verdict"] == "ready", f"→ {rep['verdict']}")
rep["context_pack_entry_id"] = 999  # posé par run_readiness quand ready
try:
    ReadinessReport.model_validate(rep)
    check("ReadinessReport valide (ready)", True)
except Exception as e:  # noqa: BLE001
    check("ReadinessReport valide (ready)", False, str(e)[:200])

# DÉTERMINISME : deux passes sur le MÊME corpus, avec des `fondations` LLM différentes (ce qui
# faisait basculer le verdict avant la 029) → verdict et couverture strictement identiques.
cov_a = {"structuree": {"dimensions": [dim_cov(d) for d in
                                       ("business_model", "financials", "valorisation")], "bloc_ok": True},
         "qualitative_marche": {"dimensions": [dim_cov(d) for d in
                                               ("produits", "positionnement", "marche",
                                                "management_allocation", "risques")], "bloc_ok": True}}
cov_b = {"structuree": {"dimensions": [dim_cov(d, [{"champ": "description", "entry_ids": [1]}]) for d in
                                       ("business_model", "financials", "valorisation")], "bloc_ok": True},
         "qualitative_marche": {"dimensions": [dim_cov(d, []) for d in
                                               ("produits", "positionnement", "marche",
                                                "management_allocation", "risques")], "bloc_ok": True}}
ra, rb = full_report(cov_a), full_report(cov_b, verdict="too_hard")
appliquer(ra, ents, ancre=_NEANT, ticker_id="NVDA")
appliquer(rb, ents, ancre=_NEANT, ticker_id="NVDA")
check("verdict indépendant des citations LLM", ra["verdict"] == "ready")
check("couverture identique à corpus figé", ra["coverage"] == rb["coverage"])

# THIN : on retire l'entry qui fonde structure_5forces → bloc qualitatif tombe, structuré intact
ents_thin = [e for e in ents if e[_LIENS] != ["marche.structure_5forces"]]
check("le corpus THIN diffère bien du corpus complet (sinon la section ne prouve rien)",
      len(ents_thin) == len(ents) - 1, f"→ {len(ents_thin)} vs {len(ents)}")
cov_thin = {"structuree": {"dimensions": [dim_cov(d) for d in
                                          ("business_model", "financials", "valorisation")], "bloc_ok": True},
            "qualitative_marche": {"dimensions": [dim_cov(d) for d in
                                                  ("produits", "positionnement", "marche",
                                                   "management_allocation", "risques")], "bloc_ok": True}}
rep2 = full_report(cov_thin)
appliquer(rep2, ents_thin, ancre=_NEANT, ticker_id="NVDA")
check("verdict recalculé = thin_qualitative (5forces retiré du corpus)",
      rep2["verdict"] == "thin_qualitative", f"→ {rep2['verdict']}")
try:
    ReadinessReport.model_validate(rep2)
    check("ReadinessReport valide (thin, gaps reconciliés)", True)
except Exception as e:  # noqa: BLE001
    check("ReadinessReport valide (thin, gaps reconciliés)", False, str(e)[:200])

print("\n13. Dispense PAR EMETTEUR - aucun heritage silencieux (regression MSFT 2026-08-30)")
# Le trou : les dispenses etaient GLOBALES. Tout nouveau ticker heritait du passe-droit NVDA sur
# `business_model.recurrence_pct` - champ alors ni fonde, ni compte comme manque, avec un libelle
# parlant de NVIDIA injecte dans SES incertitudes. Une dispense enonce un fait sur un emetteur.
check("aucune dispense pour un ticker inconnu", nonblocking_gaps_for("MSFT") == {})
check("aucune dispense sans ticker (defaut sur)", nonblocking_gaps_for(None) == {})
check("dispense NVDA insensible a la casse", nonblocking_gaps_for("nvda") == nonblocking_gaps_for("NVDA"))

bm_nvda = run([], [], [dim_cov("business_model")], ticker_id="NVDA")["structuree"]["dimensions"][0]
bm_msft = run([], [], [dim_cov("business_model")], ticker_id="MSFT")["structuree"]["dimensions"][0]
check("NVDA : recurrence_pct dispense (absent des non-fondables)",
      "recurrence_pct" not in bm_nvda["champs_non_fondables"])
check("MSFT : recurrence_pct BLOQUE (aucun heritage)",
      "recurrence_pct" in bm_msft["champs_non_fondables"], f"-> {bm_msft['champs_non_fondables']}")
check("MSFT : marche.croissance_marche_historique bloque aussi",
      "croissance_marche_historique" in
      run([dim_cov("marche")], [], ticker_id="MSFT")["qualitative_marche"]["dimensions"][0]["champs_non_fondables"])

# Le libelle NVDA ne doit jamais atterrir dans les incertitudes d'un autre emetteur.
rep_msft = {"incertitudes_investissables": []}
_declare_nonblocking_gaps(rep_msft, run([dim_cov("marche")], [], [dim_cov("business_model")],
                                        ticker_id="MSFT"), "MSFT")
check("aucune incertitude NVDA injectee chez MSFT",
      rep_msft["incertitudes_investissables"] == [], f"-> {rep_msft['incertitudes_investissables']}")

# Un corpus complet SANS les champs dispenses ne peut plus etre `ready` pour un ticker sans dispense.
rep_msft_ready = full_report({"structuree": {"dimensions": [dim_cov(d) for d in
                                             ("business_model", "financials", "valorisation")], "bloc_ok": True},
                              "qualitative_marche": {"dimensions": [dim_cov(d) for d in
                                                     ("produits", "positionnement", "marche",
                                                      "management_allocation", "risques")], "bloc_ok": True}})
appliquer(rep_msft_ready, ents, ancre=_NEANT, ticker_id="MSFT")
check("corpus 'ready NVDA' n'est PAS ready pour MSFT (2 champs non fondes)",
      rep_msft_ready["verdict"] == "not_ready", f"-> {rep_msft_ready['verdict']}")


print("\n14. Narration contrainte — le rationale ne contredit plus son verdict (dette A, rapport #24)")

# Vocabulaire ferme : `ready` est une sous-chaine de `not_ready` et de `already`.
check("`not_ready` n'est pas lu comme `ready`",
      verdicts_nommes("le dossier est not_ready") == {"not_ready"})
check("`not ready` (espace) reconnu aussi",
      verdicts_nommes("le dossier est not ready") == {"not_ready"})
check("`already` ne declenche pas `ready`", verdicts_nommes("deja couvert, already vu") == set())
check("`ready` seul reconnu", verdicts_nommes("le dossier est ready") == {"ready"})
check("`thin_qualitative` reconnu",
      verdicts_nommes("=> thin_qualitative") == {"thin_qualitative"})
check("prose sans verdict = aucun", verdicts_nommes("bloc qualitatif incomplet (tier A-)") == set())

# Reproduction du rapport #24 : verdict `ready`, prose narrant `thin_qualitative`.
rep24 = full_report(cov_ready, verdict="ready")
rep24["rationale"] = ("Le socle EDGAR est complet et recent. Le bloc qualitatif-marche est "
                      "incomplet (tier A-), sous le plancher B+ requis => thin_qualitative. "
                      "Les 51 entries sont majoritairement tier A.")
appliquer(rep24, ents, ancre=_NEANT, ticker_id="NVDA")
r24 = rep24["rationale"]
check("la phrase narrant un autre verdict est RETIREE", "thin_qualitative." not in r24, f"-> {r24}")
check("le retrait est DECLARE, jamais silencieux", "1 phrase(s) du curator retiree(s)" in r24
      or "retirée(s)" in r24, f"-> {r24}")
check("l'en-tete porte le verdict recompute", r24.startswith("[Verdict recomputé : ready"), f"-> {r24[:60]}")
check("les phrases compatibles sont gardees", "Le socle EDGAR est complet" in r24)
check("la derniere phrase neutre est gardee", "51 entries" in r24)

# Le cas nominal ne doit pas etre mutile.
rep_ok = full_report(cov_ready, verdict="ready")
rep_ok["rationale"] = "Dossier complet, 44 entries tier A, aucune incertitude bloquante."
appliquer(rep_ok, ents, ancre=_NEANT, ticker_id="NVDA")
check("prose neutre integralement conservee",
      rep_ok["rationale"].endswith("Dossier complet, 44 entries tier A, aucune incertitude bloquante."))
check("mentionner SON PROPRE verdict reste permis",
      "ready" in constrain_rationale({"verdict": "ready", "rationale": "le dossier est ready."},
                                     cov_ready)["rationale"].split("]")[1])

# Contrat : rationale a min_length=1 — l'en-tete garantit un texte non vide meme si tout est retire.
vide = constrain_rationale({"verdict": "not_ready", "rationale": "thin_qualitative partout. ready ?"},
                           cov_ready)
check("rationale non vide meme si toute la prose est retiree", len(vide["rationale"]) > 1)
check("les 2 retraits sont comptes", "2 phrase(s)" in vide["rationale"], f"-> {vide['rationale']}")

# L'en-tete NOMME les champs non fondes : l'humain lit le motif, pas seulement le verdict.
cov_gap = {"structuree": {"dimensions": [dim_cov(d) for d in
                                         ("business_model", "financials", "valorisation")], "bloc_ok": True},
           "qualitative_marche": {"dimensions": [dim_cov(d) for d in
                                                 ("produits", "positionnement", "marche",
                                                  "management_allocation", "risques")], "bloc_ok": False}}
cov_gap["qualitative_marche"]["dimensions"][0]["champs_non_fondables"] = ["unit_economics"]
tete = constrain_rationale({"verdict": "thin_qualitative", "rationale": "RAS."}, cov_gap)["rationale"]
check("l'en-tete nomme le champ non fonde", "produits.unit_economics" in tete, f"-> {tete[:120]}")
check("l'en-tete dit quel bloc est incomplet", "qualitatif-marché incomplet" in tete, f"-> {tete[:120]}")

# ══════════════════════════════════════════════════════════════════════════════════════════════
# CAPACITÉ 4 — la porte de complétude à TROIS états (roadmap 02)
# ══════════════════════════════════════════════════════════════════════════════════════════════

_ANCRE_JUIN = _ancre(date(2026, 6, 1))            # postérieure à `_JADIS` : elle périme
_PANNE = MaterialEventLookup(status="unavailable", cik=1, raison="503 EDGAR")


def _seul(gaps: list) -> dict:
    """Le gap unique d'une liste — ou un gabarit VIDE si elle n'en contient pas exactement un.

    ⚠️ Un `gaps[0]` nu tue le script sur un `IndexError` dès que la liste est vide, c'est-à-dire
    exactement dans le cas négatif que la section existe pour attraper : le bilan disparaît, et une
    suite qui ne rend plus de bilan se lit comme un script mort, pas comme un échec nommé (2ᵉ des
    trois faux verts, `feedback_test_negatif_trois_faux_verts`). Mesuré : en supprimant
    `champs_perimes` de la porte, §17 mourait ici et §18/§19 n'étaient jamais exécutées."""
    return gaps[0] if len(gaps) == 1 else {
        "champs_cibles": [], "manque": "", "coverage_actuelle": "aucune", "remede": None}

print("\n15. Trois états — `couvert` / `couvert_perime` / `non_couvert` jamais confondus")
# `risques.risques_cles` BLOQUE sur l'actualité, `marche.croissance_marche_historique` non. Le même
# corpus, la même date, la même ancre : c'est le PROFIL DU CHAMP qui décide, pas l'âge tout seul.
_E_RISQUE = [entry(70, "A", ["risques.risques_cles"])]

d_courant = run([dim_cov("risques")], _E_RISQUE)["qualitative_marche"]["dimensions"][0]
check("couvert : sans événement matériel, la matière au plancher fonde",
      d_courant["ok"] is True and d_courant["champs_perimes"] == [], f"→ {d_courant}")
check("couvert : l'entry apparaît bien dans les fondations",
      d_courant["fondations"] == [{"champ": "risques_cles", "entry_ids": [70]}],
      f"→ {d_courant['fondations']}")

motifs = {}
d_perime = run([dim_cov("risques")], _E_RISQUE, ancre=_ANCRE_JUIN,
               motifs=motifs)["qualitative_marche"]["dimensions"][0]
check("couvert_perime : la MÊME entry ne fonde plus après l'événement",
      d_perime["champs_perimes"] == ["risques_cles"], f"→ {d_perime}")
check("couvert_perime : le champ compte aussi comme non fondable",
      d_perime["champs_non_fondables"] == ["risques_cles"], f"→ {d_perime}")
check("couvert_perime : rien ne reste dans les fondations (pas de fondation de façade)",
      d_perime["fondations"] == [] and d_perime["tier_atteint"] is None, f"→ {d_perime}")
check("couvert_perime : le motif NOMME l'entry et son ancienneté",
      "#70" in motifs.get("risques.risques_cles", "")
      and "perimee" in motifs.get("risques.risques_cles", ""),
      f"→ {motifs}")

d_lacune = run([dim_cov("risques")], [], ancre=_ANCRE_JUIN)["qualitative_marche"]["dimensions"][0]
check("non_couvert : aucune matière au plancher",
      d_lacune["champs_non_fondables"] == ["risques_cles"], f"→ {d_lacune}")
check("non_couvert n'est PAS couvert_perime (on ne rafraîchit pas ce qu'on n'a pas)",
      d_lacune["champs_perimes"] == [], f"→ {d_lacune}")

# `champs_perimes` est un SOUS-ENSEMBLE déclaré de `champs_non_fondables` — le contrat l'exige, et
# c'est ce qui garantit que le total des manques ne double pas quand on ajoute le troisième état.
for _nom, _d in (("courant", d_courant), ("périmé", d_perime), ("lacune", d_lacune)):
    check(f"[{_nom}] champs_perimes ⊆ champs_non_fondables",
          set(_d["champs_perimes"]) <= set(_d["champs_non_fondables"]), f"→ {_d}")

# LE contraste : même entry, même ancre, deux champs — seul celui dont le PROFIL bloque tombe.
d_nonbloq = run([dim_cov("marche")], [
    entry(71, "B", ["marche.croissance_marche_historique"], "web_search_reputable"),
    entry(72, "B", ["marche.structure_5forces"], "agent_synthesis"),
], ancre=_ANCRE_JUIN)["qualitative_marche"]["dimensions"][0]
check("un champ dont l'actualité NE bloque PAS reste couvert malgré l'événement",
      d_nonbloq["ok"] is True and d_nonbloq["champs_perimes"] == [], f"→ {d_nonbloq}")

# `indeterminable` n'est pas `perimee` (#53) : le champ tombe pareil, mais le motif dit la VRAIE
# cause. Confondre les deux ferait chercher une source plus récente là où il faut une source datable.
motifs_i = {}
run([dim_cov("risques")], [entry(73, "A", ["risques.risques_cles"], source_date=None)],
    ancre=_ANCRE_JUIN, motifs=motifs_i)
_m = motifs_i.get("risques.risques_cles", "")
check("entry non datable → le champ tombe, et le motif dit `indeterminable`",
      "indeterminable" in _m, f"→ {_m}")
check("… et il ne prétend PAS que l'entry est antérieure à l'événement",
      "antérieur de" not in _m, f"→ {_m}")

motifs_p = {}
run([dim_cov("risques")], _E_RISQUE, ancre=_PANNE, motifs=motifs_p)
_mp = motifs_p.get("risques.risques_cles", "")
check("flux injoignable → le champ tombe, et le motif NOMME la panne",
      "injoignable" in _mp and "503 EDGAR" in _mp, f"→ {_mp}")
check("une panne n'est jamais racontée comme « rien n'a changé » (#49)",
      "aucun 8-K" not in _mp, f"→ {_mp}")

print("\n16. ACCEPTATION — le même corpus vieillit sans qu'une seule ligne soit écrite")
# C'est le test central de la capacité : `couvert` → `couvert_perime` doit tenir à l'ARRIVÉE d'un
# événement, pas à une modification du corpus. Les entries sont comparées avant/après.
_avant = copy.deepcopy(ents)
rep_a = full_report(copy.deepcopy(cov_ready))
appliquer(rep_a, ents, ancre=_NEANT, ticker_id="NVDA")
check("ligne de base : ce corpus est `ready` sans événement matériel",
      rep_a["verdict"] == "ready", f"→ {rep_a['verdict']}")
check("ligne de base : aucune cause de non-readiness", rep_a["cause_non_ready"] is None,
      f"→ {rep_a['cause_non_ready']}")

rep_b = full_report(copy.deepcopy(cov_ready))
appliquer(rep_b, ents, ancre=_ANCRE_JUIN, ticker_id="NVDA")
check("ACCEPTATION : le même corpus devient `not_ready` à l'arrivée d'un 8-K postérieur",
      rep_b["verdict"] == "not_ready", f"→ {rep_b['verdict']}")
check("ACCEPTATION : et la cause est la PÉREMPTION, pas la lacune",
      rep_b["cause_non_ready"] == "peremption", f"→ {rep_b['cause_non_ready']}")
check("ACCEPTATION : le corpus n'a pas bougé d'un octet", ents == _avant,
      "→ la porte a MUTÉ les entries qu'elle lit")

# Les 9 champs qui basculent sont exactement ceux dont le profil bloque — la mesure de la ligne de
# base sur NVDA/MSFT en donnait 9 chacun. Un écart ici voudrait dire que la porte lit autre chose
# que `FIELD_PROFILES`.
_perimes_b = [f"{d['dimension']}.{c}"
              for b in (rep_b["coverage"]["structuree"], rep_b["coverage"]["qualitative_marche"])
              for d in b["dimensions"] for c in d["champs_perimes"]]
_bloquants = sorted(p for p, prof in FIELD_PROFILES.items()
                    if prof["actualite_bloquante"] and p not in nonblocking_gaps_for("NVDA"))
check("les champs basculés sont EXACTEMENT les champs bloquants du profil",
      sorted(_perimes_b) == _bloquants, f"→ {sorted(_perimes_b)} vs {_bloquants}")

# La porte est PURE : elle n'écrit rien. Le grep porte sur le CORPS des fonctions, docstrings
# retirées — un interdit énoncé dans sa propre docstring se lirait sinon comme sa violation
# (`feedback_grep_interdit_lit_sa_propre_enonciation`).
def _corps(fn) -> str:
    return inspect.getsource(fn).split('"""', 2)[-1]


_CORPS_PORTE = _corps(recompute_coverage) + _corps(reconcile_gaps)
for _interdit in ("UPDATE", "INSERT", "await ", "conn."):
    check(f"la porte ne contient pas `{_interdit.strip()}`", _interdit not in _CORPS_PORTE,
          "→ l'actualité serait persistée : exactement la cause n°2 du diagnostic #50")

print("\n17. Deux manques, DEUX remèdes — collecte vs rafraîchissement")
# `produits` : `description` BLOQUE (matière présente mais vieille → rafraîchir), `unit_economics`
# est absent (→ collecter). La dimension porte donc les deux gestes en même temps.
motifs_r = {}
cov_mix = run([dim_cov("produits")], [entry(80, "A", ["produits.description"])],
              ancre=_ANCRE_JUIN, motifs=motifs_r)
d_mix = cov_mix["qualitative_marche"]["dimensions"][0]
check("la dimension porte un périmé ET une lacune",
      d_mix["champs_non_fondables"] == ["description", "unit_economics"]
      and d_mix["champs_perimes"] == ["description"], f"→ {d_mix}")

# Le modèle a cru les deux champs vides et propose un gap de collecte sur les deux.
rep_mix = {"gaps": [{"dimension": "produits",
                     "champs_cibles": ["description", "unit_economics"],
                     "manque": "aucune source ne documente ces champs",
                     "queries_suggerees": ["produits nvidia"], "priorite": "haute",
                     "coverage_actuelle": "aucune", "origine": "curator"}]}
reconcile_gaps(rep_mix, cov_mix, motifs=motifs_r)
g_collecte = [g for g in rep_mix["gaps"] if g["remede"] == "collecte"]
g_refresh = [g for g in rep_mix["gaps"] if g["remede"] == "rafraichissement"]
check("le gap du LLM est raboté aux champs à COLLECTER",
      len(g_collecte) == 1 and g_collecte[0]["champs_cibles"] == ["unit_economics"],
      f"→ {g_collecte}")
check("aucun gap de collecte ne porte un champ périmé",
      all("description" not in g["champs_cibles"] for g in g_collecte), f"→ {g_collecte}")
check("un gap de RAFRAÎCHISSEMENT est synthétisé par le code",
      len(g_refresh) == 1 and g_refresh[0]["champs_cibles"] == ["description"], f"→ {g_refresh}")
check("le gap de rafraîchissement PORTE le motif (l'entry et sa cause)",
      "#80" in _seul(g_refresh)["manque"], f"→ {_seul(g_refresh)['manque'][:160]}")
check("… et il dit que la matière EXISTE (sinon il se lit comme une collecte)",
      "RAFRAÎCHIR" in _seul(g_refresh)["manque"]
      and _seul(g_refresh)["coverage_actuelle"] != "aucune", f"→ {_seul(g_refresh)}")
check("bijection maintenue : ∪ champs_cibles == champs_non_fondables",
      sorted(c for g in rep_mix["gaps"] for c in g["champs_cibles"])
      == sorted(d_mix["champs_non_fondables"]), f"→ {rep_mix['gaps']}")

# Sans aucun gap du modèle, le code synthétise les DEUX, avec leurs remèdes respectifs.
rep_vide = {"gaps": []}
reconcile_gaps(rep_vide, cov_mix, motifs=motifs_r)
check("gaps entièrement synthétisés : un par remède",
      sorted(g["remede"] for g in rep_vide["gaps"]) == ["collecte", "rafraichissement"],
      f"→ {[g['remede'] for g in rep_vide['gaps']]}")
check("le remède par défaut d'un gap est la collecte (le cas historique)",
      _seul([g for g in rep_vide["gaps"] if g["remede"] == "collecte"])["champs_cibles"]
      == ["unit_economics"], f"→ {rep_vide['gaps']}")

print("\n18. `cause_non_ready` — dérivée, jamais racontée")
_cas = (
    ("aucun manque → None", run([dim_cov("produits")], [
        entry(90, "A", ["produits.description"]), entry(91, "A", ["produits.unit_economics"])]), None),
    ("péremption seule", run([dim_cov("produits")], [
        entry(92, "A", ["produits.description"]), entry(93, "A", ["produits.unit_economics"])],
        ancre=_ANCRE_JUIN), "peremption"),
    ("lacune seule", run([dim_cov("produits")], [], ancre=_ANCRE_JUIN), "lacune"),
    ("les deux → mixte", cov_mix, "mixte"),
)
for _lib, _cov, _attendu in _cas:
    check(f"cause : {_lib}", compute_cause_non_ready(_cov) == _attendu,
          f"→ {compute_cause_non_ready(_cov)}")

# La cause traverse jusqu'au rapport validé, et jusqu'à l'en-tête que l'humain lit.
check("la cause est portée par le rapport", rep_b["cause_non_ready"] == "peremption")
try:
    ReadinessReport.model_validate({**rep_b, "context_pack_entry_id": None})
    check("ReadinessReport valide avec une cause de péremption", True)
except Exception as e:  # noqa: BLE001
    check("ReadinessReport valide avec une cause de péremption", False, str(e)[:200])
check("l'en-tête du rationale NOMME la cause",
      "(cause : peremption)" in rep_b["rationale"], f"→ {rep_b['rationale'][:140]}")
check("l'en-tête distingue les périmés des non fondés",
      "PÉRIMÉ(S)" in rep_b["rationale"], f"→ {rep_b['rationale'][:200]}")

print("\n19. Un dépôt purement FORMEL ne périme personne (fixture construite)")
# ⚠️ Fixture CONSTRUITE, et c'est délibéré : aucun 8-K des trois émetteurs mesurés n'est purement
# formel, donc une copie du flux réel serait NON DISCRIMINANTE — verte sans rien éprouver
# (`feedback_fixture_copiee_du_reel`, versant §2bis de check_material_events).
_FORMEL = ancre_substantielle(_ancre(date(2026, 6, 1), items=("9.01",)))
_MIXTE = ancre_substantielle(_ancre(date(2026, 6, 1), items=("8.01", "9.01")))
_6K = ancre_substantielle(_ancre(date(2026, 6, 1), items=(), form="6-K"))

check("un 8-K item 9.01 seul ne fournit AUCUNE ancre", _FORMEL.status == "none", f"→ {_FORMEL}")
d_formel = run([dim_cov("risques")], _E_RISQUE, ancre=_FORMEL)["qualitative_marche"]["dimensions"][0]
check("… donc il ne périme rien", d_formel["champs_perimes"] == [] and d_formel["ok"] is True,
      f"→ {d_formel}")
# Discriminance : la MÊME date, non filtrée, périme bien. Sans cette ligne, la précédente serait
# verte même si le filtre n'existait pas.
d_brut = run([dim_cov("risques")], _E_RISQUE,
             ancre=_ancre(date(2026, 6, 1), items=("9.01",)))["qualitative_marche"]["dimensions"][0]
check("la fixture est DISCRIMINANTE : non filtrée, la même date périme",
      d_brut["champs_perimes"] == ["risques_cles"], f"→ {d_brut}")

d_mixte = run([dim_cov("risques")], _E_RISQUE, ancre=_MIXTE)["qualitative_marche"]["dimensions"][0]
check("un 8-K portant AUSSI un item substantiel périme", d_mixte["champs_perimes"] == ["risques_cles"],
      f"→ {d_mixte}")
check("un 6-K SANS item reste une ancre (sans item ≠ sans substance)", _6K.status == "found",
      f"→ {_6K}")
d_6k = run([dim_cov("risques")], _E_RISQUE, ancre=_6K)["qualitative_marche"]["dimensions"][0]
check("… et il périme comme les autres", d_6k["champs_perimes"] == ["risques_cles"], f"→ {d_6k}")

# L'oubli d'un argument REQUIS est une TypeError au site d'appel, jamais un verdict laxiste par
# défaut. ⚠️ Deux arguments sont désormais requis (`ancre` depuis la capacité 4, `index_couverture`
# depuis la 036) : les omettre tous les deux d'un coup rendrait l'assert vert quel que soit celui
# qui a repris un défaut — il ne saurait plus lequel il garde. Un oubli à la fois, chacun nommé.
def _sans(**kw):
    _vide = {"structuree": {"dimensions": [], "bloc_ok": True},
             "qualitative_marche": {"dimensions": [], "bloc_ok": True}}
    try:
        recompute_coverage(_vide, [], **kw)
        return False
    except TypeError:
        return True


check("appeler la porte SANS ancre lève", _sans(index_couverture={}),
      "→ un défaut silencieux a été appliqué à `ancre`")
check("appeler la porte SANS index de couverture lève", _sans(ancre=_NEANT),
      "→ un défaut silencieux a été appliqué à `index_couverture` : l'absence d'émetteur "
      "se lirait « le corpus ne fonde rien »")
check("… et avec les deux, elle prononce (les asserts ci-dessus ne sont pas verts par accident)",
      not _sans(ancre=_NEANT, index_couverture={}))

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
