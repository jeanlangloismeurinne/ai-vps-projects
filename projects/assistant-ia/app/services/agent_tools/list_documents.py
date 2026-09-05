"""Outil `list_documents` — les noms des documents que l'utilisateur possède déjà.

## Pourquoi cet outil existe

`capture_note` en mode `document` adresse **par nom** : le nom est la clef, `slugify` la fonction
de hachage. Un adressage par nom ne fonctionne que si l'écrivain connaît les noms en circulation.
Le modèle, lui, repart de zéro à chaque tour — l'historique récent ne contient pas l'état du
coffre.

Le défaut a été mesuré, pas supposé. Deux rejeux de la même demande (« crée une liste de startups
du spatial dont les innovations sont à creuser ») ont produit `startups-spatial.md` puis
`startups-spatial-a-creuser.md` : deux fichiers pour une seule liste, et un utilisateur qui perd
la moitié de ses entrées sans qu'aucune erreur ne soit levée. Aucune consigne dans le doc système
ne corrige ça, parce que ce n'est pas un problème de comportement mais d'information manquante.

## Ce que l'outil ne fait pas

Il ne renvoie **pas** le contenu des documents : seulement leur nom, leur chemin et leur taille en
lignes. Rapatrier les corps serait un autre outil, avec une autre politique — et surtout ça
gonflerait le contexte à chaque tour pour un besoin qui est « ce nom existe-t-il déjà ? ».

## Taint

`taints_context=False`, et ce n'est pas une négligence. Le taint marque le contenu que
*l'utilisateur demandeur n'a pas tapé lui-même* (roadmap §2.2). Ici, les noms de documents ont
été écrits par cet utilisateur, dans son propre coffre, via cet agent. Il n'y a pas de tiers dans
la boucle. Le jour où un document pourra être alimenté par une source externe (import de mail,
lecture de fichier déposé), cette ligne devra être rediscutée — c'est écrit ici pour que la
question se repose au bon moment.
"""
from __future__ import annotations

import logging

from app.services import journal_vault
from app.services.agent_tools.base import ToolContext, ToolError, ToolResult, ToolSpec
from app.services.agent_tools.manifest import Effect, RateLimit, ToolManifest

logger = logging.getLogger(__name__)

# Plafond de ce qui remonte au modèle. Au-delà, la liste coûte plus de contexte qu'elle n'en fait
# gagner ; les documents les plus fournis sont les plus susceptibles d'être ceux qu'on complète.
MAX_DOCUMENTS = 60

SCHEMA = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False,
}

MANIFEST = ToolManifest(
    name="list_documents",
    description=(
        "Liste les documents nommés déjà présents dans la base de connaissance de l'utilisateur "
        "(nom, chemin, nombre de lignes) — sans leur contenu. À appeler **avant** d'écrire dans "
        "un document avec `capture_note` en mode `document` : si un document correspond à ce que "
        "l'utilisateur désigne, réutilise son nom exact, sinon tu crées un doublon. À utiliser "
        "aussi quand il demande ce qu'il a déjà noté, quelles listes il a, ou où quelque chose "
        "a été rangé."
    ),
    schema=SCHEMA,
    effect=Effect.READ,
    # Contenu écrit par l'utilisateur lui-même, dans son propre coffre — cf. docstring du module.
    taints_context=False,
    reversible=True,
    scope="base de connaissance (vault) de l'utilisateur",
    visibility=True,
    # Deux appels suffisent dans un tour (vérifier, puis re-vérifier après une écriture). Le
    # plafond journalier est large : une lecture locale ne coûte ni argent ni effet de bord.
    rate_limit=RateLimit(per_turn=2, per_day=200),
    egress=None,
)


async def _execute(resolved: dict, ctx: ToolContext) -> ToolResult:
    """Aucun `resolve` : l'outil ne prend aucun argument, il n'y a rien à figer ni à confirmer.

    Une erreur d'accès au vault remonte en `ToolError` — donc en `{"error": …}` explicite côté
    modèle. Renvoyer une liste vide sur un vault illisible lui ferait conclure « tu n'as aucun
    document » et créer un doublon : exactement le défaut que cet outil corrige (leçon SearXNG).
    """
    try:
        docs = await journal_vault.list_documents()
    except journal_vault.VaultError as exc:
        raise ToolError(f"lecture impossible de la base de connaissance : {exc}") from exc
    except OSError as exc:
        raise ToolError(f"base de connaissance inaccessible : {exc}") from exc

    total = len(docs)
    tronque = total > MAX_DOCUMENTS
    docs = docs[:MAX_DOCUMENTS]

    logger.info("list_documents: %d document(s) (tronqué=%s)", total, tronque)

    if not docs:
        return ToolResult(payload={
            "documents": [],
            "note": "Aucun document nommé n'existe encore. Le premier que tu écriras sera créé.",
        })

    payload = {
        "documents": [
            {"nom": d.title, "chemin": d.relative_path, "lignes": d.lines} for d in docs
        ],
        "note": "Pour écrire dans l'un d'eux, rappelle `capture_note` avec `mode=document` et "
                "**exactement** le `nom` ci-dessus. N'en crée un nouveau que si aucun ne "
                "correspond.",
    }
    if tronque:
        payload["avertissement"] = (
            f"{total} documents au total, seuls les {MAX_DOCUMENTS} premiers sont listés."
        )
    return ToolResult(payload=payload)


SPEC = ToolSpec(manifest=MANIFEST, execute=_execute)
