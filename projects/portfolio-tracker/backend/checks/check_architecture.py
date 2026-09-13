"""Vérifie que l'ORGANISATION des fichiers et les docs d'ARCHITECTURE ne dérivent pas — la même
garantie que le reste de la suite, appliquée à la structure du projet elle-même.

CE QU'IL TIENT (chaque invariant nommé, jamais un décompte) :
  1. **Bijection registre ↔ docs** : chaque `app/<module>/ARCHITECTURE.md` déclaré dans
     `ARCHITECTURE-CIBLE.md` existe, et réciproquement — on n'ajoute pas un module sans le déclarer,
     ni ne déclare un module fantôme. Le registre (la CIBLE) est le DÉTENTEUR UNIQUE (#46) de la
     liste ; ce check ne code aucune liste en dur, donc rien à rigidifier quand un module s'ajoute.
  2. **Intégrité des pointeurs** : tout `check_*.py` cité par un doc EXISTE (pas de pointeur mort).
  3. **Garde orpheline** : tout `check_*.py` de `checks/` est cité par au moins un doc — une garantie
     (« réalisé ») sans contrat documenté (« cible ») est invisible.
  4. **Discipline de dossier** : `roadmap/` ne contient que `V3/` et `archive/` — aucune spec ne
     retombe à la racine.
  5. **Non-régression de l'autonomie de /V3** : aucun doc de `V3/` ne référence un ANCIEN chemin de
     spec (hors `00-REPRISE-ARCHIVE.md`, journal historique volontairement figé).

POURQUOI PUR FILESYSTEM/AST : il tourne sans docker-DB ni réseau (`net=none` dans `run_all.sh`).
Prouvé rouge par `negatif_architecture.sh` (une mutation par invariant, chacune sur son assert nommé).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan  # noqa: E402

# Chemins résolus depuis __file__ → tourne À L'IDENTIQUE en conteneur (run_all.sh : /app + /roadmap
# montés) et sur l'HÔTE (hook pré-commit, sans docker). Aucune liste en dur, aucune dépendance app.
_HERE = Path(__file__).resolve()
BACKEND = _HERE.parent.parent          # conteneur : /app · hôte : <repo>/…/backend
APP = BACKEND / "app"
CHECKS = BACKEND / "checks"
# roadmap : monté en /roadmap dans le conteneur, sinon frère du backend (<…>/roadmap).
ROADMAP = next(
    (c for c in (Path("/roadmap"), BACKEND.parent / "roadmap") if (c / "V3").is_dir()),
    BACKEND.parent / "roadmap",
)
V3 = ROADMAP / "V3"
CIBLE = V3 / "ARCHITECTURE-CIBLE.md"

# Anciens chemins qui ne doivent PLUS apparaître dans les docs de /V3 (réorg 2026-09-13).
STALE = (
    "roadmap/provenance-cards",
    "roadmap/00-principe-directeur",
    "roadmap/01-spec-v2-unifiee",
    "roadmap/02-spec-autorite",
    "roadmap/03-spec-frameworks",
    "roadmap/benchmark-methodologies-decision",
)


def main() -> int:
    b = Bilan()

    if not b.check(CIBLE.exists(), f"ARCHITECTURE-CIBLE.md présent ({CIBLE})"):
        # Un prérequis manquant ne doit jamais passer pour un 0 (feedback_check_degrade_en_sortant_a_zero).
        return b.summary() or 1

    cible_txt = CIBLE.read_text(encoding="utf-8")

    # ── 1. Bijection registre ↔ docs ──────────────────────────────────────────────────────────
    declared = set(re.findall(r"app/[a-z0-9_/]+?/ARCHITECTURE\.md", cible_txt))
    actual = {str(p.relative_to(BACKEND)) for p in APP.rglob("ARCHITECTURE.md")}
    b.require(declared, len(actual), "registre CIBLE ↔ docs sur disque (même compte)")
    for d in sorted(declared - actual):
        b.check(False, f"doc déclaré dans la CIBLE mais absent du disque : {d}")
    for a in sorted(actual - declared):
        b.check(False, f"doc sur disque mais non déclaré dans la CIBLE : {a}")
    b.check(declared == actual, "bijection registre ↔ docs exacte")

    # ── 2 & 3. Pointeurs vers les checks : intégrité + orphelins ───────────────────────────────
    doc_files = [CIBLE] + sorted(APP.rglob("ARCHITECTURE.md"))
    cited: set[str] = set()
    for doc in doc_files:
        cited |= set(re.findall(r"check_[a-z0-9_]+\.py", doc.read_text(encoding="utf-8")))
    existing = {p.name for p in CHECKS.glob("check_*.py")}

    for miss in sorted(cited - existing):
        b.check(False, f"pointeur mort : `{miss}` cité par un doc n'existe pas dans checks/")
    b.check(cited <= existing, "tout check cité existe (pas de pointeur mort)")

    for orphan in sorted(existing - cited):
        b.check(False, f"garde orpheline : `{orphan}` n'est cité par aucun ARCHITECTURE.md")
    b.check(existing <= cited, "tout check est adossé à une cible (aucun orphelin)")

    # ── 4. Discipline de dossier roadmap/ ─────────────────────────────────────────────────────
    autorises = {"V3", "archive"}
    intrus = sorted(p.name for p in ROADMAP.iterdir() if p.name not in autorises)
    for x in intrus:
        b.check(False, f"racine roadmap/ : `{x}` hors de V3/ et archive/")
    b.check(not intrus, "roadmap/ ne contient que V3/ et archive/")

    # ── 5. Non-régression de l'autonomie de /V3 ───────────────────────────────────────────────
    for md in sorted(V3.rglob("*.md")):
        if md.name == "00-REPRISE-ARCHIVE.md":
            continue  # journal historique : ses chemins décrivent l'état d'alors, figés à dessein.
        txt = md.read_text(encoding="utf-8")
        for tok in STALE:
            b.check(tok not in txt, f"autonomie /V3 : `{md.name}` cite un ancien chemin `{tok}`")

    return b.summary()


if __name__ == "__main__":
    sys.exit(main())
