#!/usr/bin/env python3
"""
Générateur de la migration 056 — prompt `search-worker` : la source d'origine d'abord (arbitrage du
2026-10-16, règle 11 du prompt). `web_search` rend désormais en tête les pages du site de l'émetteur,
marquées `site_emetteur: true` ; la consigne dit qu'un fait sur l'émetteur se cite sur sa page d'origine
et qu'une reprise ne se cite qu'à défaut. Cas : la prévision de NVIDIA (ma_5, plan #267) prise sur un
miroir brésilien alors que le communiqué est sur nvidia.com.

Même forme que la 055 : relit le fichier committé et pousse le texte assemblé.

Usage :  python _gen_056.py > 056_v3_prompt_source_origine.sql
"""
from __future__ import annotations

from _gen_025 import PROMPTS, build_prompt, sql_quote, strip_frontmatter

FICHIER, AGENT = "11-search-worker.md", "search-worker"
REQUIS = "`site_emetteur: true`"


def main() -> None:
    preamble = strip_frontmatter((PROMPTS / "00-preambule-commun.md").read_text())
    prompt = build_prompt(preamble, strip_frontmatter((PROMPTS / FICHIER).read_text()))
    if REQUIS not in prompt or '"extraits":' not in prompt:
        raise SystemExit(f"{FICHIER} : règle de la source d'origine ou extraits absents. Corriger le fichier.")
    lit = REQUIS.replace("_", "\\_")
    print("-- Migration 056 — prompt search-worker : la source d'origine d'abord (site de l'émetteur,")
    print("-- à défaut ailleurs), arbitrage du 2026-10-16. Généré par _gen_056.py — ne pas éditer à la main.")
    print("BEGIN;")
    print(
        f"UPDATE agent_prompts SET prompt_text={sql_quote(prompt)}, "
        f"version = version + 1, synced = false, updated_at = NOW() "
        f"WHERE agent_name={sql_quote(AGENT)} AND flow_version='v2';"
    )
    print("DO $$ DECLARE n integer; BEGIN")
    print(f"  SELECT count(*) INTO n FROM agent_prompts WHERE agent_name = {sql_quote(AGENT)} AND flow_version = 'v2'")
    print(f"     AND prompt_text LIKE '%{lit}%' ESCAPE '\\' AND prompt_text LIKE '%\"extraits\":%';")
    print("  IF n <> 1 THEN RAISE EXCEPTION '056/K : prompt search-worker v2 non resynchronisé (%)', n; END IF;")
    print("END $$;")
    print("COMMIT;")


if __name__ == "__main__":
    main()
