"""Vérification du REGISTRE NOMINATIF DES SOURCES (capacité 2, `02-spec-autorite-vs-actualite.md`).

Sans réseau ni modèle. Le registre est un **desserrage** — il ouvre l'admission de sources qui
valaient 0,50. Ce qui le rend acceptable tient à trois conditions, et ce check existe pour qu'aucune
ne puisse sauter en silence : rien n'est promu automatiquement · l'admission est nominative, datée
et motivée · le standing est accordé PAR NATURE, donc aucune source nouvelle ne peut fonder une
mesure chiffrée. Si l'une des trois tombe, la révision devient exactement le trou décrit par
`feedback_optional_schema_gate`.

  • §1  ATTEIGNABILITÉ (#32) — le tier accordé atteint réellement le plancher des trois champs
        desserrés par la capacité 0. Un registre qui n'accorderait pas assez serait un desserrage
        sans bénéficiaire, c'est-à-dire l'état qu'il est censé corriger.
  • §2  STANDING PAR COUPLE (source × nature) — c'est l'assert central de la capacité. Une source
        admise pour `interpretation` ne gagne AUCUN standing sur une `mesure`.
  • §3  DOMAINE HORS REGISTRE — reste `web_search_generic` 0,50, inchangé.
  • §4  JAMAIS DE DÉMOTION (#33) — une règle spécifique ne resserre pas la générique au passage :
        EDGAR, IR d'émetteur et presse financière traversent le registre intacts.
  • §5  PORTÉE — un émetteur hors du secteur admis, ou inconnu du registre, n'hérite de rien.
  • §6  DÉTENTEUR UNIQUE (#46) — les DEUX sites qui qualifient une source appellent `qualify` ;
        aucun ne ré-implémente la table. C'est la garde qui manquait à `_current_fact_ids` (#43).
  • §7  PLAFOND ≠ QUALIFICATION — `source_type_max` promeut, `classify_source_type` non. Replier
        l'un dans l'autre ferait traverser `qualify` à une source déjà promue, donc sans condition
        de nature : §2 deviendrait faux sans qu'aucun assert de §2 ne bouge.
  • §8  MÉTADONNÉES D'ADMISSION — date, motif écrit, natures au vocabulaire, tier accordable ; un
        tier non supporté LÈVE au lieu de se ranger sous le plafond le plus proche.
  • §9  GABARIT, PAS ACTEUR (#31) — un motif de portée sectorielle ne nomme aucun émetteur.

⚠️ **Pas de §état persisté, et c'est délibéré.** #43 exige de lire l'état en base plutôt que le
diff — mais la capacité 2 n'écrit RIEN : elle qualifie, au moment où une entry se crée. Ses deux
points de lecture (`worker._normalise_entry` avant le filtre de plancher, `service.store_knowledge`
à l'écriture) sont tous deux exercés ici, sur les mêmes entrées qu'en production. Ajouter une
section SQL aujourd'hui donnerait un assert vert sur zéro ligne — une fixture non discriminante,
le premier des trois faux verts (§24 de `CHANTIER_OUTILLAGE_DEV.md`). Elle se justifiera dès qu'une
entry admise existera en base.
"""
import inspect
import re
import sys
from datetime import date

from app.agents.v2 import worker as worker_mod
from app.agents.v2.common import FIELD_PROFILES, MVDD_SPEC, NATURES
from app.agents.v2.curator import FIELD_PLANCHER_OVERRIDES
from app.knowledge import service as service_mod
from app.knowledge.service import RELIABILITY_TABLE, compute_reliability
from app.knowledge.source_registry import (
    _ADMISES,
    _TICKER_SECTEURS,
    SourceAdmise,
    TierNonSupporte,
    admissions_pour,
    qualify,
    secteur_de,
)
from app.knowledge.websearch import classify_source_type, source_type_max

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


# Les trois champs desserrés B+ → B par la capacité 0 — ceux dont le registre est le bénéficiaire.
_CHAMPS_DESSERRES = (
    "positionnement.moat_preuves",
    "positionnement.position_vs_pairs",
    "marche.structure_5forces",
)
_TICKER_TEST = "RVMD"
_URL_ADMISE = "https://endpts.com/revolution-medicines-rasonque-approval/"


def _generique(url, ticker):
    return classify_source_type(url, ticker)


