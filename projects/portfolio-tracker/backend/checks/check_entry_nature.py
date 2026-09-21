"""Vérification de l'AXE `nature` d'une entry (capacité 1, `doctrine-trois-axes.md`).

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
        les entries actives, aucune nature hors vocabulaire, et tout fait à RECETTE DÉTERMINISTE
        (un `metric` dans `content_structured`, écrit par les 8 producteurs) est `mesure` — invariant
        #51 revérifié sur l'ÉTAT, sur TOUS les tickers, JAMAIS un décompte du corpus. L'ancien
        `== 13` était un instantané du banc d'essai promu en cible ; il confondait `fact_financial`
        avec « sortie déterministe » et a rougi dès que le collecteur (§3.6, maillon 4 du lot 2c) a
        écrit des faits web `edgar_official` SANS `metric` — compatibles, pas des parasites. §0.6 :
        « les données en base ne dictent jamais la roadmap », leur nombre est un RÉSULTAT, pas un but.
  • §7bis LE VOCABULAIRE FERMÉ, ANCRÉ SUR LE CORPUS — le parcours jeton par jeton de §5bis est
        généré depuis `_MARQUEURS_DE_DERIVATION`, donc retirer un jeton retire son propre assert
        (4ᵉ faux vert) : il ne peut pas voir une amputation. L'ancre non circulaire est le corpus
        réel, via les ids que la migration 044 requalifie — relus DEPUIS le fichier (#46).

Hors ligne :
    docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
      --env-file checks/env.checks $IMG python checks/check_entry_nature.py
Avec l'état persisté (§7) — réseau `coolify` + vraie URL de base :
    docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
      --env-file checks/env.checks -e CHECK_DB_URL="postgresql://…/db_portfolio" \
      $IMG python checks/check_entry_nature.py
"""
import glob
import inspect
import os
import re
import sys
import typing

from app.agents.v2.common import (
    FIELD_PROFILES,
    NATURES,
    _MARQUEURS_DE_DERIVATION,
    annonce_une_derivation,
    derive_nature,
)
from app.agents.v2.worker import _normalise_entry
from app.contracts.worker_delegation_schema import EntryType
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
#
# ⚠️ L'assert pinçait la signature à TROIS paramètres. Il a rougi le 2026-09-21 quand `content` est
# entré dans la règle (garde du guichet, #78) — et c'est le bon comportement, ce n'est pas lui qui
# était faux, c'est sa FORMULATION qui disait autre chose que ce qu'on garde. L'invariant n'a
# jamais été un nombre de paramètres : c'est « chaque ingrédient est une COLONNE stockée de la
# ligne », donc la règle est rejouable sur n'importe quelle ligne à n'importe quel instant.
# `content` le respecte, `covers` ne le respectait pas. Le compte est un symptôme, la rejouabilité
# est la garantie — et un assert qui fige le symptôme se fait modifier à chaque évolution légitime
# jusqu'à ce que quelqu'un le désarme.
_ING = set(inspect.signature(derive_nature).parameters)
_COLONNES_INGREDIENTS = {"entry_type", "source_type", "content"}
check("les ingrédients de `derive_nature` sont exactement trois COLONNES + la proposition de l'agent",
      _ING == _COLONNES_INGREDIENTS | {"declared"}, f"→ {sorted(_ING)}")
check("… et `covers` n'en est plus un ingrédient",
      "covers" not in _ING,
      "→ une règle dont un ingrédient n'est pas dans la ligne n'est pas rejouable (#48)")
# La preuve que ce sont bien des COLONNES et pas des noms plausibles est en §7, qui les SELECT
# sur la vraie table : ici, hors ligne, on ne peut affirmer que la liste — un `content` qui ne
# serait pas une colonne rendrait §7 rouge au SELECT, pas vert en silence.
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

