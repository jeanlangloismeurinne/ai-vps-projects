"""
Classifieur de la KB journal — ticket #1787559677485.

Responsabilité unique : prendre un texte libre (verbatim Slack) et produire les
métadonnées de classification {contexte, nature[], tags[], title}.

Règles invariantes :
- Le prompt est construit DEPUIS categories.schema.yaml au runtime (jamais recopié en dur).
- Appel unique DeepInfra (Llama 3.1 8B) : classification + title dans le même call.
- Température ≤ 0.2.
- Texte utilisateur passé en tant que DONNÉE délimitée, jamais en instruction.
- Validation stricte contre le vocabulaire du YAML — valeur hors vocab → rejet (pas correction).
- Fallback garanti : JSON invalide / API down / vocab violé → résultat « à classer »,
  aucune exception remontée vers l'appelant (on ne perd jamais une note utilisateur).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from app.config import settings
from app.services import deepinfra_client

logger = logging.getLogger(__name__)

# Chemin absolu du schema file (toujours résolu par rapport à ce module).
_SCHEMA_PATH = Path(__file__).parent.parent / "knowledge" / "categories.schema.yaml"

# Schéma JSON Schema pour la sortie du modèle.
_OUTPUT_JSON_SCHEMA: dict[str, Any] = {
    "title": "journal_classification",
    "type": "object",
    "properties": {
        "contexte": {
            "type": "string",
            "description": "Axe contexte — exactement une valeur du vocabulaire fermé.",
        },
        "nature": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Axe nature — une ou plusieurs valeurs du vocabulaire fermé.",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tags libres complémentaires — vocabulaire ouvert.",
        },
        "title": {
            "type": "string",
            "description": "Titre court (≤ 8 mots) résumant le sujet de l'entrée.",
        },
    },
    "required": ["contexte", "nature", "tags", "title"],
}

# Résultat de fallback « à classer » (aucune exception remontée vers l'appelant).
_FALLBACK_TAG = "a_classer"


@dataclass
class ClassificationResult:
    contexte: Optional[str]
    nature: Optional[list[str]]
    tags: list[str]
    title: str
    is_fallback: bool = False


# ---------------------------------------------------------------------------
# Chargement du schema file
# ---------------------------------------------------------------------------

def _load_schema() -> dict[str, Any]:
    """Charge categories.schema.yaml et renvoie le dict brut."""
    with open(_SCHEMA_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _extract_vocabulary(schema: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Extrait (contexte_values, nature_values) depuis le schema YAML."""
    axes = schema.get("axes", {})
    contexte_values: list[str] = axes.get("contexte", {}).get("values", [])
    nature_values: list[str] = axes.get("nature", {}).get("values", [])
    return contexte_values, nature_values


# ---------------------------------------------------------------------------
# Construction du prompt depuis le YAML (jamais en dur dans le code)
# ---------------------------------------------------------------------------

def _build_system_prompt(schema: dict[str, Any]) -> str:
    """Construit le prompt système à partir du schema YAML.

    Le vocabulaire est injecté directement depuis le fichier, jamais codé en dur.
    """
    axes = schema.get("axes", {})
    contexte_vals = axes.get("contexte", {}).get("values", [])
    contexte_desc = axes.get("contexte", {}).get("description", "")
    contexte_card = axes.get("contexte", {}).get("cardinality", "1")

    nature_vals = axes.get("nature", {}).get("values", [])
    nature_desc = axes.get("nature", {}).get("description", "")
    nature_card = axes.get("nature", {}).get("cardinality", "1..n")

    tags_desc = schema.get("tags_libres", {}).get("description", "")
    tags_card = schema.get("tags_libres", {}).get("cardinality", "0..n")
    tags_examples = schema.get("tags_libres", {}).get("examples", [])

    contexte_list = ", ".join(f'"{v}"' for v in contexte_vals)
    nature_list = ", ".join(f'"{v}"' for v in nature_vals)
    tags_ex_list = ", ".join(f'"{v}"' for v in tags_examples)

    return f"""Tu es un classificateur de notes personnelles. Tu produis UNIQUEMENT des métadonnées JSON, jamais de reformulation du texte.

## Taxonomie (source de vérité)

### axe contexte
Description : {contexte_desc}
Cardinalité : {contexte_card} (exactement une valeur)
Valeurs autorisées (FERMÉ) : [{contexte_list}]

### axe nature
Description : {nature_desc}
Cardinalité : {nature_card} (zéro, une ou plusieurs valeurs)
Valeurs autorisées (FERMÉ) : [{nature_list}]

### tags libres
Description : {tags_desc}
Cardinalité : {tags_card}
Exemples (non exhaustifs) : [{tags_ex_list}]
Remarque : le vocabulaire est ouvert — tu peux créer de nouveaux tags si pertinent.

## Règles strictes
1. `contexte` : exactement UNE valeur parmi les valeurs autorisées ci-dessus — aucune autre.
2. `nature` : zéro, une ou plusieurs valeurs parmi les valeurs autorisées ci-dessus — aucune autre.
   Si AUCUNE valeur du vocabulaire ne décrit correctement la note, renvoie `[]`. N'invente
   jamais une nature approximative pour remplir le champ : une liste vide est préférable.
3. `tags` : tableau libre (peut être vide []).
4. `title` : titre court en français (≤ 8 mots), résume le sujet principal. Jamais une reformulation du texte.
5. Tu ne reformules JAMAIS le texte de l'utilisateur. Tu ne produis QUE des métadonnées.
6. Réponds UNIQUEMENT avec un objet JSON valide, sans texte autour.

## Format de sortie attendu
{{
  "contexte": "<une valeur parmi {contexte_list}>",
  "nature": ["<zéro, une ou plusieurs valeurs parmi {nature_list}>"],
  "tags": ["<tags libres optionnels>"],
  "title": "<titre court>"
}}"""


