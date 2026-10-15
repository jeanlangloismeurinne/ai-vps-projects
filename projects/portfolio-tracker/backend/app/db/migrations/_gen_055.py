#!/usr/bin/env python3
"""
Générateur de la migration 055 — les EXTRAITS LITTÉRAUX d'une fiche (#126, arbitrage du 2026-10-15),
dans l'exemple de sortie des prompts `ingestion-agent` et `search-worker`.

`ProducedEntry` porte désormais `extraits` (REQUIS) : les passages du document, recopiés mot pour mot,
que le serveur vérifie contre le texte réellement rapporté par les outils. L'exemple JSON d'un prompt est
une pièce du contrat (#39/#121) : sans la clef, le modèle suivrait l'exemple et chaque fiche serait
refusée. Même forme que la 054, dont le récit suit.

--- Récit de la 054 (forme reprise telle quelle) :
Resynchronisation sur la DATATION de la 045 (#79), constatée manquante le 2026-10-13 (#121).

La panne de la 037, rejouée un cran plus loin. La 045 a retiré `source_date` du contrat d'entry
(`ProducedEntry`, `extra="forbid"`) et l'a remplacé par `portee_temporelle` + deux dates ; la règle de
datation a été ajoutée en SUFFIXE DE CODE (`worker.py`, `_CLOSING_INSTRUCTION`), mais l'exemple JSON des
deux prompts en base portait encore `"source_date"` — et ces prompts disent « aucune clef hors de
l'exemple ». Sur les longs passages, le modèle obéit à l'exemple : 15 mandats `echec_collecte` sur ce
motif du 2026-09-25 au 2026-10-13, dont NVDA qf_8 (mandats 2612/2613, la conformité aux clauses au
26/07 jamais collectée). Garde de régression : `checks/check_prompts_exemples.py` (fichier ET base).

Comme la 037, elle ne retape aucun prompt : elle relit les fichiers committés et pousse le texte
assemblé (la base était, avant elle, le miroir exact du commit précédent — vérifié le 2026-10-13).

Usage :  python _gen_055.py > 055_v3_prompt_extraits_litteraux.sql
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
REQUIS = '"extraits":'


def main() -> None:
    preamble = strip_frontmatter((PROMPTS / "00-preambule-commun.md").read_text())
    textes: list[tuple[str, str]] = []
    for fname, agent in TARGETS:
        prompt = build_prompt(preamble, strip_frontmatter((PROMPTS / fname).read_text()))
        if INTERDIT in prompt or REQUIS not in prompt:
            raise SystemExit(
                f"{fname} : exemple sans extraits littéraux ({INTERDIT} présent ou {REQUIS} absent). "
                "Corriger le fichier, pas la migration.")
        textes.append((agent, prompt))

    print("-- Migration 055 — prompts ingestion-agent / search-worker : les extraits littéraux d'une")
    print("-- fiche (#126), dans l'exemple de sortie et dans la règle (règle #19/#39/#121).")
    print("-- Généré par _gen_055.py — ne pas éditer à la main.")
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
    print(f"    '055/K : % prompt(s) v2 resynchronisé(s) sur {len(TARGETS)} — exemple sans extraits littéraux', n;")
    print("  END IF;")
    print("END $$;")
    print("COMMIT;")


if __name__ == "__main__":
    main()
