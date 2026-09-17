"""L'INVENTAIRE TEL QUE L'APPARIEUR LE MONTRERA AU MODÈLE — la frontière gratuite du maillon 4bis.

CE QU'IL MESURE
---------------
Pour chaque émetteur : l'inventaire `us-gaap` réellement déposé, rendu par
`apparieur.resumer_inventaire` / `rendre_inventaire` — c'est-à-dire **le texte exact** qui partira
dans le contexte du modèle. Puis trois nombres qui décident si ce contexte est tenable : combien de
concepts, combien de caractères, combien de jetons d'entrée (donc combien ça coûte).

POURQUOI IL EXISTE AVANT L'AGENT, ET PAS APRÈS
-----------------------------------------------
L'étape 2a demande au modèle d'adresser 269 à 627 concepts PAR LEUR NOM sans en réinventer. Le remède
par le prompt est déjà mesuré et disqualifié : 11 lignes justes sur NVDA, et le MÊME prompt rend 10
lignes fausses sur MSFT (`feedback_jugement_modele_instable_entre_passages`). Ce qui reste, c'est
l'OUTIL DE LECTURE — et un outil de lecture ne se juge pas sur l'intention, il se lit
(`feedback_adressage_par_nom_exige_lecture`, `feedback_frontiere_gratuite_avant_depense_modele`).

Ce mesureur ne touche NI la base NI un modèle : quelques appels publics à data.sec.gov. Il se relit
EN TEXTE avant le premier jeton payé, et il se rejoue après chaque changement du rendu.

L'INVARIANT QU'IL GARDE, ET QUI N'EST PAS DÉCORATIF
---------------------------------------------------
`[B]` : le vocabulaire que le modèle LIT est exactement celui que le pont `[V]` ACCEPTE. On le
vérifie en RELISANT le texte rendu (premier mot de chaque ligne) et en comparant l'ensemble obtenu
aux clefs de l'inventaire — pas en comptant les lignes du résumé, qui ne prouverait rien du rendu.
Un rendu qui filtrerait « les concepts vivants » ou « ceux du dernier exercice » fabriquerait des
refus dont le modèle ne pouvait pas sortir, et le taux de refus mesurerait alors notre filtre. C'est
la même faute que celle d'un `list_*` qui ne couvre qu'une partie du corpus : elle passe en
`verdict=ok`.

Usage (réseau public, aucune base, aucun modèle, aucune dépense modèle) :

    bash tools/inventaire_apparieur.sh                    # les 3 émetteurs pilotes, extrait + stats
    bash tools/inventaire_apparieur.sh RVMD --plein        # la table ENTIÈRE, telle qu'elle partira
    bash tools/inventaire_apparieur.sh NVDA --extrait 60
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, timezone, datetime

from app.agents.v2.apparieur import (
    AppariementSansObjet,
    dernier_depot_vu,
    rendre_inventaire,
    resumer_inventaire,
)
from app.knowledge.edgar_facts import EdgarUnavailable, fetch_company_facts
from app.knowledge.edgar_feed import EdgarFeedUnavailable, resolve_cik

ok = fail = 0

# Tarif d'entrée du modèle de la chaîne (DeepSeek-V4-Flash via DeepInfra, $/M jetons). Sert à
# CHIFFRER la décision « inventaire entier plutôt que liste courte » : si le nombre est négligeable,
# il n'y a pas d'arbitrage à faire, et ce mesureur est ce qui permet de l'affirmer au lieu de le
# supposer. Le ratio 4 caractères/jeton est l'ordre de grandeur usuel sur du texte ASCII tabulé.
_USD_PAR_M_JETONS_ENTREE = 0.08
_CARACTERES_PAR_JETON = 4


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def _concepts_du_texte(texte: str) -> list[str]:
    """Les noms de concepts RELUS dans le texte rendu — premier mot de chaque ligne non vide.

    On relit le rendu au lieu de faire confiance au résumé : c'est le TEXTE qui part au modèle, et
    c'est donc lui qui doit être total. Un rendu qui tronquerait une ligne longue, fusionnerait deux
    concepts ou mangerait un nom à l'alignement passerait un contrôle fait sur la liste d'entrée.
    """
    return [ligne.split()[0] for ligne in texte.splitlines() if ligne.strip()]


async def inventorier(symbole: str, *, extrait: int, plein: bool) -> bool:
    """L'inventaire d'UN émetteur, rendu et mesuré. False si le pré-requis « émetteur lisible » casse."""
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

    lignes = resumer_inventaire(facts)
    texte = rendre_inventaire(lignes)
    relus = _concepts_du_texte(texte)

    # ── ce que ça coûte de tout montrer ───────────────────────────────────────────────────────────
    jetons = len(texte) // _CARACTERES_PAR_JETON
    cout = jetons * _USD_PAR_M_JETONS_ENTREE / 1_000_000
    par_nature: dict[str, int] = {}
    for l in lignes:
        par_nature[l.nature] = par_nature.get(l.nature, 0) + 1
    print(f"  CIK {cik:010d} · {len(facts)} concepts déposés · "
          + " · ".join(f"{n} {k}" for k, n in sorted(par_nature.items())))
    print(f"  rendu : {len(texte):,} caractères ≈ {jetons:,} jetons d'entrée ≈ ${cout:.4f} par appel")

    try:
        depot = dernier_depot_vu(facts)
    except AppariementSansObjet as e:
        check(f"[D] {symbole} : `dernier_depot_vu` datable", False, f"→ {e}")
        return False
    print(f"  dernier_depot_vu = {depot}")

    # ── la table, telle qu'elle partira ───────────────────────────────────────────────────────────
    print(f"\n  inventaire{'' if plein else f' (extrait : {min(extrait, len(lignes))} lignes sur {len(lignes)})'} :")
    if plein:
        print(texte)
    else:
        moitie = max(extrait // 2, 1)
        print("\n".join(texte.splitlines()[:moitie]))
        if len(lignes) > extrait:
            print(f"  … {len(lignes) - extrait} ligne(s) …")
        print("\n".join(texte.splitlines()[-(extrait - moitie):]))

    # ── [B] le vocabulaire LU est celui que `[V]` ACCEPTE ─────────────────────────────────────────
    print()
    manquants = sorted(set(facts) - set(relus))
    intrus = sorted(set(relus) - set(facts))
    check(f"[B] {symbole} : le rendu nomme les {len(facts)} concepts de l'inventaire, et eux seuls",
          not manquants and not intrus,
          f"→ {len(manquants)} absent(s) du rendu {manquants[:5]} · {len(intrus)} intrus {intrus[:5]}")
    check(f"[B] {symbole} : une ligne par concept, aucun doublon",
          len(relus) == len(set(relus)) == len(facts),
          f"→ {len(relus)} ligne(s) pour {len(facts)} concept(s), {len(set(relus))} nom(s) distinct(s)")
    check(f"[C] {symbole} : le discriminant flux/solde est rendu, pas supposé",
          par_nature.get("flux", 0) > 0 and par_nature.get("instant", 0) > 0,
          f"→ {par_nature} (un inventaire sans flux OU sans instant signale un rendu cassé, "
          "pas un émetteur atypique)")
    aujourdhui = datetime.now(timezone.utc).date()
    check(f"[D] {symbole} : `dernier_depot_vu` ({depot}) n'est pas dans le futur",
          date.fromisoformat(depot) <= aujourdhui,
          f"→ postérieur à {aujourdhui} : un dépôt futur figerait une borne qu'aucun dépôt réel ne "
          "franchira, donc une carte valable pour toujours")
    return True


async def main_async(symboles: list[str], *, extrait: int, plein: bool) -> int:
    print("=" * 100)
    print("INVENTAIRE APPARIEUR — le contexte exact que le modèle lira, mesuré avant toute dépense")
    print("=" * 100)

    # §A pré-requis : sans symbole, tout ce qui suit rendrait « 0 concept » sur des émetteurs qui
    # déposent tout — un zéro rassurant, exactement le faux vert à refuser
    # (`feedback_check_degrade_en_sortant_a_zero`).
    print("\n[A] pré-requis du mesureur")
    check("[A] au moins un symbole à inventorier", bool(symboles), "→ aucun argument")

    lisibles = 0
    if not fail:
        for symbole in symboles:
            if await inventorier(symbole, extrait=extrait, plein=plein):
                lisibles += 1
        print()
        check("[E] tous les émetteurs demandés ont été lus",
              lisibles == len(symboles), f"→ {lisibles}/{len(symboles)}")

    print(f"\n{'=' * 100}")
    print(f"BILAN inventaire apparieur — {len(symboles)} émetteur(s) demandé(s), {lisibles} lu(s) "
          f"· {ok} vérifications OK, {fail} échec(s)")
    if fail:
        print("Un pré-requis manquant sort en exit != 0 : un inventaire tronqué se lirait comme un\n"
              "émetteur qui dépose peu, et le taux de refus de l'apparieur mesurerait notre rendu.",
              file=sys.stderr)
    return 1 if fail else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("symboles", nargs="*",
                    help="symboles boursiers (défaut : les 3 émetteurs pilotes du lot 3)")
    ap.add_argument("--plein", action="store_true",
                    help="imprimer la table ENTIÈRE (ce qui part réellement au modèle)")
    ap.add_argument("--extrait", type=int, default=40,
                    help="nombre de lignes de l'extrait quand la table n'est pas imprimée en plein")
    args = ap.parse_args()
    return asyncio.run(main_async(args.symboles or ["NVDA", "MSFT", "RVMD"],
                                  extrait=args.extrait, plein=args.plein))


if __name__ == "__main__":
    raise SystemExit(main())
