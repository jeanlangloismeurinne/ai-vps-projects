"""Réconciliation des DEUX vocabulaires du système — test de non-régression permanent (spec v3 §6).

CE QU'IL PROUVE
---------------
Le système parle deux langues qui ne se rencontrent jamais :

  · le vocabulaire des QUESTIONS — les `chemin_indexation` déclarés par `frameworks.yaml`, ce qu'un
    lien de couverture a le droit de désigner. Un tag hors de cette liste ne fonde rien : l'entry
    est stockée et devient orpheline, en silence.
  · le vocabulaire de SORTIE — les feuilles du `ResearchMemo`, ce que les analystes doivent remplir.

Un champ du mémo sans question est un champ qu'AUCUNE entry ne peut fonder : il sera rempli quand
même, sans preuve indexable. Une question que le mémo ne consomme jamais est une étagère où l'on
range des faits que personne ne vient chercher.

⚠️ CE QUE CE MESUREUR A MESURÉ JUSQU'AU 2026-09-21, ET POURQUOI C'ÉTAIT FAUX
----------------------------------------------------------------------------
Il comparait le mémo à `FIELD_PROFILES` — la grille MVDD de 19 chemins — et rendait `14 orphelins
+ 3 inutilisés`. Or le lot 3 a RETIRÉ à cette grille son autorité : le vocabulaire unique, c'est
`framework_questions`. Le mesureur était donc resté sur l'étalon que le chantier venait de déposer,
et son couple 14/3 a été recopié tel quel dans le 00-REPRISE, la spec §0.3 et les notes de lot.
`tools/acceptation_frameworks.py`, lui, avait déjà basculé : il rendait 30/13. Une règle tenue à
deux endroits re-diverge au correctif suivant (`feedback_correctif_regle_jumeaux`) — la règle vit
désormais ICI seule, dans `ecart()`, et l'acceptation la CONSOMME.

Le couple réel est `30 / 13`, et il est PIRE que 14/3 pour une raison qui n'est pas un défaut de
code : les 13 questions des deux pilotes vivent sous `qualite_financiere.*` et `defendabilite.*`,
qui ne sont des blocs du mémo sous aucune forme. **L'intersection est vide.** Ce n'est pas un
écart à colmater champ par champ, c'est l'état terminal de la roadmap : le 0/0 exige un framework
par bloc de mémo, pas un alias de plus. D'où §C, qui compte les BLOCS et non les feuilles — un
« 30 » nu se lit comme 30 bugs, alors qu'il dit « 6 chapitres sur 6 sans méthodologie approuvée »
(`feedback_rendu_est_un_producteur`).

CE SCRIPT EST ÉCRIT POUR ROUGIR AUJOURD'HUI (30 orphelins + 13 inutilisés) et pour virer au vert
quand chaque bloc du mémo sera la projection d'un framework acquitté. C'est un test négatif qui a
déjà rougi, donc éprouvé (`feedback_test_negatif_obligatoire`). Le jour où il passe au vert, la §6
de la spec est tenue — pas avant.

POURQUOI IL IMPORTE AU LIEU DE LIRE LA SOURCE
---------------------------------------------
Son ancêtre `/tmp/vocab.py` re-parsait `common.py` et `analysis_v2_schemas.py` à coups de regex. Une
regex qui cesse de mordre ne se plaint pas : elle rend un ensemble VIDE, donc « 0 orpheline », donc
un vert parfait sur un système inchangé — le premier des quatre faux verts, en pire, puisqu'il
grandit avec le refactoring qu'il est censé surveiller. Ici les deux vocabulaires sont IMPORTÉS de
leurs détenteurs uniques (#46) : `load_frameworks()` d'un côté, les `model_fields` Pydantic de
l'autre. Un renommage de champ change le résultat au lieu de le vider.

Les §A asserts existent pour la même raison : un ensemble vide, un référentiel illisible ou une
table d'alias qui ne pointe plus nulle part doit produire un FAIL NOMMÉ, jamais un zéro rassurant.

Usage (aucun réseau, aucune base — `frameworks.yaml` est un fichier inerte, et c'est une
réconciliation de contrats entre eux) :

    bash tools/reconcilier_vocabulaires.sh
"""
from __future__ import annotations

import sys

