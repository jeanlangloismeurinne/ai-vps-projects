#!/usr/bin/env python3
"""
Générateur de la migration 057 — `fetch_url` apprend `chercher` : l'ouvrier peut dire ce qu'il
cherche DANS le document, dans les mots du document (règle 12 du prompt search-worker). Mesuré sur
la circulaire DEF 14A NVIDIA : la ligne d'actionnariat (« Jen-Hsun Huang … 870,604,104 … ») est
rang 126/288 sur le mandat complet, rang 4 sur le seul intitulé de section — une ligne de tableau
n'a presque aucune sémantique propre, son intitulé si. Deux pièces changent ensemble : le prompt
(règle 12) et `tools_json.fetch_url` (propriété `chercher`, facultative) — les resynchroniser
séparément laisserait l'une suivre l'autre sans garantie (#19).

Même forme que la 056 : relit les fichiers committés et pousse le texte/JSON assemblés.

Usage :  python _gen_057.py > 057_v3_fetch_url_chercher.sql
"""
from __future__ import annotations

import json

from _gen_025 import PROMPTS, SEARCH_WORKER_TOOLS, build_prompt, sql_quote, strip_frontmatter

FICHIER, AGENT = "11-search-worker.md", "search-worker"
REQUIS = "CHERCHER DANS UN LONG DOCUMENT"


def main() -> None:
    preamble = strip_frontmatter((PROMPTS / "00-preambule-commun.md").read_text())
    prompt = build_prompt(preamble, strip_frontmatter((PROMPTS / FICHIER).read_text()))
    if REQUIS not in prompt:
        raise SystemExit(f"{FICHIER} : règle 12 (chercher) absente. Corriger le fichier d'abord.")

    tools_sql = sql_quote(json.dumps(SEARCH_WORKER_TOOLS, ensure_ascii=False))
    fetch_url_tool = next(
        t for t in SEARCH_WORKER_TOOLS if t["function"]["name"] == "fetch_url"
    )
    if "chercher" not in fetch_url_tool["function"]["parameters"]["properties"]:
        raise SystemExit("SEARCH_WORKER_TOOLS.fetch_url : propriété 'chercher' absente. Corriger _gen_025.py.")
    if "chercher" in fetch_url_tool["function"]["parameters"].get("required", []):
        raise SystemExit("SEARCH_WORKER_TOOLS.fetch_url : 'chercher' doit rester FACULTATIF.")

    print("-- Migration 057 — prompt search-worker + tools_json : `fetch_url` apprend `chercher`")
    print("-- (règle 12, chercher dans un long document par ses propres mots). Généré par")
    print("-- _gen_057.py — ne pas éditer à la main.")
    print("BEGIN;")
    print(
        f"UPDATE agent_prompts SET prompt_text={sql_quote(prompt)}, "
        f"tools_json={tools_sql}::jsonb, "
        f"version = version + 1, synced = false, updated_at = NOW() "
        f"WHERE agent_name={sql_quote(AGENT)} AND flow_version='v2';"
    )
    print("DO $$ DECLARE n integer; BEGIN")
    print(f"  SELECT count(*) INTO n FROM agent_prompts WHERE agent_name = {sql_quote(AGENT)} AND flow_version = 'v2'")
    print(f"     AND prompt_text LIKE '%{REQUIS}%'")
    print("     AND tools_json::text LIKE '%chercher%';")
    print("  IF n <> 1 THEN RAISE EXCEPTION '057 : prompt/tools_json search-worker v2 non resynchronisé (%)', n; END IF;")
    print("END $$;")
    print("COMMIT;")


if __name__ == "__main__":
    main()