print("\n5bis. LA GARDE DU GUICHET (#78) — une dérivation ANNONCÉE ne se tamponne pas `mesure`")
# POURQUOI CETTE SECTION EXISTE, mesuré et pas déduit. Le 2026-09-21, la réponse #475 a été
# supprimée pour avoir publié « guidance de dépenses en trésorerie 1,81–1,93 MdUSD », un chiffre
# qu'aucune société n'a publié. Le garde d'abord envisagé vivait chez l'analyste (« aucun nombre du
# verbatim absent des entries citées ») ; il a été MESURÉ VERT sur ce cas précis, parce que 1,81 et
# 1,93 figurent bel et bien dans l'entry #312, qui était bel et bien citée. L'analyste avait
# recopié fidèlement une pièce qui mentait sur son propre statut : #312 est `fact_financial` ×
# `company_ir_official`, donc `mesure`, donc tier A — et sa dernière phrase est une soustraction.
# Seize entries sur 161 `mesure` courantes étaient dans ce cas (migration 044).
_CALCUL = "Calcul : 155,237 × 0,8060 = 125,121 MUSD."
_RELEVE = "Le résultat d'exploitation FY2026 s'élève à 155 237 MUSD (10-K, us-gaap:OperatingIncomeLoss)."
check("un `fact_financial` EDGAR qui ANNONCE son calcul → `interpretation`",
      nature_of(entry_type="fact_financial", source_type="edgar_official",
                content=_CALCUL) == "interpretation",
      "→ un chiffre calculé hérite de l'autorité du dépôt dont il est tiré")
check("… et le même sans annonce de calcul reste `mesure` (la garde DISCRIMINE)",
      nature_of(entry_type="fact_financial", source_type="edgar_official",
                content=_RELEVE) == "mesure",
      "→ la garde rétrograde tout : elle ne garde plus rien, elle punit")
check("… `content` absent ne rétrograde pas (les producteurs qui ne le passent pas sont inchangés)",
      nature_of(entry_type="fact_financial", source_type="edgar_official") == "mesure")
check("… le motif NOMME le marqueur trouvé, il ne se contente pas de refuser",
      "en déduisant" in derive_nature(entry_type="fact_financial", source_type="edgar_official",
                                      content="En déduisant la SBC, 1,81 MdUSD.")[1],
      f"→ {derive_nature(entry_type='fact_financial', source_type='edgar_official', content='En déduisant la SBC.')[1]}")
# Le vocabulaire est FERMÉ et éprouvé JETON PAR JETON sur son détenteur : une énumération recopiée
# ici resterait verte le jour où un marqueur est retiré du détenteur (#46). Chaque jeton doit donc
# rétrograder par lui-même — un jeton mort dans la liste serait exactement le « vocabulaire encore
# ouvert » que le commentaire de `_INTERPRETING_ENTRY_TYPES` proscrit.
# ⚠️ ET CE PARCOURS NE PEUT PAS VOIR UNE AMPUTATION : il est GÉNÉRÉ depuis le détenteur, donc
# retirer un jeton retire aussi son assert (4ᵉ faux vert — un assert écrit depuis sa propre
# constante). Ce qu'il garde réellement est plus étroit : aucun jeton n'est INATTEIGNABLE par
# construction (une majuscule dans la liste ne matcherait jamais un `content.lower()`). L'ancre
# non circulaire contre l'amputation est le CORPUS RÉEL — §7bis.
for _m in _MARQUEURS_DE_DERIVATION:
    check(f"le marqueur « {_m} » rétrograde à lui seul",
          nature_of(entry_type="fact_financial", source_type="edgar_official",
                    content=f"Chiffre obtenu {_m} 12 MUSD.") == "interpretation",
          "→ jeton mort dans le vocabulaire")
check("la détection est insensible à la CASSE (les producteurs écrivent « Calcul : » en tête)",
      annonce_une_derivation("CALCUL : 3 − 1 = 2") == "calcul :",
      f"→ {annonce_une_derivation('CALCUL : 3 − 1 = 2')!r}")
# ⚠️ Le jeton employé ici n'est NI celui de l'assert « le motif NOMME le marqueur » ci-dessus, NI
# celui que le test négatif retire du vocabulaire : une fixture qui déclenche deux contrôles ne dit
# pas lequel discrimine (#56).
check("`annonce_une_derivation` rend le marqueur, pas un booléen (le motif doit le nommer)",
      annonce_une_derivation("un total de soit environ 12 MUSD") == "soit environ",
      f"→ {annonce_une_derivation('un total de soit environ 12 MUSD')!r}")
check("une prose sans marqueur ne rend rien", annonce_une_derivation(_RELEVE) is None)
check("un contenu vide ne rend rien (et ne lève pas)", annonce_une_derivation(None) is None)
# LES DEUX AXES NE SE MÉLANGENT PAS (#50) : la rétrogradation touche la nature, JAMAIS le tier. Le
# dépôt reste un dépôt ; c'est la phrase qu'on en a tirée qui n'est pas un relevé. On l'éprouve sur
# la chaîne réelle de qualification, pas sur `derive_nature` seul : c'est `qualify` qui rend les
# deux, et c'est là qu'un correctif maladroit les confondrait.
_st_calc, _nat_calc, _ = qualify(source_type="edgar_official", url=None, ticker_id="TEST",
                                 entry_type="fact_financial", content=_CALCUL)
