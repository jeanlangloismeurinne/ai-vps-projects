"""Rejeu du corpus de non-régression — capacité 2 (`capture_note`).

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

Cas rejoués (verbatim de la roadmap `agent-intention-et-capture-kb.md`) :
  C1 — note de lecture   → attendu : un `.md` neuf sous `notes/`
  C2 — « stocke ce lien dans une liste de sources utiles » → attendu : `listes/sources-utiles.md`
  C8 — « crée une liste de startups… » avec 2 noms → attendu : une 2e liste, 2 éléments
  C2bis — second ajout sur la même liste → attendu : `+1` ligne, `-0` (l'invariant de D5)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings                                       # noqa: E402
from app.services import agent_doc                                    # noqa: E402
from app.services.agent_tools import loop                             # noqa: E402
from app.services.agent_tools.manifest import TurnState               # noqa: E402

# Channel dédié au rejeu : les lignes d'`agent_tool_calls` produites ici restent distinguables
# d'un usage réel, sans qu'il faille les effacer après coup.
REPLAY_CHANNEL = "C_REPLAY_CAP2"

CAS: list[tuple[str, str]] = [
    ("C1", "Note de lecture Safran : le EU Space Act impose un régime d'autorisation unique "
           "aux opérateurs de constellations, ce qui change la donne pour les équipementiers "
           "européens — à recouper avec la position d'Airbus."),
    ("C2", "Stocke ce lien dans une liste de sources utiles : payloadspace.com"),
    ("C8", "Crée une liste de startups du secteur du spatial dont les innovations sont à creuser. "
           "Voilà de premiers noms : Isembard, Tachyon Industrie"),
    ("C2bis", "Ajoute aussi spacenews.com à ma liste de sources utiles."),
]

ECHECS: list[str] = []


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
            slack_ts=f"replay-{nom}",
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
    doc = await agent_doc.get_active_doc()
    if not doc:
        print("ECHEC — aucun doc système actif : rien à rejouer.")
        return 1
    print(f"doc système actif : v{doc.version} ({len(doc.content)} car.)")

    root = Path(settings.JOURNAL_VAULT_PATH)
    avant = _fichiers_md(root)
    print(f"vault avant : {len(avant)} fichier(s) .md")

    resultats: dict[str, list[str]] = {}
    # `None` = le snapshot n'a jamais été pris. C'est distinct de « fichier vide » et c'est ce qui
    # évite qu'un cas non exécuté passe pour un ajout réussi.
    avant_bis: str | None = None
    for nom, message in CAS:
        # Snapshot de la liste juste avant C2bis : l'invariant « +1 / -0 » se mesure sur le
        # fichier, pas sur la réponse du modèle.
        if nom == "C2bis":
            cible = root / "listes" / "sources-utiles.md"
            avant_bis = cible.read_text(encoding="utf-8") if cible.exists() else None
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
    listes = sorted(f for f in nouveaux if f.startswith("listes/"))
    check("C2 + C8 : deux fichiers sous listes/", len(listes) >= 2, str(listes))

    cible = root / "listes" / "sources-utiles.md"
    if avant_bis is None:
        check("C2bis : la liste sources-utiles existait avant le second ajout", False,
              "fichier absent — C2 n'a rien écrit, l'invariant d'ajout n'est pas mesurable")
    else:
        apres_bis = cible.read_text(encoding="utf-8")
        check("C2bis : l'ajout n'a rien réécrit (préfixe conservé)",
              apres_bis.startswith(avant_bis), "le contenu antérieur a bougé")
        check("C2bis : exactement +1 ligne, -0",
              apres_bis.count("\n") == avant_bis.count("\n") + 1,
              f"{avant_bis.count(chr(10))} → {apres_bis.count(chr(10))} lignes")

    print("\n" + "=" * 60)
    if ECHECS:
        print(f"ECHEC — {len(ECHECS)} assertion(s) :")
        for e in ECHECS:
            print(f"  ✗ {e}")
        return 1
    print("OK — capacité 2 acceptée (capture_note écrit dans le vault, l'ajout est un ajout).")
    return 0


sys.exit(asyncio.run(main()))
