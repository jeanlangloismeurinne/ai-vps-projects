"""Vérification de la TABLE DE PROFILS PAR CHAMP (capacité 0, `02-spec-autorite-vs-actualite.md`).

Sans réseau ni modèle. La table est de la DOCTRINE : elle n'est encore câblée nulle part (les
capacités 1 à 5 la consommeront). Ce check est donc le seul garde-fou qui existe sur elle, et il
porte sur ce qui la rendrait inexploitable plus tard :

  • §1  COUVERTURE — les 19 champs requis ont un profil, et la table n'en porte aucun de trop.
        ⚠️ Chaque champ est vérifié PAR SON NOM (une assertion par champ) : retirer une ligne doit
        faire rougir un assert qui NOMME le champ, jamais lever un KeyError ni sauter la section
        (les trois faux verts — §24 de `CHANTIER_OUTILLAGE_DEV.md`).
  • §2  DOMAINES — nature dans le vocabulaire fermé, plancher dans `TIER_ORDER`, actualité booléenne.
  • §3  ATTEIGNABILITÉ (#32) — un plancher qu'aucun `source_type` ne peut atteindre est un champ
        infondable déguisé en lacune. Forme faible mais réelle : on ne sait pas quelles sources
        savent nourrir quel champ, on sait qu'aucune ne doit être exclue par le barème seul.
  • §4  DÉTENTEUR UNIQUE (#46) — la table EST le plancher que `curator._plancher_for` applique, et
        aucune SECONDE table de planchers ne subsiste dans le curator. C'est la seconde table qui
        empêchait le desserrage de #50 d'atteindre la porte, et qui rendait §5 circulaire.
  • §5  DESSERRAGE EXPLICITE — tout plancher plus permissif que celui de sa dimension porte une clef
        `desserrage` écrite. Un desserrage tacite est le trou silencieux de
        `feedback_optional_schema_gate`.
  • §6  GABARIT, PAS ACTEUR (#31) — aucun motif ne nomme un émetteur ni une juridiction.
  • §7  PAS DE COMPOSITE — la table ne porte aucun scalaire agrégé : la porte lira un TRIPLET.
"""
import inspect
import re
import sys

from app.agents.v2.common import (
    FIELD_PROFILES,
    MVDD_FIELD_PATHS,
    MVDD_SPEC,
    NATURES,
    TIER_ORDER,
    profile_for,
)
from app.agents.v2 import curator as curator_mod
from app.agents.v2.curator import _plancher_for
from app.knowledge.service import RELIABILITY_TABLE

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


_RANK = {t: i for i, t in enumerate(TIER_ORDER)}
_DIM_PLANCHER = {s["dimension"]: s["tier_plancher"] for s in MVDD_SPEC}


def _plancher_socle(path: str) -> str:
    """Le plancher de RÉFÉRENCE contre lequel un desserrage se mesure : celui de la dimension MVDD.

    ⚠️ Il lisait `FIELD_PLANCHER_OVERRIDES` en priorité jusqu'au 2026-09-08. C'était une comparaison
    circulaire : un champ abaissé dans cette seconde table se comparait à sa propre valeur abaissée,
    donc §5 le voyait « ne desserre pas » et n'exigeait aucune déclaration. Le seul champ concerné,
    `marche.croissance_marche_historique`, était bel et bien un desserrage B+ → B non déclaré — un
    desserrage tacite invisible à l'assert écrit pour les attraper. La suppression de la seconde
    table (#46, capacité 4) l'a fait apparaître. Le socle MVDD est la seule référence qui ne puisse
    pas être bougée par le fichier qu'elle contrôle."""
    return _DIM_PLANCHER[path.split(".", 1)[0]]


print("1. couverture — un profil par champ MVDD requis, ni plus ni moins")
# Itération sur les CHEMINS REQUIS, avec .get() : un champ retiré de la table produit un FAIL
# nommé, pas une exception qui tuerait le script avant ses autres sections.
for path in sorted(MVDD_FIELD_PATHS):
    check(f"`{path}` a un profil", FIELD_PROFILES.get(path) is not None,
          "→ champ requis SANS doctrine écrite (capacité 0 incomplète)")
for path in sorted(set(FIELD_PROFILES) - set(MVDD_FIELD_PATHS)):
    check(f"`{path}` est un champ requis", False,
          "→ profil ORPHELIN : la table décrit un champ que MVDD_SPEC n'exige pas")
check(f"les {len(MVDD_FIELD_PATHS)} champs requis sont exactement couverts",
      set(FIELD_PROFILES) == set(MVDD_FIELD_PATHS),
      f"→ {len(FIELD_PROFILES)} profils pour {len(MVDD_FIELD_PATHS)} champs")