from app.agents.v2.frameworks import load_frameworks
from app.contracts.memo_blocs import BLOCS_MEMO, feuilles_memo

ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


# ⚠️ LA LISTE DES BLOCS A DÉMÉNAGÉ LE 2026-09-24 (lot 5). Elle vivait ici, recopiée à la main ; le
# projecteur et le pont des définitions en avaient besoin aussi, et trois exemplaires re-divergent
# au premier renommage (`feedback_correctif_regle_jumeaux`). Détenteur unique :
# `app.contracts.memo_blocs`, où elle est DÉRIVÉE de `ResearchMemo.model_fields`.
# `feuilles_memo()` l'a suivie, pour la même raison : elle dépendait d'elle.

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

# Le pont entre le mémo et la grille MVDD (`FIELD_PROFILES`) : même objet, préfixe différent.
#
# ⚠️ CETTE TABLE NE SERT PLUS AU VERDICT DE CE SCRIPT. Elle projetait des feuilles de mémo sur des
# chemins MVDD ; le lot 3 a retiré son autorité à cette grille, et §B juge désormais contre les
# `chemin_indexation` des frameworks, SANS alias — aucune question ne s'appelle
# `produits.unit_economics`. La garder ici et l'utiliser là-bas, c'est exactement ce qui a laissé
# ce mesureur rendre 14/3 pendant que l'acceptation rendait 30/13.
#
# Elle reste EXPORTÉE pour un seul consommateur, `tools/ligne_de_base_frameworks.py`, dont le
# travail est précisément de décrire l'ANCIEN monde : la ligne de base §9.1 est « le constat du
# défaut qui motive la v3 », jamais une cible (spec §9.1). La supprimer effacerait le constat.
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


def vocabulaire_questions() -> dict[str, str]:
    """Les `chemin_indexation` des questions, lus dans `frameworks.yaml` — chemin → framework id.

    `chemin_indexation` et non `id` : c'est LUI que le mémo consommerait. Comparer des `qf_1` à des
    `business_model.description` rendrait l'écart rouge par mésappariement de vocabulaire, pas par
    l'écart qu'on mesure.

    Aucune tolérance à l'échec de lecture ici : si `load_frameworks()` lève, la pile remonte. Un
    `except` qui rendrait `{}` produirait « 0 question jamais consommée » sur zéro question — un
    zéro rassurant sur une panne (`feedback_check_degrade_en_sortant_a_zero`).
    """
    fichier = load_frameworks()
    return {q.chemin_indexation: f.id for f in fichier.frameworks for q in f.questions}


def ecart(memo: set[str], vocabulaire: set[str]) -> tuple[list[str], list[str]]:
    """LA règle T6/T7, détenue une seule fois (#46) — `acceptation_frameworks` la consomme.

    Retourne (feuilles de mémo qu'aucune question ne fonde, questions que le mémo ne consomme
    jamais). Pas d'alias : sous le vocabulaire des frameworks il n'y a plus deux préfixes pour un
    même objet, c'est tout l'intérêt du lot 3.
    """
    sans_question = sorted(f for f in memo - DERIVES if f not in vocabulaire)
    jamais_consommees = sorted(vocabulaire - memo)
    return sans_question, jamais_consommees


