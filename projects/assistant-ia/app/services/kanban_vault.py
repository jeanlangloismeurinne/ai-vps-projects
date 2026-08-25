"""
Miroir one-way du kanban vers le vault Obsidian (#1787600247611, sprint « Substrat »).

Sens de la synchro : **DB → MD uniquement**. Postgres (`boards`/`columns`/`cards`/`card_fields`)
reste la source de vérité ; le vault reçoit une **projection dérivée read-only**. Contrairement au
writer journal (`journal_vault.py`, append-only), ce module est un **miroir réconcilié** : une carte
supprimée en base voit sa note disparaître du vault.

Garde-fous non négociables (repris de `journal_vault.py`) :
- chemins **toujours** dérivés d'un slug ASCII borné généré côté serveur (`slugify`), jamais d'un
  `title`/`board` brut ; double barrière `_resolve_within_vault` ;
- écriture atomique (tmp + `os.replace`) ;
- **aucune** écriture ni suppression hors `vault/tasks/`. La réconciliation ne touche jamais les
  notes journal ni la racine du vault.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.db import get_pool
# Helpers factorisés depuis le writer journal : une seule implémentation des garde-fous de chemin
# et du versionnage git pour tout le vault.
from app.services.journal_vault import (
    VaultError,
    _git,
    _resolve_within_vault,
    ensure_vault,
    slugify,
)

logger = logging.getLogger(__name__)

_TASKS_SUBDIR = "tasks"

# Mapping colonne → status, figé en tête de module (pas de magie dispersée). Proposition de la
# roadmap `kb-visualisation-obsidian.md` §Décisions, validée pour le sprint Substrat.
# Clés comparées sur le nom de colonne normalisé (lowercase, sans accent via slugify).
_STATUS_DONE = {"termine", "done", "fait", "cloture", "closed"}
_STATUS_REMINDER = {"rappels", "rappel", "reminder", "reminders"}


def _status_for_column(column_name: str) -> str:
    key = slugify(column_name)
    if key in _STATUS_DONE:
        return "done"
    if key in _STATUS_REMINDER:
        return "reminder"
    return "open"


def _iso(dt: datetime | None) -> str | None:
    """ISO 8601 UTC (`Z`). Les colonnes sont TIMESTAMPTZ → asyncpg renvoie du tz-aware ; on
    normalise en UTC pour un rendu stable, insensible au fuseau du process."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _card_frontmatter(card, board_name: str, column_name: str, tags: list[str]) -> str:
    """Contrat roadmap §5 / ticket #1787600247611. `due` absent quand `due_date` est NULL."""
    data: dict = {
        "type": "task",
        "card_id": str(card["id"]),          # clé de réconciliation stable
        "board": board_name,
        "column": column_name,
        "position": card["position"],
    }
    if card["due_date"] is not None:
        due = card["due_date"]
        if due.tzinfo is not None:
            due = due.astimezone(timezone.utc)
        data["due"] = due.date().isoformat()
    data["status"] = _status_for_column(column_name)
    data["tags"] = list(tags)
    data["created_at"] = _iso(card["created_at"])
    data["updated_at"] = _iso(card["updated_at"])
    data["source"] = "kanban"
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{body}---\n"


def _render_card(card, board_name: str, column_name: str, tags: list[str]) -> str:
    fm = _card_frontmatter(card, board_name, column_name, tags)
    return fm + "\n" + (card["description"] or "")


def _atomic_write(target: Path, content: str) -> None:
    """Écriture atomique : un lecteur (Obsidian, git) ne voit jamais un fichier à moitié écrit."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, target)
    except OSError as exc:
        if tmp.exists():
            tmp.unlink()
        raise VaultError(f"écriture impossible dans le vault : {exc}") from exc


def _read_card_id(path: Path) -> str | None:
    """Extrait `card_id` du frontmatter d'une note existante, pour réconcilier par identité stable
    (pas par slug) : un titre modifié déplace le fichier sans créer de doublon."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    try:
        meta = yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return None
    if isinstance(meta, dict):
        cid = meta.get("card_id")
        return str(cid) if cid else None
    return None


def _index_existing(tasks_root: Path) -> dict[str, Path]:
    """Indexe les notes présentes sous `tasks/` par `card_id`. Une note sans `card_id` lisible
    (fichier étranger déposé à la main) est ignorée : on ne la réécrit ni ne la supprime."""
    index: dict[str, Path] = {}
    if not tasks_root.exists():
        return index
    for path in tasks_root.rglob("*.md"):
        if path.name.startswith("."):
            continue
        cid = _read_card_id(path)
        if cid:
            index[cid] = path
    return index


