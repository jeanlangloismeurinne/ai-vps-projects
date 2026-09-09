"""Réconciliation des DEUX vocabulaires du système — test de non-régression permanent (spec v3 §6).

CE QU'IL PROUVE
---------------
Le système parle deux langues qui ne se rencontrent jamais :

  · le vocabulaire d'INDEXATION — `MVDD_FIELD_PATHS`, ce que `covers` a le droit de désigner.
    `worker._resolve_covers` retourne `None` sur tout tag hors de cette liste : l'entry est stockée
    et ne fonde rien. Elle devient orpheline, en silence.
  · le vocabulaire de SORTIE — les feuilles du `ResearchMemo`, ce que les analystes doivent remplir.

Un champ du mémo sans chemin d'indexation est un champ qu'AUCUNE entry ne peut fonder : il sera
rempli quand même, sans preuve indexable. Un chemin indexable que le mémo ne consomme jamais est une
étagère où l'on range des faits que personne ne vient chercher — `risques.risques_cles`, le chemin le
plus peuplé de la base, est dans ce cas.

CE SCRIPT EST ÉCRIT POUR ROUGIR AUJOURD'HUI (14 orphelins + 3 inutilisés) et pour virer au vert au
lot 3, quand `framework_questions` deviendra le vocabulaire UNIQUE. C'est un test négatif qui a déjà
rougi, donc éprouvé (`feedback_test_negatif_obligatoire`). Le jour où il passe au vert, la §6 de la
spec est tenue — pas avant.

POURQUOI IL IMPORTE AU LIEU DE LIRE LA SOURCE
---------------------------------------------
Son ancêtre `/tmp/vocab.py` re-parsait `common.py` et `analysis_v2_schemas.py` à coups de regex. Une
regex qui cesse de mordre ne se plaint pas : elle rend un ensemble VIDE, donc « 0 orpheline », donc
un vert parfait sur un système inchangé — le premier des quatre faux verts, en pire, puisqu'il
grandit avec le refactoring qu'il est censé surveiller. Ici les deux vocabulaires sont IMPORTÉS de
leurs détenteurs uniques (#46) : `MVDD_FIELD_PATHS` d'un côté, les `model_fields` Pydantic de
l'autre. Un renommage de champ change le résultat au lieu de le vider.

Les §A asserts existent pour la même raison : un ensemble vide ou une table d'alias qui ne pointe
plus nulle part doit produire un FAIL NOMMÉ, jamais un zéro rassurant.

Usage (aucun réseau, aucune base — c'est une réconciliation de contrats) :

    bash tools/reconcilier_vocabulaires.sh
"""
from __future__ import annotations

import sys

from app.agents.v2.common import MVDD_FIELD_PATHS
from app.contracts import analysis_v2_schemas as S

ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


# Les 6 blocs du `ResearchMemo` qui portent de la connaissance sur l'émetteur. Les deux listes
# d'incertitudes et `posture` n'en sont pas : ce sont des méta-champs du mémo lui-même.
BLOCS: dict[str, type] = {
    "business_model": S.BusinessModel,
    "moat": S.Moat,
    "financials": S.Financials,
    "management": S.Management,
    "industry": S.Industry,
    "valuation": S.Valuation,
}

# Champs DÉRIVÉS d'autres champs du mémo : ils n'ont pas à être fondés par une entry, ils se
# calculent. Les exclure n'est pas une dispense de confort — c'est la différence entre « rien ne peut
# le fonder » (le défaut qu'on mesure) et « rien n'a besoin de le fonder » (un calcul).
# ⚠️ Toute addition ici retire un champ du compte des orphelins : elle se justifie par le fait que le
# champ est CALCULÉ à partir d'autres champs du même mémo, jamais par le fait qu'il est difficile à
# fonder.
DERIVES: frozenset[str] = frozenset({
    "financials.roic_vs_wacc",              # = roic_pct − wacc_estime_pct
    "financials.wacc_estime_pct",           # estimation, pas une observation
    "valuation.iv_range",                   # sortie de epv / dcf_scenarios
    "valuation.marge_securite_base_pct",    # = (iv_range − prix_actuel) / iv_range
    "moat.score",                           # jugement agrégé, grounding délégué à moat.preuves
    "management.score",                     # idem
})

