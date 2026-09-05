#!/usr/bin/env python3
"""Le Hub ne doit JAMAIS abîmer le frontmatter d'un document en le sauvegardant.

Panne d'origine (2026-09-04, `00-REPRISE.md` du hub §8) : le handler d'édition reconstruisait
le frontmatter à plat en `clé: valeur`. Sur `01-spec-v2-unifiee.md`, 15 lignes devenaient 7 en
UNE sauvegarde — les scalaires de bloc (`role: >`, `downstream: >`) perdaient tout leur contenu,
et une ligne de continuation contenant un `: ` était promue en clef parasite. Silencieux : pas
d'erreur, redirection `flash=saved`, et un diff git qui ressemble à une édition légitime.

Ce check rejoue une sauvegarde SANS MODIFICATION sur tous les documents de roadmap du repo. Il
exige :
  - le frontmatter identique **octet pour octet** — c'est là qu'était la destruction ;
  - le corps identique **après strip** — le Hub normalise volontairement CRLF→LF et la newline
    de fin (voir le commentaire dans `_render_saved_document`). Mesuré au moment d'écrire ce
    check : 4 documents sur 46 dévient de cette forme canonique par leur seul espacement, aucun
    par son contenu. Tolérer l'espacement, et rien d'autre, est ce qui rend le check tenable
    sans le rendre aveugle : toute perte ou promotion de contenu le fait virer au rouge.

C'est le trajet exact des micro-éditions faites dans le Hub avant d'inscrire une roadmap.

Usage : python3 projects/hub/checks/check_frontmatter_preserved.py
Sortie : 0 si tous les documents sont préservés, 1 sinon (ou si le pré-requis manque).
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "projects" / "hub"))

try:
    import yaml

    from app.roadmap import _render_saved_document
except ImportError as exc:  # pré-requis manquant → rouge, jamais un skip
    print(f"ÉCHEC : dépendance absente ({exc}).")
    print("Ce check doit tourner avec les dépendances du Hub installées (fastapi, pyyaml).")
    sys.exit(1)


def main() -> int:
    docs = sorted(REPO.glob("projects/*/roadmap/**/*.md")) + sorted(REPO.glob("projects/*/*.md"))
    checked = damaged = 0

    for path in docs:
        raw = path.read_text()
        if not raw.startswith("---\n"):
            continue  # sans frontmatter, il n'y a rien à préserver
        checked += 1

        # Sauvegarde à vide : on renvoie le corps et le statut que le formulaire aurait affichés.
        body = raw.split("\n---\n", 1)[1] if "\n---\n" in raw else ""
        status = ""
        for line in raw.split("\n---\n", 1)[0].split("\n"):
            if line.startswith("status:"):
                status = line.partition(":")[2].strip()
                break

        # Contrôle indépendant : le frontmatter doit être du YAML valide AVANT toute
        # sauvegarde. Deux 00-REPRISE.md ne l'étaient pas (`role:` en scalaire simple dont la
        # valeur contenait « État : »), et préserver octet pour octet préserve aussi ce défaut.
        try:
            yaml.safe_load(_frontmatter(raw))
        except yaml.YAMLError as exc:
            damaged += 1
            print(f"YAML INVALIDE  {path.relative_to(REPO)}")
            print(f"        {str(exc).splitlines()[0]}")
            continue

        after = _render_saved_document(raw, body=body, status=status)

        fm_before, fm_after = _frontmatter(raw), _frontmatter(after)
        body_before, body_after = _body(raw).strip(), _body(after).strip()

        if fm_before != fm_after or body_before != body_after:
            damaged += 1
            rel = path.relative_to(REPO)
            print(f"ABÎMÉ  {rel}")
            if fm_before != fm_after:
                n_before, n_after = fm_before.count("\n") + 1, fm_after.count("\n") + 1
                print(f"        frontmatter : {n_before} lignes avant → {n_after} après")
                for key in sorted(_keys(raw) - _keys(after)):
                    print(f"        clef PERDUE   : {key}")
                for key in sorted(_keys(after) - _keys(raw)):
                    print(f"        clef PARASITE : {key}")
            if body_before != body_after:
                print(f"        CORPS modifié : {len(body_before)} → {len(body_after)} caractères")

    print(f"\n{checked} document(s) avec frontmatter vérifié(s), {damaged} abîmé(s).")
    if damaged:
        print("ÉCHEC : une sauvegarde depuis le Hub n'a pas préservé le document.")
        return 1
    print("OK : frontmatter préservé octet pour octet, corps inchangé.")
    return 0


def _frontmatter(raw: str) -> str:
    """Le frontmatter BRUT, sans les délimiteurs `---`."""
    m = re.match(r"^---\n([\s\S]*?)\n---\n?", raw)
    return m.group(1) if m else ""


def _body(raw: str) -> str:
    m = re.match(r"^---\n([\s\S]*?)\n---\n?", raw)
    return raw[m.end():] if m else raw


def _keys(raw: str) -> set[str]:
    """Clefs de premier niveau du frontmatter (non indentées)."""
    return {
        line.partition(":")[0]
        for line in _frontmatter(raw).split("\n")
        if ":" in line and not line.startswith((" ", "\t", "-", "#"))
    }


if __name__ == "__main__":
    sys.exit(main())
