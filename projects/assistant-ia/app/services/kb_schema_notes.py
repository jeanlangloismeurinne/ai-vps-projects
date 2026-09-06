"""
Notes de navigation du vault (#1787600247612, sprint « Substrat » ; refondu le 2026-09-06).

Écrit à la racine du vault les pages qui rendent la KB *parcourable* :
- `Accueil.md`   — page d'atterrissage : la **synthèse par thème**, chaque thème listant ses notes ;
- `Journal.md`   — l'inventaire exhaustif des notes, du plus récent au plus ancien ;
- `Tâches.md`    — le kanban, par tableau et par colonne ;
- `Taxonomie.md` — le vocabulaire de classification, **généré depuis**
  `app/knowledge/categories.schema.yaml` (source de vérité).

Ces fichiers sont maintenus par l'agent, idempotents (réécrits seulement si le contenu change),
atomiques, confinés au vault, versionnés en best-effort.

⚠️ **Pourquoi ces pages se génèrent depuis le disque et non depuis `journal_kb_entries`.**
C'est le correctif du défaut mesuré le 2026-09-06 : `Accueil.md` proposait `[[Tâches]]` et
`[[Journal]]`, deux vues **Obsidian Bases** (`.base`). Quartz — la seule surface de lecture réelle,
`kb.jlmvpscode.duckdns.org` — ne traite que le `.md` : les deux fichiers étaient dans le coffre et
absents du site. **Deux des trois portes d'entrée de la base rendaient 404, depuis le basculement
Obsidian → Quartz du 2026-08-25.** Générer depuis l'index aurait la même faiblesse par un autre
bout : une ligne d'index dont le fichier a disparu produit un lien mort. En balayant le disque, un
lien ne peut désigner qu'un fichier qui existe — l'invariant est structurel, pas surveillé.

L'index reste utile pour une seule chose, le **libellé** : le front-matter d'une note ne porte pas
son titre (il vit dans `journal_kb_entries.title`). Un titre absent dégrade en nom de fichier
déslugifié — jamais en lien manquant.

Les `.base` restent générés : invisibles sur le web, ils gardent leur valeur de vue filtrable dans
Obsidian bureau. Ce qui a changé, c'est que **plus aucune page ne les référence par wikilink**.
"""
from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
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
_JOURNAL = "Journal.md"
_TACHES = "Tâches.md"
_TACHES_BASE = "Tâches.base"
_JOURNAL_BASE = "Journal.base"

# Pages racine gérées ici : elles sont exclues du balayage, sinon l'inventaire s'indexerait lui-même.
_PAGES_RACINE = {_ACCUEIL, _TAXONOMIE, _JOURNAL, _TACHES, "README.md"}

# Un tag ne devient un « thème » qu'à partir de deux notes. En dessous, il ne regroupe rien : une
# page de thème à une seule note est un détour, pas une synthèse. Les notes qu'aucun thème ne
# rassemble sont listées à part plutôt que rattachées de force au tag le moins éloigné — un
# regroupement qui ne laisse jamais d'isolé ne mesure rien (même raison qu'en roadmap §7).
_SEUIL_THEME = 2

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _lire_frontmatter(path: Path) -> dict:
    """Front-matter d'un fichier du coffre, ou `{}` si absent/illisible.

    Ne lève jamais : un fichier mal formé doit disparaître de la navigation, pas faire échouer la
    génération de toutes les pages — sinon une note corrompue rend la base entière inaccessible.
    """
    try:
        texte = path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("kb_schema_notes: lecture impossible (%s)", path)
        return {}
    m = _FRONTMATTER_RE.match(texte)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        logger.warning("kb_schema_notes: front-matter illisible (%s)", path)
        return {}


def _deslugifier(nom: str) -> str:
    """Repli de libellé : `2026-08-24-notes-de-lecture` → `Notes de lecture`."""
    sans_date = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", nom)
    return sans_date.replace("-", " ").strip().capitalize() or nom


