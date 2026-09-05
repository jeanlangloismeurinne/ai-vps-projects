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

## Rejouabilité — le défaut corrigé le 2026-09-05

La première version comparait `apres - avant` sur l'ensemble du vault et concluait « C2 n'a rien
écrit » au second passage : les fichiers existaient déjà, la différence était vide, et deux
assertions viraient au rouge sans qu'aucune régression n'ait eu lieu. Un script qui ne peut pas
tourner deux fois n'est pas une mesure, c'est une impression.

La correction : chaque exécution travaille sous un **suffixe de session** propre (`--session`,
horodaté par défaut). Les noms de documents deviennent « sources utiles r1730… » — donc des
fichiers neufs à chaque passage, et une ligne de base connue. Les cas mesurent alors un *delta*
qu'ils ont eux-mêmes provoqué, pas un état accumulé.

Ce que ça coûte : le vault se remplit d'un jeu de documents de rejeu. Ils sont reconnaissables au
suffixe et se suppriment en une commande (affichée en fin de run).

Cas rejoués (verbatim de la roadmap `agent-intention-et-capture-kb.md`, + suffixe de session) :
  C1 — note de lecture   → attendu : un `.md` neuf sous `notes/`
  C2 — « stocke ce lien dans une liste de sources utiles » → attendu : `documents/sources-utiles…`
  C8 — « crée une liste de startups… » avec 2 noms → attendu : un 2e document, 2 noms dedans
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
    """Le corpus, paramétré par le suffixe de session.

    Le suffixe est glissé **dans le nom que l'utilisateur donne**, pas dans une variable de code :
    c'est le modèle qui doit le reporter dans son appel d'outil, donc on teste aussi qu'il
    reprend le nom tel qu'il l'a reçu — le comportement même dont dépend l'adressage par nom.
    """
    return [
        ("C1", "Note de lecture Safran : le EU Space Act impose un régime d'autorisation unique "
               "aux opérateurs de constellations, ce qui change la donne pour les équipementiers "
               f"européens — à recouper avec la position d'Airbus. (rejeu {suffixe})"),
        ("C2", f"Stocke ce lien dans une liste de sources utiles {suffixe} : payloadspace.com"),
        ("C8", "Crée une liste de startups du secteur du spatial dont les innovations sont à "
               f"creuser, appelée startups spatial {suffixe}. Voilà de premiers noms : Isembard, "
               "Tachyon Industrie"),
        ("C2bis", f"Ajoute aussi spacenews.com à ma liste de sources utiles {suffixe}."),
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
    slug_sources = journal_vault.slugify(f"sources utiles {suffixe}")
    slug_startups = journal_vault.slugify(f"startups spatial {suffixe}")
    f_sources = root / "documents" / f"{slug_sources}.md"
    f_startups = root / "documents" / f"{slug_startups}.md"

    # ── Ligne de base : mesurée AVANT le lot, jamais rappelée de mémoire. ────────────────────
    avant = _fichiers_md(root)
    docs_avant = {f for f in avant if f.startswith("documents/")}
    print(f"vault avant : {len(avant)} fichier(s) .md, dont {len(docs_avant)} document(s)")
    check("ligne de base : les fichiers de cette session n'existent pas encore",
          _lignes(f_sources) is None and _lignes(f_startups) is None,
          f"{slug_sources} / {slug_startups} déjà présents — relancer avec un autre --session")

    resultats: dict[str, list[str]] = {}
    jalons: dict[str, int | None] = {}
    for nom, message in cas_du_corpus(suffixe):
        # Jalons pris juste avant les cas d'ajout : l'invariant « +n / -0 » se mesure sur le
        # fichier, pas sur la réponse du modèle.
        if nom == "C2bis":
            jalons["sources"] = _lignes(f_sources)
        if nom == "C8bis":
            jalons["startups"] = _lignes(f_startups)
            jalons["docs"] = len({f for f in _fichiers_md(root) if f.startswith("documents/")})
        appels, _ = await rejouer(nom, message, doc)
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
    check("C2 : le document de sources est créé sous documents/",
          _lignes(f_sources) is not None, f"{f_sources.name} absent")
    check("C8 : le document de startups est créé sous documents/",
          _lignes(f_startups) is not None, f"{f_startups.name} absent")

    # C2bis — l'ajout est un ajout.
    if jalons.get("sources") is None:
        check("C2bis : le document existait avant le second ajout", False,
              "fichier absent — C2 n'a rien écrit, l'invariant d'ajout n'est pas mesurable")
    else:
        apres_bis = _lignes(f_sources)
        check("C2bis : le document a grossi, sans rien perdre",
              apres_bis is not None and apres_bis > jalons["sources"],
              f"{jalons['sources']} → {apres_bis} lignes")
        check("C2bis : spacenews.com est bien dans le document",
              "spacenews.com" in f_sources.read_text(encoding="utf-8"),
              "l'élément demandé n'a pas été écrit")

    # C8bis — le défaut du doublon. C'est *la* raison d'être de `list_documents`.
    if jalons.get("startups") is None:
        check("C8bis : le document de startups existait avant la relance", False,
              "fichier absent — C8 n'a rien écrit")
    else:
        docs_apres = len({f for f in apres if f.startswith("documents/")})
        check("C8bis : aucun document supplémentaire créé (pas de doublon de nom)",
              docs_apres == jalons["docs"],
              f"{jalons['docs']} → {docs_apres} documents ; "
              f"nouveaux : {sorted(f for f in nouveaux if f.startswith('documents/'))}")
        check("C8bis : Orbital Matter a bien atterri dans le document existant",
              "Orbital Matter" in f_startups.read_text(encoding="utf-8"),
              "écrit ailleurs, ou pas écrit")
        check("C8bis : les noms de C8 sont toujours là (rien n'a été réécrit)",
              "Isembard" in f_startups.read_text(encoding="utf-8"),
              "le contenu antérieur a disparu")

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