def _q(url, ticker, entry_type, covers, declaree=None):
    """Reproduit le chemin de PRODUCTION : qualification générique par domaine, puis registre."""
    return qualify(
        source_type=_generique(url, ticker), url=url, ticker_id=ticker,
        entry_type=entry_type, covers=covers, nature_declaree=declaree,
    )


print("1. atteignabilité (#32) — le tier accordé nourrit-il vraiment les champs desserrés ?")
_RANK = {t: i for i, t in enumerate(["C", "C+", "B-", "B", "B+", "A-", "A"])}
for src in _ADMISES:
    tier_effectif = RELIABILITY_TABLE[src.source_type_accorde][0]
    check(f"`{src.domain}` : tier accordé {src.tier} == tier réel du source_type ({tier_effectif})",
          tier_effectif == src.tier,
          f"→ {src.source_type_accorde} vaut {tier_effectif}, le registre annonce {src.tier}")
for champ in _CHAMPS_DESSERRES:
    doctrine = FIELD_PROFILES[champ]["plancher"]
    check(f"`{champ}` est desserré à B dans la doctrine", doctrine == "B", f"→ {doctrine}")
    atteignables = [s for s in _ADMISES if _RANK[s.tier] >= _RANK[doctrine]]
    check(f"`{champ}` a au moins une source admise à son plancher de doctrine", bool(atteignables),
          "→ desserrage sans bénéficiaire, l'état que la capacité 2 corrige")


print("1bis. portée RÉELLE du desserrage — la doctrine et la porte ne coïncident pas encore")
# Mesuré le 2026-09-05 : `FIELD_PROFILES` porte le desserrage B+ → B décidé en capacité 0, mais la
# porte de complétude lit encore `FIELD_PLANCHER_OVERRIDES`, qui ne contient QUE
# `marche.croissance_marche_historique`. Les trois champs desserrés sont donc toujours jugés à B+ au
# gate : une entry admise par le registre à B y serait rejetée, et le registre serait un desserrage
# SANS EFFET — précisément ce que la capacité 2 est censée corriger.
#
# Le câblage appartient à la capacité 4 (`curator.recompute_coverage` est son contexte partagé), et
# le faire ici déplacerait la ligne de base que son test central doit mesurer AVANT son lot. On ne
# corrige donc pas : on NOMME. La liste ci-dessous est l'écart connu ; quand la capacité 4 fera lire
# `FIELD_PROFILES` à la porte, elle se videra et les asserts resteront verts sans être touchés.
_DESSERRAGE_NON_CABLE = frozenset(_CHAMPS_DESSERRES)
_DIM_PLANCHER = {s["dimension"]: s["tier_plancher"] for s in MVDD_SPEC}
for champ in _CHAMPS_DESSERRES:
    doctrine = FIELD_PROFILES[champ]["plancher"]
    porte = FIELD_PLANCHER_OVERRIDES.get(champ, _DIM_PLANCHER[champ.split(".", 1)[0]])
    ecart = _RANK[porte] > _RANK[doctrine]
    check(f"`{champ}` : écart doctrine({doctrine})/porte({porte}) déclaré s'il existe",
          (not ecart) or champ in _DESSERRAGE_NON_CABLE,
          "→ écart non déclaré : le registre admet une source que la porte rejettera en silence")
non_cables_resolus = {c for c in _DESSERRAGE_NON_CABLE
                      if _RANK[FIELD_PLANCHER_OVERRIDES.get(c, _DIM_PLANCHER[c.split('.', 1)[0]])]
                      <= _RANK[FIELD_PROFILES[c]["plancher"]]}
check("la liste des écarts ne survit pas à leur câblage",
      not non_cables_resolus,
      f"→ {sorted(non_cables_resolus)} sont câblés : les retirer de `_DESSERRAGE_NON_CABLE`")

admissions_rvmd = {s.domain for s in _ADMISES if s.portee in {f"ticker:{_TICKER_TEST}",
                                                              f"secteur:{secteur_de(_TICKER_TEST)}"}}
check(f"{_TICKER_TEST} dispose d'au moins 2 sources admissibles (acceptation roadmap)",
      len(admissions_rvmd) >= 2, f"→ {sorted(admissions_rvmd)}")


print("\n2. standing par COUPLE (source × nature) — l'assert central de la capacité")
st_interp, nat_interp, _ = _q(_URL_ADMISE, _TICKER_TEST, "analysis", ["positionnement.moat_preuves"])
check("source admise + interprétation → promue", st_interp == "web_search_reputable",
      f"→ {st_interp}")
check("  et la nature reste `interpretation`", nat_interp == "interpretation", f"→ {nat_interp}")