def _wikilink(chemin_relatif: str, libelle: str) -> str:
    """Lien vers une note, par son chemin **sans extension**.

    Le chemin complet plutôt que le seul nom de fichier : deux notes de même nom dans deux années
    différentes se résoudraient sinon l'une sur l'autre, en silence.
    """
    return f"[[{chemin_relatif}|{libelle}]]"


def _scanner_notes(root: Path, titres: dict[str, str]) -> list[dict]:
    """Balaye les notes du coffre. Une note = un `.md` portant un `doc_id` en front-matter.

    Le discriminant est le `doc_id`, pas le chemin : il distingue une note d'une page de navigation
    ou d'un miroir de carte, quel que soit le répertoire — l'ingestion `#journal` écrit dans
    `{année}/`, l'agent dans `notes/{année}/`, et un troisième producteur écrirait ailleurs encore.
    """
    notes: list[dict] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if rel in _PAGES_RACINE or rel.startswith("tasks/") or "/.git/" in f"/{rel}":
            continue
        fm = _lire_frontmatter(path)
        if not fm.get("doc_id"):
            continue
        sans_ext = rel[:-3]
        notes.append({
            "chemin": sans_ext,
            "titre": titres.get(rel) or _deslugifier(path.stem),
            "tags": [str(t) for t in (fm.get("tags") or [])],
            "nature": [str(n) for n in (fm.get("nature") or [])],
            "contexte": fm.get("contexte") or "",
            "date": str(fm.get("created_at") or "")[:10],
        })
    notes.sort(key=lambda n: (n["date"], n["chemin"]), reverse=True)
    return notes


def _scanner_taches(root: Path) -> list[dict]:
    taches: list[dict] = []
    dossier = root / "tasks"
    if not dossier.is_dir():
        return taches
    for path in sorted(dossier.rglob("*.md")):
        fm = _lire_frontmatter(path)
        if fm.get("type") != "task":
            continue
        rel = path.relative_to(root).as_posix()
        taches.append({
            "chemin": rel[:-3],
            "titre": _deslugifier(path.stem),
            "board": str(fm.get("board") or "—"),
            "column": str(fm.get("column") or "—"),
            "due": str(fm.get("due") or ""),
            "status": str(fm.get("status") or ""),
        })
    return taches


def _grouper_par_theme(notes: list[dict]) -> tuple[list[tuple[str, list[dict]]], list[dict]]:
    """Renvoie (thèmes triés, notes isolées).

    Une note appartient à **tous** ses thèmes : la navigation est un graphe, pas un arbre. Vouloir
    un parent unique obligerait à départager `Safran` et `EU Space Act` sur une note qui parle des
    deux — un arbitrage que rien ne fonde et qui rend la seconde entrée introuvable.
    """
    par_tag: dict[str, list[dict]] = defaultdict(list)
    for note in notes:
        for tag in note["tags"]:
            par_tag[tag].append(note)

    themes = [(tag, membres) for tag, membres in par_tag.items() if len(membres) >= _SEUIL_THEME]
    themes.sort(key=lambda kv: (-len(kv[1]), kv[0].lower()))

    regroupees = {n["chemin"] for _, membres in themes for n in membres}
    isolees = [n for n in notes if n["chemin"] not in regroupees]
    return themes, isolees