_st_rel, _nat_rel, _ = qualify(source_type="edgar_official", url=None, ticker_id="TEST",
                               entry_type="fact_financial", content=_RELEVE)
check("`qualify` propage la rétrogradation de nature", _nat_calc == "interpretation",
      f"→ `{_nat_calc}` : `content` n'atteint pas `derive_nature` depuis le chemin d'écriture")
check("… sans toucher au `source_type` (donc au tier) : deux axes, jamais mélangés (#50)",
      _st_calc == _st_rel == "edgar_official", f"→ `{_st_calc}` vs `{_st_rel}`")
# LE POINT DE LECTURE RÉEL. `qualify` est un maillon ; ce qui compte est que `content` arrive
# jusqu'à lui DEPUIS les deux sites d'appel. Un paramètre ajouté au détenteur et non transmis par
# l'appelant est un décideur sans producteur : 0 appel, 0 ligne, garde verte
# (`feedback_controle_au_point_de_lecture`).
for _nom, _fn in (("store_knowledge", store_knowledge),
                  ("_normalise_entry (search-worker)", _normalise_entry)):
    check(f"`{_nom}` transmet `content=` à `qualify`",
          "content=content" in inspect.getsource(_fn),
          "→ la garde est écrite chez son détenteur et jamais atteinte depuis ce chemin")

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


def _ids_migration_044() -> list[int]:
    """Les ids que la migration 044 requalifie, lus DEPUIS le fichier — jamais recopiés ici.

    La migration est le détenteur unique (#46) de la mesure qui a motivé la garde du guichet : les
    entries `mesure` dont la prose annonçait son propre calcul, relevées sur le corpus réel le
    2026-09-21. Un fichier introuvable ou une liste vide doivent ROUGIR (ancre creuse), jamais
    faire sauter la section (`feedback_check_degrade_en_sortant_a_zero`).
    """
    motif = os.path.join(os.path.dirname(__file__), "..", "app", "db", "migrations", "044_*.sql")
    return sorted({int(n) for f in glob.glob(motif)
                   for bloc in re.findall(r"id IN \(([\d,\s]+)\)", open(f, encoding="utf-8").read())
                   for n in bloc.replace(" ", "").split(",") if n})


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
        # L'invariant #51 sur l'ÉTAT PERSISTÉ : un fait à RECETTE DÉTERMINISTE est toujours `mesure`.
        # Le discriminant est STRUCTUREL — la présence d'un `metric` dans `content_structured`, que
        # les 8 producteurs déterministes écrivent tous (edgar_feed, financials_feed, valuation_feed,
        # base_rate_corpus) et que le search-worker du collecteur (§3.6) n'écrit jamais (faits
        # narratifs web, `content_structured` vide). L'ancien SELECT comptait les `fact_financial`
        # d'un ticker et exigeait `== 13` : un décompte du banc d'essai promu en cible (§0.6), qui a
        # rougi dès que le maillon 4 a écrit 30 faits web `edgar_official`/`company_ir_official` SANS
        # `metric`, tous frais et tous `mesure`. Le nombre est un RÉSULTAT de la collecte, pas un but.
        det = await conn.fetch(
            "SELECT id, ticker_id, nature FROM knowledge_entries "
            f"WHERE {ENTRIES_COURANTES} "
            "  AND entry_type IN ('fact_financial', 'fact_statistical') "
            "  AND (content_structured->>'metric') IS NOT NULL ORDER BY ticker_id, id")
        par_nature = await conn.fetch(
            "SELECT nature, count(*) n FROM knowledge_entries "
            f"WHERE {ENTRIES_COURANTES} GROUP BY 1 ORDER BY 1")
        # §7bis — l'ancre du vocabulaire fermé sur le corpus RÉEL (voir plus bas).
        requalifiees = await conn.fetch(
            "SELECT id, entry_type, source_type, content FROM knowledge_entries "
            "WHERE id = ANY($1) ORDER BY id", _ids_migration_044())
        return nuls, hors, det, par_nature, requalifiees
    finally:
        await conn.close()


