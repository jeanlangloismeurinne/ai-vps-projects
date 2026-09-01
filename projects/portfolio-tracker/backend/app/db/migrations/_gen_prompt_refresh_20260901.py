#!/usr/bin/env python3
"""
Générateur de la migration 033 — resynchronisation du prompt `debate-agent` (2026-09-01).

Réutilise l'assemblage de `_gen_025.py` (préambule commun + corps, frontmatter retiré) pour garantir
que le `prompt_text` poussé en DB est IDENTIQUE au commit (règle #19, la DB est le 3ᵉ point de
synchro). N'émet un UPDATE que pour `debate-agent` — ne touche pas les 11 autres.

Motif — désynchro trouvée au PREMIER appel réel du lot 9 (dry-run thèse #5), invisible hors ligne :
l'exemple JSON du prompt datait d'AVANT le figeage du Pydantic `ConvictionChallenge` et montrait
`"franchi": false` (booléen), `"observation_courante"`, et **aucun** `valeur_observee`. Le modèle a
recopié l'exemple ; les 3 hypothèses sont parties en `seuil_franchi=True/False` → 2 tentatives
refusées → HTTP 502.

Le vrai danger n'était pas le 502 (bruyant, donc bénin) mais ce qu'il masquait : `_forcer_seuils_figes`
ne dérive QUE si `h.get("valeur_observee") is not None`. Un prompt qui n'enseigne jamais ce champ
rend la dérivation **no-op silencieuse** — le garde-fou central du lot 9 (seuils figés en lecture
seule, franchissement recalculé) serait mort sans qu'aucun check hors ligne ne le voie, puisqu'ils
alimentent tous le pont avec des fixtures déjà conformes.

Correctif conforme à la règle « desserrage de schéma = trou silencieux » : on DURCIT le prompt (table
des champs + mention explicite que le système réécrit les seuils et redérive `seuil_franchi`, donc
sous-déclarer n'achète rien), on ne desserre PAS le contrat.

Usage :  python _gen_prompt_refresh_20260901.py > 033_v2_debate_prompt_sync.sql
"""
from __future__ import annotations

from _gen_025 import PROMPTS, build_prompt, sql_quote, strip_frontmatter

TARGETS: list[tuple[str, str]] = [
    ("60-debate-agent.md", "debate-agent"),
]


def main() -> None:
    preamble = strip_frontmatter((PROMPTS / "00-preambule-commun.md").read_text())
    print("-- Migration 033 — resynchro prompt debate-agent sur ConvictionChallenge (règle #19)")
    print("-- Généré par _gen_prompt_refresh_20260901.py — ne pas éditer à la main.")
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
