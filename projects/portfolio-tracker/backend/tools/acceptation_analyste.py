"""Acceptation de l'ANALYSTE contre le VRAI modèle et le VRAI corpus (lot 3, maillon 1).

Un prompt/schéma n'est pas acquis tant qu'il n'a pas tourné contre le vrai modèle
(`feedback_verifier_contre_api_reelle`). La moitié déterministe est éprouvée hors-ligne par
`checks/check_analyste.py` (63 assertions, mutations gardées par `checks/negatif_analyste.sh`) ;
ICI on fait répondre DeepSeek sur le corpus RÉEL de deux émetteurs d'archétypes contrastés, on LIT
les réponses en texte, et on compte les critères mécaniques.

CE QUE CETTE MESURE PEUT MONTRER, ET QU'AUCUN CHECK HORS-LIGNE NE MONTRE : les refus du pont sur
des réponses réelles. Un `sens` inventé, un rang qui n'atteint pas le plancher, une nature absente
des sources citées — chacun sort en `refus`, nommé, et chacun se répare dans le PROMPT, pas dans le
pont (`feedback_optional_schema_gate` : on durcit la consigne d'abord, on ne desserre pas la garde).

NE PERSISTE RIEN. `repondre()` construit et valide (contrat + pont), n'écrit pas en base.

⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code DÉPLOYÉ, qui peut précéder celui
qu'on éprouve. Lanceur : `tools/acceptation_analyste.sh`.

Codes : 0 = tous les critères tenus · 1 = un critère rouge · 2 = pas mesurable (env/modèle indispo).
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback

from app.agents.v2.analyste import (
    corpus_citable,
    questions_sans_objet,
    repondre,
    statuts_admissibles,
)
from app.agents.v2.dossier import charger_dossier
from app.agents.v2.frameworks import load_frameworks
from app.agents.v2.traducteur import questions_applicables
from app.db.database import close_pool, get_db_session, init_pool

# NVDA (rentable) vs RVMD (pré-revenus) : même contraste que l'acceptation du traducteur — c'est le
# sens des deux pilotes, et c'est sur `pre_revenus` que les `sans_objet` du référentiel se voient.
CAS = [
    ("NVDA", "qualite_financiere", "rentable"),
    ("RVMD", "qualite_financiere", "pre_revenus"),
]

# Le dossier envoyé au modèle est PLAFONNÉ — un corpus entier ferait un prompt de plusieurs
# centaines de milliers de tokens pour une mesure qui doit rester à quelques centimes.
#
# ⚠️ L'ASSEMBLAGE N'EST PLUS FAIT ICI. Il était recopié à l'identique dans `tools/executer_chaine.py`
# — une règle tenue à deux endroits re-diverge au correctif suivant (#46,
# `feedback_correctif_regle_jumeaux`) — et il coupait par la DATE, donc il pouvait écarter la pièce
# qui fonde un ingrédient tout en gardant trois versions d'un autre. C'était l'outil de MESURE qui
# fabriquait la non-représentativité du corpus de test. Détenteur unique : `app/agents/v2/dossier.py`
# (gardé par `checks/check_dossier.py` + `checks/negatif_dossier.sh`). Ici on LIT, et on dit ce qui
# est resté dehors : une mesure tronquée qui tait sa troncature ferait lire « le corpus ne fonde
# pas » là où c'est le plafond qui a coupé.
PLAFOND = int(os.environ.get("ACCEPTATION_CORPUS_MAX", "40"))


def _montrer(resultat, ticker: str) -> None:
    par_statut: dict[str, list] = {}
    for a in resultat.answers:
        par_statut.setdefault(a.statut, []).append(a)

    for a in par_statut.get("repondu", []) + par_statut.get("approxime", []):
        marque = "≈" if a.statut == "approxime" else "·"
        print(f"\n  {marque} {a.question_id} [{a.statut}] rang {a.fondation.rang_derive} "
              f"/ nature {a.fondation.nature_effective} / sens {a.reponse.sens}")
        print(f"      {a.reponse.verbatim}")
        if a.reponse.valeur is not None:
            print(f"      valeur : {a.reponse.valeur} {a.reponse.unite}")
        print(f"      cite : {a.fondation.cited_entry_ids}")
        if a.approximation:
            print(f"      méthode : {a.approximation.methode}")
            print(f"      hypothèses : {a.approximation.hypotheses_explicites}")
            print(f"      sensibilité : {a.approximation.sensibilite}")
    for a in par_statut.get("non_fondable", []):
        print(f"\n  ⚠ {a.question_id} [non_fondable] remède {a.gap.remede} / {a.gap.priorite}")
        print(f"      manque : {a.gap.manque}")
    for a in par_statut.get("sans_objet", []):
        subst = a.sans_objet.substitut_applique or "aucun substitut"
        print(f"\n  ∅ {a.question_id} [sans_objet → {subst}] {a.sans_objet.motif[:110]}")
    for qid, motif in resultat.refus:
        print(f"\n  ✗ {qid} [REFUS — panne d'agent, AUCUN mandat n'en sort]\n      {motif[:400]}")


async def _admissibilite(fichier) -> int:
    """DRY-RUN, AUCUN APPEL MODÈLE : ce que le corpus réel rend possible, question par question.

    `feedback_frontiere_gratuite_avant_depense_modele` — on exécute le producteur déterministe et on
    LIT sa sortie en texte avant de payer. C'est ce tableau qui dit si une question est refusable
    par construction (aucun statut ouvert hors `sans_fondement`), et donc si le `refus` observé
    contre le vrai modèle était une panne d'agent ou un corpus qui ne pouvait pas fonder.
    """
    for ticker, framework_id, archetype in CAS:
        print(f"\n{'='*78}\n{ticker} · {framework_id} · archétype « {archetype} »\n{'='*78}")
        async with get_db_session() as conn:
            dossier = await charger_dossier(
                conn, ticker_id=ticker, framework_id=framework_id,
                framework_version=fichier.schema_version, plafond=PLAFOND)
        entries = dossier.entries
        print(dossier.bilan())
        for q in questions_applicables(fichier, framework_id, archetype):
            citables = corpus_citable(q, entries)
            ouverts, ecartes = statuts_admissibles(q, citables)
            natures: dict[str, int] = {}
            tiers: dict[str, int] = {}
            for e in citables.values():
                natures[str(e.get("nature"))] = natures.get(str(e.get("nature")), 0) + 1
                tiers[str(e.get("reliability_tier"))] = tiers.get(str(e.get("reliability_tier")), 0) + 1
            mort = ouverts == ["sans_fondement"]
            print(f"\n  {'✗' if mort else '·'} {q.id} plancher {q.plancher_tier} / nature attendue "
                  f"{q.nature_attendue}")
            print(f"      citables {len(citables)}/{len(entries)} · tiers {dict(sorted(tiers.items()))} "
                  f"· natures {dict(sorted(natures.items()))}")
            print(f"      statuts ouverts : {ouverts}")
            for m in ecartes:
                print(f"      → {m}")
            if mort:
                print("      ⇒ AUCUNE réponse possible : la question sort en `non_fondable` SANS "
                      "appel modèle (#40)")
    return 0


async def main() -> int:
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquante.", file=sys.stderr)
        return 2
    if "--admissibilite" in sys.argv:
        fichier = load_frameworks()
        await init_pool(url)
        try:
            return await _admissibilite(fichier)
        finally:
            await close_pool()
    if not os.environ.get("DEEPINFRA_API_KEY"):
        print("DATABASE_URL / DEEPINFRA_API_KEY manquantes — l'acceptation appelle le VRAI modèle, "
              "elle ne se simule pas.", file=sys.stderr)
        return 2

    fichier = load_frameworks()
    await init_pool(url)
    ok = fail = 0
    try:
        for ticker, framework_id, archetype in CAS:
            print(f"\n{'='*78}\n{ticker} · {framework_id} · archétype « {archetype} »\n{'='*78}")
            async with get_db_session() as conn:
                dossier = await charger_dossier(
                    conn, ticker_id=ticker, framework_id=framework_id,
                    framework_version=fichier.schema_version, plafond=PLAFOND)
            entries = dossier.entries
            tiers: dict[str, int] = {}
            for e in entries.values():
                tiers[str(e.get("reliability_tier"))] = tiers.get(str(e.get("reliability_tier")), 0) + 1
            print(dossier.bilan())
            print(f"  · tiers {dict(sorted(tiers.items()))}")
            if not entries:
                fail += 1
                print("  FAIL aucun corpus pour ce ticker — la mesure ne porterait sur rien "
                      "(un zéro ne se lit pas comme un vert)")
                continue

            try:
                resultat = await repondre(ticker, framework_id, archetype,
                                          analyste="acceptation", entries=entries, fichier=fichier)
            except Exception as e:  # noqa: BLE001
                fail += 1
                print(f"  FAIL {type(e).__name__}: {e}")
                traceback.print_exc()
                continue

            _montrer(resultat, ticker)

            attendus_so = {q.id for q in questions_sans_objet(fichier, framework_id, archetype)}
            rendus_so = {a.question_id for a in resultat.answers if a.statut == "sans_objet"}
            applicables = {q.id for q in questions_applicables(fichier, framework_id, archetype)}
            run = resultat.run
            if run is not None:
                print(f"\n  télémétrie : {run.tokens_in} in / {run.tokens_out} out · "
                      f"${run.cost_usd:.4f}")

            # ① Le critère qui ne peut se mesurer QUE contre le vrai modèle : ce qu'il rend passe le
            #    contrat ET le pont. Un refus ici est une consigne à durcir, pas une garde à ouvrir.
            if not resultat.refus:
                ok += 1
                print(f"  ok   les {len(applicables)} questions applicables passent contrat ET pont "
                      "(aucun refus)")
            else:
                fail += 1
                print(f"  FAIL {len(resultat.refus)} refus : {[q for q, _ in resultat.refus]} — "
                      "à réparer dans le PROMPT, jamais en desserrant le pont")

            # ② Les hors-sujet viennent du référentiel, pas du modèle : ils sortent tous, et
            #    exactement ceux-là.
            if rendus_so == attendus_so:
                ok += 1
                print(f"  ok   les {len(attendus_so)} `sans_objet` sont exactement ceux du "
                      f"référentiel pour cet archétype")
            else:
                fail += 1
                print(f"  FAIL `sans_objet` rendus {sorted(rendus_so)} ≠ attendus "
                      f"{sorted(attendus_so)}")

            # ③ Aucune question ne s'évapore — `repondre` lève sinon, on le REDIT sur une ligne
            #    réelle pour que le bilan ne porte pas sur zéro.
            couvertes = {a.question_id for a in resultat.answers} | {q for q, _ in resultat.refus}
            if couvertes == applicables | attendus_so:
                ok += 1
                print(f"  ok   les {len(couvertes)} questions du framework sortent toutes nommées")
            else:
                fail += 1
                print(f"  FAIL questions non traitées : "
                      f"{sorted((applicables | attendus_so) - couvertes)}")

        print(f"\n{'='*78}\n{ok} vérifications OK, {fail} échec(s)")
        print("⚠️ Le reste s'apprécie À LA LECTURE : les `verbatim` répondent-ils à la question "
              "POSÉE (et pas à côté) ? les `non_fondable` nomment-ils un manque qu'une collecte "
              "peut combler ? une `approximation` déclare-t-elle des hypothèses qu'on peut "
              "contester ? un `sens` est-il celui que le verbatim décrit ?")
        return 1 if fail else 0
    finally:
        await close_pool()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