st_mes, nat_mes, motif_mes = _q(_URL_ADMISE, _TICKER_TEST, "fact_financial", ["financials.levier"])
check("MÊME source + mesure → AUCUN standing gagné", st_mes == "web_search_generic",
      f"→ {st_mes} : une source admise pour l'interprétation fonde une mesure chiffrée")
check("  et la nature est bien `mesure` (l'assert ci-dessus n'est pas vide)", nat_mes == "mesure",
      f"→ {nat_mes} — sans quoi le refus porterait sur autre chose que le cas visé")
check("  le refus est DIT dans le motif, pas muet", "aucun standing" in motif_mes,
      f"→ {motif_mes}")
score_mes, tier_mes, _ = compute_reliability(st_mes, entry_type="fact_financial")
check("  la mesure reste chiffrée à 0,50 / C+", (score_mes, tier_mes) == (0.50, "C+"),
      f"→ {score_mes} / {tier_mes}")

# Le modèle ne peut pas contourner par une nature déclarée : seul `evenement` est promouvable, et
# une promotion vers `evenement` ne donne aucun standing sur `mesure` non plus.
st_decl, nat_decl, _ = _q(_URL_ADMISE, _TICKER_TEST, "fact_financial", ["financials.levier"],
                          declaree="interpretation")
check("déclaration `interpretation` par le modèle ignorée sur un fait", nat_decl == "mesure",
      f"→ {nat_decl}")
check("  et le source_type ne monte pas par ce chemin", st_decl == "web_search_generic",
      f"→ {st_decl} : le modèle achèterait son standing en déclarant sa nature")


print("\n3. domaine hors registre — inchangé")
st_inc, _, _ = _q("https://un-blog-quelconque.example/analyse", _TICKER_TEST, "analysis",
                  ["positionnement.moat_preuves"])
check("domaine inconnu reste `web_search_generic`", st_inc == "web_search_generic", f"→ {st_inc}")
check("  soit 0,50 / C+", RELIABILITY_TABLE[st_inc] == ("C+", 0.50), f"→ {RELIABILITY_TABLE[st_inc]}")


print("\n4. jamais de démotion (#33) — la règle générique traverse intacte")
for url, attendu, quoi in (
    ("https://www.sec.gov/Archives/edgar/data/x.htm", "edgar_official", "dépôt EDGAR"),
    ("https://ir.revmed.com/news/x", "company_ir_official", "IR d'émetteur"),
    ("https://www.reuters.com/business/x", "financial_press", "presse financière"),
    ("https://revmed.com/investors/x", "company_ir_official", "IR par chemin (#33)"),
):
    st, _, _ = _q(url, _TICKER_TEST, "fact_financial", ["financials.levier"])
    check(f"{quoi} : {attendu} conservé", st == attendu, f"→ {st}")
    check(f"  {quoi} : plafond affiché identique", source_type_max(url, _TICKER_TEST) == attendu,
          f"→ {source_type_max(url, _TICKER_TEST)}")


print("\n5. portée — aucune admission héritée par défaut")
st_nvda, _, _ = _q(_URL_ADMISE, "NVDA", "analysis", ["positionnement.moat_preuves"])
check("émetteur hors secteur admis n'hérite de rien", st_nvda == "web_search_generic",
      f"→ {st_nvda}")
st_none, _, _ = _q(_URL_ADMISE, None, "analysis", ["positionnement.moat_preuves"])
check("émetteur absent (None) n'hérite de rien", st_none == "web_search_generic", f"→ {st_none}")
check("secteur d'un ticker inconnu = None", secteur_de("ZZZZ") is None, f"→ {secteur_de('ZZZZ')}")
check("un ticker déclaré au registre a bien un secteur",
      secteur_de(_TICKER_TEST) in {v for v in _TICKER_SECTEURS.values()},
      f"→ {secteur_de(_TICKER_TEST)}")
check("le sous-domaine hérite du domaine admis",
      bool(admissions_pour("https://news.endpts.com/x", _TICKER_TEST)))
check("un domaine qui CONTIENT le nom admis n'hérite pas",
      not admissions_pour("https://endpts.com.phishing.example/x", _TICKER_TEST))


print("\n6. détenteur unique (#46) — les deux sites de qualification appellent la MÊME fonction")
for mod, nom in ((worker_mod, "worker"), (service_mod, "service")):
    src = inspect.getsource(mod)
    check(f"`{nom}` appelle `qualify(`", "qualify(" in src)
    check(f"`{nom}` ne ré-implémente pas la table d'admission",
          "_ADMISES" not in src and "endpts.com" not in src,
          "→ une admission recopiée re-divergera au correctif suivant")
