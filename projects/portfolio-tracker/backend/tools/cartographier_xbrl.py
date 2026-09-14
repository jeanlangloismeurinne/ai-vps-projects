"""Cartographie des concepts XBRL RÉELLEMENT déposés par un émetteur, confrontée au catalogue POSTES.

CE QU'IL MESURE
---------------
Deux nombres, par ticker :

  · combien de concepts `us-gaap` l'émetteur DÉPOSE (lu dans `companyfacts`, un appel) ;
  · combien de postes du catalogue `edgar_feed.POSTES` trouvent chez LUI un concept candidat déposé.

Et la liste que ces deux nombres rendent lisible : **ce que l'émetteur publie et que nous n'écoutons
pas** — les concepts présents dans son dernier exercice annuel et qu'aucun poste ne réclame.

POURQUOI IL EXISTE (mesure du 2026-09-14)
------------------------------------------
Le catalogue interrogeait 8 concepts. NVDA en dépose 627, MSFT 562, RVMD 269. Sur 74 lignes de plan
mesurées en `--plan-only`, 7 partaient vers EDGAR (dont 5 sur un FAUX appariement) et 66 vers une
recherche web payante en tier B — pour des niveaux bruts que la SEC publie en tier A. Le défaut
n'était pas dans la réponse d'EDGAR, qui rend exactement le concept demandé ; il était dans le choix
du concept, fait AVANT l'appel.

Ce mesureur est la frontière gratuite de ce chantier
(`feedback_frontiere_gratuite_avant_depense_modele`) : il ne coûte que des appels publics, il ne
touche NI la base NI un modèle, et il se relit EN TEXTE avant toute dépense. Il se rejoue après
chaque enrichissement du catalogue — c'est lui qui dit si le poste ajouté se fonde réellement.

CE QU'IL N'EST PAS
------------------
Ce n'est pas une mesure : `companyfacts` rend un inventaire brut, toutes unités et tous cadrages
confondus. Choisir LE point d'un exercice reste le travail de `select_concept` sur le chemin
`companyconcept`, qui lui est déjà éprouvé par `checks/check_edgar_feed.py`. Ici on répond à
« de quoi cet émetteur parle-t-il ? », pas à « combien ? ».

Ce n'est pas non plus une source de conception de framework. Les questions d'un framework se
décident AVANT de regarder ce que la donnée offre (§0.6, `feedback_portfolio_v3_framework_avant_donnees`) :
cette carte dit où un ingrédient DÉJÀ décidé peut se collecter au tier A — jamais quels ingrédients
mériteraient d'être demandés. Elle est lue par le catalogue, jamais par le traducteur.

UN ABSENT N'EST PAS UN ÉCHEC
-----------------------------
RVMD ne dépose ni `IncreaseDecreaseInInventories` (une biotech pré-revenus n'a pas de stocks) ni
`LongTermDebtCurrent` (sa dette est en obligations convertibles). C'est le cas NOMINAL, déjà écrit
dans `edgar_feed` : « le concept se choisit sur ce que l'émetteur DÉPOSE, jamais sur ce que sa
catégorie est censée déposer » (#30). Un poste non fondé retombe proprement au web. Ce qui sort en
`exit != 0`, ce sont les PRÉ-REQUIS — un catalogue vide, un poste sans candidat, un émetteur
injoignable — parce qu'une mesure incomplète écrase de la vérité
(`feedback_check_degrade_en_sortant_a_zero`).

Usage (réseau public, aucune base, aucun modèle) :

    bash tools/cartographier_xbrl.sh NVDA MSFT RVMD
    bash tools/cartographier_xbrl.sh NVDA --hors-catalogue 40
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from typing import Any, Optional

from app.knowledge.edgar_facts import EdgarUnavailable, fetch_company_facts
from app.knowledge.edgar_feed import POSTES, EdgarFeedUnavailable, resolve_cik

ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


# Formes annuelles : un concept « vivant » est un concept que le DERNIER exercice porte encore. Un
# concept abandonné depuis 2019 est déposé au sens de l'API, mais il ne suit plus l'entreprise.
_FORMES_ANNUELLES = {"10-K", "10-K/A", "20-F", "20-F/A"}


def _candidats(poste: Any) -> list[str]:
    """Tous les concepts candidats d'un poste, second volet d'un composite inclus."""
    return list(poste.concepts) + list(getattr(poste, "composite_concepts", []) or [])


def _dernier_end(points: list[dict[str, Any]], *, annuel_seulement: bool) -> Optional[date]:
    """Date de fin du point le plus récent. None si le concept n'a aucun point exploitable."""
    best: Optional[date] = None
    for p in points:
        if annuel_seulement and p.get("form") not in _FORMES_ANNUELLES:
            continue
        try:
            d = date.fromisoformat(str(p.get("end")))
        except (TypeError, ValueError):
            continue
        if best is None or d > best:
            best = d
    return best


