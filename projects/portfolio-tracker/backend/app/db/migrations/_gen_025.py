#!/usr/bin/env python3
"""
Générateur reproductible de la migration 025 (agents V2 / provider).

Lit les prompts figés (`roadmap/provenance-cards/prompts/`), assemble « préambule commun + corps »
pour chaque agent, et émet le SQL des INSERT dans `agent_prompts` (flow_version='v2'). Évite le
copier-coller manuel de 12 gros prompts et garantit que la DB = 3ᵉ point de synchro (règle #19) des
prompts committés.

Usage :  python _gen_025.py > 025_v2_agents_provider.sql
(exécuté depuis backend/app/db/migrations/ ; chemins calculés depuis __file__)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
# backend/app/db/migrations -> remonte à la racine projet portfolio-tracker
PROJECT_ROOT = HERE.parents[3]
PROMPTS = PROJECT_ROOT / "roadmap" / "provenance-cards" / "prompts"

MODEL_V2 = "deepseek-ai/DeepSeek-V4-Flash-0731"

# fichier prompt -> agent_name (roster README.md)
AGENTS: list[tuple[str, str]] = [
    ("10-ingestion-agent.md", "ingestion-agent"),
    ("11-search-worker.md", "search-worker"),
    ("12-gap-intake.md", "gap-intake"),
    ("13-groundedness-checker.md", "groundedness-checker"),
    ("20-knowledge-curator.md", "knowledge-curator"),
    ("30-research-agent.md", "research-agent"),
    ("40-bull-agent.md", "bull-agent"),
    ("41-bear-agent.md", "bear-agent"),
    ("50-thesis-agent-synthese.md", "thesis-agent"),
    ("60-debate-agent.md", "debate-agent"),
    ("70-monitoring-agent.md", "monitoring-agent"),
    ("80-postmortem-agent.md", "postmortem-agent"),
]

# tools_json (schémas OpenAI) — uniquement search-worker (seul agent en tool-calling natif).
SEARCH_WORKER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Recherche web (SearXNG/API) pour trouver des sources sur une requête ciblée.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Requête de recherche ciblée."},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Récupère le contenu texte d'une URL (page IR, communiqué, article).",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL à récupérer."}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge",
            "description": "Interroge la base knowledge_entries existante (anti-doublon avant store).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker_id": {"type": "string"},
                    "query": {"type": "string"},
                    "min_reliability": {"type": "number", "default": 0.0},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        },
    },
]

TOOLS_BY_AGENT: dict[str, list] = {"search-worker": SEARCH_WORKER_TOOLS}


def strip_frontmatter(text: str) -> str:
    """Retire le bloc YAML `--- … ---` en tête s'il existe."""
    if text.startswith("---"):
        m = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
        if m:
            return text[m.end():]
    return text.strip("\n")


def sql_quote(s: str) -> str:
    """Littéral SQL simple-quoté avec échappement des quotes internes."""
    return "'" + s.replace("'", "''") + "'"


def build_prompt(preamble: str, body: str) -> str:
    return f"{preamble.strip()}\n\n{body.strip()}\n"


def main() -> None:
    preamble = strip_frontmatter((PROMPTS / "00-preambule-commun.md").read_text())

    lines: list[str] = []
    lines.append("-- ── INSERT des 12 agents V2 (généré par _gen_025.py — ne pas éditer à la main) ──")
    lines.append(
        "INSERT INTO agent_prompts "
        "(agent_name, flow_version, provider, model, tools_json, prompt_text, synced) VALUES"
    )
    rows: list[str] = []
    for fname, agent_name in AGENTS:
        body = strip_frontmatter((PROMPTS / fname).read_text())
        prompt = build_prompt(preamble, body)
        tools = TOOLS_BY_AGENT.get(agent_name)
        tools_sql = "NULL::jsonb" if tools is None else sql_quote(json.dumps(tools, ensure_ascii=False)) + "::jsonb"
        rows.append(
            f"  ({sql_quote(agent_name)}, 'v2', 'deepinfra', {sql_quote(MODEL_V2)}, "
            f"{tools_sql}, {sql_quote(prompt)}, TRUE)"
        )
    lines.append(",\n".join(rows))
    lines.append(
        "ON CONFLICT (agent_name, flow_version) DO UPDATE SET "
        "provider=EXCLUDED.provider, model=EXCLUDED.model, tools_json=EXCLUDED.tools_json, "
        "prompt_text=EXCLUDED.prompt_text, updated_at=NOW();"
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
