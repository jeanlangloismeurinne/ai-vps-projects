#!/usr/bin/env python3
"""
Générateur d'UPDATE ciblé des prompts durcis (2026-08-30) — research/bull/bear.

Réutilise la logique d'assemblage de `_gen_025.py` (préambule commun + corps, frontmatter retiré)
pour garantir que le `prompt_text` poussé en DB est IDENTIQUE au commit (règle #19, DB = 3ᵉ point de
synchro). N'émet un UPDATE que pour les 3 agents modifiés — ne touche pas les 9 autres.

Motif : le bear-agent laissait `reverse_dcf.croissance_implicite_prix_actuel_pct` à `null` (constaté
en base, analyses #2/#3) alors que le bull le remplissait. Étape 1 « durcir le prompt d'abord ».

Usage :  python _gen_prompt_refresh_20260830.py > refresh_prompts_20260830.sql
"""
from __future__ import annotations

from _gen_025 import PROMPTS, build_prompt, sql_quote, strip_frontmatter

TARGETS: list[tuple[str, str]] = [
    ("30-research-agent.md", "research-agent"),
    ("40-bull-agent.md", "bull-agent"),
    ("41-bear-agent.md", "bear-agent"),
]


def main() -> None:
    preamble = strip_frontmatter((PROMPTS / "00-preambule-commun.md").read_text())
    print("-- Refresh prompts durcis 2026-08-30 (research/bull/bear) — généré, ne pas éditer à la main")
    print("BEGIN;")
    for fname, agent_name in TARGETS:
        body = strip_frontmatter((PROMPTS / fname).read_text())
        prompt = build_prompt(preamble, body)
        print(
            f"UPDATE agent_prompts SET prompt_text={sql_quote(prompt)}, updated_at=NOW() "
            f"WHERE agent_name={sql_quote(agent_name)} AND flow_version='v2';"
        )
    print("COMMIT;")


if __name__ == "__main__":
    main()
