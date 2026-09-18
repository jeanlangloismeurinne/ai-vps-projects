"""Acceptation du PRODUCTEUR de carte sur le chemin d'exécution (lot 3, maillon 4bis — étape 2d).

Ce que les checks ne peuvent pas prouver, et que ce fichier prouve : que la carte s'écrit VRAIMENT
en base, se relit VRAIMENT, et que sa garde d'âge vire VRAIMENT — contre le vrai modèle, le vrai
dépôt SEC et la vraie base. `check_collecte_executor` §10 éprouve les quatre états sur des frontières
substituées ; un mock ne peut pas rougir sur un codec JSONB, une contrainte d'unicité ou un `<` entre
un `text` Postgres et une chaîne Python.

LA LIGNE DE BASE EST REQUÊTÉE ICI, PAS RAPPELÉE (`feedback_ligne_de_base_est_une_mesure`). Le
diagnostic qui a motivé ce lot — `appariement_cartes` vide, aucun producteur en production — était
vrai le 2026-09-18 au matin. Le recopier ici mesurerait un souvenir : le critère [1] le REMESURE.

POURQUOI LE CRITÈRE QUI COMPTE EST [4], ET PAS « LA CARTE S'ÉCRIT »
--------------------------------------------------------------------
Qu'une carte s'écrive puis se relise est nécessaire et se contourne tout seul : il suffit que la
garde d'âge soit fausse par construction pour que toute carte soit éternellement « à jour », et
l'écriture-relecture reste verte. C'est très exactement l'état d'avant ce lot (#70) — la comparaison
`X < X`, toujours fausse, sous un log qui prétendait le contraire. [4] oppose donc à la carte une
date STRICTEMENT POSTÉRIEURE au dépôt réel et exige un `None` : la branche « périmée » doit être
ATTEIGNABLE sur des données réelles, pas seulement dans un test qui fabrique ses deux dates.

Et [5], qui ferme la porte que [4] laisse ouverte : une garde d'âge parfaite sur une carte que
personne n'écoute ne change rien. On compare, gratuitement et dans le même run, l'ensemble des lignes
que l'aiguilleur SORTANT (`poste_retenu` seul) route vers EDGAR à celui que la carte route vers
EDGAR. S'ils sont identiques, la carte est un décor.

⚠️ TOUT SE PASSE DANS UNE TRANSACTION ROLLBACK — zéro résidu, et [6] le VÉRIFIE après coup plutôt
que de le promettre. La carte produite ici est une vraie carte ; la laisser en base ferait passer une
mesure pour de la production (`feedback_fixture_pollue_le_reel`).

⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code DÉPLOYÉ, qui peut précéder celui
qu'on éprouve. Lanceur : `tools/acceptation_carte_executeur.sh`.

Coût : UN appel apparieur (≈ $0.0015), aucun appel traducteur — le plan est RELU en base, pas
retraduit. Aucune collecte réelle n'est déclenchée (ni socle EDGAR, ni search-worker).

Codes : 0 = tous les critères tenus · 1 = un critère rouge · 2 = pas mesurable (env/modèle/SEC/plan).
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback
from datetime import date, timedelta

from app.agents.v2.appariement_persist import lire_carte
from app.agents.v2.collecte_executor import (
    assurer_carte,
    poste_retenu,
    router_source,
)
from app.agents.v2.collecteur import ligne_aveugle
from app.contracts.collection_plan_schema import CollectionPlan, CollectionPlanItem
from app.db.database import close_pool, get_db_session, init_pool

ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


async def _dernier_plan(conn) -> tuple[int, CollectionPlan]:
    """Le plan persisté le plus récent, RELU en base. On ne retraduit pas : le plan est une donnée
    de production existante, et la retraduire coûterait un appel modèle pour fabriquer une entrée
    moins réelle que celle qui est déjà là."""
    tete = await conn.fetchrow(
        "SELECT id, ticker_id, framework_id, framework_version, archetype "
        "FROM collection_plans ORDER BY id DESC LIMIT 1")
    if tete is None:
        raise RuntimeError("aucun plan persisté dans `collection_plans` — rien à apparier")
    lignes = await conn.fetch(
        "SELECT question_id, ingredient_id, statut, metrique, source_pressentie, ancre, motif, poste "
        "FROM collection_plan_items WHERE plan_id = $1 ORDER BY id", tete["id"])
    items = [CollectionPlanItem(**{k: v for k, v in dict(r).items() if v is not None})
             for r in lignes]
    return tete["id"], CollectionPlan(
        ticker_id=tete["ticker_id"], framework_id=tete["framework_id"],
        framework_version=tete["framework_version"], archetype=tete["archetype"], items=items)


def _cles_edgar(plan: CollectionPlan, statuts) -> set[tuple[str, str]]:
    """Les couples (question, ingrédient) que l'aiguillage route vers EDGAR — avec ou sans carte.
    Déterministe et gratuit : c'est la comparaison au titulaire du critère [5]."""
    out = set()
    for it in plan.items:
        if it.statut != "traduit":
            continue
        cle = (it.question_id, it.ingredient_id)
        st = statuts.get(cle) if statuts else None
        if router_source(ligne_aveugle(it, plan.ticker_id), carte_statut=st) == "edgar":
            out.add(cle)
    return out