def _build_user_message(text: str) -> str:
    """Encapsule le texte utilisateur comme DONNÉE délimitée (anti prompt-injection)."""
    return f"""Classifie la note suivante.

<note>
{text}
</note>

Réponds uniquement avec l'objet JSON demandé."""


# ---------------------------------------------------------------------------
# Validation du vocabulaire
# ---------------------------------------------------------------------------

def _validate_result(
    raw: dict[str, Any],
    contexte_vals: list[str],
    nature_vals: list[str],
) -> ClassificationResult:
    """Valide le résultat contre le vocabulaire du YAML.

    Lève ValueError si une valeur hors vocabulaire est détectée.
    Ne corrige jamais silencieusement.
    """
    # --- contexte ---
    contexte = raw.get("contexte")
    if not isinstance(contexte, str) or contexte not in contexte_vals:
        raise ValueError(
            f"Valeur hors vocabulaire pour 'contexte': {contexte!r} "
            f"— attendu l'une de {contexte_vals}"
        )

    # --- nature ---
    # 0..n : une liste vide est un résultat valide (aucune nature du vocabulaire ne convient).
    # C'est volontaire — voir le commentaire de cardinalité dans categories.schema.yaml.
    nature = raw.get("nature")
    if not isinstance(nature, list):
        raise ValueError(f"'nature' doit être une liste, reçu : {nature!r}")
    invalid_nature = [v for v in nature if v not in nature_vals]
    if invalid_nature:
        raise ValueError(
            f"Valeurs hors vocabulaire pour 'nature': {invalid_nature} "
            f"— attendu parmi {nature_vals}"
        )

    # --- tags (vocabulaire ouvert — pas de validation de valeur) ---
    tags = raw.get("tags")
    if not isinstance(tags, list):
        tags = []

    # --- title ---
    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"'title' doit être une chaîne non vide, reçu : {title!r}")

    return ClassificationResult(
        contexte=contexte,
        nature=nature,
        tags=tags,
        title=title.strip(),
        is_fallback=False,
    )


def _fallback_result(text: str) -> ClassificationResult:
    """Résultat de repli « à classer » — jamais d'exception vers l'appelant."""
    # Le title est un court extrait du texte original pour traçabilité.
    preview = text.strip()[:60].replace("\n", " ")
    if len(text.strip()) > 60:
        preview += "…"
    return ClassificationResult(
        contexte=None,
        nature=None,
        tags=[_FALLBACK_TAG],
        title=preview or "Note sans titre",
        is_fallback=True,
    )


# ---------------------------------------------------------------------------
# Interface publique
# ---------------------------------------------------------------------------

async def classify(text: str) -> ClassificationResult:
    """Classifie un texte libre et renvoie ses métadonnées.

    Garanties :
    - Ne lève jamais d'exception vers l'appelant.
    - En cas d'échec (API, JSON, vocab), renvoie un résultat is_fallback=True
      avec tags=["a_classer"] afin que la note soit quand même enregistrée.

    Args:
        text: Texte verbatim de l'utilisateur (message Slack ou autre).

    Returns:
        ClassificationResult avec is_fallback=False si la classification a réussi,
        is_fallback=True sinon.
    """
    if not text or not text.strip():
        logger.warning("journal_kb_classifier.classify : texte vide — fallback immédiat")
        return _fallback_result(text or "")

    # Chargement du schema (lecture disque légère — le fichier est petit)
    try:
        schema = _load_schema()
        contexte_vals, nature_vals = _extract_vocabulary(schema)
    except Exception as exc:
        logger.error("journal_kb_classifier : impossible de charger le schema YAML : %s", exc)
        return _fallback_result(text)

    system_prompt = _build_system_prompt(schema)
    user_message = _build_user_message(text)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # Tentative principale + 1 retry automatique du deepinfra_client.
    # En cas d'échec, on tente une seconde fois avec un prompt simplifié,
    # puis on bascule sur le fallback.
    for attempt in range(2):
        try:
            raw = await deepinfra_client.chat_json(
                messages=messages,
                model=settings.DEEPINFRA_MODEL_CLASSIF,
                schema=_OUTPUT_JSON_SCHEMA,
                temperature=0.15,  # ≤ 0.2 — classification déterministe
            )
            result = _validate_result(raw, contexte_vals, nature_vals)
            logger.info(
                "journal_kb_classifier : classification OK "
                "(contexte=%s, nature=%s, tags=%s, title=%r)",
                result.contexte, result.nature, result.tags, result.title,
            )
            return result

        except ValueError as exc:
            # JSON invalide ou vocabulaire violé.
            logger.warning(
                "journal_kb_classifier (attempt %d/2) : validation échouée — %s",
                attempt + 1, exc,
            )
            if attempt == 0:
                # Retry : on relance le même appel (le client a déjà fait son propre retry réseau).
                continue
            # Après 2 tentatives : fallback.
            logger.error(
                "journal_kb_classifier : fallback après 2 tentatives de validation"
            )
            return _fallback_result(text)

        except Exception as exc:
            # API indisponible, timeout, clé manquante, etc.
            logger.error(
                "journal_kb_classifier (attempt %d/2) : erreur API — %s: %s",
                attempt + 1, type(exc).__name__, exc,
            )
            if attempt == 0:
                continue
            return _fallback_result(text)

    # Sécurité (ne devrait pas être atteint).
    return _fallback_result(text)
