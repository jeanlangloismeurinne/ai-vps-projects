#!/usr/bin/env python3
"""
Générateur de la migration 054 — resynchronisation des prompts `ingestion-agent` et `search-worker`
sur la DATATION de la 045 (#79), constatée manquante le 2026-10-13 (#121).

La panne de la 037, rejouée un cran plus loin. La 045 a retiré `source_date` du contrat d'entry
(`ProducedEntry`, `extra="forbid"`) et l'a remplacé par `portee_temporelle` + deux dates ; la règle de
datation a été ajoutée en SUFFIXE DE CODE (`worker.py`, `_CLOSING_INSTRUCTION`), mais l'exemple JSON des
deux prompts en base portait encore `"source_date"` — et ces prompts disent « aucune clef hors de
l'exemple ». Sur les longs passages, le modèle obéit à l'exemple : 15 mandats `echec_collecte` sur ce
motif du 2026-09-25 au 2026-10-13, dont NVDA qf_8 (mandats 2612/2613, la conformité aux clauses au
26/07 jamais collectée). Garde de régression : `checks/check_prompts_exemples.py` (fichier ET base).

Comme la 037, elle ne retape aucun prompt : elle relit les fichiers committés et pousse le texte
assemblé (la base était, avant elle, le miroir exact du commit précédent — vérifié le 2026-10-13).

Usage :  python _gen_054.py > 054_v3_prompt_sync_datation.sql
"""
from __future__ import annotations

from _gen_025 import PROMPTS, build_prompt, sql_quote, strip_frontmatter

TARGETS: list[tuple[str, str]] = [
    ("10-ingestion-agent.md", "ingestion-agent"),
    ("11-search-worker.md", "search-worker"),
]

# Forme d'ÉMISSION (guillemets + deux-points), jamais le mot : les prompts corrigés PARLENT de
# `source_date` (« plus de `source_date` non plus ») — `feedback_grep_interdit_lit_sa_propre_enonciation`.
INTERDIT = '"source_date":'
REQUIS = '"portee_temporelle":'


def main() -> None:
    preamble = strip_frontmatter((PROMPTS / "00-preambule-commun.md").read_text())
    textes: list[tuple[str, str]] = []
    for fname, agent in TARGETS:
        prompt = build_prompt(preamble, strip_frontmatter((PROMPTS / fname).read_text()))
        if INTERDIT in prompt or REQUIS not in prompt:
            raise SystemExit(
                f"{fname} : exemple encore à l'ancienne datation ({INTERDIT} présent ou {REQUIS} absent). "
                "Corriger le fichier, pas la migration.")
        textes.append((agent, prompt))

    print("-- Migration 054 — resynchro des prompts ingestion-agent / search-worker sur la datation")
    print("-- de la 045 (#79) : l'exemple JSON portait encore `source_date` (#121, règle #19).")
    print("-- Généré par _gen_054.py — ne pas éditer à la main.")
    print("BEGIN;")
    for agent, prompt in textes:
        print(
            f"UPDATE agent_prompts SET prompt_text={sql_quote(prompt)}, "
            f"version = version + 1, synced = false, updated_at = NOW() "
            f"WHERE agent_name={sql_quote(agent)} AND flow_version='v2';"
        )
    noms = ", ".join(sql_quote(agent) for _, agent in TARGETS)
    lit_i = INTERDIT.replace("_", "\\_")
    lit_r = REQUIS.replace("_", "\\_")
    # K1 — l'UPDATE a mordu ; K2 — le texte EN BASE (point de lecture de l'agent) ne porte plus
    # l'ancienne clef et porte la nouvelle.
    print("DO $$ DECLARE n integer; BEGIN")
    print(f"  SELECT count(*) INTO n FROM agent_prompts WHERE agent_name IN ({noms}) AND flow_version = 'v2'")
    print(f"     AND prompt_text NOT LIKE '%{lit_i}%' ESCAPE '\\' AND prompt_text LIKE '%{lit_r}%' ESCAPE '\\';")
    print(f"  IF n <> {len(TARGETS)} THEN RAISE EXCEPTION")
    print(f"    '054/K : % prompt(s) v2 resynchronisé(s) sur {len(TARGETS)} — exemple encore à l''ancienne datation', n;")
    print("  END IF;")
    print("END $$;")
    print("COMMIT;")


if __name__ == "__main__":
    main()