async def main() -> int:
    if not os.environ.get("DATABASE_URL") or not os.environ.get("DEEPINFRA_API_KEY"):
        print("DATABASE_URL / DEEPINFRA_API_KEY manquantes — cette acceptation appelle le VRAI "
              "modèle et la VRAIE base, elle ne se simule pas.", file=sys.stderr)
        return 2
    await init_pool(os.environ["DATABASE_URL"])
    try:
        async with get_db_session() as conn:
            # ── [1] LA LIGNE DE BASE, REQUÊTÉE — hors transaction, sur l'état réel ────────────────
            avant = await conn.fetchval("SELECT count(*) FROM appariement_cartes")
            try:
                plan_id, plan = await _dernier_plan(conn)
            except Exception as e:  # noqa: BLE001
                print(f"  ABANDON mesure : {e}", file=sys.stderr)
                return 2
            traduits = [it for it in plan.items if it.statut == "traduit"]
            print(f"\n  LIGNE DE BASE (mesurée à l'instant, pas rappelée) : "
                  f"{avant} carte(s) en base · plan #{plan_id} {plan.ticker_id}/"
                  f"{plan.framework_id} {plan.framework_version} · {len(traduits)} ligne(s) "
                  f"`traduit` sur {len(plan.items)}")
            check("[1] la ligne de base est LISIBLE (un plan réel existe et se relit en base)",
                  len(traduits) > 0,
                  "→ aucune ligne `traduit` : il n'y a rien à apparier, la mesure serait vide")

            # Le titulaire : ce que l'aiguilleur route vers EDGAR SANS carte. Requis maintenant,
            # pendant que la table est dans son état de départ.
            sortant = _cles_edgar(plan, None)
            print(f"  TITULAIRE (poste_retenu seul) : {len(sortant)} ligne(s) vers EDGAR, "
                  f"{len(traduits) - len(sortant)} vers le web payant")

            tr = conn.transaction()
            await tr.start()
            try:
                # ── [2] LA PRODUCTION — absente en base ⟹ reconstruite, et ÉCRITE ─────────────────
                c1 = await assurer_carte(plan, conn=conn)
                dans = await conn.fetchval(
                    "SELECT count(*) FROM appariement_cartes WHERE ticker_id = $1 "
                    "AND framework_id = $2 AND framework_version = $3",
                    plan.ticker_id, plan.framework_id, plan.framework_version)
                print(f"\n  carte : etat={c1.etat} · dépôt courant {c1.depot_courant} · "
                      f"{len(c1.statuts or {})} ligne(s) · ${c1.cout_usd:.4f}")
                check("[2] la carte est PRODUITE et ÉCRITE en base (`reconstruite` + 1 ligne "
                      "lisible sur sa clef) — pas seulement construite en mémoire",
                      c1.etat == "reconstruite" and dans == 1 and c1.statuts,
                      f"→ etat={c1.etat}, lignes sur la clef={dans}")

                # ── [3] LA RELECTURE — le deuxième passage est GRATUIT ────────────────────────────
                c2 = await assurer_carte(plan, conn=conn)
                check("[3] le passage suivant relit la carte : `fraiche`, coût modèle NUL. Une "
                      "carte repayée à chaque exécution serait verte partout ailleurs",
                      c2.etat == "fraiche" and c2.cout_usd == 0.0
                      and c2.statuts == c1.statuts,
                      f"→ etat={c2.etat}, cout=${c2.cout_usd:.4f}, "
                      f"statuts identiques={c2.statuts == c1.statuts}")

                # ── [4] LA GARDE D'ÂGE VIRE SUR DONNÉES RÉELLES ──────────────────────────────────
                # Le critère qui ne se contourne pas : on oppose à la carte une date STRICTEMENT
                # postérieure au dépôt réel qu'elle porte. `lire_carte` doit rendre None. Si la
                # comparaison était encore `X < X` (#70), elle rendrait la carte — verte partout.
                demain = (date.fromisoformat(c1.depot_courant) + timedelta(days=1)).isoformat()
                perimee = await lire_carte(
                    conn, ticker_id=plan.ticker_id, framework_id=plan.framework_id,
                    framework_version=plan.framework_version, depot_courant=demain)
                encore = await lire_carte(
                    conn, ticker_id=plan.ticker_id, framework_id=plan.framework_id,
                    framework_version=plan.framework_version, depot_courant=c1.depot_courant)
                check(f"[4] la garde d'âge VIRE sur la carte réelle : opposée au {demain} elle se "
                      f"relit PÉRIMÉE (None), opposée à son propre dépôt ({c1.depot_courant}) elle "
                      "reste valide — la branche « périmée » est atteignable, pas décorative",
                      perimee is None and encore is not None,
                      f"→ périmée={perimee is not None}, même dépôt={encore is not None}")

                # ── [5] LA CARTE DÉCIDE VRAIMENT — sinon elle est un décor ────────────────────────
                avec = _cles_edgar(plan, c1.statuts)
                recuperees = sorted(avec - sortant)
                abandonnees = sorted(sortant - avec)
                print(f"\n  CONFRONTATION : {len(avec)} ligne(s) vers EDGAR avec la carte contre "
                      f"{len(sortant)} sans · {len(recuperees)} récupérée(s) du web · "
                      f"{len(abandonnees)} abandonnée(s)")
                for q, i in recuperees:
                    print(f"    RÉCUPÉRÉE  {q}.{i} → {c1.statuts[(q, i)]}")
                for q, i in abandonnees:
                    it = next(x for x in plan.items
                              if (x.question_id, x.ingredient_id) == (q, i))
                    print(f"    ABANDONNÉE {q}.{i} → {c1.statuts.get((q, i))} "
                          f"(poste au plan : {it.poste} · {it.metrique})")
                check("[5] la carte CHANGE le routage : l'ensemble des lignes EDGAR n'est pas "
                      "celui du titulaire. Une carte parfaite que personne n'écoute ne vaut rien",
                      avec != sortant,
                      f"→ mêmes {len(avec)} lignes qu'avec `poste_retenu` seul : la carte est lue "
                      "mais ne décide rien")

                # ── la distribution, MESURÉE et non gardée (on chiffre avant de durcir) ───────────
                dist: dict[str, int] = {}
                for st in (c1.statuts or {}).values():
                    dist[st] = dist.get(st, 0) + 1
                print(f"\n  MESURE (non gardée) · distribution des trois états : "
                      + " · ".join(f"{n} {s}" for s, n in sorted(dist.items())))

                # ── LA MESURE QUI EMPÊCHE DE CÉLÉBRER UN GAIN QUE LA COLLECTE NE TOUCHERA PAS ────
                # `router_source` peut dire « edgar » sans que `_SocleEdgar` sache exécuter la
                # ligne : le socle ne collecte que les 33 RECETTES du catalogue `POSTES`, et une
                # `approximation` est une FORMULE sur des concepts XBRL nus. `collecter_un` retombe
                # alors au web par un repli NOMMÉ. Compter les lignes « récupérées » sans compter
                # celles-là ferait lire un décompte de routage comme une économie de collecte —
                # exactement la prime à l'erreur que le critère [5] retire au titulaire.
                # Non gardé : c'est une MESURE de ce qui reste à faire (maillon 4), pas un défaut du
                # producteur de carte. Le jour où le socle exécute une formule, ce nombre tombe.
                executables = [(q, i) for (q, i) in recuperees
                               if poste_retenu(
                                   next(x.poste for x in plan.items
                                        if (x.question_id, x.ingredient_id) == (q, i)),
                                   next(x.metrique for x in plan.items
                                        if (x.question_id, x.ingredient_id) == (q, i))) is not None]
                print(f"\n  MESURE (non gardée) · sur {len(recuperees)} ligne(s) que la carte "
                      f"route vers EDGAR et que le titulaire envoyait au web, "
                      f"{len(executables)} sont EXÉCUTABLES par `_SocleEdgar` aujourd'hui "
                      f"(un poste du catalogue survit aux vétos). Les "
                      f"{len(recuperees) - len(executables)} autres repartent au web par le repli "
                      "nommé de `collecter_un` : la carte a tranché, le socle ne sait pas encore "
                      "exécuter une FORMULE sur des concepts nus. C'est le contenu du maillon 4, "
                      "et c'est pourquoi ce nombre est imprimé et non gardé.")
            finally:
                await tr.rollback()

            # ── [6] ZÉRO RÉSIDU — vérifié, pas promis ────────────────────────────────────────────
            apres = await conn.fetchval("SELECT count(*) FROM appariement_cartes")
            check("[6] ROLLBACK effectif : la base est revenue à sa ligne de base. Une carte de "
                  "mesure laissée en production servirait de « corpus réel » au lot suivant",
                  apres == avant, f"→ {avant} avant, {apres} après")
    finally:
        await close_pool()

    print(f"\n{'='*100}")
    print(f"BILAN acceptation carte-exécuteur — {ok} critère(s) OK, {fail} échec(s)")
    return 1 if fail else 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
