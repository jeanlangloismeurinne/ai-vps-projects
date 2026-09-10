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
  • §2bis LA RÈGLE N'A QUE DES INGRÉDIENTS DE LA LIGNE (migration 036) — la branche `covers` est
        supprimée : elle faisait dépendre la nature de l'ASSERTION de ce qu'elle est censée
        COUVRIR (#57 en miniature) et, surtout, plaçait un ingrédient hors de la ligne, ce qui
        rendait la nature non rejouable (#48). Ce qu'on perd est mesuré, pas supposé.
  • §3  `mesure` NE S'ACCORDE PAS PAR DÉFAUT — un entry_type inconnu ou non déterministe retombe
        sur `interpretation` (#44 : « non qualifiable » n'est pas « mesure au rabais »). Le
        vocabulaire fermé est parcouru jeton par jeton, depuis son détenteur.
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
import typing

from app.agents.v2.common import (
    FIELD_PROFILES,
    NATURES,
    derive_nature,
)
from app.contracts.worker_delegation_schema import EntryType
from app.db.migrations._gen_036 import SUBSTITUTIONS_ENTRY_TYPE
from app.knowledge import ENTRIES_COURANTES
from app.knowledge.service import store_knowledge
from app.knowledge.source_registry import qualify

# Le vocabulaire FERMÉ d'`entry_type` (036), lu sur son détenteur (#46). §3 le parcourt jeton par
# jeton : une énumération recopiée ici resterait verte le jour où le contrat s'élargit.
_ENTRY_TYPES_FERMES = frozenset(typing.get_args(EntryType))

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
check("… et l'entry `fact_statistical` qui le fonde est une `mesure`",
      nature_of(entry_type="fact_statistical", source_type="financial_press") == "mesure")
# Symétrique : un champ de nature dominante `mesure` rempli par une synthèse d'agent reste une
# interprétation. Constaté en base (2 entries `analysis` couvrant `produits.unit_economics`).
check("`produits.unit_economics` est un champ de nature `mesure`",
      FIELD_PROFILES["produits.unit_economics"]["nature"] == "mesure")
check("… mais une entry `analysis` reste `interpretation`",
      nature_of(entry_type="analysis", source_type="agent_synthesis") == "interpretation")

print("\n2bis. la nature ne se dérive QUE de ce qui est DANS la ligne (migration 036)")
# ⚠️ La branche `covers` de `derive_nature` a été supprimée le 2026-09-10. Elle disait « une entry
# dont TOUS les champs couverts sont de nature dominante `mesure` est une mesure » — c'était #57 en
# miniature, et surtout le mode de panne de #48 : un ingrédient de la règle vivait hors de la ligne,
# donc la nature n'était PAS rejouable, alors que c'est la propriété pour laquelle son motif n'est
# justement pas persisté. La garde est écrite en POSITIF (la signature n'a que deux ingrédients
# arbitrables), jamais en `grep` d'un token absent : un grep de présence est satisfait par la prose
# et un grep d'absence est mis en défaut par elle (#56).
_ING = set(inspect.signature(derive_nature).parameters)
check("`derive_nature` n'a que trois entrées : deux colonnes + la proposition de l'agent",
      _ING == {"entry_type", "source_type", "declared"}, f"→ {sorted(_ING)}")
check("… et `covers` n'en est plus un ingrédient",
      "covers" not in _ING,
      "→ une règle dont un ingrédient n'est pas dans la ligne n'est pas rejouable (#48)")
# Ce qu'on PERD est mesuré, pas supposé : les 19 entries `fact_qualitative` qui tenaient leur
# `mesure` de cette seule branche deviennent `interpretation`. Le mouvement va dans le sens PRUDENT
# (#44), donc il ne fabrique aucune autorité — il en retire. L'assert le fige : le jour où un
# `fact_qualitative` redeviendrait `mesure`, c'est que la branche serait revenue par une porte
# dérobée.
check("un `fact_qualitative` EDGAR est désormais `interpretation`, quoi qu'il couvre",
      nature_of(entry_type="fact_qualitative", source_type="edgar_official") == "interpretation",
      "→ c'est le sens PRUDENT : la capacité revient par `nature_attendue` de la question (lot 2c)")

print("\n3. `mesure` ne s'accorde jamais par défaut (#44)")
check("entry_type inconnu → interpretation",
      nature_of(entry_type="type_jamais_vu", source_type="edgar_official") == "interpretation")
check("fact_qualitative → interpretation (défaut prudent)",
      nature_of(entry_type="fact_qualitative", source_type="edgar_official") == "interpretation")
check("… et le motif NOMME le défaut plutôt que de se taire",
      "défaut prudent" in derive_nature(entry_type="fact_qualitative",
                                        source_type="edgar_official")[1],
      f"→ {derive_nature(entry_type='fact_qualitative', source_type='edgar_official')[1]}")
# Le vocabulaire d'`entry_type` est FERMÉ depuis la 036 : les seuls jetons qui accordent `mesure`
# sont ceux qu'un producteur déterministe écrit. On l'éprouve jeton par jeton, sur le détenteur —
# une énumération recopiée resterait verte le jour où le contrat s'élargit (#46).
_MESURENT = {"fact_financial", "fact_statistical"}
for _et in sorted(_ENTRY_TYPES_FERMES):
    _attendue = "mesure" if _et in _MESURENT else "interpretation"
    check(f"`{_et}` × edgar_official → {_attendue}",
          nature_of(entry_type=_et, source_type="edgar_official") == _attendue,
          f"→ {nature_of(entry_type=_et, source_type='edgar_official')}")
check("les deux jetons mesurants appartiennent bien au vocabulaire fermé (fixture non périmée)",
      _MESURENT <= _ENTRY_TYPES_FERMES, f"→ {sorted(_ENTRY_TYPES_FERMES)}")

print("\n4. la source l'emporte sur l'entry_type — un énoncé ne mesure pas")
for src in ("llm_memory", "agent_synthesis"):
    check(f"fact_financial × `{src}` → interpretation",
          nature_of(entry_type="fact_financial", source_type=src) == "interpretation",
          "→ a hérité de l'autorité d'un dépôt")
    check(f"fact_statistical × `{src}` → interpretation",
          nature_of(entry_type="fact_statistical", source_type=src) == "interpretation")
    check(f"fact_qualitative × `{src}` → interpretation",
          nature_of(entry_type="fact_qualitative", source_type=src) == "interpretation")

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
                declared="evenement") == "evenement")
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
# Depuis la capacité 2, `store_knowledge` n'appelle plus `derive_nature` en direct : il passe par
# `source_registry.qualify`, qui dérive la nature PUIS applique le registre nominatif. La chaîne
# gagne un maillon, la règle garde un détenteur unique — et c'est l'ORDRE qui est load-bearing (la
# nature se dérive du source_type générique, le registre s'applique après). On vérifie donc la
# chaîne complète, pas l'appel direct : un `qualify` qui cesserait d'appeler `derive_nature`
# rendrait ce check vert sur un chemin mort.
check("`store_knowledge` appelle `qualify`", "qualify(" in src)
check("`qualify` est bien le maillon qui appelle `derive_nature`",
      "derive_nature(" in inspect.getsource(qualify),
      "→ la chaîne store_knowledge → qualify → derive_nature est rompue")
check("`store_knowledge` ne dérive pas la nature une seconde fois",
      "derive_nature(" not in src,
      "→ deux chemins de dérivation coexistent, ils divergeront au prochain correctif")
# Le grep de source est un PROXY : il dit que l'appel existe, pas que sa valeur atteint l'INSERT.
# Le point de lecture réel est la colonne — c'est §7 qui l'éprouve.
# ⚠️ L'ancre était `"covers, nature"`, la colonne qui PRÉCÉDAIT `nature` dans la liste. Elle a
# disparu avec la 036, et une ancre positionnelle se serait tue au lieu de rougir si `nature` avait
# quitté l'INSERT en même temps. On asserte donc la STRUCTURE — `nature` figure dans la liste de
# colonnes de l'INSERT ET dans son `RETURNING` — plutôt qu'un voisinage textuel (#56).
_liste_colonnes = src.split("INSERT INTO knowledge_entries (", 1)[-1].split(")", 1)[0]
check("… et insère la valeur dérivée (`nature` dans la liste de colonnes de l'INSERT)",
      "nature" in {c.strip() for c in _liste_colonnes.split(",")},
      f"→ {_liste_colonnes.split()}")
check("… et la relit en retour, donc l'appelant voit ce qui a été écrit",
      "RETURNING" in src and "nature" in src.split("RETURNING", 1)[1].split("\n", 1)[0])

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
        # ⚠️ `AND is_deleted = FALSE` retiré des quatre requêtes le 2026-09-10 (migration 036 : la
        # colonne est archivée, elle valait FALSE sur les 180 lignes — le conjoint n'a jamais rien
        # filtré). La phrase n'est pas réécrite à la main pour autant : elle vient du détenteur
        # unique (#46), sinon ce check redeviendrait un jumeau de la définition de « entry vivante ».
        nuls = await conn.fetchval(
            "SELECT count(*) FROM knowledge_entries "
            f"WHERE nature IS NULL AND {ENTRIES_COURANTES}")
        hors = await conn.fetchval(
            "SELECT count(*) FROM knowledge_entries WHERE nature IS NOT NULL AND NOT (nature = ANY($1))",
            sorted(NATURES))
        # `base_rate` → `fact_statistical` (036) : le vocabulaire d'`entry_type` ne nomme plus le
        # livre de méthode qui produit la fréquence, il nomme ce que l'assertion EST (#57).
        det = await conn.fetch(
            "SELECT id, nature FROM knowledge_entries "
            f"WHERE ticker_id = 'RVMD' AND {ENTRIES_COURANTES} "
            "  AND entry_type IN ('fact_financial', 'fact_statistical') ORDER BY id")
        # Ce qui reste à substituer, mesuré et non supposé. Tant que la 036 n'est pas appliquée, le
        # 13ᵉ fait déterministe de RVMD porte encore `base_rate` : `det` en rend 12, et le rouge
        # doit DIRE que c'est le vocabulaire qui est en retard, pas un producteur qui a cessé.
        a_substituer = await conn.fetch(
            "SELECT entry_type, count(*) n FROM knowledge_entries "
            f"WHERE ticker_id = 'RVMD' AND {ENTRIES_COURANTES} "
            "  AND entry_type = ANY($1) GROUP BY 1 ORDER BY 1",
            sorted(SUBSTITUTIONS_ENTRY_TYPE))
        par_nature = await conn.fetch(
            "SELECT nature, count(*) n FROM knowledge_entries "
            f"WHERE {ENTRIES_COURANTES} GROUP BY 1 ORDER BY 1")
        return nuls, hors, det, a_substituer, par_nature
    finally:
        await conn.close()


nuls, hors, det, a_substituer, par_nature = asyncio.run(_etat())
check("aucune entry active sans `nature`", nuls == 0, f"→ {nuls} NULL")
check("aucune `nature` hors vocabulaire en base", hors == 0, f"→ {hors} lignes")
# Le compte est ASSERTÉ, pas seulement affiché : une fixture qui rétrécit (un producteur qui cesse
# d'écrire) rendrait « toutes mesure » vrai sur zéro ligne — faux vert n°1 (§24).
#
# ⚠️ CE COMPTE EST UNE ACCEPTATION DE LA 036, et il est ROUGE avant elle — délibérément. Le SELECT
# ci-dessus parle le vocabulaire d'APRÈS (`fact_statistical`) ; tant que la migration n'est pas
# appliquée, le 13ᵉ fait déterministe de RVMD porte encore `base_rate` et échappe au filtre. Un
# rouge d'acceptation ne vaut que s'il est SATISFIABLE (`feedback_acceptation_rouge_bidirection-
# nelle`) : la satisfiabilité se mesure ici même, en comptant ce qu'il reste à substituer. Si
# `det + à substituer == 13`, la migration ferme l'écart exactement ; si le compte ne tombe pas, ce
# n'est PAS un problème de vocabulaire et rabaisser le plancher masquerait un producteur muet
# (`feedback_optional_schema_gate` — on rejoue les producteurs, on ne baisse jamais le plancher).
_restants = {r["entry_type"]: r["n"] for r in a_substituer}
_total_det = len(det) + sum(_restants.values())
check("RVMD porte bien 13 entries déterministes actives", len(det) == 13,
      f"→ {len(det)} sous le vocabulaire fermé + {sum(_restants.values())} en attente de "
      f"substitution {_restants} — la 036 n'est pas appliquée"
      if _restants else f"→ {len(det)}")
check("… et l'écart est bien celui du VOCABULAIRE : 13 une fois la substitution faite",
      _total_det == 13,
      f"→ {len(det)} + {_restants} = {_total_det} : la 036 ne suffira pas, un producteur est muet")
for row in det:
    check(f"entry #{row['id']} (producteur déterministe) est `mesure`", row["nature"] == "mesure",
          f"→ `{row['nature']}`")
print("  — répartition des entries actives : "
      + ", ".join(f"{r['nature']}={r['n']}" for r in par_nature))

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