nuls, hors, det, par_nature, requalifiees = asyncio.run(_etat())
check("aucune entry active sans `nature`", nuls == 0, f"→ {nuls} NULL")
check("aucune `nature` hors vocabulaire en base", hors == 0, f"→ {hors} lignes")
# ⚠️ NON-VACUITÉ (faux vert n°1, §24) : « tous mesure » est vrai sur zéro ligne. Un producteur
# déterministe qui cesserait d'écrire viderait `det` et rendrait l'invariant creux — on exige donc
# qu'il en existe au moins un. Ce n'est PAS une cible chiffrée (§0.6) : le seuil est « ≥ 1 », jamais
# « exactement N ». Le nombre exact de faits déterministes est un résultat de la collecte pilotée par
# le plan, pas un objectif (`feedback_ligne_de_base_est_une_mesure`).
check("il existe des faits à recette déterministe (metric structuré) — l'invariant n'est pas creux",
      len(det) > 0, f"→ {len(det)} fait(s) déterministe(s)")
# L'invariant lui-même : chacun est `mesure`. #51 le garantit au point d'écriture (`store_knowledge`,
# détenteur unique) ; §7 le REVÉRIFIE sur l'état persisté (#43 : un correctif d'écriture se juge au
# comptage par clef, pas sur son diff). Il porte sur TOUS les tickers, pas sur le seul banc d'essai.
for row in det:
    check(f"fait déterministe #{row['id']} ({row['ticker_id']}) est `mesure`",
          row["nature"] == "mesure", f"→ `{row['nature']}`")
_tickers_det = sorted({r["ticker_id"] for r in det if r["ticker_id"]})
print(f"  — faits à recette déterministe actifs : {len(det)} sur "
      f"{len(_tickers_det)} ticker(s) ({', '.join(_tickers_det)}), tous `mesure`")
print("  — répartition des entries actives : "
      + ", ".join(f"{r['nature']}={r['n']}" for r in par_nature))

print("\n7bis. LE VOCABULAIRE FERMÉ, ANCRÉ SUR LE CORPUS RÉEL (et non sur lui-même)")
# POURQUOI CETTE SECTION EXISTE. Le parcours jeton par jeton de §5bis est GÉNÉRÉ depuis
# `_MARQUEURS_DE_DERIVATION` : retirer un jeton du détenteur retire aussi l'assert qui le gardait —
# un assert écrit depuis sa propre constante (4ᵉ faux vert). Il ne peut donc PAS voir une
# amputation du vocabulaire, qui est exactement la régression à craindre : la garde continuerait de
# tamponner `mesure` des entries dont la prose annonce son calcul, en silence.
# L'ancre non circulaire est le CORPUS. La migration 044 tient la mesure du 2026-09-21 — les entries
# `mesure` dont la prose annonçait sa propre dérivation — et ses ids sont relus DEPUIS le fichier,
# jamais recopiés ici (#46). Chacune doit TOUJOURS être vue par la règle. L'assert ne dépend pas de
# l'application de la migration : il porte sur le `content` stocké, que 044 ne touche pas.
_ids_044 = _ids_migration_044()
check("la migration 044 nomme les entries qu'elle requalifie — l'ancre n'est pas vide",
      len(_ids_044) > 0,
      "→ fichier `044_*.sql` introuvable ou sans liste d'ids : l'ancre du vocabulaire a disparu")
check("… et la base les porte toutes — l'ancre n'est pas creuse",
      len(requalifiees) == len(_ids_044), f"→ {len(requalifiees)}/{len(_ids_044)} en base")
for row in requalifiees:
    _marq = annonce_une_derivation(row["content"])
    check(f"#{row['id']} du corpus réel ANNONCE son calcul, la règle le voit encore",
          _marq is not None,
          "→ le jeton qui le détectait a quitté `_MARQUEURS_DE_DERIVATION` : le vocabulaire fermé "
          "s'est amputé, et aucun assert de §5bis ne pouvait le dire")
    check(f"… donc #{row['id']} sort `interpretation` de la règle complète",
          derive_nature(entry_type=row["entry_type"], source_type=row["source_type"],
                        content=row["content"])[0] == "interpretation",
          f"→ marqueur `{_marq}`, entry_type `{row['entry_type']}`, source `{row['source_type']}`")
_marqueurs_corpus = sorted({annonce_une_derivation(r["content"]) for r in requalifiees
                            if annonce_une_derivation(r["content"])})
print(f"  — {len(requalifiees)} entries du corpus réel, {len(_marqueurs_corpus)} marqueur(s) "
      f"attesté(s) : {', '.join(f'« {m} »' for m in _marqueurs_corpus)}")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
