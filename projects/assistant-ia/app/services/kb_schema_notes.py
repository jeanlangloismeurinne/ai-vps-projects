"""
Notes-schéma du vault (#1787600247612, sprint « Substrat »).

Écrit dans le vault les notes qui rendent la KB *explorable* dans Obsidian :
- une page d'accueil (MOC) ;
- une note taxonomie **générée depuis** `app/knowledge/categories.schema.yaml` (source de vérité) ;
- deux vues base de données (**Obsidian Bases**, plugin cœur) : Tâches (kanban filtrable) et Journal.

Ces fichiers sont maintenus par l'agent (écrits côté host), idempotents (réécrits seulement si le
contenu change), atomiques, confinés au vault, versionnés en best-effort. Ils vivent à la racine du
vault (hors `tasks/` et hors dossiers d'années journal).

Bases vs Dataview — décision roadmap : **Bases** (plugin cœur, fichiers `.base` YAML, pas d'install
tierce). Le format des `.base` reste **provisoire** tant que le conteneur Obsidian (#1787600247613,
sprint Viewer) n'a pas confirmé la version embarquée : dépendance croisée #612 ↔ #613. Repli
documenté = Dataview (mêmes vues en blocs ```dataview``` dans des notes `.md`).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

from app.services.journal_vault import (
    VaultError,
    _git,
    _resolve_within_vault,
    ensure_vault,
)

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent.parent / "knowledge" / "categories.schema.yaml"

# Fichiers gérés par ce module (racine du vault). Les noms accentués sont volontaires : ce sont des
# titres de notes lus par l'utilisateur, pas des chemins dérivés d'entrée brute.
_ACCUEIL = "Accueil.md"
_TAXONOMIE = "Taxonomie.md"
_TACHES_BASE = "Tâches.base"
_JOURNAL_BASE = "Journal.base"


def _accueil_md() -> str:
    return """# Accueil — base de connaissance