print("\n2. domaines des trois axes")
for path in sorted(FIELD_PROFILES):
    p = FIELD_PROFILES[path]
    check(f"`{path}` nature dans le vocabulaire fermé", p.get("nature") in NATURES,
          f"→ {p.get('nature')!r}")
    check(f"`{path}` plancher est un tier connu", p.get("plancher") in _RANK,
          f"→ {p.get('plancher')!r}")
    check(f"`{path}` actualite_bloquante est un booléen",
          isinstance(p.get("actualite_bloquante"), bool), f"→ {p.get('actualite_bloquante')!r}")
    check(f"`{path}` porte un motif écrit", bool((p.get("motif") or "").strip()),
          "→ un profil sans motif est un réglage, pas une doctrine")

print("\n3. atteignabilité du plancher (#32) — aucun champ infondable déguisé en lacune")
for path in sorted(FIELD_PROFILES):
    plancher = FIELD_PROFILES[path].get("plancher")
    atteignables = [s for s, (tier, _) in RELIABILITY_TABLE.items()
                    if tier in _RANK and _RANK[tier] <= _RANK.get(plancher, len(TIER_ORDER))]
    check(f"`{path}` ({plancher}) est atteignable par ≥1 source_type", bool(atteignables),
          "→ aucun source_type de RELIABILITY_TABLE n'atteint ce plancher")

print("\n4. détenteur unique (#46) — la table EST le plancher que la porte applique")
# Jusqu'au 2026-09-08 cette section vérifiait l'ACCORD entre deux tables de planchers. Deux tables
# d'accord restent deux tables : c'est la seconde qui a empêché le desserrage de #50 d'atteindre la
# porte pendant trois jours, et qui a rendu §5 circulaire. La capacité 4 a supprimé
# `curator.FIELD_PLANCHER_OVERRIDES` ; ce qui se vérifie désormais est qu'elle ne revienne pas, et
# que la fonction de production lise bien CETTE table — pas qu'elle s'accorde avec une jumelle.
_SRC_CURATOR = inspect.getsource(curator_mod)
check("aucune seconde table de planchers dans le curator",
      "FIELD_PLANCHER_OVERRIDES: dict" not in _SRC_CURATOR
      and "FIELD_PLANCHER_OVERRIDES = {" not in _SRC_CURATOR,
      "→ table réintroduite : le desserrage de FIELD_PROFILES cessera d'atteindre la porte")
for path in sorted(FIELD_PROFILES):
    dim, champ = path.split(".", 1)
    attendu = FIELD_PROFILES[path].get("plancher")
    # Plancher de dimension volontairement ABSURDE : si `_plancher_for` retombait dessus, la valeur
    # rendue serait « C » et l'assert rougirait. Passer le vrai plancher de dimension rendrait le
    # test non discriminant sur tout champ que la table ne desserre pas.
    check(f"`{path}` : la porte applique le plancher de la table ({attendu})",
          _plancher_for(dim, champ, "C") == attendu,
          f"→ la porte applique {_plancher_for(dim, champ, 'C')}")

print("\n5. tout desserrage est DÉCLARÉ, jamais tacite")
for path in sorted(FIELD_PROFILES):
    p = FIELD_PROFILES[path]
    courant, propose = _plancher_socle(path), p.get("plancher")
    if propose not in _RANK or courant not in _RANK:
        continue
    if _RANK[propose] > _RANK[courant]:  # rang plus grand = tier moins bon = desserrage
        check(f"`{path}` desserré {courant}→{propose} et le DÉCLARE",
              bool((p.get("desserrage") or "").strip()),
              "→ desserrage tacite : exactement le trou de feedback_optional_schema_gate")
    else:
        check(f"`{path}` ne desserre pas ({courant} → {propose})", True)

print("\n6. gabarit, pas acteur (#31) — aucun motif ne nomme un émetteur ni une juridiction")
# Un motif est réutilisable par TOUT émetteur. Nommer un acteur (ou un formulaire propre à une
# juridiction) rend la doctrine inapplicable au premier émetteur non américain.
_INTERDITS = ["NVDA", "MSFT", "RVMD", "NVIDIA", "MICROSOFT", "RASONQUE", "FDA", "SEC", "EDGAR",
              "10-K", "10-Q", "8-K", "6-K", "DEF 14A"]
for path in sorted(FIELD_PROFILES):
    p = FIELD_PROFILES[path]
    texte = f"{p.get('motif', '')} {p.get('desserrage', '')}".upper()
    trouves = [m for m in _INTERDITS if re.search(rf"(?<![A-Z0-9]){re.escape(m)}(?![A-Z0-9])", texte)]
    check(f"`{path}` motif générique", not trouves, f"→ nomme {trouves}")

print("\n7. pas de score composite — la porte lira un triplet, jamais un nombre")
for path in sorted(FIELD_PROFILES):
    numeriques = [k for k, v in FIELD_PROFILES[path].items()
                  if isinstance(v, (int, float)) and not isinstance(v, bool)]
    check(f"`{path}` ne porte aucun scalaire agrégé", not numeriques, f"→ {numeriques}")

print("\n8. accesseur — un champ sans doctrine ne se traite pas « au mieux »")
try:
    profile_for("dimension_inexistante.champ")
    check("profile_for lève sur un champ inconnu", False, "→ a rendu un défaut silencieux")
except KeyError:
    check("profile_for lève sur un champ inconnu", True)

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
