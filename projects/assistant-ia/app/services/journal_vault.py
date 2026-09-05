"""
Vault Obsidian du journal — pivot Markdown lisible (#1787559677486).

Le Markdown est la source de vérité ; Postgres n'est qu'un index dérivé. Ce module est donc
volontairement défensif : il n'écrase jamais un fichier, ne supprime jamais rien, et ne construit
jamais un chemin depuis une entrée utilisateur brute.

Décision v1 : vault = dépôt git local sur le VPS (pas de Nextcloud sur la machine). Commit local
après chaque écriture, aucun push — le contenu est personnel (`visibility: private`).
"""
import asyncio
import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from app.config import settings

logger = logging.getLogger(__name__)

_SLUG_MAX = 60
_COLLISION_MAX = 50          # au-delà, on refuse plutôt que de boucler
_GIT_AUTHOR = "assistant-ia <assistant@jlmvpscode.duckdns.org>"

# Répertoire des listes nommées (D5). Un fichier par liste, alimenté **en ajout pur**.
_LISTS_SUBDIR = "listes"
# Un élément de liste tient sur une ligne : au-delà ce n'est plus un élément, c'est une note.
_LIST_ITEM_MAX = 300

_README = """# Journal — vault Obsidian

Ce dossier est **écrit par l'agent**. Ne le modifiez pas à la main : l'index Postgres
(`journal_kb_entries`) est dérivé de ces fichiers et serait désynchronisé.

Un fichier = une note. Le corps est le verbatim de ce que vous avez écrit dans Slack `#journal` ;
le front-matter est produit par le classifieur.

## Consulter le vault

Deux voies d'accès :

**En ligne** (lecture seule, rien à installer) : <https://kb.jlmvpscode.duckdns.org> — site
statique généré depuis ce vault (graphe, backlinks, recherche plein texte). Protégé par mot de
passe.

**En local** (pour l'ouvrir dans Obsidian) :

```bash
git clone ssh://root@204.168.250.110/storage/journal-vault ~/journal-vault
```

Puis ouvrez `~/journal-vault` comme coffre dans Obsidian. Pour rafraîchir : `git pull`.

Les commits sont locaux au VPS : il n'y a pas de dépôt distant, et ce vault n'est **pas** inclus
dans le repo `ai-vps-projects`.
"""


class VaultError(Exception):
    """Écriture impossible. L'appelant doit le signaler à l'utilisateur, pas l'avaler."""


@dataclass
class VaultEntry:
    doc_id: str
    slug: str
    relative_path: str      # ex. "2026/2026-08-24-reunion-equipe-produit.md"
    absolute_path: str


@dataclass
class VaultListEntry:
    """Résultat d'un ajout à une liste nommée.

    `created` distingue « j'ai créé la liste » de « j'ai ajouté à une liste existante » : c'est la
    seule chose que l'accusé de réception doit dire différemment, et le code appelant ne peut pas
    la redéduire (le fichier existe dans les deux cas au retour).
    """
    doc_id: str
    slug: str
    relative_path: str      # ex. "listes/sources-utiles.md"
    absolute_path: str
    title: str
    created: bool
    added: list[str]        # lignes réellement ajoutées, après nettoyage


def _vault_root() -> Path:
    return Path(settings.JOURNAL_VAULT_PATH)


def slugify(text: str) -> str:
    """Slug ASCII borné, dérivé côté serveur. Jamais de séparateur de chemin en sortie : c'est
    ce qui neutralise les tentatives de traversée (`../`, `/etc/passwd`)."""
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    slug = slug[:_SLUG_MAX].strip("-")
    return slug or "note"


def _resolve_within_vault(root: Path, *parts: str) -> Path:
    """Résout un chemin et vérifie qu'il reste sous le vault. Deuxième barrière après `slugify` :
    on ne fait pas confiance à une seule couche pour une écriture disque."""
    root_resolved = root.resolve()
    candidate = root_resolved.joinpath(*parts)
    resolved = Path(os.path.normpath(str(candidate)))
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise VaultError(f"chemin hors du vault refusé : {resolved}")
    return resolved


def _frontmatter(doc_id: str, contexte, nature, tags, created_at: datetime, slack_ts) -> str:
    data = {
        "doc_id": doc_id,
        "contexte": contexte,
        "nature": list(nature or []),
        "tags": list(tags or []),
        "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "slack_ts": str(slack_ts) if slack_ts else None,
    }
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{body}---\n"


