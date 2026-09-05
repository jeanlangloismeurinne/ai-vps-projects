"""Déplacement unique `listes/` → `documents/` dans le vault (capacité 2, généralisation).

    python3 checks/migrate_listes_to_documents.py [--apply]

Pourquoi un script et pas un `git mv` à la main : l'entête de chaque fichier porte un `doc_id`
qui embarque le répertoire (`assistant-ia:vps_files:listes/{slug}`) et un `type: list`. Déplacer
le fichier sans réécrire ces deux champs laisserait un document dont le chemin et la clef ne
concordent plus — le prochain `append_to_document` calculerait un `doc_id` différent de celui
inscrit dans le fichier, et personne ne le verrait.

**Ce script réécrit des fichiers du vault.** C'est la seule chose du projet qui en a le droit, et
c'est pour ça qu'elle est ici, en un passage unique, hors du chemin d'écriture de l'agent —
jamais dans `journal_vault.append_to_document`, dont l'invariant est de ne jamais réécrire.

Idempotent : sans `listes/`, il ne fait rien. Sans `--apply`, il n'écrit rien et affiche ce qu'il
ferait.
"""
from __future__ import annotations

import sys
from pathlib import Path

VAULT = Path("/storage/journal-vault")
SRC, DST = VAULT / "listes", VAULT / "documents"

APPLY = "--apply" in sys.argv


def main() -> int:
    if not SRC.is_dir():
        print("rien à faire : aucun répertoire `listes/`")
        return 0

    fichiers = sorted(SRC.glob("*.md"))
    if not fichiers:
        print("rien à faire : `listes/` est vide")
        return 0

    print(f"{len(fichiers)} fichier(s) à déplacer vers documents/ (apply={APPLY})\n")
    for src in fichiers:
        cible = DST / src.name
        if cible.exists():
            print(f"  ! {src.name} — une cible existe déjà, ignoré (à traiter à la main)")
            continue
        texte = src.read_text(encoding="utf-8")
        neuf = (texte
                .replace("doc_id: assistant-ia:vps_files:listes/",
                         "doc_id: assistant-ia:vps_files:documents/")
                .replace("\ntype: list\n", "\ntype: document\n"))
        change = "oui" if neuf != texte else "non (entête déjà conforme)"
        print(f"  → {src.name} — entête réécrite : {change}")
        if APPLY:
            DST.mkdir(parents=True, exist_ok=True)
            cible.write_text(neuf, encoding="utf-8")
            src.unlink()

    if APPLY:
        restant = list(SRC.glob("*")) if SRC.is_dir() else []
        if not restant:
            SRC.rmdir()
            print("\n`listes/` supprimé (vide).")
        else:
            print(f"\n`listes/` conservé : {len(restant)} fichier(s) restant(s).")
        print("Pense à committer le vault : git -C /storage/journal-vault add -A && commit")
    else:
        print("\n(essai à blanc — relancer avec --apply)")
    return 0


sys.exit(main())