src_service = inspect.getsource(service_mod)
check("`service` n'appelle plus `derive_nature` en direct (il passe par `qualify`)",
      "derive_nature(" not in src_service,
      "→ deux chemins de dérivation de nature coexistent")
# L'ordre est load-bearing : la nature se dérive du source_type GÉNÉRIQUE, le registre s'applique
# après. Le prouver par le comportement, pas par un grep : si l'ordre s'inversait, la promotion
# précéderait la dérivation et §2 ne pourrait plus refuser la mesure.
st_ordre, _, _ = qualify(source_type="web_search_reputable", url=_URL_ADMISE,
                         ticker_id=_TICKER_TEST, entry_type="analysis",
                         covers=["positionnement.moat_preuves"])
check("`qualify` ne promeut QUE depuis `web_search_generic`", st_ordre == "web_search_reputable",
      f"→ {st_ordre}")


print("\n7. plafond ≠ qualification — la séparation est load-bearing")
check("`classify_source_type` ignore le registre",
      classify_source_type(_URL_ADMISE, _TICKER_TEST) == "web_search_generic",
      "→ une source promue en amont traverserait `qualify` sans condition de nature")
check("`source_type_max` applique le registre",
      source_type_max(_URL_ADMISE, _TICKER_TEST) == "web_search_reputable",
      "→ le modèle verrait 0,50 sur une source admise et l'écarterait avant lecture")
check("le plafond n'est jamais inférieur à la qualification générique",
      all(_RANK[RELIABILITY_TABLE[source_type_max(u, _TICKER_TEST)][0]]
          >= _RANK[RELIABILITY_TABLE[classify_source_type(u, _TICKER_TEST)][0]]
          for u in (_URL_ADMISE, "https://www.sec.gov/x", "https://blog.example/x")))


print("\n8. métadonnées d'admission — nominative, datée, motivée")
for src in _ADMISES:
    check(f"`{src.domain}` porte une date d'admission", isinstance(src.admis_le, date))
    check(f"`{src.domain}` porte un motif écrit (≥ 60 car.)", len(src.motif.strip()) >= 60,
          f"→ {len(src.motif.strip())} caractères")
    check(f"`{src.domain}` : natures au vocabulaire fermé", set(src.natures) <= set(NATURES),
          f"→ {sorted(src.natures)}")
    check(f"`{src.domain}` : portée bien formée", re.fullmatch(r"(secteur|ticker):\S+", src.portee)
          is not None, f"→ {src.portee}")
    check(f"`{src.domain}` : aucun standing sur `mesure`", "mesure" not in src.natures,
          "→ une source non primaire fonderait un chiffre ; décision de doctrine, pas de ligne")
try:
    SourceAdmise(domain="x.example", portee="ticker:X", natures=frozenset({"interpretation"}),
                 tier="B+", admis_le=date(2026, 9, 5), motif="m" * 60)
    check("un tier non accordable LÈVE", False, "→ accordé en silence sous le plafond le plus proche")
except TierNonSupporte:
    check("un tier non accordable LÈVE", True)
try:
    SourceAdmise(domain="x.example", portee="ticker:X", natures=frozenset(), tier="B",
                 admis_le=date(2026, 9, 5), motif="m" * 60)
    check("une admission sans nature LÈVE", False, "→ admission vide acceptée")
except ValueError:
    check("une admission sans nature LÈVE", True)
try:
    SourceAdmise(domain="x.example", portee="ticker:X", natures=frozenset({"interpretation"}),
                 tier="B", admis_le=date(2026, 9, 5), motif="   ")
    check("une admission sans motif LÈVE", False, "→ admission non motivée acceptée")
except ValueError:
    check("une admission sans motif LÈVE", True)


print("\n9. gabarit, pas acteur (#31) — un motif sectoriel ne nomme aucun émetteur")
_TICKERS_CONNUS = tuple(_TICKER_SECTEURS)
for src in _ADMISES:
    if not src.portee.startswith("secteur:"):
        continue
    nommes = [t for t in _TICKERS_CONNUS if re.search(rf"\b{re.escape(t)}\b", src.motif)]
    check(f"`{src.domain}` : motif sectoriel sans émetteur nommé", not nommes, f"→ {nommes}")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
