#!/usr/bin/env python3
"""L'inscription d'une roadmap depuis le Hub ne doit toucher QUE la ligne « Roadmap active ».

Le pointeur « roadmap active » du `00-REPRISE.md` est, par décision (`CONTROL_SYSTEM.md` §2), le
SEUL endroit où vit l'information « sur quoi on avance ». Le Hub est le seul outil qui l'écrit
sans relecture humaine : s'il déplace, duplique ou abîme quoi que ce soit d'autre dans un fichier
de reprise, la mémoire du système part avec — et le mode de panne serait silencieux, comme l'était
la destruction de frontmatter du §8.

Le check rejoue une inscription sur les fichiers de reprise RÉELS du repo (jamais une fixture
fabriquée : une fixture plus régulière que la prod est un check aveugle) et exige :
  - le frontmatter identique octet pour octet ;
  - **exactement une** ligne pointeur après inscription — qu'il y en ait eu zéro (insertion) ou
    une (substitution) avant ;
  - toutes les autres lignes non vides du corps identiques, dans le même ordre. L'espacement
    seul est toléré, comme dans `check_frontmatter_preserved.py` : ce qui doit virer au rouge,
    c'est une perte, un doublon ou un déplacement de contenu, pas une ligne blanche ;
  - l'idempotence : inscrire deux fois == inscrire une fois.

⚠️ Les deux dernières assertions ne sont pas redondantes. Mesuré en écrivant ce check, sur une
implémentation « append » volontairement fautive : le comptage de pointeurs l'attrape sur le
`00-REPRISE.md` du hub (qui en portait déjà un → 2 après), mais **pas** sur ceux de
comms-gateway et portfolio-tracker, qui n'en avaient aucun. Sur ces deux-là, c'est l'idempotence
seule qui vire au rouge. Retirer l'une des deux rendrait le check aveugle sur 2 fichiers sur 3.

Il vérifie aussi la résolution de chemin racine → `roadmap/**` (§2), qui n'est pas cosmétique :
portfolio-tracker a le sien dans `roadmap/provenance-cards/`, et un Hub qui ne le trouve pas
créerait un second fichier de reprise concurrent.

Usage : python3 projects/hub/checks/check_reprise_inscription.py
Sortie : 0 si tout est conforme, 1 sinon (ou si le pré-requis manque).
"""
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
# Le module lit PROJECTS_DIR à l'import (c'est `/projects` dans le conteneur) : hors conteneur,
# le pointer sur le repo est ce qui permet au check de tourner sur les fichiers réels.
os.environ.setdefault("PROJECTS_DIR", str(REPO / "projects"))
sys.path.insert(0, str(REPO / "projects" / "hub"))

try:
    from app.roadmap import POINTER_RE, _inscribe_roadmap, _reprise_path
except ImportError as exc:  # pré-requis manquant → rouge, jamais un skip
    print(f"ÉCHEC : dépendance absente ({exc}).")
    print("Ce check doit tourner avec les dépendances du Hub installées (fastapi, pyyaml).")
    sys.exit(1)

# Résolution attendue : racine d'abord, `roadmap/**` en second, None quand il n'y en a pas.
# Ces quatre projets sont l'état réel du repo — portfolio-tracker est le cas hors racine.
EXPECTED_PATHS = {
    "hub": "projects/hub/00-REPRISE.md",
    "comms-gateway": "projects/comms-gateway/00-REPRISE.md",
    "newsletter-summary": "projects/newsletter-summary/00-REPRISE.md",
    "portfolio-tracker": "projects/portfolio-tracker/roadmap/provenance-cards/00-REPRISE.md",
    "bank-review": None,
}


def main() -> int:
    failures = 0

    # ── 1. Résolution du chemin ────────────────────────────────────────────────
    for project, expected in EXPECTED_PATHS.items():
        got = _reprise_path(project)
        got_rel = str(got.relative_to(REPO)) if got else None
        if got_rel != expected:
            failures += 1
            print(f"RÉSOLUTION  {project}")
            print(f"        attendu : {expected}")
            print(f"        obtenu  : {got_rel}")

    # ── 2. Inscription sur les fichiers réels ──────────────────────────────────
    checked = 0
    for project, expected in EXPECTED_PATHS.items():
        if not expected:
            continue
        path = REPO / expected
        raw = path.read_text()
        checked += 1

        after = _inscribe_roadmap(raw, "roadmap/exemple-cible.md")
        rel = path.relative_to(REPO)

        pointers = [ln for ln in after.split("\n") if POINTER_RE.match(ln)]
        if len(pointers) != 1:
            failures += 1
            print(f"POINTEUR  {rel} : {len(pointers)} ligne(s) « Roadmap active », 1 attendue")
            for p in pointers:
                print(f"        {p[:100]}")
        elif "exemple-cible.md" not in pointers[0]:
            failures += 1
            print(f"POINTEUR  {rel} : la cible n'est pas dans la ligne écrite")
            print(f"        {pointers[0][:100]}")

        if _frontmatter(raw) != _frontmatter(after):
            failures += 1
            print(f"FRONTMATTER  {rel} : modifié par une inscription")

        # Toutes les autres lignes doivent être intactes et dans le même ordre : on retire
        # les lignes pointeur de part et d'autre, le reste doit coïncider exactement.
        before_rest = _content_lines(raw)
        after_rest = _content_lines(after)
        if before_rest != after_rest:
            failures += 1
            print(f"CORPS  {rel} : {len(before_rest)} lignes avant → {len(after_rest)} après "
                  f"(hors ligne pointeur)")
            for i, (b, a) in enumerate(zip(before_rest, after_rest)):
                if b != a:
                    print(f"        1re divergence l.{i + 1} : {b[:60]!r} → {a[:60]!r}")
                    break

        if _inscribe_roadmap(after, "roadmap/exemple-cible.md") != after:
            failures += 1
            print(f"IDEMPOTENCE  {rel} : inscrire deux fois ne rend pas le même fichier")

    print(f"\n{len(EXPECTED_PATHS)} résolution(s) et {checked} inscription(s) vérifiées, "
          f"{failures} anomalie(s).")
    if failures:
        print("ÉCHEC : l'inscription depuis le Hub abîme le fichier de reprise.")
        return 1
    print("OK : pointeur unique, frontmatter et corps préservés, résolution racine → roadmap/**.")
    return 0


def _frontmatter(raw: str) -> str:
    m = re.match(r"^---\n([\s\S]*?)\n---\n?", raw)
    return m.group(1) if m else ""


def _content_lines(raw: str) -> list[str]:
    """Les lignes porteuses de contenu, hors ligne pointeur : ce qui ne doit jamais bouger."""
    return [ln for ln in raw.split("\n") if ln.strip() and not POINTER_RE.match(ln)]


if __name__ == "__main__":
    sys.exit(main())
