"""Vérification de l'AXE `nature` d'une entry (capacité 1, `02-spec-autorite-vs-actualite.md`).

Sans réseau ni modèle, sauf §7 qui a besoin de la base (montage explicite, cf. README) — les six
premières sections tournent hors ligne et sont celles qui gardent la RÈGLE ; la septième vérifie
l'ÉTAT persisté après backfill, qui est l'autre moitié du travail (#43 : un correctif d'écriture ne
se juge pas sur son diff mais sur le comptage par clef).

  • §1  VOCABULAIRE — `mesure` / `evenement` / `interpretation`, domaine fermé, chaque valeur
        ATTEIGNABLE (#32). Une nature qu'aucune entrée ne peut produire serait un mot mort dans un
        CHECK SQL, et la porte n'aurait aucune branche pour elle.
  • §2  DEUX VOCABULAIRES — la nature d'une ENTRY ne se dérive JAMAIS de la nature dominante du
        CHAMP. C'est l'assert qui empêche la capacité 1 d'annuler le résultat de la capacité 0.
  • §3  `mesure` NE S'ACCORDE PAS PAR DÉFAUT — un entry_type inconnu, une couverture vide ou
        hétérogène retombent sur `interpretation` (#44 : « non qualifiable » n'est pas « mesure au
        rabais »).
  • §4  LA SOURCE L'EMPORTE — `llm_memory` / `agent_synthesis` ne mesurent jamais, quel que soit
        l'entry_type. Le filtre passe AVANT l'entry_type, sinon un `fact_financial` restitué de
        mémoire hériterait de l'autorité d'un dépôt.
  • §5  RESSERRER, JAMAIS DESSERRER (garde symétrique de #29) — une déclaration d'agent n'est
        honorée que pour promouvoir vers `evenement`. Les deux desserrages nommés (EDGAR requalifié
        `interpretation`, énoncé requalifié `mesure`) sont testés un par un.
  • §6  DÉTENTEUR UNIQUE (#46) — aucun producteur ne ré-implémente la règle : `store_knowledge` est
        le seul site d'écriture, et il n'accepte pas de `nature` en entrée.
  • §7  ÉTAT PERSISTÉ (optionnel, DATABASE_URL réelle) — acceptation de la roadmap : aucun NULL sur
        les entries actives, et les 13 entries déterministes du banc d'essai sont toutes `mesure`.

Hors ligne :
    docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
      --env-file checks/env.checks $IMG python checks/check_entry_nature.py
Avec l'état persisté (§7) — réseau `coolify` + vraie URL de base :
    docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
      --env-file checks/env.checks -e CHECK_DB_URL="postgresql://…/db_portfolio" \
      $IMG python checks/check_entry_nature.py
"""
import inspect
import os
import sys

from app.agents.v2.common import (
    FIELD_PROFILES,
    MVDD_FIELD_PATHS,
    NATURES,
    derive_nature,
)
from app.knowledge.service import store_knowledge

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def nature_of(**kw):
    return derive_nature(**kw)[0]


print("1. vocabulaire fermé et ATTEIGNABLE (#32) — un mot mort n'est pas une prudence")
check("vocabulaire = {mesure, evenement, interpretation}",
      NATURES == frozenset({"mesure", "evenement", "interpretation"}), f"→ {sorted(NATURES)}")
atteignables = {
    "mesure": nature_of(entry_type="fact_financial", source_type="edgar_official"),
    "interpretation": nature_of(entry_type="analysis", source_type="agent_synthesis"),
    "evenement": nature_of(entry_type="fact_qualitative", source_type="edgar_official",
                           declared="evenement"),
}
for attendue, obtenue in sorted(atteignables.items()):
    check(f"`{attendue}` est atteignable par au moins une entrée", obtenue == attendue,
          f"→ a rendu `{obtenue}`")
check("aucune nature hors vocabulaire n'est produite",
      set(atteignables.values()) <= NATURES, f"→ {sorted(set(atteignables.values()))}")

print("\n2. deux vocabulaires — la nature d'une ENTRY ≠ la nature dominante du CHAMP")
# Le contre-exemple est structurel, pas anecdotique : `valorisation.base_rate_anchor` est un champ
# d'INTERPRÉTATION (capacité 0 : ce qui doit le fonder est un raisonnement de classe de référence),
# et l'entry qui le remplit est une FRÉQUENCE EMPIRIQUE, donc une mesure. Si ce check virait au
# rouge, c'est que la capacité 1 aurait recopié la table de la capacité 0 au lieu de dériver.
check("`valorisation.base_rate_anchor` est un champ d'interprétation",
      FIELD_PROFILES["valorisation.base_rate_anchor"]["nature"] == "interpretation")