# Le pont entre les deux vocabulaires : même objet, préfixe différent. Cette table est la DETTE que
# la v3 supprime — au lot 3 il n'y aura plus qu'un vocabulaire, donc plus d'alias à tenir.
# ⚠️ Elle est vérifiée dans les deux sens en §A : une clef qui n'est plus une feuille du mémo
# masquerait un orphelin (un correctif omet de retirer), une valeur hors index en fabriquerait un.
ALIAS: dict[str, str] = {
    "business_model.description": "business_model.description",
    "business_model.drivers_revenus": "business_model.drivers_revenus",
    "business_model.recurrence_pct": "business_model.recurrence_pct",
    "business_model.unit_economics": "produits.unit_economics",
    "moat.preuves": "positionnement.moat_preuves",
    "financials.roic_pct": "financials.roic_pct",
    "financials.fcf_conversion_pct": "financials.fcf_conversion_pct",
    "financials.intensite_capex_pct": "financials.intensite_capex_pct",
    "financials.levier": "financials.levier",
    "industry.croissance_marche_historique_pct": "marche.croissance_marche_historique",
    "industry.position_vs_pairs": "positionnement.position_vs_pairs",
    "management.incitations": "management_allocation.incitations",
    "management.skin_in_game_pct": "management_allocation.skin_in_game_pct",
    "valuation.prix_actuel": "valorisation.prix_actuel",
    "valuation.relatif": "valorisation.relatif_multiple",
    "valuation.base_rate_anchor": "valorisation.base_rate_anchor",
}


def feuilles_memo() -> set[str]:
    """Les feuilles du `ResearchMemo`, lues dans le contrat lui-même — jamais recopiées."""
    out: set[str] = set()
    for prefixe, cls in BLOCS.items():
        for nom in cls.model_fields:
            if nom == "source_entry_refs":     # la référence n'est pas un champ de connaissance
                continue
            out.add(f"{prefixe}.{nom}")
    return out


def main() -> int:
    memo = feuilles_memo()
    index = set(MVDD_FIELD_PATHS)

    # ── §A — le mesureur mesure-t-il quelque chose ? ─────────────────────────────
    # Sans ces quatre asserts, toute panne de lecture se lit « 0 orpheline ».
    check("[A] le vocabulaire d'INDEXATION est non vide", bool(index),
          "→ MVDD_FIELD_PATHS vide : tout champ du mémo paraîtrait orphelin")
    check("[A] le vocabulaire de SORTIE est non vide", bool(memo),
          "→ aucune feuille lue : 'zéro orpheline' serait vrai sur zéro ligne")
    aliases_morts = sorted(k for k in ALIAS if k not in memo)
    check("[A] chaque clef d'ALIAS est encore une feuille du mémo", not aliases_morts,
          f"→ {aliases_morts} : un alias périmé DISPENSE un champ qui n'existe plus, "
          f"et masquerait le jour où un champ homonyme réapparaît")
    cibles_mortes = sorted(v for v in ALIAS.values() if v not in index)
    check("[A] chaque cible d'ALIAS est un chemin indexable réel", not cibles_mortes,
          f"→ {cibles_mortes} : la cible n'existe pas dans MVDD_FIELD_PATHS, "
          f"le champ serait compté orphelin à tort")
    derives_morts = sorted(d for d in DERIVES if d not in memo)
    check("[A] chaque champ déclaré DÉRIVÉ est encore une feuille du mémo", not derives_morts,
          f"→ {derives_morts} : une dispense qui ne dispense plus rien")

    print(f"\nvocabulaire d'INDEXATION (covers, MVDD_FIELD_PATHS) : {len(index)} chemins")
    print(f"champs FEUILLES du ResearchMemo (hors refs)         : {len(memo)}")
    print(f"   dont dérivés d'autres champs (pas à fonder)      : {len(DERIVES & memo)}")

    # ── §B — les deux écarts, qui sont l'objet du script ─────────────────────────
    orphelins = sorted(f for f in memo - DERIVES if ALIAS.get(f) not in index)
    print(f"\n⚠️  champs du mémo SANS chemin d'indexation ({len(orphelins)}) — "
          f"aucune entry ne peut les fonder :")
    for f in orphelins:
        print(f"   · {f}")

    consommes = {ALIAS[k] for k in ALIAS if k in memo}
    inutilises = sorted(index - consommes)
    print(f"\nchemins indexables JAMAIS consommés par le mémo ({len(inutilises)}) — "
          f"des faits rangés que personne ne vient chercher :")
    for c in inutilises:
        print(f"   · {c}")

    print()
    check("[B] zéro feuille de mémo sans chemin d'indexation (T6)", not orphelins,
          f"→ {len(orphelins)} champs produits sans preuve indexable possible")
    check("[B] zéro chemin indexable jamais consommé (T7)", not inutilises,
          f"→ {len(inutilises)} chemins alimentés pour personne")

    print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
    if fail:
        print("ROUGE ATTENDU au lot 0 — il vire au vert au lot 3, quand `framework_questions`\n"
              "devient le vocabulaire unique (spec v3 §6). Un vert ici AVANT le lot 3 est un\n"
              "défaut du mesureur, pas une bonne nouvelle.", file=sys.stderr)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