async def cartographier(symbole: str, *, hors_catalogue: int) -> bool:
    """Carte d'UN émetteur. Rend False si le pré-requis « émetteur lisible » n'est pas tenu."""
    print(f"\n{'─' * 100}\n{symbole}")
    try:
        cik = await resolve_cik(symbole)
    except EdgarFeedUnavailable as e:
        check(f"[A] {symbole} : CIK résolu", False, f"→ {e}")
        return False
    try:
        facts = await fetch_company_facts(cik)
    except EdgarUnavailable as e:
        check(f"[A] {symbole} : companyfacts lisible", False, f"→ {e}")
        return False

    vivants = {c: d for c in facts if (d := _dernier_end(facts[c], annuel_seulement=True))}
    print(f"  CIK {cik:010d} · {len(facts)} concepts us-gaap déposés "
          f"· {len(vivants)} encore portés par un exercice annuel")

    # ── ce que le catalogue sait demander chez CET émetteur ────────────────────────────────────────
    print(f"\n  postes du catalogue ({len(POSTES)}) :")
    fondes = 0
    reclames: set[str] = set()
    for poste in POSTES:
        cands = _candidats(poste)
        reclames.update(cands)
        # Le candidat retenu se choisit sur la FRAÎCHEUR, l'ordre n'arbitrant qu'à fraîcheur égale —
        # c'est la règle de `select_concept`, et la carte doit raconter la même histoire que le
        # collecteur. Lire « le premier candidat déposé » annoncerait `revenue` chez NVDA sur un
        # concept arrêté en 2022, quand le runtime, lui, prend le concept encore alimenté.
        deposes = [(c, d) for c in cands
                   if c in facts and (d := _dernier_end(facts[c], annuel_seulement=False))]
        if not deposes:
            print(f"    absent  {poste.metric:<34} aucun de {len(cands)} candidat(s) déposé")
            continue
        fondes += 1
        retenu, d = max(deposes, key=lambda cd: (cd[1], -cands.index(cd[0])))
        autres = f" (+{len(deposes) - 1} autre(s) candidat(s) déposé(s))" if len(deposes) > 1 else ""
        print(f"    fondé   {poste.metric:<34} {retenu} (dernier point {d}){autres}")
    print(f"\n  → {fondes}/{len(POSTES)} postes fondés pour {symbole}")

    # ── ce que l'émetteur publie et que nous n'écoutons pas ────────────────────────────────────────
    if hors_catalogue:
        muets = sorted(
            ((c, d) for c, d in vivants.items() if c not in reclames),
            key=lambda cd: (cd[1], len(facts[cd[0]])), reverse=True,
        )
        print(f"\n  concepts du dernier exercice qu'AUCUN poste ne réclame "
              f"({len(muets)}, les {min(hors_catalogue, len(muets))} plus récents) :")
        for concept, d in muets[:hors_catalogue]:
            print(f"    · {concept:<64} {d}")
    return True


async def main_async(symboles: list[str], *, hors_catalogue: int) -> int:
    print("=" * 100)
    print("CARTOGRAPHIE XBRL — ce que l'émetteur dépose, face à ce que le catalogue sait demander")
    print("=" * 100)

    # §A pré-requis : un catalogue vide ou un poste sans candidat rendrait « 0 poste fondé » sur un
    # émetteur qui dépose tout — un zéro rassurant, exactement le faux vert à refuser.
    print("\n[A] pré-requis du mesureur")
    check("[A] le catalogue POSTES n'est pas vide", bool(POSTES), "→ rien à confronter")
    sans_candidat = [p.metric for p in POSTES if not _candidats(p)]
    check("[A] chaque poste porte au moins un concept candidat", not sans_candidat,
          f"→ {sans_candidat}")
    doublons = sorted({p.metric for p in POSTES if [q.metric for q in POSTES].count(p.metric) > 1})
    check("[A] aucun `metric` de poste en double (#46, détenteur unique)", not doublons,
          f"→ {doublons}")
    check("[A] au moins un symbole à cartographier", bool(symboles), "→ aucun argument")

    lisibles = 0
    if not fail:
        for symbole in symboles:
            if await cartographier(symbole, hors_catalogue=hors_catalogue):
                lisibles += 1
        print()
        check("[B] tous les émetteurs demandés ont été lus",
              lisibles == len(symboles), f"→ {lisibles}/{len(symboles)}")

    print(f"\n{'=' * 100}")
    print(f"BILAN cartographie — {len(symboles)} émetteur(s) demandé(s), {lisibles} lu(s), "
          f"{len(POSTES)} poste(s) au catalogue · {ok} vérifications OK, {fail} échec(s)")
    if fail:
        print("Un pré-requis manquant sort en exit != 0 : une carte incomplète se lirait comme une\n"
              "absence de données chez l'émetteur, ce qui est faux.", file=sys.stderr)
    return 1 if fail else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("symboles", nargs="*", default=["NVDA", "MSFT", "RVMD"],
                    help="symboles boursiers (défaut : les 3 émetteurs pilotes du lot 3)")
    ap.add_argument("--hors-catalogue", type=int, default=25,
                    help="nombre de concepts non réclamés à lister (0 pour n'en lister aucun)")
    args = ap.parse_args()
    symboles = args.symboles or ["NVDA", "MSFT", "RVMD"]
    return asyncio.run(main_async(symboles, hors_catalogue=args.hors_catalogue))


if __name__ == "__main__":
    raise SystemExit(main())
