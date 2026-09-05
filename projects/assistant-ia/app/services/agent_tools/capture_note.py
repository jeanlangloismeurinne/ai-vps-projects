"""Outil `capture_note` — le chemin d'écriture de l'agent vers la base de connaissance.

Roadmap `agent-intention-et-capture-kb.md`, capacité 2 (D3/D5/D6). Corpus visé : C1 (note de
lecture jamais captée), C2 / C6 / C8 (« stocke ce lien dans une liste de… », trois fois en huit
jours, chaque fois refusé par un « je n'ai pas de mémoire persistante »).

## Frontière modèle / code (invariant A3)

| Le modèle fait | Le code fait |
|---|---|
| Choisir le mode, fournir le Markdown verbatim, **nommer** le document | Slugifier ce nom, résoudre le chemin, vérifier qu'il reste dans le vault, classer, écrire, indexer |

Le modèle ne produit **jamais** un chemin. Il produit un libellé humain (« sources utiles ») que
`slugify` réduit à `sources-utiles` — sans séparateur de chemin possible en sortie. La surface
d'attaque se réduit donc à du texte, dans un fichier Markdown du coffre de l'utilisateur.

## Deux modes, et pourquoi exactement deux

Ce ne sont pas « une note » et « une liste ». Un Markdown porte déjà les puces, les tableaux, les
cases à cocher et les titres : coder une primitive par forme de contenu était l'erreur de la
première version. Ce qui distingue réellement les deux modes est l'**adressage** :

- `note`     → `journal_vault.write_entry(subdir="notes")` : adressage **daté**,
  `notes/{année}/{AAAA-MM-JJ}-{slug}.md`. Chaque capture crée un fichier neuf — cinq notes sur le
  même sujet coexistent lisiblement (C1 était cinq messages sur la même lecture). Passe par le
  classifieur et entre dans l'index de recherche.
- `document` → `journal_vault.append_to_document()` : adressage **par nom**. « mes sources
  utiles » doit retomber sur le fichier d'hier. Crée le document s'il n'existe pas, ajoute à la
  suite sinon, **sans jamais réécrire** ce qui précède.

Il n'y a délibérément pas de troisième mode « créer » distinct d'« ajouter » : le code crée
toujours à la volée, donc la distinction n'existerait que dans l'intention du modèle et un
malentendu y serait silencieux.

## L'outil de lecture qui va avec

L'adressage par nom ne vaut que si le modèle voit les noms existants — sinon il en invente un
voisin (observé en rejeu : `startups-spatial` puis `startups-spatial-a-creuser`, deux fichiers
pour une même demande). C'est l'objet de `list_documents`, à appeler avant d'écrire.

## Ce qui n'est pas ici

L'accusé de réception ne porte pour l'instant que le chemin écrit, pas d'URL cliquable vers
kb-viewer : c'est la capacité 4, et son test d'acceptation doit rester rouge tant qu'elle n'est
pas faite.
"""
from __future__ import annotations

import logging

from app.services import journal_kb_classifier, journal_kb_index, journal_vault
from app.services.agent_tools.base import PreparedCall, ToolContext, ToolError, ToolResult, ToolSpec
from app.services.agent_tools.manifest import Effect, RateLimit, ToolManifest

logger = logging.getLogger(__name__)

# Sous-répertoire des captures conversationnelles datées. Constante de code : le modèle ne
# choisit jamais où l'on écrit (cf. `create_reminder.REMINDER_COLUMN`, même règle).
NOTES_SUBDIR = "notes"

# Un contenu plus long que ça n'est pas tapé dans Slack — c'est un contenu recopié depuis une
# lecture d'outil. On refuse explicitement plutôt que de tronquer en silence.
CONTENT_MAX = 20_000
# Au-delà, « le nom du document » est une phrase, pas un nom.
NAME_MAX = 120
PREVIEW_MAX = 300

SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {
            "type": "string",
            "enum": ["note", "document"],
            "description": (
                "`note` : conserver un texte daté, autonome (note de lecture, réflexion, compte "
                "rendu) — un fichier neuf à chaque fois. `document` : écrire dans un document que "
                "l'utilisateur désigne par son nom (une liste de sources, un tableau de suivi, "
                "des idées) — le contenu est ajouté à la suite de ce qui s'y trouve déjà, et le "
                "document est créé s'il n'existe pas. Ne demande jamais l'autorisation de créer."
            ),
        },
        "name": {
            "type": "string",
            "description": (
                "Si mode = document : le nom du document, tel que l'utilisateur le désigne "
                "(ex. « sources utiles », « startups spatial », « courses »). Un nom court, pas "
                "une phrase. Appelle d'abord `list_documents` et **réutilise le nom exact** d'un "
                "document existant s'il correspond — sinon tu crées un doublon."
            ),
        },
        "content": {
            "type": "string",
            "description": (
                "Le contenu, en Markdown, **verbatim** : tel que l'utilisateur l'a écrit. Ne "
                "reformule pas, ne résume pas, n'ajoute rien qu'il n'ait pas écrit, et n'y mets "
                "pas le reste de son message. Utilise la forme Markdown qu'appelle la demande : "
                "`- élément` par ligne pour une liste, `- [ ] tâche` pour des cases à cocher, "
                "`| a | b |` pour une ligne de tableau, du texte simple pour un paragraphe. En "
                "mode `document`, ce contenu est ajouté tel quel à la fin du document : n'y "
                "recopie pas ce qui s'y trouve déjà."
            ),
        },
    },
    "required": ["mode", "content"],
    "additionalProperties": False,
}

