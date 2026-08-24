"""
Client DeepInfra pour assistant-ia — endpoint OpenAI-compatible.

Porté depuis projects/portfolio-tracker/backend/app/agents/providers/deepinfra_provider.py
(pas d'import inter-projets : copie adaptée, interface simplifiée).

Interface publique :
  - chat(messages, model, temperature, max_tokens) → str
  - chat_json(messages, model, schema) → dict

Règles de robustesse :
  - Timeout explicite (TIMEOUT_S).
  - 1 retry automatique sur erreur réseau ou 5xx ; jamais de retry sur 4xx.
  - Aucun secret loggé : on logue le code HTTP et la raison, jamais le payload ni la clé.
  - DEEPINFRA_API_KEY vide → RuntimeError à l'appel, pas à l'import (le démarrage de l'app
    ne doit jamais casser).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Timeout total par requête (secondes). Peut être surchargé paramètre par paramètre.
TIMEOUT_S: int = 120

# Nombre de retries sur erreur réseau / 5xx (jamais sur 4xx).
_MAX_RETRIES: int = 1


def _get_headers() -> dict[str, str]:
    """Construit les headers d'authentification.

    Lève RuntimeError si la clé est absente — à l'appel, pas à l'import.
    """
    key = settings.DEEPINFRA_API_KEY
    if not key:
        raise RuntimeError(
            "DEEPINFRA_API_KEY est vide — configure-la dans les variables d'env Coolify "
            "avant d'appeler un service DeepInfra."
        )
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _endpoint() -> str:
    base = (settings.DEEPINFRA_API_BASE or "https://api.deepinfra.com/v1/openai").rstrip("/")
    return f"{base}/chat/completions"


async def _post_with_retry(
    payload: dict[str, Any],
    timeout: int = TIMEOUT_S,
) -> dict[str, Any]:
    """POST vers /chat/completions avec 1 retry sur réseau/5xx.

    4xx → propagé immédiatement sans retry.
    Ne logue jamais le payload ni la clé.
    """
    url = _endpoint()
    last_exc: Optional[Exception] = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(url, headers=_get_headers(), json=payload)

            if r.status_code >= 500:
                logger.error(
                    "DeepInfra %s (attempt %d/%d): %s",
                    r.status_code, attempt + 1, _MAX_RETRIES + 1,
                    r.reason_phrase,
                )
                if attempt < _MAX_RETRIES:
                    last_exc = httpx.HTTPStatusError(
                        f"HTTP {r.status_code}", request=r.request, response=r
                    )
                    continue
                r.raise_for_status()

            if r.status_code >= 400:
                # 4xx : pas de retry — logue et lève immédiatement.
                logger.error(
                    "DeepInfra %s (4xx, no retry): %s",
                    r.status_code,
                    r.reason_phrase,
                )
                r.raise_for_status()

            return r.json()

        except httpx.TimeoutException as exc:
            logger.error(
                "DeepInfra timeout (attempt %d/%d)", attempt + 1, _MAX_RETRIES + 1
            )
            last_exc = exc
            if attempt < _MAX_RETRIES:
                continue
            raise RuntimeError(
                "DeepInfra n'a pas répondu dans le délai imparti — tu peux relancer."
            ) from exc

        except httpx.HTTPStatusError:
            raise

        except httpx.RequestError as exc:
            logger.error(
                "DeepInfra réseau (attempt %d/%d): %s",
                attempt + 1, _MAX_RETRIES + 1,
                type(exc).__name__,
            )
            last_exc = exc
            if attempt < _MAX_RETRIES:
                continue
            raise RuntimeError(
                "DeepInfra : erreur réseau après retry — tu peux relancer."
            ) from exc

    # Ne devrait pas être atteint, mais satisfait mypy.
    raise RuntimeError("DeepInfra : échec inattendu après retry.") from last_exc


async def chat(
    messages: list[dict[str, Any]],
    model: str,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    timeout: int = TIMEOUT_S,
) -> str:
    """Appel texte simple vers DeepInfra.

    Args:
        messages: Liste de messages OpenAI-compat (role + content).
        model: Identifiant du modèle DeepInfra (ex: settings.DEEPINFRA_MODEL_CLASSIF).
        temperature: Température de sampling.
        max_tokens: Limite de tokens en sortie (None = défaut du modèle).
        timeout: Timeout total en secondes.

    Returns:
        Contenu texte du premier choix.

    Raises:
        RuntimeError: Clé manquante, timeout, ou erreur HTTP non récupérable.
    """
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    data = await _post_with_retry(payload, timeout=timeout)

    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""

    usage = data.get("usage") or {}
    logger.debug(
        "DeepInfra chat — model=%s tokens_in=%s tokens_out=%s",
        data.get("model", model),
        usage.get("prompt_tokens", "?"),
        usage.get("completion_tokens", "?"),
    )

    return content


async def chat_json(
    messages: list[dict[str, Any]],
    model: str,
    schema: dict[str, Any],
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    timeout: int = TIMEOUT_S,
) -> dict[str, Any]:
    """Appel JSON structuré vers DeepInfra.

    Stratégie en deux temps :
    1. Tente `response_format={"type": "json_schema", ...}` (meilleure contrainte structurelle).
    2. Si le modèle renvoie 4xx (json_schema non supporté), retombe automatiquement sur
       `response_format={"type": "json_object"}` — le prompt suffit à guider la structure.

    La sortie est toujours validée côté Python (json.loads + vérif des clés required)
    car `strict` n'est pas garanti sur tous les modèles.

    Args:
        messages: Liste de messages OpenAI-compat.
        model: Identifiant du modèle DeepInfra.
        schema: Schéma JSON Schema décrivant l'objet attendu en sortie.
            Doit contenir au moins {"type": "object", "properties": {...}}.
            Les champs "required" et "title" sont utilisés pour la validation et le naming.
        temperature: Température de sampling (faible par défaut pour la génération JSON).
        max_tokens: Limite de tokens en sortie.
        timeout: Timeout total en secondes.

    Returns:
        Dict Python parsé et validé (clés de premier niveau).

    Raises:
        RuntimeError: Clé manquante, timeout, ou erreur HTTP non récupérable.
        ValueError: Sortie non parsable ou clés obligatoires manquantes.
    """
    schema_name = schema.get("title") or "response"

    def _base_payload(response_format: dict[str, Any]) -> dict[str, Any]:
        p: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "response_format": response_format,
        }
        if max_tokens is not None:
            p["max_tokens"] = max_tokens
        return p

    # Tentative 1 : json_schema (supporté par DeepSeek V4 et d'autres modèles récents).
    payload_schema = _base_payload({
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "schema": schema,
            "strict": True,
        },
    })

    data: Optional[dict[str, Any]] = None
    try:
        data = await _post_with_retry(payload_schema, timeout=timeout)
    except httpx.HTTPStatusError as exc:
        # 4xx : json_schema non supporté par ce modèle → fallback json_object.
        status = exc.response.status_code
        if 400 <= status < 500:
            logger.info(
                "DeepInfra chat_json : json_schema non supporté par %s (HTTP %s) "
                "— fallback json_object",
                model, status,
            )
            payload_obj = _base_payload({"type": "json_object"})
            data = await _post_with_retry(payload_obj, timeout=timeout)
        else:
            raise RuntimeError(
                f"DeepInfra chat_json : erreur HTTP {status} non récupérable."
            ) from exc

    assert data is not None  # toujours vrai ici

    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    raw_content = msg.get("content") or ""

    # Parsing JSON — erreur explicite si le modèle n'a pas respecté le format.
    try:
        result: dict[str, Any] = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"DeepInfra chat_json : la sortie n'est pas du JSON valide "
            f"(modèle={model}, début='{raw_content[:120]}')"
        ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            f"DeepInfra chat_json : attendu un objet JSON, reçu {type(result).__name__}"
        )

    # Validation des clés de premier niveau déclarées dans le schéma.
    required_keys: list[str] = schema.get("required") or []
    missing = [k for k in required_keys if k not in result]
    if missing:
        raise ValueError(
            f"DeepInfra chat_json : clés obligatoires manquantes dans la réponse : "
            f"{missing} (modèle={model})"
        )

    usage = data.get("usage") or {}
    logger.debug(
        "DeepInfra chat_json — model=%s tokens_in=%s tokens_out=%s",
        data.get("model", model),
        usage.get("prompt_tokens", "?"),
        usage.get("completion_tokens", "?"),
    )

    return result