check("… et l'entry `base_rate` qui le fonde est une `mesure`",
      nature_of(entry_type="base_rate", source_type="financial_press",
                covers=["valorisation.base_rate_anchor"]) == "mesure")
# Symétrique : un champ de nature dominante `mesure` rempli par une synthèse d'agent reste une
# interprétation. Constaté en base (2 entries `analysis` couvrant `produits.unit_economics`).
check("`produits.unit_economics` est un champ de nature `mesure`",
      FIELD_PROFILES["produits.unit_economics"]["nature"] == "mesure")
check("… mais une entry `analysis` qui le couvre reste `interpretation`",
      nature_of(entry_type="analysis", source_type="agent_synthesis",
                covers=["produits.unit_economics"]) == "interpretation")

print("\n3. `mesure` ne s'accorde jamais par défaut (#44)")
check("entry_type inconnu → interpretation",
      nature_of(entry_type="type_jamais_vu", source_type="edgar_official") == "interpretation")
check("fact_qualitative sans covers → interpretation",
      nature_of(entry_type="fact_qualitative", source_type="edgar_official") == "interpretation")
check("fact_qualitative couvrant un champ d'interprétation → interpretation",
      nature_of(entry_type="fact_qualitative", source_type="edgar_official",
                covers=["risques.risques_cles"]) == "interpretation")
check("fact_qualitative couvrant UN champ de mesure → mesure",
      nature_of(entry_type="fact_qualitative", source_type="edgar_official",
                covers=["business_model.recurrence_pct"]) == "mesure")
# L'unanimité est la règle, et c'est le cas qui la distingue d'un « au moins un ».
check("covers HÉTÉROGÈNE (mesure + interprétation) → interpretation",
      nature_of(entry_type="fact_qualitative", source_type="edgar_official",
                covers=["business_model.recurrence_pct", "business_model.drivers_revenus"])
      == "interpretation")
check("covers HÉTÉROGÈNE — l'ordre des chemins ne change rien",
      nature_of(entry_type="fact_qualitative", source_type="edgar_official",
                covers=["business_model.drivers_revenus", "business_model.recurrence_pct"])
      == "interpretation")
check("chemin HORS vocabulaire `covers` → ne vote pas `mesure`, et ne lève pas",
      nature_of(entry_type="fact_qualitative", source_type="edgar_official",
                covers=["dimension_inexistante.champ"]) == "interpretation")
check("les chemins testés appartiennent bien au vocabulaire `covers` (fixture non périmée)",
      {"business_model.recurrence_pct", "business_model.drivers_revenus",
       "risques.risques_cles", "produits.unit_economics"} <= MVDD_FIELD_PATHS)

print("\n4. la source l'emporte sur l'entry_type — un énoncé ne mesure pas")
for src in ("llm_memory", "agent_synthesis"):
    check(f"fact_financial × `{src}` → interpretation",
          nature_of(entry_type="fact_financial", source_type=src) == "interpretation",
          "→ a hérité de l'autorité d'un dépôt")
    check(f"base_rate × `{src}` → interpretation",
          nature_of(entry_type="base_rate", source_type=src) == "interpretation")
    check(f"fact_qualitative × `{src}` couvrant un champ de mesure → interpretation",
          nature_of(entry_type="fact_qualitative", source_type=src,
                    covers=["business_model.recurrence_pct"]) == "interpretation")

print("\n5. le modèle peut RESSERRER, jamais desserrer (garde symétrique de #29)")
check("EDGAR requalifié `interpretation` par l'agent → reste `mesure`",
      nature_of(entry_type="fact_financial", source_type="edgar_official",
                declared="interpretation") == "mesure",
      "→ le desserrage a été honoré, le plancher A du champ est contournable")
check("… et le refus est DIT dans le motif, jamais silencieux",
      "écartée" in derive_nature(entry_type="fact_financial", source_type="edgar_official",
                                 declared="interpretation")[1])
check("énoncé d'agent requalifié `mesure` → reste `interpretation`",
      nature_of(entry_type="analysis", source_type="agent_synthesis",
                declared="mesure") == "interpretation",
      "→ un modèle s'est accordé l'autorité de la fiabilité")