MANIFEST = ToolManifest(
    name="capture_note",
    description=(
        "Écrit durablement dans la base de connaissance de l'utilisateur — son coffre de notes "
        "Markdown, qu'il relit dans Obsidian et sur le web. Deux usages : conserver une note "
        "datée (mode `note`), ou écrire dans un document qu'il désigne par son nom, en ajoutant "
        "à la suite (mode `document`). Le contenu est du Markdown libre : listes à puces, cases "
        "à cocher, tableaux, paragraphes, titres. À utiliser dès qu'il dit « note », "
        "« enregistre », « stocke », « garde », « retiens », « ajoute à ma liste de… », « crée "
        "une liste / un tableau de… ». Tu as bien une mémoire durable : c'est cet outil."
    ),
    schema=SCHEMA,
    effect=Effect.WRITE,
    taints_context=False,       # écrit dans le vault, ne rapporte aucun contenu extérieur
    reversible=True,            # fichier Markdown éditable et supprimable
    scope="base de connaissance (vault) de l'utilisateur",
    visibility=True,            # D6 : on écrit, puis on confirme — demander avait perdu C6
    # 4 par tour : C6 porte deux intentions, un tour peut légitimement viser deux documents et
    # une note. 40 par jour : plafond de dégâts d'une boucle, sans gêner un usage réel.
    rate_limit=RateLimit(per_turn=4, per_day=40),
    egress=None,
)


def _preview(text: str) -> str:
    flat = " ".join((text or "").split())
    return flat if len(flat) <= PREVIEW_MAX else flat[:PREVIEW_MAX].rstrip() + "…"


def _bloc_cite(text: str) -> str:
    """Rend un bloc Markdown en citation Slack, en préservant ses retours à la ligne.

    La confirmation doit montrer la **forme** de ce qui va être écrit — une puce reste une puce,
    une ligne de tableau reste une ligne de tableau. L'aplatir en une phrase masquerait justement
    ce que cette version de l'outil apporte.
    """
    lignes = text.strip().split("\n")
    if len(lignes) > 12:
        lignes = lignes[:12] + [f"… (+{len(lignes) - 12} lignes)"]
    return "\n".join(f"> {ligne}" for ligne in lignes)


async def _resolve(args: dict, ctx: ToolContext) -> PreparedCall:
    """Valide et fige le payload. Aucun appel réseau ici : la classification est un appel modèle,
    elle n'a pas à être payée pour un appel qui sera refusé par la policy ou jamais confirmé."""
    mode = str(args.get("mode") or "").strip().lower()
    if mode not in ("note", "document"):
        raise ToolError("`mode` doit valoir `note` ou `document`")

    content = str(args.get("content") or "").strip()
    if not content:
        raise ToolError("`content` est vide : précise le texte à enregistrer.")
    if len(content) > CONTENT_MAX:
        raise ToolError(
            f"texte trop long ({len(content)} caractères, max {CONTENT_MAX}). "
            f"Découpe-le en plusieurs écritures."
        )

    if mode == "note":
        return PreparedCall(
            resolved={"mode": "note", "content": content},
            summary=f"Note dans la base de connaissance :\n{_bloc_cite(content)}",
        )

    # ── mode document ────────────────────────────────────────────────────────
    name = str(args.get("name") or "").strip()
    if not name:
        raise ToolError("`name` est obligatoire en mode `document` : nomme le document.")
    if len(name) > NAME_MAX:
        raise ToolError(f"`name` trop long ({len(name)} car.) : donne un nom court.")

    # Le code décide du chemin. Le slug est calculé ici pour que la confirmation affiche le
    # fichier réel, et non le libellé que le modèle a proposé.
    slug = journal_vault.slugify(name)
    return PreparedCall(
        resolved={"mode": "document", "name": name, "slug": slug, "content": content},
        summary=(f"Ajout au document *{name}* (`documents/{slug}.md`) :\n"
                 f"{_bloc_cite(content)}"),
    )


# ── Exécution ────────────────────────────────────────────────────────────────

