"""Rejeu du corpus de non-régression — capacité 2 (`capture_note` + `list_documents`).

    docker exec -w /app -e PYTHONPATH=/app assistant-ia python checks/replay_capture_corpus.py

Ce script **appelle le modèle réel** et **écrit réellement dans le vault** : c'est tout son objet.
Un correctif de prompt ou de manifeste n'est pas acquis tant qu'il n'a pas tourné contre le vrai
modèle — le contrat `tools[]` est *proposé* au modèle, il n'est pas exécuté par lui.

Ce qui est simulé, et pourquoi : seuls les envois Slack (`post_blocks`) sont neutralisés, pour ne
pas poster dans `#assistant` un tour que l'utilisateur n'a pas écrit. Le doc système actif, le
registre d'outils, la policy, le classifieur, le writer et l'index sont les vrais.

L'historique de conversation n'est **pas** rechargé ni sauvegardé : chaque cas est rejoué isolé, à
partir du seul doc actif. C'est ce qui rend le résultat attribuable au doc et à l'outil, et non à
ce qui traînait dans le fil.

## Rejouabilité — deux défauts corrigés le 2026-09-05

**Premier défaut.** La version initiale comparait `apres - avant` sur l'ensemble du vault et
concluait « C2 n'a rien écrit » au second passage : les fichiers existaient déjà, la différence
était vide, et deux assertions viraient au rouge sans qu'aucune régression n'ait eu lieu. Un
script qui ne peut pas tourner deux fois n'est pas une mesure, c'est une impression.

**Second défaut, celui de la correction elle-même.** La correction fut d'ajouter un suffixe de
session au nom demandé (« sources utiles r29097 »). Elle a viré au rouge pour une raison qui est
en fait un succès : le modèle a appelé `list_documents`, vu le `sources-utiles.md` existant, et
**réutilisé son nom exact** — ce que le doc système v4 lui ordonne précisément de faire. Le
script attendait un fichier suffixé qui, par construction, ne pouvait plus naître. L'assertion
était au mauvais point de lecture : elle vérifiait un *nom prédit par le script* là où le contrat
porte sur *le document effectivement écrit*.

**La forme retenue.** Le script ne prédit plus aucun chemin pour les cas d'ajout : il prend un
relevé des lignes de `documents/*.md` avant le tour, un après, et **déduit** la cible du delta.
C'est le seul point de lecture qui reste juste que le modèle réutilise un document ancien ou en
crée un neuf. Le suffixe de session ne subsiste que là où l'enjeu est « un second document
a-t-il été fabriqué ? » (C8/C8bis), où il garantit un point de départ vierge.

Cas rejoués (verbatim de la roadmap `agent-intention-et-capture-kb.md`) :
  C1 — note de lecture   → attendu : un `.md` neuf sous `notes/`
  C2 — « stocke ce lien dans une liste de sources utiles » → attendu : **un** document touché
  C8 — « crée une liste de startups… » avec 2 noms → attendu : un document neuf, 2 noms dedans
  C2bis — second ajout sur le même document → attendu : `+n` lignes, `-0` (l'invariant de D5)
  C8bis — **la même demande que C8, formulée autrement** → attendu : *aucun* nouveau document
          (c'est le test du doublon `startups-spatial` / `startups-spatial-a-creuser`)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings                                       # noqa: E402
from app.services import agent_doc                                    # noqa: E402
from app.services.agent_tools import loop                             # noqa: E402
from app.services.agent_tools.manifest import TurnState               # noqa: E402

# Channel dédié au rejeu : les lignes d'`agent_tool_calls` produites ici restent distinguables
# d'un usage réel, sans qu'il faille les effacer après coup.
REPLAY_CHANNEL = "C_REPLAY_CAP2"

ECHECS: list[str] = []


def cas_du_corpus(suffixe: str) -> list[tuple[str, str]]:
    """Le corpus. Le suffixe de session ne porte que sur C8/C8bis.

    C2 et C2bis restent au verbatim de la roadmap, sans suffixe : leur contrat est « le lien
    atterrit dans *un* document de sources », que ce document existe depuis hier ou naisse
    maintenant. Y injecter un nom fabriqué reviendrait à tester que le modèle ignore les
    documents existants — l'inverse de ce que le doc système v4 lui demande.

    C8/C8bis, eux, testent le doublon : il leur faut un nom dont on sait qu'aucun document ne le
    porte encore, sinon « aucun document supplémentaire » serait vrai sans rien prouver.
    """
    return [
        ("C1", "Note de lecture Safran : le EU Space Act impose un régime d'autorisation unique "
               "aux opérateurs de constellations, ce qui change la donne pour les équipementiers "
               f"européens — à recouper avec la position d'Airbus. (rejeu {suffixe})"),
        ("C2", "Stocke ce lien dans une liste de sources utiles : payloadspace.com"),
        ("C8", "Crée une liste de startups du secteur du spatial dont les innovations sont à "
               f"creuser, appelée startups spatial {suffixe}. Voilà de premiers noms : Isembard, "
               "Tachyon Industrie"),
        ("C2bis", "Ajoute aussi spacenews.com à ma liste de sources utiles."),
        ("C8bis", f"Rajoute Orbital Matter dans mes startups spatial {suffixe}."),
    ]


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ✓ {label}")
    else:
        print(f"  ✗ {label} — {detail}")
        ECHECS.append(f"{label} — {detail}" if detail else label)


def _fichiers_md(root: Path) -> set[str]:
    return {
        str(p.relative_to(root))
        for p in root.rglob("*.md")
        if ".git" not in p.parts
    }


def _lignes(path: Path) -> int | None:
    """Nombre de lignes, ou `None` si le fichier n'existe pas.

    `None` n'est pas `0` : c'est ce qui distingue « le cas n'a rien écrit » de « le cas a écrit un
    fichier vide », et ça évite qu'un cas non exécuté passe pour un ajout réussi.
    """
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").count("\n")


def _relevé_documents(root: Path) -> dict[str, int]:
    """Nombre de lignes de chaque `documents/*.md`, par nom de fichier.

    C'est la primitive de mesure du script : deux relevés encadrant un tour donnent la cible
    réellement écrite, sans que le script ait à deviner sous quel nom le modèle a rangé la chose.
    """
    d = root / "documents"
    if not d.is_dir():
        return {}
    return {p.name: p.read_text(encoding="utf-8").count("\n") for p in d.glob("*.md")}


def _delta(avant: dict[str, int], apres: dict[str, int]) -> tuple[list[str], list[str]]:
    """(fichiers apparus, fichiers dont le nombre de lignes a augmenté). Jamais les deux fois le
    même : un fichier neuf n'est pas un fichier « qui a grossi »."""
    apparus = sorted(set(apres) - set(avant))
    grossis = sorted(n for n in apres if n in avant and apres[n] > avant[n])
    return apparus, grossis


