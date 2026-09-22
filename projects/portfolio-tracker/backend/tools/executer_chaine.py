"""PREMIER PASSAGE RÉEL de la chaîne frameworks — traducteur → collecte → analyste → manager.

POURQUOI CET OUTIL EXISTE
-------------------------
Les six agents de la chaîne existent, sont validés hors ligne, et **rien ne les appelait**. Mesuré
le 2026-09-21 : `collecte_executor`, `analyste` et `framework_persist` avaient ZÉRO appelant dans
`app/`. La conséquence se lisait dans l'acceptation : `framework_answers` vide, `framework_mandates`
vide, et six critères sur huit rouges « sur zéro ligne » — jamais sur une mauvaise valeur. T8 était
par ailleurs vert à 6/0 sous `ROLLBACK`, ce qui est vrai et ne dit rien du réel : un mécanisme
prouvé en transaction n'a pas tourné (`feedback_controle_au_point_de_lecture` — un décideur sans
producteur ne décide jamais).

CE N'EST PAS L'ORCHESTRATEUR DÉFINITIF. La spec §8.3 place l'entrée sur `/v2/watchlist` (ajout d'un
ticker → traducteur → collecteurs → frameworks). Cet outil est le passage MANUEL qui doit venir
avant : on ne câble pas une boucle automatique sur une chaîne dont personne n'a jamais lu la sortie.

⚠️ IL ÉCRIT EN PROD, ET C'EST LE BUT
------------------------------------
`knowledge_entries`, `collection_plans`, `question_coverage`, `appariement_cartes`,
`framework_answers`, `framework_mandates`. Il DÉPENSE : traducteur, apparieur (si la carte manque),
search-worker par ligne web, analyste.

Il imprime en fin de course l'INVENTAIRE NOMMÉ de tout ce qu'il a écrit, ids compris. Ce n'est pas
de la décoration : ce chantier a déjà laissé des notes fabriquées servir douze jours de « corpus
réel » à deux tests d'acceptation (`feedback_fixture_pollue_le_reel`). Si la sortie est fausse, on
retire par ces ids et on corrige EN AMONT avant de réessayer — jamais l'inverse.

Usage :

    bash tools/executer_chaine.sh RVMD qualite_financiere pre_revenus
    bash tools/executer_chaine.sh RVMD qualite_financiere pre_revenus --sans-collecte

`--sans-collecte` saute le maillon 1 (aucune dépense traducteur/web) et fait répondre l'analyste
sur le corpus DÉJÀ en base : c'est le passage le moins cher pour voir si la seconde moitié tient.

Codes : 0 = la chaîne est allée au bout · 1 = un maillon a refusé · 2 = pas exécutable (env).
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback
from typing import Any

from app.agents.v2.analyste import repondre
from app.agents.v2.collecte_executor import executer_collecte_framework
from app.agents.v2.dossier import charger_dossier
from app.agents.v2.framework_persist import persist_answer, read_dispenses
from app.agents.v2.frameworks import load_frameworks
from app.agents.v2.manager import reviser_framework
from app.agents.v2.manager_persist import persist_review
from app.db.database import close_pool, get_db_session, init_pool

# Même plafond que `tools/acceptation_analyste.py` — et pour la même raison : un dossier entier
# ferait un prompt de plusieurs centaines de milliers de tokens. La troncature est DITE.
#
# ⚠️ Seul le PLAFOND est partagé, plus la règle. L'assemblage vivait ici ET dans l'acceptation, sous
# le commentaire « même plafond que l'autre, et pour la même raison » — c'est-à-dire une règle sans
# détenteur, qui re-diverge au correctif suivant (#46). Elle est désormais dans
# `app/agents/v2/dossier.py`, et ce passage se contente de l'appeler.
PLAFOND = int(os.environ.get("CHAINE_CORPUS_MAX", "40"))

# L'analyste n'a pas de défaut (§3.4) : deux réponses anonymes à une même question sont
# indiscernables. Ce passage signe donc ses réponses.
ANALYSTE = os.environ.get("CHAINE_ANALYSTE", "passage_manuel_v3")


def _titre(n: int, texte: str) -> None:
    print(f"\n{'─'*78}\nMAILLON {n} — {texte}\n{'─'*78}")


async def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    ticker_id, framework_id, archetype = sys.argv[1], sys.argv[2], sys.argv[3]
    sans_collecte = "--sans-collecte" in sys.argv

    # ⚠️ Les deux pré-requis se refusent AVANT toute dépense et avant la première écriture (#40) :
    # découvrir au maillon 2 qu'il manque une clef laisserait un plan et des entries à demi écrits.
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquante.", file=sys.stderr)
        return 2
    if not os.environ.get("DEEPINFRA_API_KEY"):
        print("DEEPINFRA_API_KEY manquante — ce passage appelle le VRAI modèle, il ne se simule pas.",
              file=sys.stderr)
        return 2

    fichier = load_frameworks()
    print(f"{'='*78}\nPASSAGE RÉEL — {ticker_id} · {framework_id} · archétype « {archetype} »\n"
          f"référentiel {fichier.schema_version} · analyste `{ANALYSTE}`\n{'='*78}")

    await init_pool(url)
    ecrits: dict[str, Any] = {}
    try:
        # ── MAILLON 1 — le plan, la collecte, les liens ─────────────────────────
        if sans_collecte:
            _titre(1, "collecte SAUTÉE (--sans-collecte) — corpus déjà en base")
        else:
            _titre(1, "traducteur → plan → collecte → liens de couverture + mandats collecteur")
            rapport = await executer_collecte_framework(ticker_id, framework_id, archetype)
            ecrits["collection_plan_id"] = rapport["plan_id"]
            ecrits["liens"] = len(rapport["liens"])
            ecrits["mandats_collecteur"] = len(rapport["mandats"])
            print(f"  plan #{rapport['plan_id']} · carte {rapport['carte_etat']} "
                  f"(dépôt {rapport['carte_depot_courant']}, {rapport['carte_lignes']} ligne(s))")
            print(f"  {rapport['lignes_vues']} ligne(s) de plan · {len(rapport['liens'])} lien(s) "
                  f"· {len(rapport['mandats'])} mandat(s) collecteur")
            print(f"  écrits : {rapport['ecrits']}")
            print(f"  coût traducteur {rapport['traducteur_cost_usd']} · "
                  f"apparieur {rapport['apparieur_cost_usd']}")

        # ── MAILLON 2 — l'analyste répond ───────────────────────────────────────
        _titre(2, "analyste — une réponse OU un refus nommé par question")
        async with get_db_session() as conn:
            dossier = await charger_dossier(
                conn, ticker_id=ticker_id, framework_id=framework_id,
                framework_version=fichier.schema_version, plafond=PLAFOND)
        entries = dossier.entries
        print(dossier.bilan())
        if not entries:
            print("  ⚠️ corpus VIDE : l'analyste ne peut que refuser. On s'arrête — un passage "
                  "sur zéro entry ne prouverait rien.")
            return 1

        resultat = await repondre(
            ticker_id, framework_id, archetype,
            analyste=ANALYSTE, entries=entries, fichier=fichier)

        par_statut: dict[str, list] = {}
        for a in resultat.answers:
            par_statut.setdefault(a.statut, []).append(a)
        print(f"  {len(resultat.answers)} réponse(s) · "
              + " · ".join(f"{k} {len(v)}" for k, v in sorted(par_statut.items()))
              + f" · {len(resultat.refus)} refus")
        for a in resultat.answers:
            if a.statut in ("repondu", "approxime"):
                print(f"\n  · {a.question_id} [{a.statut}] rang {a.fondation.rang_derive} "
                      f"/ nature {a.fondation.nature_effective} / sens {a.reponse.sens}")
                print(f"      {a.reponse.verbatim}")
                if a.reponse.valeur is not None:
                    print(f"      valeur : {a.reponse.valeur} {a.reponse.unite}")
                print(f"      cite : {a.fondation.cited_entry_ids}")
            elif a.statut == "non_fondable":
                print(f"\n  ⚠ {a.question_id} [non_fondable] remède {a.gap.remede}")
                print(f"      manque : {a.gap.manque}")
            elif a.statut == "sans_objet":
                print(f"\n  ∅ {a.question_id} [sans_objet → "
                      f"{a.sans_objet.substitut_applique or 'aucun substitut'}]")
                print(f"      {a.sans_objet.motif[:160]}")
        for qid, motif in resultat.refus:
            print(f"\n  ✗ {qid} [REFUS — panne d'agent, AUCUN mandat n'en sort]\n      {motif[:300]}")

        if not resultat.answers:
            print("\n  ⚠️ aucune réponse : rien à persister, rien à réviser. On s'arrête.")
            return 1

        # ── MAILLON 3 — persistance des réponses ────────────────────────────────
        _titre(3, "persistance des réponses (`framework_answers`)")
        ids_answers: list[int] = []
        async with get_db_session() as conn:
            async with conn.transaction():
                for a in resultat.answers:
                    ids_answers.append(await persist_answer(conn, a))
        ecrits["framework_answers"] = ids_answers
        print(f"  {len(ids_answers)} réponse(s) écrite(s) : {ids_answers}")

        # ── MAILLON 4 — le manager relit, et ses renvois deviennent des mandats ──
        _titre(4, "manager — 4 contrôles par réponse ; l'avis se recalcule, le MANDAT se persiste")
        async with get_db_session() as conn:
            dispenses = await read_dispenses(
                conn, ticker_id=ticker_id, framework_id=framework_id,
                framework_version=fichier.schema_version)
        review = reviser_framework(
            resultat.answers, fichier=fichier, framework_id=framework_id,
            archetype=archetype, ticker_id=ticker_id, entries=entries,
            dispenses=frozenset(dispenses))

        for (qid, analyste), d in sorted(review.decisions.items()):
            marque = "✓" if d.verdict == "acquitte" else "↩"
            print(f"  {marque} {qid} [{d.verdict}] {d.motif}")
        async with get_db_session() as conn:
            async with conn.transaction():
                bilan = await persist_review(
                    conn, review, framework_version=fichier.schema_version)
        ecrits["framework_mandates"] = bilan
        print(f"\n  mandats : {bilan['mandats_ecrits']} écrit(s), "
              f"{bilan['mandats_deja_ouverts']} déjà ouvert(s) · ids {bilan['ids']}")

        # ── INVENTAIRE — ce qu'il faut retirer si la sortie est fausse ──────────
        print(f"\n{'='*78}\nINVENTAIRE DES ÉCRITS — à retirer par ces ids si la sortie est fausse\n"
              f"{'='*78}")
        for clef, val in ecrits.items():
            print(f"  {clef:24} {val}")
        print("\n⚠️ LE VERDICT EST À LA LECTURE, pas au code de sortie. Un `repondu` bien formé "
              "sur un fait inventé passe les quatre contrôles : ils gardent la STRUCTURE, jamais "
              "le sens (`feedback_garde_structure_pas_sens`). Relire chaque verbatim contre les "
              "entries citées AVANT de déclarer le passage acquis.")
        return 0
    finally:
        await close_pool()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