async def _execute_note(resolved: dict, ctx: ToolContext) -> ToolResult:
    content = resolved["content"]
    hash_ = journal_kb_index.content_hash(content)

    # Dédup avant le classifieur : évite un appel modèle et un fichier orphelin dans le vault.
    # Un échec de lecture d'index ne doit pas empêcher d'écrire la note — le pivot est le disque.
    try:
        existing = await journal_kb_index.find_duplicate(hash_)
    except Exception:
        logger.exception("capture_note: lecture de l'index impossible, on écrit quand même")
        existing = None
    if existing:
        return ToolResult(
            payload={
                "status": "déjà enregistrée",
                "uri": existing,
                "note": "Ce texte exact est déjà dans la base de connaissance. Dis-le à "
                        "l'utilisateur en nommant le fichier, n'écris pas de doublon.",
            },
            slack_text=f"Déjà dans la base de connaissance : `{existing}`",
            slack_blocks=[{
                "type": "section",
                "text": {"type": "mrkdwn",
                         "text": f":card_index_dividers: Déjà enregistré — `{existing}`"},
            }],
        )

    # Le classifieur ne lève jamais : en cas d'échec il renvoie `is_fallback=True` et la note est
    # écrite sous le tag « à classer » plutôt que perdue.
    classe = await journal_kb_classifier.classify(content)

    entry = await journal_vault.write_entry(
        title=classe.title,
        body=content,
        contexte=classe.contexte,
        nature=classe.nature,
        tags=classe.tags,
        slack_ts=ctx.turn.slack_ts,
        subdir=NOTES_SUBDIR,
    )

    indexed = True
    try:
        await journal_kb_index.upsert(
            doc_id=entry.doc_id,
            uri=entry.relative_path,
            title=classe.title,
            body=content,
            contexte=classe.contexte,
            nature=classe.nature,
            tags=classe.tags,
            hash_=hash_,
            slack_ts=ctx.turn.slack_ts,
        )
    except Exception:
        # La note est sur disque : ce n'est pas une perte, c'est une absence des recherches. On le
        # dit au modèle plutôt que de le taire, sans transformer l'appel en échec.
        logger.exception("capture_note: indexation échouée pour %s", entry.doc_id)
        indexed = False

    logger.info(
        "capture_note: note écrite (%s, fallback=%s, indexée=%s)",
        entry.relative_path, classe.is_fallback, indexed,
    )

    etiquettes = [classe.contexte] if classe.contexte else []
    etiquettes += list(classe.nature or [])
    etiquettes += [f"#{t}" for t in (classe.tags or [])]
    ligne_meta = " · ".join(etiquettes) if etiquettes else "à classer"

    payload = {
        "status": "enregistrée",
        "uri": entry.relative_path,
        "title": classe.title,
        "classée": not classe.is_fallback,
        "note": "La note est écrite dans la base de connaissance et confirmée à l'utilisateur "
                "dans le fil. Acquitte brièvement, ne recopie pas le contenu.",
    }
    if not indexed:
        payload["avertissement"] = (
            "Le fichier est écrit mais l'index de recherche n'a pas été mis à jour : "
            "la note n'apparaîtra pas dans les recherches tant qu'il n'est pas reconstruit."
        )

    texte = f":card_index_dividers: Noté — *{classe.title}*\n{ligne_meta}\n`{entry.relative_path}`"
    if not indexed:
        texte += "\n_(écrit dans le coffre, mais absent de l'index de recherche)_"

    return ToolResult(
        payload=payload,
        slack_blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": texte}}],
        slack_text=f"Noté : {classe.title} — {entry.relative_path}",
    )


async def _execute_document(resolved: dict, ctx: ToolContext) -> ToolResult:
    entry = await journal_vault.append_to_document(
        name=resolved["name"],
        block=resolved["content"],
    )

    logger.info(
        "capture_note: %d ligne(s) ajoutée(s) à %s (création=%s)",
        entry.added_lines, entry.relative_path, entry.created,
    )

    verbe = "Document créé" if entry.created else "Ajouté au document"
    texte = (f":pushpin: {verbe} *{entry.title}*\n"
             f"{_bloc_cite(entry.block)}\n`{entry.relative_path}`")

    return ToolResult(
        payload={
            "status": "document créé" if entry.created else "contenu ajouté",
            "uri": entry.relative_path,
            "document": entry.title,
            "lignes_ajoutées": entry.added_lines,
            "note": "Le contenu est écrit à la fin du document et confirmé à l'utilisateur dans "
                    "le fil. Acquitte brièvement, ne recopie pas le document.",
        },
        slack_blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": texte}}],
        slack_text=f"{verbe} {entry.title} — {entry.relative_path}",
    )


async def _execute(resolved: dict, ctx: ToolContext) -> ToolResult:
    """Reçoit le payload **résolu** — jamais les arguments bruts du modèle.

    Une `VaultError` remonte telle quelle : `loop._handle_call` la convertit en `role=tool` avec
    `{"error": …}`. Jamais un résultat vide, jamais un succès silencieux (leçon SearXNG).
    """
    try:
        if resolved.get("mode") == "note":
            return await _execute_note(resolved, ctx)
        return await _execute_document(resolved, ctx)
    except journal_vault.VaultError as exc:
        raise ToolError(f"écriture impossible dans la base de connaissance : {exc}") from exc


SPEC = ToolSpec(manifest=MANIFEST, execute=_execute, resolve=_resolve)