async def rejouer(nom: str, message: str, doc) -> tuple[list[str], str]:
    """Déroule un tour et renvoie (outils appelés, réponse finale)."""
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
    print(f"    réponse : {outcome.text[:200]}")
    return appels, outcome.text


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default=f"r{int(time.time()) % 100000}",
                        help="suffixe de session (défaut : horodaté)")
    args = parser.parse_args()
    suffixe = args.session

    doc = await agent_doc.get_active_doc()
    if not doc:
        print("ECHEC — aucun doc système actif : rien à rejouer.")
        return 1
    print(f"doc système actif : v{doc.version} ({len(doc.content)} car.)")
    print(f"suffixe de session : {suffixe}")

    root = Path(settings.JOURNAL_VAULT_PATH)
    from app.services import journal_vault
    slug_startups = journal_vault.slugify(f"startups spatial {suffixe}")
    f_startups = root / "documents" / f"{slug_startups}.md"

    # ── Ligne de base : mesurée AVANT le lot, jamais rappelée de mémoire. ────────────────────
    avant = _fichiers_md(root)
    relevés: dict[str, dict[str, int]] = {"depart": _relevé_documents(root)}
    print(f"vault avant : {len(avant)} fichier(s) .md, "
          f"dont {len(relevés['depart'])} document(s) nommé(s)")
    check("ligne de base : le document de startups de cette session n'existe pas encore",
          _lignes(f_startups) is None,
          f"{slug_startups}.md déjà présent — relancer avec un autre --session")

    resultats: dict[str, list[str]] = {}
    # Relevés encadrant chaque tour : la cible est **déduite** du delta, jamais prédite.
    for nom, message in cas_du_corpus(suffixe):
        relevés[f"avant_{nom}"] = _relevé_documents(root)
        appels, _ = await rejouer(nom, message, doc)
        relevés[f"apres_{nom}"] = _relevé_documents(root)
        resultats[nom] = appels

    apres = _fichiers_md(root)
    nouveaux = sorted(apres - avant)
    print(f"\nvault après : {len(apres)} fichier(s) .md — nouveaux : {nouveaux}")

    print("\n--- Acceptation (roadmap capacité 2) ---")
    check("C1 a appelé capture_note", "capture_note" in resultats["C1"], str(resultats["C1"]))
    check("C1 : un .md neuf sous notes/",
          any(f.startswith("notes/") for f in nouveaux), str(nouveaux))
    check("C2 a appelé capture_note", "capture_note" in resultats["C2"], str(resultats["C2"]))
    check("C8 a appelé capture_note", "capture_note" in resultats["C8"], str(resultats["C8"]))

    # C2 — un document de sources, existant ou neuf, a bien reçu le lien. Un seul.
    apparus, grossis = _delta(relevés["avant_C2"], relevés["apres_C2"])
    cible_sources = (apparus + grossis)[0] if (apparus + grossis) else None
    check("C2 : exactement un document touché sous documents/",
          len(apparus) + len(grossis) == 1, f"apparus={apparus} grossis={grossis}")
    if cible_sources:
        texte = (root / "documents" / cible_sources).read_text(encoding="utf-8")
        check(f"C2 : payloadspace.com est dans {cible_sources}",
              "payloadspace.com" in texte, "le lien demandé n'a pas été écrit")

    # C8 — le document neuf est créé sous le nom demandé, avec les deux noms.
    check("C8 : le document de startups est créé sous documents/",
          _lignes(f_startups) is not None, f"{f_startups.name} absent")
    if f_startups.exists():
        t8 = f_startups.read_text(encoding="utf-8")
        check("C8 : les deux noms sont dans le document",
              "Isembard" in t8 and "Tachyon" in t8, "un des deux noms manque")

    # C2bis — l'ajout est un ajout : même fichier, plus de lignes, rien de perdu.
    apparus, grossis = _delta(relevés["avant_C2bis"], relevés["apres_C2bis"])
    check("C2bis : aucun document neuf, un document complété",
          not apparus and len(grossis) == 1, f"apparus={apparus} grossis={grossis}")
    if grossis:
        nom_f = grossis[0]
        check("C2bis : c'est le même document qu'en C2",
              cible_sources is None or nom_f == cible_sources,
              f"C2 → {cible_sources}, C2bis → {nom_f}")
        t = (root / "documents" / nom_f).read_text(encoding="utf-8")
        check("C2bis : spacenews.com est bien dans le document",
              "spacenews.com" in t, "l'élément demandé n'a pas été écrit")
        check("C2bis : payloadspace.com y est toujours (rien n'a été réécrit)",
              "payloadspace.com" in t, "le contenu antérieur a disparu")

    # C8bis — le défaut du doublon. C'est *la* raison d'être de `list_documents`.
    apparus, grossis = _delta(relevés["avant_C8bis"], relevés["apres_C8bis"])
    check("C8bis : aucun document supplémentaire créé (pas de doublon de nom)",
          not apparus, f"documents apparus : {apparus}")
    check("C8bis : le document existant a été complété", len(grossis) == 1, str(grossis))
    if f_startups.exists():
        t8 = f_startups.read_text(encoding="utf-8")
        check("C8bis : Orbital Matter a atterri dans le document de C8",
              "Orbital Matter" in t8, "écrit ailleurs, ou pas écrit")
        check("C8bis : les noms de C8 sont toujours là (rien n'a été réécrit)",
              "Isembard" in t8, "le contenu antérieur a disparu")

    print(f"\nMénage : rm {root}/documents/*{suffixe}*.md")
    print("\n" + "=" * 60)
    if ECHECS:
        print(f"ECHEC — {len(ECHECS)} assertion(s) :")
        for e in ECHECS:
            print(f"  ✗ {e}")
        return 1
    print("OK — capacité 2 acceptée (écriture réelle, ajout sans réécriture, pas de doublon).")
    return 0


sys.exit(asyncio.run(main()))
