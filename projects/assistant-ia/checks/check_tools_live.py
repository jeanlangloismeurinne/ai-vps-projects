"""Vérification LIVE du support `tools` de DeepInfra — appel réel (#1787579840501).

À exécuter dans le container de production (la clé DeepInfra n'est pas sur l'hôte) :

    docker exec -w /app -e PYTHONPATH=/app <container> python checks/check_tools_live.py

Ce check est **bloquant pour tout le chantier `agent-outillage`** : la roadmap suppose une
boucle de tool-calling. Si le modèle de conversation ne supporte pas `tools`, ce n'est pas un
détail d'implémentation — c'est l'ordre des tickets qui change.

Pourquoi il existe : précédent exact sur ce projet, DeepInfra a renvoyé **HTTP 405 sur
`response_format: json_schema`** pour Llama 3.1 8B-Turbo. Le code partait en fallback silencieux
et le défaut n'a été trouvé qu'en testant contre l'API réelle (commit `a574a75`).

Volontairement écrit en `httpx` brut, sans passer par `deepinfra_client` : ce check doit pouvoir
tourner **avant** que le support `tools` soit ajouté au client (#1787579840502), et il vérifie le
contrat de l'API, pas notre couche.

Les 4 assertions du ticket :
  1. un appel avec un outil déclaré ne renvoie pas d'erreur HTTP ;
  2. une question qui appelle clairement l'outil produit un `tool_calls` aux arguments parsables ;
  3. une question qui ne l'appelle pas produit du texte, sans `tool_calls` fantôme ;
  4. la réinjection d'un `role=tool` est acceptée et donne une réponse finale.
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402

# Outil factice, volontairement sans rapport avec le catalogue réel : on teste le protocole de
# l'API, pas la pertinence d'un outil du projet.
TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Donne la météo actuelle d'une ville.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Nom de la ville"},
            },
            "required": ["city"],
            "additionalProperties": False,
        },
    },
}


async def _post(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """POST brut vers /chat/completions. Renvoie (status, json) sans jamais lever."""
    base = (settings.DEEPINFRA_API_BASE or "https://api.deepinfra.com/v1/openai").rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.DEEPINFRA_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{base}/chat/completions", headers=headers, json=payload)
    try:
        body = r.json()
    except ValueError:
        body = {"_raw": r.text[:500]}
    return r.status_code, body


def _message(body: dict[str, Any]) -> dict[str, Any]:
    return ((body.get("choices") or [{}])[0].get("message")) or {}


async def main() -> int:
    model = settings.DEEPINFRA_MODEL_CHAT
    print(f"modèle : {model}\nendpoint : {settings.DEEPINFRA_API_BASE}\n")

    if not settings.DEEPINFRA_API_KEY:
        print("ECHEC — DEEPINFRA_API_KEY vide : ce check doit tourner dans le container.")
        return 1

    echecs: list[str] = []

    # ── 1 & 2. Question qui appelle clairement l'outil ────────────────────────
    print("--- 1+2. appel attendu de l'outil ---")
    status, body = await _post({
        "model": model,
        "messages": [
            {"role": "system", "content": "Tu utilises les outils disponibles quand c'est pertinent."},
            {"role": "user", "content": "Quel temps fait-il à Lyon en ce moment ?"},
        ],
        "tools": [TOOL],
        "tool_choice": "auto",
        "temperature": 0.1,
    })
    print(f"  HTTP {status}")
    tool_calls: list[dict[str, Any]] = []
    if status >= 400:
        # C'est exactement le mode de défaillance du précédent 405 : on l'affiche en clair.
        echecs.append(f"appel avec `tools` refusé : HTTP {status} — {json.dumps(body)[:300]}")
    else:
        msg = _message(body)
        tool_calls = msg.get("tool_calls") or []
        print(f"  tool_calls={len(tool_calls)}  content={(msg.get('content') or '')[:80]!r}")
        if not tool_calls:
            echecs.append("aucun `tool_calls` sur une question qui appelle clairement l'outil")
        else:
            tc = tool_calls[0]
            fn = tc.get("function") or {}
            print(f"  name={fn.get('name')!r}  arguments={fn.get('arguments')!r}  id={tc.get('id')!r}")
            if fn.get("name") != "get_weather":
                echecs.append(f"outil appelé inattendu : {fn.get('name')!r}")
            if not tc.get("id"):
                echecs.append("`tool_calls[].id` absent — impossible de rattacher le `role=tool`")
            try:
                args = json.loads(fn.get("arguments") or "")
                if not isinstance(args, dict) or "city" not in args:
                    echecs.append(f"arguments sans la clé `city` : {args!r}")
            except (json.JSONDecodeError, TypeError):
                echecs.append(f"arguments non parsables en JSON : {fn.get('arguments')!r}")

    # ── 3. Question sans rapport : aucun tool_call fantôme ────────────────────
    print("\n--- 3. pas de tool_call fantôme ---")
    status3, body3 = await _post({
        "model": model,
        "messages": [
            {"role": "system", "content": "Tu utilises les outils disponibles quand c'est pertinent."},
            {"role": "user", "content": "Explique-moi en une phrase ce qu'est un nombre premier."},
        ],
        "tools": [TOOL],
        "tool_choice": "auto",
        "temperature": 0.1,
    })
    print(f"  HTTP {status3}")
    if status3 >= 400:
        echecs.append(f"appel #3 refusé : HTTP {status3}")
    else:
        msg3 = _message(body3)
        fantomes = msg3.get("tool_calls") or []
        content3 = (msg3.get("content") or "").strip()
        print(f"  tool_calls={len(fantomes)}  content={content3[:100]!r}")
        if fantomes:
            echecs.append(
                f"tool_call fantôme sur une question hors sujet : "
                f"{[(c.get('function') or {}).get('name') for c in fantomes]}"
            )
        if not content3:
            echecs.append("réponse texte vide sur une question qui n'appelle aucun outil")

    # ── 4. Réinjection d'un role=tool ────────────────────────────────────────
    print("\n--- 4. réinjection role=tool ---")
    if not tool_calls:
        echecs.append("réinjection non testée : aucun tool_call obtenu à l'étape 2")
    else:
        tc = tool_calls[0]
        status4, body4 = await _post({
            "model": model,
            "messages": [
                {"role": "system", "content": "Tu utilises les outils disponibles quand c'est pertinent."},
                {"role": "user", "content": "Quel temps fait-il à Lyon en ce moment ?"},
                # Le message assistant doit être réinjecté verbatim, tool_calls compris.
                {
                    "role": "assistant",
                    "content": _message(body).get("content") or "",
                    "tool_calls": tool_calls,
                },
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "content": json.dumps({"city": "Lyon", "temp_c": 21, "sky": "ensoleillé"}),
                },
            ],
            "tools": [TOOL],
            "temperature": 0.1,
        })
        print(f"  HTTP {status4}")
        if status4 >= 400:
            echecs.append(
                f"réinjection `role=tool` refusée : HTTP {status4} — {json.dumps(body4)[:300]}"
            )
        else:
            msg4 = _message(body4)
            final = (msg4.get("content") or "").strip()
            print(f"  réponse finale={final[:160]!r}")
            if not final:
                echecs.append("réponse finale vide après réinjection du résultat d'outil")
            elif "21" not in final:
                # Non bloquant en soi, mais si le modèle ignore le résultat réinjecté, la boucle
                # ne sert à rien. On le signale comme échec : c'est le point du ticket.
                echecs.append(
                    f"la réponse finale n'exploite pas le résultat d'outil (attendu « 21 ») : {final[:120]!r}"
                )

    print("\n" + "=" * 60)
    if echecs:
        print(f"ECHEC — {len(echecs)} assertion(s) :")
        for e in echecs:
            print(f"  ✗ {e}")
        print(
            "\nNe pas contourner par un fallback silencieux (c'est l'erreur du précédent 405) :\n"
            "documenter et remonter le choix du modèle en décision de roadmap."
        )
        return 1
    print(f"OK — {model} accepte `tools`, émet des tool_calls parsables, n'en invente pas,")
    print("     et exploite un résultat réinjecté en `role=tool`.")
    return 0


sys.exit(asyncio.run(main()))