def main() -> int:
    memo = feuilles_memo()
    questions = vocabulaire_questions()
    index = set(questions)

    # ── §A — le mesureur mesure-t-il quelque chose ? ─────────────────────────────
    # Sans ces asserts, toute panne de lecture se lit « 0 orpheline ».
    check("[A] le vocabulaire des QUESTIONS est non vide", bool(index),
          "→ aucun `chemin_indexation` lu : tout champ du mémo paraîtrait orphelin")
    check("[A] le vocabulaire de SORTIE est non vide", bool(memo),
          "→ aucune feuille lue : 'zéro orpheline' serait vrai sur zéro ligne")
    # L'appartenance d'un `chemin_indexation` à son framework N'EST PAS vérifiée ici : c'est
    # l'invariant [N] de `_valider_pont_definitions`, et `vocabulaire_questions()` passe par
    # `load_frameworks()`, qui LÈVE. Le vérifier une seconde fois ici en referait un jumeau — la
    # panne exacte que ce correctif répare.
    fichier = load_frameworks()
    fw_ids = {f.id for f in fichier.frameworks}
    derives_morts = sorted(d for d in DERIVES if d not in memo)
    check("[A] chaque champ déclaré DÉRIVÉ est encore une feuille du mémo", not derives_morts,
          f"→ {derives_morts} : une dispense qui ne dispense plus rien")
    # ALIAS ne juge plus rien ici, mais `ligne_de_base_frameworks` l'utilise encore contre la grille
    # MVDD : une clef périmée y DISPENSERAIT un champ qui n'existe plus. On la garde sous garde.
    aliases_morts = sorted(k for k in ALIAS if k not in memo)
    check("[A] chaque clef d'ALIAS est encore une feuille du mémo (pour la ligne de base §9.1)",
          not aliases_morts,
          f"→ {aliases_morts} : un alias périmé DISPENSE un champ qui n'existe plus, "
          f"et masquerait le jour où un champ homonyme réapparaît")

    print(f"\nvocabulaire des QUESTIONS (frameworks.yaml) : {len(index)} chemins, "
          f"{len(fw_ids)} framework(s)")
    print(f"champs FEUILLES du ResearchMemo (hors refs)         : {len(memo)}")
    print(f"   dont dérivés d'autres champs (pas à fonder)      : {len(DERIVES & memo)}")

    # ── §B — les deux écarts, qui sont l'objet du script ─────────────────────────
    orphelins, inutilises = ecart(memo, index)
    print(f"\n⚠️  champs du mémo SANS question qui les fonde ({len(orphelins)}) — "
          f"aucune entry ne peut les fonder :")
    for f in orphelins:
        print(f"   · {f}")

    print(f"\nquestions JAMAIS consommées par le mémo ({len(inutilises)}) — "
          f"des faits rangés que personne ne vient chercher :")
    for c in inutilises:
        print(f"   · {c}   [{questions[c]}]")

    # ── §C — l'écart est-il champ-par-champ, ou bloc-par-bloc ? ──────────────────
    # Un « 30 » nu se lit comme 30 champs cassés. Il dit en réalité : combien de chapitres de la
    # note n'ont AUCUNE méthodologie approuvée. Sans ce décompte, le rendu fabrique un diagnostic
    # faux (`feedback_rendu_est_un_producteur`).
    #
    # ⚠️ CE DÉCOMPTE MESURAIT LA MAUVAISE CHOSE JUSQU'AU 2026-09-24. Il testait
    # `chemin.startswith(f"{bloc}.")` — c'est-à-dire la COÏNCIDENCE DE NOMS entre un framework et un
    # chapitre. Or l'invariant [N] force la racine du chemin à valoir l'id du framework : §C ne
    # pouvait virer au vert qu'en appelant un framework `financials`, soit « un alias de plus »,
    # ce que l'en-tête de ce fichier rejette explicitement. Le lot 5 déclare le lien dans le
    # référentiel (`bloc_memo`), et §C le LIT — un lien déclaré, jamais un nom deviné.
    revendique = {f.bloc_memo: f.id for f in fichier.frameworks}
    blocs_couverts = sorted(b for b in BLOCS_MEMO if b in revendique)
    blocs_nus = sorted(set(BLOCS_MEMO) - set(revendique))
    print(f"\nchapitres de la note adossés à une méthodologie approuvée : "
          f"{len(blocs_couverts)} / {len(BLOCS_MEMO)}")
    for b in blocs_couverts:
        print(f"   ✓ {b} ← {revendique[b]}")
    for b in blocs_nus:
        print(f"   · {b} — aucune méthodologie approuvée")

    print()
    check("[B] zéro feuille de mémo sans question (T6)", not orphelins,
          f"→ {len(orphelins)} champs produits sans preuve indexable possible")
    check("[B] zéro question jamais consommée (T7)", not inutilises,
          f"→ {len(inutilises)} questions instruites pour personne")

    print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
    if fail:
        print("ROUGE ATTENDU — il vire au vert quand CHAQUE bloc du mémo sera la projection d'un\n"
              "framework acquitté (spec v3 §6). Avec 2 pilotes sur 6 blocs, §C montre que l'écart\n"
              "est bloc-par-bloc : c'est l'état terminal de la roadmap, pas un lot. Un vert ici\n"
              "avant cela est un défaut du mesureur, pas une bonne nouvelle.", file=sys.stderr)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
