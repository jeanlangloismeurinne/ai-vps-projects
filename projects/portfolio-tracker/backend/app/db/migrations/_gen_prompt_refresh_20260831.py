#!/usr/bin/env python3
"""
Générateur d'UPDATE ciblé des prompts (2026-08-31) — bull/bear (dette B) + curator (dette A).

Réutilise l'assemblage de `_gen_025.py` (préambule commun + corps, frontmatter retiré) pour garantir
que le `prompt_text` poussé en DB est IDENTIQUE au commit (règle #19, la DB est le 3ᵉ point de
synchro). N'émet un UPDATE que pour les 3 agents modifiés — ne touche pas les 9 autres.

Motifs :
  • bull/bear — `assumptions` portait `croissance_revenue` / `expansion_marge_fcf` sans unité dans le
    nom : bull a rendu 0.15 (fraction) quand bear rendait 8.0 (pourcent) pour la même grandeur,
    facteur ~53, muet parce que les deux sont des `float` valides. Renommés `*_pct`, avec la consigne
    explicite « 12 %/an s'écrit 12.0, jamais 0.12 ».
  • curator — l'exemple de `rationale` du prompt NOMMAIT lui-même un verdict
    (« … → thin_qualitative »), ce que le modèle a imité : rapport #24, verdict `ready` et prose
    narrant `thin_qualitative`, sur un ordre de tiers inversé. L'exemple est corrigé et un garde-fou
    interdit désormais de nommer un verdict dans le rationale (le code le retire de toute façon).

Usage :  python _gen_prompt_refresh_20260831.py > refresh_prompts_20260831.sql
"""
from __future__ import annotations

from _gen_025 import PROMPTS, build_prompt, sql_quote, strip_frontmatter

TARGETS: list[tuple[str, str]] = [
    ("40-bull-agent.md", "bull-agent"),
    ("41-bear-agent.md", "bear-agent"),
    ("20-knowledge-curator.md", "knowledge-curator"),
]


def main() -> None:
    preamble = strip_frontmatter((PROMPTS / "00-preambule-commun.md").read_text())
    print("-- Refresh prompts 2026-08-31 (bull/bear _pct + curator rationale) — généré, ne pas éditer")
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