def _accueil_md(notes: list[dict], taches: list[dict]) -> str:
    themes, isolees = _grouper_par_theme(notes)

    lines = [
        "# Base de connaissance",
        "",
        "> Coffre **écrit par l'agent** (assistant-ia), en lecture seule. Les pages de navigation",
        "> ci-dessous sont régénérées automatiquement — ne les éditez pas à la main.",
        "",
        "| | |",
        "|---|---|",
        f"| **[[Journal]]** | les {len(notes)} notes, de la plus récente à la plus ancienne |",
        f"| **[[Tâches]]** | les {len(taches)} tâches du kanban, par tableau et colonne |",
        "| **[[Taxonomie]]** | le vocabulaire de classification |",
        "",
        "## Thèmes",
        "",
    ]

    if themes:
        lines += [
            f"{len(themes)} thèmes regroupent {len(notes) - len(isolees)} des {len(notes)} notes.",
            "Une note appartient à tous ses thèmes.",
            "",
        ]
        for tag, membres in themes:
            lines.append(f"### {tag}  ·  {len(membres)} notes")
            lines.append("")
            for note in membres:
                lines.append(f"- {_wikilink(note['chemin'], note['titre'])}  <sub>{note['date']}</sub>")
            lines.append("")
    else:
        lines += ["*Aucun thème pour l'instant : il faut au moins deux notes partageant un tag.*", ""]

    if isolees:
        lines += [
            "## Notes isolées",
            "",
            "Ces notes ne partagent encore aucun tag avec une autre. Elles ne sont rattachées à",
            "aucun thème plutôt que rattachées au moins éloigné.",
            "",
        ]
        for note in isolees:
            lines.append(f"- {_wikilink(note['chemin'], note['titre'])}  <sub>{note['date']}</sub>")
        lines.append("")

    return "\n".join(lines)


def _journal_md(notes: list[dict]) -> str:
    lines = [
        "# Journal — toutes les notes",
        "",
        f"{len(notes)} notes, de la plus récente à la plus ancienne. Retour à l'[[Accueil]].",
        "",
    ]
    mois_courant = ""
    for note in notes:
        mois = note["date"][:7] or "sans date"
        if mois != mois_courant:
            lines += ["", f"## {mois}", ""]
            mois_courant = mois
        meta = " · ".join(filter(None, [
            note["contexte"],
            ", ".join(note["nature"]),
            " ".join(f"#{t.replace(' ', '-')}" for t in note["tags"]),
        ]))
        lines.append(f"- **{_wikilink(note['chemin'], note['titre'])}** <sub>{note['date']}</sub>")
        if meta:
            lines.append(f"  <sub>{meta}</sub>")
    lines.append("")
    return "\n".join(lines)


def _taches_md(taches: list[dict]) -> str:
    lines = [
        "# Tâches",
        "",
        f"{len(taches)} tâches, miroir du kanban. Retour à l'[[Accueil]].",
        "",
    ]
    par_groupe: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for tache in taches:
        par_groupe[(tache["board"], tache["column"])].append(tache)

    for (board, column) in sorted(par_groupe):
        lines += [f"## {board} · {column}", ""]
        for tache in sorted(par_groupe[(board, column)], key=lambda t: (t["due"] or "9999", t["titre"])):
            echeance = f"  <sub>échéance {tache['due']}</sub>" if tache["due"] else ""
            lines.append(f"- {_wikilink(tache['chemin'], tache['titre'])}{echeance}")
        lines.append("")
    return "\n".join(lines)


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


async def _titres_par_uri() -> dict[str, str]:
    """Libellés des notes, lus dans l'index. Best-effort **par construction** : l'index ne décide
    de rien ici, il n'habille que des liens déjà établis par le balayage du disque. Index
    indisponible → libellés déslugifiés, navigation intacte."""
    try:
        from app.db import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT uri, title FROM journal_kb_entries WHERE title <> ''")
        return {r["uri"]: r["title"] for r in rows}
    except Exception:
        logger.exception("kb_schema_notes: titres indisponibles, repli sur les noms de fichiers")
        return {}


async def sync_schema_notes() -> dict:
    """(Ré)écrit les pages de navigation à la racine du vault. Idempotent : ne réécrit et ne
    committe que les fichiers dont le contenu a changé."""
    root = await ensure_vault()
    titres = await _titres_par_uri()
    notes = _scanner_notes(root, titres)
    taches = _scanner_taches(root)

    files = {
        _ACCUEIL: _accueil_md(notes, taches),
        _JOURNAL: _journal_md(notes),
        _TACHES: _taches_md(taches),
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