check("promotion vers `evenement` depuis `interpretation` → honorée",
      nature_of(entry_type="fact_qualitative", source_type="edgar_official",
                covers=["risques.risques_cles"], declared="evenement") == "evenement")
check("promotion vers `evenement` depuis `mesure` → honorée",
      nature_of(entry_type="fact_financial", source_type="edgar_official",
                declared="evenement") == "evenement")
check("`evenement` ne se dégrade pas : une déclaration hors vocabulaire est ignorée",
      nature_of(entry_type="fact_financial", source_type="edgar_official",
                declared="rumeur") == "mesure")
check("déclaration identique à la dérivation → aucun bruit dans le motif",
      "écartée" not in derive_nature(entry_type="fact_financial", source_type="edgar_official",
                                     declared="mesure")[1])

print("\n6. détenteur unique (#46) — la nature n'est pas un paramètre d'écriture")
sig = inspect.signature(store_knowledge).parameters
check("`store_knowledge` n'accepte AUCUN paramètre `nature`", "nature" not in sig,
      "→ un producteur pourrait imposer la sienne et court-circuiter la règle")
check("`store_knowledge` accepte `nature_declaree` (proposition arbitrée)",
      "nature_declaree" in sig)
src = inspect.getsource(store_knowledge)
check("`store_knowledge` appelle `derive_nature`", "derive_nature(" in src)
# Le grep de source est un PROXY : il dit que l'appel existe, pas que sa valeur atteint l'INSERT.
# Le point de lecture réel est la colonne — c'est §7 qui l'éprouve.
check("… et insère la valeur dérivée (colonne présente dans l'INSERT)",
      "covers, nature" in src and ", nature," in src)

print("\n7. état persisté après backfill (acceptation de la roadmap)")
db_url = os.environ.get("CHECK_DB_URL")
if not db_url:
    # ⚠️ Un pré-requis manquant SORT en échec, il ne saute pas la section : une mesure incomplète
    # qui sort à 0 écrase de la vérité (`feedback_check_degrade_en_sortant_a_zero`).
    print("  FAIL §7 non exécutée — CHECK_DB_URL absente ; la moitié « état » n'a pas été mesurée")
    print(f"\n{'='*60}\n{ok} vérifications OK, {fail + 1} échec(s)")
    sys.exit(1)

import asyncio  # noqa: E402  (import tardif : §1-§6 doivent tourner sans base)

import asyncpg  # noqa: E402


async def _etat():
    conn = await asyncpg.connect(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        nuls = await conn.fetchval(
            "SELECT count(*) FROM knowledge_entries "
            "WHERE nature IS NULL AND superseded_by IS NULL AND is_deleted = FALSE")
        hors = await conn.fetchval(
            "SELECT count(*) FROM knowledge_entries WHERE nature IS NOT NULL AND NOT (nature = ANY($1))",
            sorted(NATURES))
        det = await conn.fetch(
            "SELECT id, nature FROM knowledge_entries "
            "WHERE ticker_id = 'RVMD' AND superseded_by IS NULL AND is_deleted = FALSE "
            "  AND entry_type IN ('fact_financial', 'base_rate') ORDER BY id")
        par_nature = await conn.fetch(
            "SELECT nature, count(*) n FROM knowledge_entries "
            "WHERE superseded_by IS NULL AND is_deleted = FALSE GROUP BY 1 ORDER BY 1")
        return nuls, hors, det, par_nature
    finally:
        await conn.close()


nuls, hors, det, par_nature = asyncio.run(_etat())
check("aucune entry active sans `nature`", nuls == 0, f"→ {nuls} NULL")
check("aucune `nature` hors vocabulaire en base", hors == 0, f"→ {hors} lignes")
# Le compte est ASSERTÉ, pas seulement affiché : une fixture qui rétrécit (un producteur qui cesse
# d'écrire) rendrait « toutes mesure » vrai sur zéro ligne — faux vert n°1 (§24).
check("RVMD porte bien 13 entries déterministes actives", len(det) == 13, f"→ {len(det)}")
for row in det:
    check(f"entry #{row['id']} (producteur déterministe) est `mesure`", row["nature"] == "mesure",
          f"→ `{row['nature']}`")
print("  — répartition des entries actives : "
      + ", ".join(f"{r['nature']}={r['n']}" for r in par_nature))

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