async def _git(root: Path, *args: str) -> tuple[int, str]:
    """Renvoie (code, sortie). Un git absent de l'image remonte en code 127 plutôt qu'en
    exception : les appelants traitent déjà le code de retour, pas besoin d'un second chemin."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", str(root), *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except (FileNotFoundError, OSError) as exc:
        return 127, f"git indisponible : {exc}"
    out, _ = await proc.communicate()
    return proc.returncode, out.decode(errors="replace").strip()


async def ensure_vault() -> Path:
    """Crée le vault et son dépôt git s'ils n'existent pas. Idempotent."""
    root = _vault_root()
    root.mkdir(parents=True, exist_ok=True)

    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(_README, encoding="utf-8")

    if not (root / ".git").exists():
        code, out = await _git(root, "init", "-q", "-b", "main")
        if code != 0:
            # Best-effort, comme `_commit` : le versionnage est un confort, le fichier Markdown est
            # la donnée. Faire échouer l'ingestion ici ferait perdre la note de l'utilisateur pour
            # un problème d'outillage — exactement ce que le vault est censé éviter.
            logger.warning(f"journal_vault: git init a échoué, vault non versionné ({out})")
        else:
            logger.info(f"journal_vault: dépôt git initialisé dans {root}")
    return root


async def _commit(root: Path, relative_path: str, message: str) -> None:
    """Commit best-effort : une note écrite mais non committée reste lisible sur disque, donc un
    échec git ne doit pas faire échouer l'ingestion."""
    code, out = await _git(root, "add", "--", relative_path, "README.md")
    if code != 0:
        logger.warning(f"journal_vault: git add a échoué ({out})")
        return
    code, out = await _git(
        root, "-c", f"user.name=assistant-ia", "-c", "user.email=assistant@jlmvpscode.duckdns.org",
        "commit", "-q", "--author", _GIT_AUTHOR, "-m", message,
    )
    if code != 0:
        logger.warning(f"journal_vault: git commit a échoué ({out})")


