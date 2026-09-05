"""Rejeu du corpus d'intention — capacité 3 (pré-classifieur multi-étiquette + fidélité C7).

    docker exec -w /app -e PYTHONPATH=/app assistant-ia python checks/replay_intent_corpus.py

Ce script **appelle le modèle réel**, **écrit dans le vault** et **crée des cartes kanban** : c'est
son objet. Le contrat `tools[]` est *proposé* au modèle ; rien ne prouve qu'il est mobilisé tant
qu'on ne l'a pas rejoué contre le vrai modèle.

Il porte les deux tests d'acceptation de la capacité 3, tels que la roadmap les énonce :

  C6 — « Enregistre ce climatiseur dans une liste … Crée un rappel … le 1er décembre. <lien> »
       → **deux** effets pour un seul message : un document touché sous `documents/` **et** une
         carte `Rappels` datée du 2026-12-01.
  C7 — « Rappelle-moi demain 9h d'acheter … ⏎ Je prendrai madame Loïc, hummus et concombre chez moi. »
       → titre de carte < 60 caractères, charge utile dans le **corps** de la carte, et la seconde
         phrase (ce que l'utilisateur dit déjà avoir) **absente** du rappel.

## Deux principes de mesure, hérités de `replay_capture_corpus.py`

**Le relevé encadre le tour.** Les cartes de la colonne `Rappels` et les lignes de `documents/*.md`
sont relevées avant et après chaque cas ; la cible est **déduite du delta**, jamais prédite par le
script. Un script qui prédit un chemin teste le script, pas le code.

**La ligne de base se requête, elle ne se remémore pas.** Les valeurs rouges du 2026-09-05 (« C6 a
produit zéro effet ») ont été mesurées *avant* la capacité 2 : le vault n'avait pas de documents et
`capture_note` n'existait pas. Relancer ce script avant tout correctif est ce qui dit où on part
réellement, une fois le doc v4 et la capture en ligne.

## Ménage

Les cartes créées pendant le rejeu sont supprimées en fin de course (elles sont identifiées par
leur `id`, relevé à la seconde près — jamais par un motif de titre). `--keep` les conserve pour
inspection. Les documents écrits dans le vault, eux, ne sont **pas** supprimés : ils portent le
suffixe de session et l'utilisateur les retire d'un clic dans Obsidian.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings                                       # noqa: E402
from app.services import agent_doc, kanban as kanban_svc              # noqa: E402
from app.services.agent_tools import create_reminder, loop            # noqa: E402
from app.services.agent_tools.manifest import TurnState               # noqa: E402

REPLAY_CHANNEL = "C_REPLAY_CAP3"

# Le 1er décembre visé par C6. L'année est celle du prochain 1er décembre à venir : le corpus a été
# écrit en 2026, mais un rejeu en janvier 2027 doit viser 2027-12-01 et non une date passée que
# `create_reminder` refuserait à juste titre.
def _cible_1er_decembre(aujourdhui: date) -> date:
    annee = aujourdhui.year if aujourdhui <= date(aujourdhui.year, 12, 1) else aujourdhui.year + 1
    return date(annee, 12, 1)


# La seconde phrase de C7 : ce que l'utilisateur dit **déjà** prendre chez lui. Elle n'appartient
# pas au rappel. Ces trois termes sont le point de lecture du critère « n'y est pas fusionnée ».
C7_HORS_RAPPEL = ("madame loïc", "madame loic", "hummus", "concombre")
# Les courses réellement demandées : elles, doivent être présentes quelque part dans la carte.
C7_DANS_RAPPEL = ("pain", "tomates cerises", "abricot")

TITRE_MAX_ACCEPTATION = 60

ECHECS: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ✓ {label}")
    else:
        print(f"  ✗ {label} — {detail}")
        ECHECS.append(f"{label} — {detail}" if detail else label)


def cas_du_corpus(suffixe: str) -> list[tuple[str, str]]:
    """Le corpus, au verbatim de la roadmap.

    Le suffixe de session ne porte que sur le **nom de document** de C6 : sans lui, le second rejeu
    compléterait le document de la veille et « un document touché » serait vrai sans rien prouver.
    Le rappel, lui, reste au verbatim — sa cible est une date, pas un nom.
    """
    return [
        ("C6",
         "Enregistre ce climatiseur dans une liste de potentiels options de climatisation à "
         f"acheter cet hiver, appelée climatisation {suffixe}. Crée un rappel pour regarder cela "
         "le 1er décembre. https://www.amazon.fr/dp/B08XYZ1234"),
        ("C7",
         "Rappelle-moi demain matin à 9h d'acheter la liste de courses suivante : pain, chips de "
         "légumes et Pringles, tomates cerises, abricot, tranche de rôti.\n"
         "Je prendrai madame Loïc, hummus et concombre chez moi."),
    ]


def _relevé_documents(root: Path) -> dict[str, int]:
    d = root / "documents"
    if not d.is_dir():
        return {}
    return {p.name: p.read_text(encoding="utf-8").count("\n") for p in d.glob("*.md")}


def _delta(avant: dict[str, int], apres: dict[str, int]) -> tuple[list[str], list[str]]:
    apparus = sorted(set(apres) - set(avant))
    grossis = sorted(n for n in apres if n in avant and apres[n] > avant[n])
    return apparus, grossis


async def _colonne_rappels() -> str:
    """L'id de la colonne `Rappels`, telle que l'outil la résout lui-même.

    On réutilise `create_reminder._target_column()` : relever une colonne que le script aurait
    choisie de son côté reviendrait à mesurer un autre endroit que celui où l'outil écrit.
    """
    return await create_reminder._target_column()


async def _relevé_cartes(column_id: str) -> dict[str, dict]:
    cartes = await kanban_svc.list_cards(column_id)
    return {str(c["id"]): dict(c) for c in cartes}


async def rejouer(nom: str, message: str, doc) -> tuple[list[str], str, list[str]]:
    """Déroule un tour et renvoie (outils appelés, réponse finale, messages Slack simulés)."""
    postes: list[str] = []

    async def faux_post(*, channel, blocks, text, thread_ts=None):
        postes.append(text)
        return "0000000000.000000"

    orig = loop.post_blocks
    loop.post_blocks = faux_post
    try:
        turn = TurnState(
            channel_id=REPLAY_CHANNEL,
            user_id="U_REPLAY",
            slack_ts=f"replay-{nom}-{int(time.time())}",
            thread_ts=f"replay-{nom}",
            doc_version=doc.version,
        )
        outcome = await loop.run_turn(
            [{"role": "system", "content": doc.content}, {"role": "user", "content": message}],
            turn,
        )
    finally:
        loop.post_blocks = orig

    appels = sorted(turn.turn_counts)
    print(f"\n--- {nom} — « {message[:70]}… »")
    print(f"    outils appelés : {appels or '(aucun)'}")
    for p in postes:
        print(f"    posté : {p}")
    print(f"    réponse : {outcome.text[:250]}")
    return appels, outcome.text, postes


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default=f"r{int(time.time()) % 100000}")
    parser.add_argument("--keep", action="store_true",
                        help="conserve les cartes créées par le rejeu (défaut : les supprimer)")
    args = parser.parse_args()
    suffixe = args.session

    doc = await agent_doc.get_active_doc()
    if not doc:
        print("ECHEC — aucun doc système actif : rien à rejouer.")
        return 1
    print(f"doc système actif : v{doc.version} ({len(doc.content)} car.)")
    print(f"suffixe de session : {suffixe}")

    root = Path(settings.JOURNAL_VAULT_PATH)
    colonne = await _colonne_rappels()
    cible_decembre = _cible_1er_decembre(date.today())
    print(f"colonne Rappels : {colonne}")
    print(f"cible de C6 : {cible_decembre.isoformat()}")

    relevés_doc: dict[str, dict[str, int]] = {}
    relevés_cartes: dict[str, dict[str, dict]] = {}
    resultats: dict[str, list[str]] = {}
    reponses: dict[str, str] = {}
    creees: list[str] = []

    for nom, message in cas_du_corpus(suffixe):
        relevés_doc[f"avant_{nom}"] = _relevé_documents(root)
        relevés_cartes[f"avant_{nom}"] = await _relevé_cartes(colonne)
        appels, texte, _ = await rejouer(nom, message, doc)
        relevés_doc[f"apres_{nom}"] = _relevé_documents(root)
        relevés_cartes[f"apres_{nom}"] = await _relevé_cartes(colonne)
        resultats[nom] = appels
        reponses[nom] = texte

    def cartes_neuves(nom: str) -> list[dict]:
        avant, apres = relevés_cartes[f"avant_{nom}"], relevés_cartes[f"apres_{nom}"]
        neuves = [apres[i] for i in apres if i not in avant]
        creees.extend(str(c["id"]) for c in neuves)
        return neuves

    print("\n--- Acceptation C6 : deux effets pour un seul message ---")
    apparus, grossis = _delta(relevés_doc["avant_C6"], relevés_doc["apres_C6"])
    check("C6 : un document touché sous documents/",
          len(apparus) + len(grossis) >= 1, f"apparus={apparus} grossis={grossis}")
    cible_doc = (apparus + grossis)[0] if (apparus + grossis) else None
    if cible_doc:
        texte_doc = (root / "documents" / cible_doc).read_text(encoding="utf-8")
        check(f"C6 : le climatiseur est dans {cible_doc}",
              "amazon.fr" in texte_doc.lower(), "le lien demandé n'a pas été écrit")

    neuves_c6 = cartes_neuves("C6")
    check("C6 : exactement une carte créée dans Rappels",
          len(neuves_c6) == 1, f"{len(neuves_c6)} carte(s) créée(s)")
    if neuves_c6:
        carte = neuves_c6[0]
        due = carte.get("due_date")
        check(f"C6 : la carte est datée du {cible_decembre.isoformat()}",
              due is not None and due.date() == cible_decembre,
              f"due_date = {due}")
    check("C6 : les deux effets dans le même tour (document ET carte)",
          bool(cible_doc) and len(neuves_c6) == 1,
          f"document={cible_doc} cartes={len(neuves_c6)}")

    print("\n--- Acceptation C7 : fidélité de capture ---")
    neuves_c7 = cartes_neuves("C7")
    check("C7 : une carte créée dans Rappels", len(neuves_c7) == 1,
          f"{len(neuves_c7)} carte(s) créée(s)")
    if neuves_c7:
        carte = neuves_c7[0]
        titre = str(carte.get("title") or "")
        corps = str(carte.get("description") or "")
        print(f"    titre  ({len(titre)} car.) : {titre!r}")
        print(f"    corps  ({len(corps)} car.) : {corps!r}")

        check(f"C7 : titre < {TITRE_MAX_ACCEPTATION} caractères",
              len(titre) < TITRE_MAX_ACCEPTATION, f"{len(titre)} caractères : {titre!r}")
        check("C7 : la charge utile est dans le corps de la carte",
              bool(corps.strip()), "description vide — la liste a nulle part où aller")

        entier = f"{titre}\n{corps}".lower()
        manquants = [t for t in C7_DANS_RAPPEL if t not in entier]
        check("C7 : les courses demandées sont dans la carte",
              not manquants, f"absents : {manquants}")
        intrus = [t for t in C7_HORS_RAPPEL if t in entier]
        check("C7 : la seconde phrase n'entre pas dans le rappel",
              not intrus, f"termes fusionnés à tort : {intrus}")

    if creees and not args.keep:
        print(f"\nMénage : suppression des {len(creees)} carte(s) créée(s) par ce rejeu")
        for card_id in creees:
            await kanban_svc.delete_card(card_id)
            print(f"  – carte {card_id} supprimée")
    elif creees:
        print(f"\n--keep : {len(creees)} carte(s) conservée(s) : {creees}")
    print(f"Documents de session à retirer si besoin : {root}/documents/*{suffixe}*.md")

    print("\n" + "=" * 60)
    if ECHECS:
        print(f"ECHEC — {len(ECHECS)} assertion(s) :")
        for e in ECHECS:
            print(f"  ✗ {e}")
        return 1
    print("OK — capacité 3 acceptée (deux intentions dans un tour, capture fidèle).")
    return 0


sys.exit(asyncio.run(main()))
