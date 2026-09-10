#!/usr/bin/env python3
"""
Générateur de la migration 037 — resynchronisation des prompts `ingestion-agent` et `search-worker`
sur le vocabulaire fermé de la 036 (2026-09-10).

POURQUOI ELLE N'EST PAS OPTIONNELLE
-----------------------------------
Un contrat d'entry a **trois** points de synchro (#39) : le CHECK SQL, le schéma Pydantic, et
**l'exemple JSON du prompt en base**. La 036 a fermé les deux premiers ; le troisième enseignait
encore l'ancien monde. Mesuré le 2026-09-10 :

  · `ingestion-agent` : « Tes `entry_type` autorisés sont uniquement : `fact_qualitative`, `event`,
    `quote`, `risk` » et un exemple portant `"entry_type": "risk"` — trois jetons que le CHECK
    refuse désormais ;
  · les deux prompts : un exemple portant `"covers"` et `"question_status"`, deux clefs que
    `ProducedEntry` (`extra="forbid"`) rejette désormais.

Le modèle recopie l'exemple. Sans la 037, **tout** ce que ces deux agents produisent est rejeté à la
validation : panne totale d'ingestion et de recherche, et invisible hors ligne — les fixtures des
checks sont déjà conformes au nouveau contrat, donc aucun check ne rougit. C'est la panne du lot 9
(033) rejouée un cran plus haut.

CE QUE LA 037 NE FAIT PAS
-------------------------
Elle ne touche PAS au concept d'ancrage probabiliste `base_rate{reference_class, taux}` des dix
autres prompts (règle 2 du préambule, bull/bear/thesis/debate/research/groundedness). Ce `base_rate`
est un CHAMP de contrat d'analyse ; seul l'`entry_type` homonyme a été renommé en `fact_statistical`.
Les confondre parce qu'ils s'écrivent pareil retirerait le garde-fou central de la règle 2.

Comme la 033, elle ne retape aucun prompt : elle relit les fichiers committés et pousse le texte
assemblé, pour que la DB soit un miroir du commit et non une troisième version.

Usage :  python _gen_037.py > 037_v2_prompt_sync_devocabularisation.sql
(exécuté depuis backend/app/db/migrations/ ; chemins calculés depuis __file__)
"""
from __future__ import annotations

from _gen_025 import PROMPTS, build_prompt, sql_quote, strip_frontmatter

TARGETS: list[tuple[str, str]] = [
    ("10-ingestion-agent.md", "ingestion-agent"),
    ("11-search-worker.md", "search-worker"),
]

# ⚠️ Les motifs sont cherchés sous leur forme d'ÉMISSION (`"covers":`, avec les guillemets et les
# deux-points), jamais sous leur forme de mot. Les prompts corrigés PARLENT de `covers` et de
# `question_status` — la nouvelle règle est précisément « plus de `covers` ni de `question_status` ».
# Un grep du simple mot rougirait sur l'énonciation de l'interdit : un faux ROUGE, qui pousse à
# retirer la phrase qui protège.  (`feedback_grep_interdit_lit_sa_propre_enonciation`)
MOTIFS_INTERDITS: list[tuple[str, str]] = [
    ('"covers":', "clef `covers` dans un exemple JSON"),
    ('"question_status":', "clef `question_status` dans un exemple JSON"),
    ('"entry_type": "risk"', "exemple typé sur un jeton retiré"),
    ('"entry_type": "quote"', "exemple typé sur un jeton retiré"),
    ('"entry_type": "event"', "exemple typé sur un jeton retiré"),
]


def main() -> None:
    preamble = strip_frontmatter((PROMPTS / "00-preambule-commun.md").read_text())

    # Garde à la GÉNÉRATION : si le fichier committé porte encore un motif retiré, la migration
    # pousserait le problème en base au lieu de le corriger. On lève ici, jamais on n'émet.
    textes: list[tuple[str, str]] = []
    for fname, agent in TARGETS:
        prompt = build_prompt(preamble, strip_frontmatter((PROMPTS / fname).read_text()))
        for motif, quoi in MOTIFS_INTERDITS:
            if motif in prompt:
                raise SystemExit(
                    f"{fname} porte encore {motif!r} ({quoi}). La 037 pousserait en base un prompt "
                    f"qui enseigne ce que le contrat refuse. Corriger le fichier, pas la migration.")
        textes.append((agent, prompt))

    print("-- Migration 037 — resynchro des prompts ingestion-agent / search-worker sur le")
    print("-- vocabulaire fermé de la 036 (règle #19 : la DB est le 3ᵉ point de synchro).")
    print("-- Généré par _gen_037.py — ne pas éditer à la main.")
    print("BEGIN;")
    for agent, prompt in textes:
        print(
            f"UPDATE agent_prompts SET prompt_text={sql_quote(prompt)}, "
            f"version = version + 1, synced = false, updated_at = NOW() "
            f"WHERE agent_name={sql_quote(agent)} AND flow_version='v2';"
        )

    # ── Gardes de la migration ────────────────────────────────────────────────────────────────
    # K1 — l'UPDATE a MORDU. Un `UPDATE … WHERE` qui ne trouve rien réussit en silence : sans cette
    # garde, une 037 qui n'aurait rien mis à jour (agent renommé, flow_version 'v3') se terminerait
    # sur un COMMIT vert, et la panne se découvrirait au premier appel réel.
    # ⚠️ `for _, agent` : les couples sont `(fichier, agent_name)`. Déballer dans l'autre sens
    # produisait `agent_name IN ('10-ingestion-agent.md', …)` — un IN qui ne matche jamais, donc une
    # K1 qui lève à tous les coups. Bug attrapé en LISANT le SQL émis, pas en relisant le Python.
    noms = ", ".join(sql_quote(agent) for _, agent in TARGETS)
    print("DO $$ DECLARE n integer; BEGIN")
    print(f"  SELECT count(*) INTO n FROM agent_prompts")
    print(f"   WHERE agent_name IN ({noms}) AND flow_version = 'v2';")
    print(f"  IF n <> {len(TARGETS)} THEN RAISE EXCEPTION")
    print(f"    '037/K1 : % prompt(s) v2 visé(s) au lieu de {len(TARGETS)} — l''UPDATE n''a pas mordu', n;")
    print("  END IF;")
    print("END $$;")

    # K2 — le texte EN BASE ne porte plus les motifs retirés. La garde de génération lit le fichier ;
    # celle-ci lit ce que la base contient VRAIMENT après l'UPDATE — le point de lecture des agents.
    # Même précaution qu'à la génération : on cherche la forme d'émission, pas le mot.
    print("DO $$ DECLARE n integer; BEGIN")
    for motif, quoi in MOTIFS_INTERDITS:
        litteral = motif.replace("'", "''").replace("%", "\\%").replace("_", "\\_")
        print(f"  SELECT count(*) INTO n FROM agent_prompts")
        print(f"   WHERE flow_version = 'v2' AND prompt_text LIKE '%{litteral}%' ESCAPE '\\';")
        print(f"  IF n > 0 THEN RAISE EXCEPTION")
        print(f"    '037/K2 : % prompt(s) v2 portent encore {motif} ({quoi})', n;")
        print("  END IF;")
    print("END $$;")

    print("COMMIT;")


if __name__ == "__main__":
    main()