> Ce coffre est **écrit par l'agent** (assistant-ia), en **lecture seule**. Ne l'éditez pas à la
> main : les notes sont des projections de Postgres (journal `journal_kb_entries`, tâches kanban
> `cards`) et une modification manuelle serait écrasée à la prochaine synchronisation.
> Voir aussi `README.md` (accès en ligne <https://kb.jlmvpscode.duckdns.org> ou clone local).

## Cartes de vue

- **[[Tâches]]** — le kanban comme base de données explorable (filtrable par colonne, échéance, tags).
- **[[Journal]]** — les entrées du journal, filtrables par contexte / nature / tags.
- **[[Taxonomie]]** — le vocabulaire de classification (axes et tags).

## Comment c'est alimenté

| Surface | Source (vérité) | Emplacement dans le vault |
|---|---|---|
| Journal | `#journal` Slack → classifieur | `AAAA/AAAA-MM-JJ-*.md` |
| Tâches | Kanban (`cards`) | `tasks/<board>/<carte>.md` |

Les vues `.base` ci-dessus utilisent le plugin cœur **Bases**. Si votre version d'Obsidian ne les
rend pas, un repli **Dataview** (mêmes vues en blocs `dataview`) peut être généré à la place.
"""


def _taxonomie_md() -> str:
    """Rendu Markdown du schéma de classification, généré DEPUIS le YAML (source de vérité).
    Change le YAML → régénère → cette note reflète le schéma courant."""
    with open(_SCHEMA_PATH, encoding="utf-8") as fh:
        schema = yaml.safe_load(fh) or {}

    lines = [
        "# Taxonomie de la base de connaissance",
        "",
        "> Note **générée** depuis `app/knowledge/categories.schema.yaml` (source de vérité du",
        "> classifieur journal). Ne pas éditer à la main.",
        "",
    ]

    axes = (schema.get("axes") or {})
    for axis_name, axis in axes.items():
        desc = (axis or {}).get("description", "")
        card = (axis or {}).get("cardinality", "")
        lines.append(f"## Axe `{axis_name}`")
        if desc:
            lines.append(f"\n{desc}")
        if card:
            lines.append(f"\n*Cardinalité : `{card}`*")
        values = (axis or {}).get("values") or []
        if values:
            lines.append("")
            lines.extend(f"- `{v}`" for v in values)
        lines.append("")

    libres = schema.get("tags_libres") or {}
    if libres:
        lines.append("## Tags libres")
        if libres.get("description"):
            lines.append(f"\n{libres['description']}")
        if libres.get("cardinality"):
            lines.append(f"\n*Cardinalité : `{libres['cardinality']}`*")
        examples = libres.get("examples") or []
        if examples:
            lines.append("\nExemples :")
            lines.extend(f"- `{v}`" for v in examples)
        lines.append("")

    return "\n".join(lines)


def _taches_base() -> str:
    """Vue Bases des tâches : le kanban explorable. Groupé par colonne (rendu type kanban),
    masque les tâches terminées, trié par échéance."""
    spec = {
        "filters": {"and": ['type == "task"']},
        "properties": {
            "note.board": {"displayName": "Board"},
            "note.column": {"displayName": "Colonne"},
            "note.due": {"displayName": "Échéance"},
            "note.status": {"displayName": "Statut"},
            "note.tags": {"displayName": "Tags"},
        },
        "views": [
            {
                "type": "table",
                "name": "À faire",
                "filters": {"and": ['status != "done"']},
                "order": ["file.name", "note.board", "note.column", "note.due", "note.tags"],
                "sort": [{"property": "note.due", "direction": "ASC"}],
                "groupBy": "note.column",
            },
            {
                "type": "table",
                "name": "Toutes les tâches",
                "order": ["file.name", "note.board", "note.column", "note.status", "note.due"],
                "sort": [{"property": "note.updated_at", "direction": "DESC"}],
            },
        ],
    }
    return yaml.safe_dump(spec, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _journal_base() -> str:
    """Vue Bases du journal : notes de journal (celles qui portent `contexte`), filtrables par
    contexte / nature / tags, triées du plus récent au plus ancien."""
    spec = {
        # Les notes journal portent `contexte` ; les tâches non → discrimine sans dépendre du chemin.
        "filters": {"and": ['file.hasProperty("contexte")']},
        "properties": {
            "note.contexte": {"displayName": "Contexte"},
            "note.nature": {"displayName": "Nature"},
            "note.tags": {"displayName": "Tags"},
            "note.created_at": {"displayName": "Créé le"},
        },
        "views": [
            {
                "type": "table",
                "name": "Journal",
                "order": ["file.name", "note.contexte", "note.nature", "note.tags", "note.created_at"],
                "sort": [{"property": "note.created_at", "direction": "DESC"}],
            },
        ],
    }
    return yaml.safe_dump(spec, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _atomic_write(target: Path, content: str) -> None:
    tmp = target.with_name(f".{target.name}.tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, target)
    except OSError as exc:
        if tmp.exists():
            tmp.unlink()
        raise VaultError(f"écriture impossible dans le vault : {exc}") from exc


async def _commit(root: Path, names: list[str]) -> None:
    code, out = await _git(root, "add", "--", *names)
    if code != 0:
        logger.warning(f"kb_schema_notes: git add a échoué ({out})")
        return
    code, out = await _git(
        root, "-c", "user.name=assistant-ia", "-c", "user.email=assistant@jlmvpscode.duckdns.org",
        "commit", "-q", "--author", "assistant-ia <assistant@jlmvpscode.duckdns.org>",
        "-m", "sync notes-schéma",
    )
    if code != 0 and "nothing to commit" not in out.lower():
        logger.warning(f"kb_schema_notes: git commit a échoué ({out})")


async def sync_schema_notes() -> dict:
    """(Ré)écrit les notes-schéma à la racine du vault. Idempotent : ne réécrit et ne committe que
    les fichiers dont le contenu a changé."""
    root = await ensure_vault()
    files = {
        _ACCUEIL: _accueil_md(),
        _TAXONOMIE: _taxonomie_md(),
        _TACHES_BASE: _taches_base(),
        _JOURNAL_BASE: _journal_base(),
    }
    changed: list[str] = []
    for name, content in files.items():
        target = _resolve_within_vault(root, name)
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            _atomic_write(target, content)
            changed.append(name)

    if changed:
        await _commit(root, changed)
    logger.info(f"kb_schema_notes: sync terminé ({len(changed)} fichiers mis à jour)")
    return {"updated": changed}