def _prune_empty_dirs(tasks_root: Path) -> None:
    """Retire les dossiers board devenus vides après suppression de leurs cartes. Ne remonte
    jamais au-dessus de `tasks/`."""
    if not tasks_root.exists():
        return
    for board_dir in sorted(tasks_root.iterdir(), reverse=True):
        if board_dir.is_dir() and not any(board_dir.iterdir()):
            board_dir.rmdir()


async def _commit(root: Path) -> None:
    """Commit best-effort de la projection. Un échec git n'empêche pas la lecture sur disque."""
    code, out = await _git(root, "add", "-A", "--", _TASKS_SUBDIR)
    if code != 0:
        logger.warning(f"kanban_vault: git add a échoué ({out})")
        return
    code, out = await _git(
        root, "-c", "user.name=assistant-ia", "-c", "user.email=assistant@jlmvpscode.duckdns.org",
        "commit", "-q", "--author", "assistant-ia <assistant@jlmvpscode.duckdns.org>",
        "-m", "sync kanban",
    )
    # code != 0 inclut « rien à committer » (aucune diff) → non loggué comme erreur.
    if code != 0 and "nothing to commit" not in out.lower():
        logger.warning(f"kanban_vault: git commit a échoué ({out})")


async def sync_kanban_vault() -> dict:
    """Réconcilie l'intégralité du vault `tasks/` avec l'état Postgres du kanban. Source de vérité
    du miroir (robuste aux écritures manquées). Renvoie un petit compte-rendu pour les logs/tests.
    """
    root = await ensure_vault()
    tasks_root = _resolve_within_vault(root, _TASKS_SUBDIR)
    tasks_root.mkdir(parents=True, exist_ok=True)

    pool = await get_pool()
    cards = await pool.fetch(
        "SELECT c.*, col.name AS column_name, b.name AS board_name "
        "FROM cards c "
        "JOIN columns col ON col.id = c.column_id "
        "JOIN boards b ON b.id = col.board_id "
        "ORDER BY b.name, c.id"          # ordre stable → suffixes de collision déterministes
    )
    tag_rows = await pool.fetch("SELECT card_id, value FROM card_fields WHERE key = 'tag'")
    tags_by_card: dict[str, list[str]] = {}
    for row in tag_rows:
        tags_by_card.setdefault(str(row["card_id"]), []).append(row["value"])

    existing = _index_existing(tasks_root)
    seen: set[str] = set()
    used_paths: dict[Path, str] = {}     # chemin → card_id (détection de collision de slug)
    written = removed = 0

    for card in cards:
        cid = str(card["id"])
        seen.add(cid)

        board_slug = slugify(card["board_name"])
        base = slugify(card["title"])
        board_dir = _resolve_within_vault(root, _TASKS_SUBDIR, board_slug)

        # Collision de slug entre cartes distinctes du même board → suffixe court dérivé du
        # card_id (stable et unique). La réconciliation restant par card_id, aucun doublon.
        candidate = _resolve_within_vault(root, _TASKS_SUBDIR, board_slug, f"{base}.md")
        if used_paths.get(candidate, cid) != cid:
            candidate = _resolve_within_vault(
                root, _TASKS_SUBDIR, board_slug, f"{base}-{cid[:8]}.md"
            )
        used_paths[candidate] = cid

        content = _render_card(card, card["board_name"], card["column_name"], tags_by_card.get(cid, []))

        old = existing.get(cid)
        if old is not None and old != candidate and old.exists():
            old.unlink()          # titre/board modifié → l'ancienne note migre vers le nouveau chemin

        if not candidate.exists() or candidate.read_text(encoding="utf-8") != content:
            board_dir.mkdir(parents=True, exist_ok=True)
            _atomic_write(candidate, content)
            written += 1

    # Cartes disparues de la base → suppression de la note. Seule suppression autorisée, confinée
    # à `tasks/` (chemins issus de `_index_existing`, donc déjà sous `tasks/`).
    for cid, path in existing.items():
        if cid not in seen and path.exists():
            path.unlink()
            removed += 1

    _prune_empty_dirs(tasks_root)

    if written or removed:
        await _commit(root)
    logger.info(f"kanban_vault: sync terminé ({len(cards)} cartes, {written} écrites, {removed} supprimées)")
    return {"cards": len(cards), "written": written, "removed": removed}