async def write_entry(
    *,
    title: str,
    body: str,
    contexte: str | None = None,
    nature: list[str] | None = None,
    tags: list[str] | None = None,
    created_at: datetime | None = None,
    slack_ts: str | None = None,
    subdir: str | None = None,
) -> VaultEntry:
    """Écrit une note dans le vault et la committe. Append-only : ne remplace jamais un fichier
    existant, ne supprime jamais rien.

    `subdir` sépare les producteurs sans changer la convention de nommage : `None` (défaut) écrit
    `{année}/{AAAA-MM-JJ}-{slug}.md`, c'est l'ingestion `#journal` ; `"notes"` écrit
    `notes/{année}/{AAAA-MM-JJ}-{slug}.md`, ce sont les captures faites par l'agent depuis une
    conversation. Le nommage reste daté dans les deux cas — c'est ce qui permet à cinq notes sur
    le même sujet de coexister lisiblement, là où un `notes/{slug}.md` aurait donné `-2`, `-3`…
    Le `subdir` est **slugifié** comme tout autre segment : il ne vient jamais d'une entrée brute.
    """
    root = await ensure_vault()
    created_at = created_at or datetime.utcnow()

    day = created_at.strftime("%Y-%m-%d")
    year = created_at.strftime("%Y")
    base_slug = f"{day}-{slugify(title)}"

    # Segments de chemin, dans l'ordre. Le namespace du `doc_id` suit le répertoire : deux
    # producteurs ne doivent pas pouvoir se collisionner sur la clef primaire de l'index.
    prefix: tuple[str, ...] = (slugify(subdir),) if subdir else ()
    namespace = prefix[0] if prefix else "journal"

    parent_dir = _resolve_within_vault(root, *prefix, year)
    parent_dir.mkdir(parents=True, exist_ok=True)

    # Collision de slug le même jour → suffixe -2, -3… On n'écrase jamais.
    slug = base_slug
    for attempt in range(1, _COLLISION_MAX + 1):
        slug = base_slug if attempt == 1 else f"{base_slug}-{attempt}"
        target = _resolve_within_vault(root, *prefix, year, f"{slug}.md")
        if not target.exists():
            break
    else:
        raise VaultError(f"trop de collisions de slug pour « {base_slug} »")

    doc_id = f"assistant-ia:vps_files:{namespace}/{slug}"
    content = _frontmatter(doc_id, contexte, nature, tags, created_at, slack_ts) + "\n" + (body or "")

    # Écriture atomique : un lecteur (Obsidian, git) ne doit jamais voir un fichier à moitié écrit.
    tmp = target.with_name(f".{target.name}.tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, target)
    except OSError as exc:
        if tmp.exists():
            tmp.unlink()          # fichier temporaire de ce module uniquement
        raise VaultError(f"écriture impossible dans le vault : {exc}") from exc

    relative_path = "/".join([*prefix, year, f"{slug}.md"])
    await _commit(root, relative_path, title or slug)
    logger.info(f"journal_vault: note écrite ({relative_path})")

    return VaultEntry(
        doc_id=doc_id,
        slug=slug,
        relative_path=relative_path,
        absolute_path=str(target),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Listes nommées (D5) — ajout pur, jamais de réécriture
# ─────────────────────────────────────────────────────────────────────────────

def _one_line(text: str, limit: int = _LIST_ITEM_MAX) -> str:
    """Replie un texte sur **exactement une ligne**, borné.

    Ce n'est pas de la cosmétique, c'est une barrière. Un élément multi-ligne casserait la
    garantie « +n lignes, -0 » de l'ajout (l'acceptation de la capacité 2 se lit en `git diff`),
    et surtout il permettrait à du contenu tiers d'insérer un délimiteur de front-matter (`---`)
    ou une entête au milieu d'un fichier déjà écrit.
    Les deux `replace` portent sur U+2028 et U+2029 — les séparateurs de ligne Unicode, donc
    invisibles dans ce source. Ils sont déjà couverts par `\\s` en Python : ils sont explicités
    parce que l'invariant « un élément = une ligne » ne doit pas reposer sur un détail
    d'implémentation de `re`, et parce qu'Obsidian les rend, lui, comme des retours à la ligne.
    """
    collapsed = re.sub(r"\s+", " ", (text or "").replace(" ", " ").replace(" ", " ")).strip()
    if len(collapsed) > limit:
        collapsed = collapsed[:limit].rstrip() + "…"
    return collapsed


def _list_header(doc_id: str, title: str, created_at: datetime) -> str:
    """Entête écrite **une seule fois**, à la création de la liste.

    Volontairement sans champ mutable (pas d'`updated_at`, pas de compteur) : le moindre champ à
    rafraîchir transformerait chaque ajout en réécriture du fichier, et l'ajout ne serait plus un
    ajout. Pas de clef `contexte` non plus — c'est ce qui tient les listes hors de la vue
    `Journal.base` (filtre `file.hasProperty("contexte")`), et `type: list` les tient hors de
    `Tâches.base` (filtre `type == "task"`).
    """
    data = {
        "doc_id": doc_id,
        "type": "list",
        "title": title,
        "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{body}---\n\n# {title}\n\n"


async def append_to_list(
    *,
    list_name: str,
    items: list[str],
    created_at: datetime | None = None,
) -> VaultListEntry:
    """Ajoute des éléments à `listes/{slug}.md`, en créant la liste si elle n'existe pas.

    `write_entry` ne sait pas faire ça : elle est append-only au sens *ne jamais écraser un
    fichier*, ce qui n'est pas la même chose que *ajouter à un fichier existant*. D'où cette
    fonction, avec les mêmes barrières (`slugify`, `_resolve_within_vault`, commit best-effort).

    Le fichier existant n'est **jamais relu ni réécrit** : la création passe par un
    `O_CREAT|O_EXCL` (atomique — deux appels concurrents ne peuvent pas écrire deux entêtes) et
    l'ajout par un `O_APPEND` (le noyau replace l'offset en fin de fichier à chaque écriture).
    C'est plus sûr ici qu'un tmp + `os.replace` : celui-ci imposerait de relire tout le fichier
    et perdrait silencieusement un ajout concurrent.
    """
    root = await ensure_vault()
    created_at = created_at or datetime.utcnow()

    clean = [line for line in (_one_line(i) for i in (items or [])) if line]
    if not clean:
        raise VaultError("aucun élément à ajouter (liste vide après nettoyage)")

    slug = slugify(list_name)
    title = _one_line(list_name, limit=120) or slug
    doc_id = f"assistant-ia:vps_files:listes/{slug}"

    lists_dir = _resolve_within_vault(root, _LISTS_SUBDIR)
    lists_dir.mkdir(parents=True, exist_ok=True)
    target = _resolve_within_vault(root, _LISTS_SUBDIR, f"{slug}.md")

    created = False
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        pass                                    # la liste existe déjà : on ajoutera à la suite
    except OSError as exc:
        raise VaultError(f"création impossible dans le vault : {exc}") from exc
    else:
        created = True
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(_list_header(doc_id, title, created_at))
        except OSError as exc:
            raise VaultError(f"écriture impossible dans le vault : {exc}") from exc

    payload = "".join(f"- {line}\n" for line in clean)
    try:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(payload)
    except OSError as exc:
        raise VaultError(f"ajout impossible dans le vault : {exc}") from exc

    relative_path = f"{_LISTS_SUBDIR}/{slug}.md"
    verbe = "crée" if created else "complète"
    await _commit(root, relative_path, f"liste {title} {verbe} (+{len(clean)})")
    logger.info(
        "journal_vault: %d ligne(s) ajoutée(s) à %s (création=%s)",
        len(clean), relative_path, created,
    )

    return VaultListEntry(
        doc_id=doc_id,
        slug=slug,
        relative_path=relative_path,
        absolute_path=str(target),
        title=title,
        created=created,
        added=clean,
    )
