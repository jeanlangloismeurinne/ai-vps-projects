"""Outil `capture_note` — le chemin d'écriture de l'agent vers la base de connaissance.

Roadmap `agent-intention-et-capture-kb.md`, capacité 2 (D3/D5/D6). Corpus visé : C1 (note de
lecture jamais captée), C2 / C6 / C8 (« stocke ce lien dans une liste de… », trois fois en huit
jours, chaque fois refusé par un « je n'ai pas de mémoire persistante »).

## Frontière modèle / code (invariant A3)

| Le modèle fait | Le code fait |
|---|---|
| Choisir le mode, fournir le texte verbatim, **nommer** la liste | Slugifier ce nom, résoudre le chemin, vérifier qu'il reste dans le vault, classer, écrire, indexer |

Le modèle ne produit **jamais** un chemin. Il produit un libellé humain (« sources utiles ») que
`slugify` réduit à `sources-utiles` — sans séparateur de chemin possible en sortie. La surface
d'attaque se réduit donc à du texte, dans un fichier Markdown du coffre de l'utilisateur.

## Deux modes, deux primitives d'écriture

- `note`  → `journal_vault.write_entry(subdir="notes")` : fichier neuf,
  `notes/{année}/{AAAA-MM-JJ}-{slug}.md`. Nommage daté : cinq notes sur le même sujet coexistent
  lisiblement (C1 était cinq messages sur la même lecture).
- `append` → `journal_vault.append_to_list()` : ajoute des lignes à `listes/{slug}.md` **sans
  relire ni réécrire** le fichier. C'est la fonction neuve de cette capacité — `write_entry` est
  append-only au sens *ne jamais écraser un fichier*, ce qui n'est pas *ajouter à un fichier*.

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

# Sous-répertoire des captures conversationnelles. Constante de code : le modèle ne choisit
# jamais où l'on écrit (cf. `create_reminder.REMINDER_COLUMN`, même règle).
NOTES_SUBDIR = "notes"

# Une note plus longue que ça n'est pas une note tapée dans Slack — c'est un contenu recopié
# depuis une lecture d'outil. On refuse explicitement plutôt que de tronquer en silence.
CONTENT_MAX = 20_000
# Au-delà, « le nom de la liste » est une phrase, pas un nom.
LIST_NAME_MAX = 120
ITEMS_MAX = 25
PREVIEW_MAX = 200

SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {
            "type": "string",
            "enum": ["note", "append"],
            "description": (
                "`note` : conserver un texte comme note durable (note de lecture, réflexion, "
                "compte rendu). `append` : ajouter un ou plusieurs éléments à une liste nommée "
                "par l'utilisateur (sources, idées, achats…). La liste est créée si elle "
                "n'existe pas encore — ne demande jamais l'autorisation de la créer."
            ),
        },
        "content": {
            "type": "string",
            "description": (
                "Si mode = note : le texte à conserver, **verbatim**, tel que l'utilisateur l'a "
                "écrit. Ne reformule pas, ne résume pas, n'ajoute rien qu'il n'ait pas écrit. "
                "N'y mets que ce qu'il a demandé d'enregistrer, pas le reste de son message."
            ),
        },
        "list_name": {
            "type": "string",
            "description": (
                "Si mode = append : le nom de la liste, tel que l'utilisateur l'a formulé "
                "(ex. « sources utiles », « climatisation », « startups spatial »). Un nom court, "
                "pas une phrase. Réutilise exactement le même nom pour retrouver la même liste."
            ),
        },
        "items": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Si mode = append : les éléments à ajouter, **un par entrée**. Un lien, un nom, "
                "un titre. Ne regroupe pas plusieurs éléments dans une seule entrée."
            ),
        },
    },
    "required": ["mode"],
    "additionalProperties": False,
}

MANIFEST = ToolManifest(
    name="capture_note",
    description=(
        "Enregistre durablement quelque chose dans la base de connaissance de l'utilisateur — "
        "son coffre de notes, qu'il relit dans Obsidian et sur le web. Deux usages : conserver "
        "une note (mode `note`), ou ajouter des éléments à une liste nommée (mode `append`). "
        "À utiliser dès qu'il dit « note », « enregistre », « stocke », « garde », « retiens », "
        "« ajoute à ma liste de… » ou « crée une liste de… ». Tu as bien une mémoire durable : "
        "c'est cet outil."
    ),
    schema=SCHEMA,
    effect=Effect.WRITE,
    taints_context=False,       # écrit dans le vault, ne rapporte aucun contenu extérieur
    reversible=True,            # fichier Markdown éditable et supprimable
    scope="base de connaissance (vault) de l'utilisateur",
    visibility=True,            # D6 : on écrit, puis on confirme — demander avait perdu C6
    # 4 par tour : C6 porte deux intentions, un tour peut légitimement viser deux listes et une
    # note. 40 par jour : plafond de dégâts d'une boucle, sans gêner un usage réel.
    rate_limit=RateLimit(per_turn=4, per_day=40),
    egress=None,
)


def _preview(text: str) -> str:
    flat = " ".join((text or "").split())
    return flat if len(flat) <= PREVIEW_MAX else flat[:PREVIEW_MAX].rstrip() + "…"


async def _resolve(args: dict, ctx: ToolContext) -> PreparedCall:
    """Valide et fige le payload. Aucun appel réseau ici : la classification est un appel modèle,
    elle n'a pas à être payée pour un appel qui sera refusé par la policy ou jamais confirmé."""
    mode = str(args.get("mode") or "").strip().lower()
    if mode not in ("note", "append"):
        raise ToolError("`mode` doit valoir `note` ou `append`")

    if mode == "note":
        content = str(args.get("content") or "").strip()
        if not content:
            raise ToolError("`content` est vide : précise le texte à enregistrer.")
        if len(content) > CONTENT_MAX:
            raise ToolError(
                f"texte trop long ({len(content)} caractères, max {CONTENT_MAX}). "
                f"Découpe-le en plusieurs notes."
            )
        return PreparedCall(
            resolved={"mode": "note", "content": content},
            summary=f"Note dans la base de connaissance :\n> {_preview(content)}",
        )

    # ── mode append ──────────────────────────────────────────────────────────
    list_name = str(args.get("list_name") or "").strip()
    if not list_name:
        raise ToolError("`list_name` est obligatoire en mode `append` : nomme la liste.")
    if len(list_name) > LIST_NAME_MAX:
        raise ToolError(f"`list_name` trop long ({len(list_name)} car.) : donne un nom court.")

    raw = args.get("items")
    if isinstance(raw, str):
        raw = [raw]
    if not raw:
        # Tolérance délibérée et bornée : le modèle range parfois l'unique élément dans `content`.
        # Une ligne par retour à la ligne — pas de découpe sur la virgule, qui appartient souvent
        # à l'élément lui-même (« Isembard, Ltd »).
        raw = [ligne for ligne in str(args.get("content") or "").splitlines()]
    items = [str(i).strip() for i in raw if str(i).strip()]
    if not items:
        raise ToolError("aucun élément à ajouter : renseigne `items`.")
    if len(items) > ITEMS_MAX:
        raise ToolError(f"trop d'éléments d'un coup ({len(items)}, max {ITEMS_MAX}).")

    # Le code décide du chemin. Le slug est calculé ici pour que la confirmation affiche le
    # fichier réel, et non le libellé que le modèle a proposé.
    slug = journal_vault.slugify(list_name)
    apercu = "\n".join(f"• {_preview(i)}" for i in items)
    return PreparedCall(
        resolved={"mode": "append", "list_name": list_name, "slug": slug, "items": items},
        summary=f"Ajout à la liste *{list_name}* (`listes/{slug}.md`) :\n{apercu}",
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


async def _execute_append(resolved: dict, ctx: ToolContext) -> ToolResult:
    entry = await journal_vault.append_to_list(
        list_name=resolved["list_name"],
        items=resolved["items"],
    )

    logger.info(
        "capture_note: %d élément(s) ajouté(s) à %s (création=%s)",
        len(entry.added), entry.relative_path, entry.created,
    )

    verbe = "Liste créée" if entry.created else "Ajouté à la liste"
    lignes = "\n".join(f"• {i}" for i in entry.added)
    texte = f":pushpin: {verbe} *{entry.title}*\n{lignes}\n`{entry.relative_path}`"

    return ToolResult(
        payload={
            "status": "liste créée" if entry.created else "éléments ajoutés",
            "uri": entry.relative_path,
            "liste": entry.title,
            "ajoutés": entry.added,
            "note": "Les éléments sont écrits dans la liste et confirmés à l'utilisateur dans le "
                    "fil. Acquitte brièvement, ne recopie pas la liste.",
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
        return await _execute_append(resolved, ctx)
    except journal_vault.VaultError as exc:
        raise ToolError(f"écriture impossible dans la base de connaissance : {exc}") from exc


SPEC = ToolSpec(manifest=MANIFEST, execute=_execute, resolve=_resolve)
