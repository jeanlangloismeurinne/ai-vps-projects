"""Acceptation de l'EXÉCUTION d'un appariement contre le vrai dépôt (lot 3, maillon 4).

Ce que les checks ne peuvent pas prouver, et que ce fichier prouve : qu'une formule écrite par
l'apparieur s'exécute VRAIMENT sur l'inventaire RÉEL de l'émetteur, que l'entry s'écrit VRAIMENT avec
son tier dérivé et sa provenance, et qu'un second passage la SUPERSÈDE au lieu de la doubler.
`check_appariement_feed` éprouve la mécanique sur des fixtures ; une fixture ne peut pas rougir sur
un concept que l'émetteur a cessé de déposer, sur deux clôtures décalées de trois jours, ni sur un
codec JSONB.

LE CHIFFRE QUE CE FICHIER MESURE, ET CELUI QU'IL REFUSE DE MESURER
-------------------------------------------------------------------
Il mesure « lignes **COLLECTÉES depuis le dépôt** » : des entries écrites, relues en base, portant
une valeur calculée sur des concepts XBRL déposés. Il ne mesure PAS « lignes routées vers EDGAR » —
ce nombre-là était déjà bon au maillon 4bis (9 lignes sur RVMD) pendant que la collecte valait zéro.
Confondre les deux est la faute que #71 a corrigée une fois ; elle se recommet en changeant de
niveau, et c'est pourquoi le critère [3] compte des LIGNES EN BASE et non des décisions de routage.

LA LIGNE DE BASE EST REQUÊTÉE, PAS RAPPELÉE (`feedback_ligne_de_base_est_une_mesure`). Le « 0 ligne
exécutable » du 2026-09-18 était vrai ce matin-là ; le recopier ici mesurerait un souvenir.

POURQUOI LE WEB EST DÉBRANCHÉ PENDANT LA MESURE
-------------------------------------------------
`collecter_un` retombe au web par un repli NOMMÉ quand il n'a ni recette ni consigne. Ce repli est
correct, il est payant, et surtout il RÉUSSIRAIT : une ligne qui repart au web pendant cette mesure
compterait comme « traitée » alors qu'elle est exactement ce que le maillon 4 doit retirer. On
substitue donc `run_search_worker` par un refus : toute retombée web devient un échec VISIBLE, pas un
succès silencieux. Les lignes soumises sont d'ailleurs choisies pour qu'aucune n'y ait de raison
d'aller — si l'une y va quand même, c'est le câblage qui a un trou, et on veut le voir.

⚠️ TOUT SE PASSE DANS UNE TRANSACTION ROLLBACK — zéro résidu, et [7] le VÉRIFIE après coup plutôt que
de le promettre. Les entries produites ici sont de VRAIS faits ; les laisser en base les ferait servir
de « corpus réel » au lot suivant (`feedback_fixture_pollue_le_reel`, 12 jours de faux corpus).

⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code DÉPLOYÉ, possiblement antérieur à
ce qu'on éprouve. Lanceur : `tools/acceptation_appariement.sh`.

Coût : au plus UN appel apparieur (≈ $0.0015) si la carte du plan manque ou a vieilli, zéro sinon.
Un appel `companyfacts` (gratuit). AUCUN appel web payant — il est débranché, cf. ci-dessus.

Codes : 0 = tous les critères tenus · 1 = un critère rouge · 2 = pas mesurable (env/SEC/plan).
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback

from app.agents.v2 import collecte_executor as _exec
from app.agents.v2.collecte_executor import (
    _SocleEdgar,
    assurer_carte,
    collecter_un,
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
    """Le plan persisté le plus récent, RELU en base — jamais retraduit (le retraduire coûterait un
    appel modèle pour fabriquer une entrée moins réelle que celle qui est déjà là)."""
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


async def _web_interdit(req):
    """Le repli web, débranché le temps de la mesure. Cf. l'en-tête : une retombée web réussie se
    lirait comme une ligne traitée, alors qu'elle est précisément ce que ce maillon doit retirer."""
    raise RuntimeError(
        f"repli WEB atteint pour « {req.ticker_id} » pendant la mesure d'appariement — "
        "cette ligne devait être collectée depuis le dépôt")


async def main() -> int:
    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL manquante — cette acceptation lit et écrit la VRAIE base.",
              file=sys.stderr)
        return 2
    await init_pool(os.environ["DATABASE_URL"])
    try:
        async with get_db_session() as conn:
            try:
                plan_id, plan = await _dernier_plan(conn)
            except Exception as e:  # noqa: BLE001
                print(f"  ABANDON mesure : {e}", file=sys.stderr)
                return 2

            # ── [1] LA LIGNE DE BASE, REQUÊTÉE — hors transaction, sur l'état réel ────────────────
            avant = await conn.fetchval(
                "SELECT count(*) FROM knowledge_entries WHERE ticker_id = $1 "
                "AND 'appariement' = ANY(tags) AND superseded_by IS NULL", plan.ticker_id)
            traduits = [it for it in plan.items if it.statut == "traduit"]
            print(f"\n  LIGNE DE BASE (mesurée à l'instant, pas rappelée) : {avant} entry(ies) "
                  f"« appariement » active(s) pour {plan.ticker_id} · plan #{plan_id} "
                  f"{plan.framework_id} {plan.framework_version} · {len(traduits)} ligne(s) "
                  f"`traduit` sur {len(plan.items)}")
            check("[1] la ligne de base est LISIBLE (un plan réel existe et se relit en base)",
                  len(traduits) > 0,
                  "→ aucune ligne `traduit` : il n'y a rien à apparier, la mesure serait vide")

            _exec.run_search_worker = _web_interdit
            tr = conn.transaction()
            await tr.start()
            try:
                # ── [2] LA CARTE, ET SES CONSIGNES ───────────────────────────────────────────────
                carte = await assurer_carte(plan, conn=conn)
                dist: dict[str, int] = {}
                for st in (carte.statuts or {}).values():
                    dist[st] = dist.get(st, 0) + 1
                print(f"\n  carte : etat={carte.etat} · dépôt courant {carte.depot_courant} · "
                      f"${carte.cout_usd:.4f} · distribution "
                      + " · ".join(f"{n} {s}" for s, n in sorted(dist.items())))
                check("[2] la carte porte des CONSIGNES exécutables, et l'inventaire est en main : "
                      "sans eux le maillon 4 n'a rien à exécuter et la mesure serait vide",
                      bool(carte.consignes) and carte.inventaire is not None,
                      f"→ {len(carte.consignes or {})} consigne(s), "
                      f"inventaire={'oui' if carte.inventaire else 'non'}")

                # Les lignes SOUMISES : routées EDGAR par la carte, sans recette du catalogue, avec
                # une consigne. C'est exactement la population que le maillon 4 débloque — celle qui
                # repartait au web en tier B pour un nombre dont tous les termes sont déposés.
                soumises = []
                for it in traduits:
                    cle = (it.question_id, it.ingredient_id)
                    st = (carte.statuts or {}).get(cle)
                    ligne = ligne_aveugle(it, plan.ticker_id)
                    if router_source(ligne, carte_statut=st) != "edgar":
                        continue
                    if poste_retenu(it.poste, it.metrique) is not None:
                        continue            # recette du catalogue : chemin `_SocleEdgar`, inchangé
                    if (carte.consignes or {}).get(cle) is None:
                        continue
                    soumises.append((cle, it, ligne))
                print(f"  SOUMISES : {len(soumises)} ligne(s) routée(s) EDGAR sans recette du "
                      f"catalogue, avec une consigne — la population que ce maillon débloque")

                # ── [3] LE CHIFFRE QUI COMPTE : LIGNES COLLECTÉES DEPUIS LE DÉPÔT ─────────────────
                socle = _SocleEdgar([])   # jamais sollicité : aucune ligne soumise n'a de recette
                collectees, refus = [], []
                for cle, it, ligne in soumises:
                    consigne = carte.consignes[cle]
                    res = await collecter_un(
                        ligne, conn=conn, socle=socle,
                        carte_statut=(carte.statuts or {}).get(cle),
                        consigne=consigne, inventaire=carte.inventaire)
                    if res.entry_id:
                        collectees.append((cle, it, consigne, res.entry_id))
                        print(f"    COLLECTÉE  {cle[0]}.{cle[1]} → entry #{res.entry_id} "
                              f"« {consigne.expression} »")
                    else:
                        refus.append((cle, it, consigne, res.echec))
                        print(f"    REFUSÉE    {cle[0]}.{cle[1]} « {consigne.expression} » "
                              f"→ {res.echec}")

                en_base = await conn.fetch(
                    "SELECT id, title, content, content_structured, reliability_tier, "
                    "reliability_score, tags, source_url, entry_type, nature "
                    "FROM knowledge_entries WHERE ticker_id = $1 AND 'appariement' = ANY(tags) "
                    "AND superseded_by IS NULL ORDER BY id", plan.ticker_id)
                print(f"\n  LIGNES COLLECTÉES DEPUIS LE DÉPÔT : {avant} → {len(en_base)} "
                      f"({len(collectees)} écriture(s) ce run, {len(refus)} refus nommé(s))")
                check("[3] des lignes sont COLLECTÉES DEPUIS LE DÉPÔT — relues en base, pas "
                      "seulement routées vers EDGAR (#71 : router n'est pas collecter)",
                      len(en_base) > avant and len(collectees) > 0,
                      f"→ {avant} avant, {len(en_base)} après, {len(collectees)} écriture(s)")

                # ── [4] CE QUE L'ENTRY PORTE, LU AU POINT DE LECTURE ──────────────────────────────
                # Relu en base et non gardé en mémoire : un drapeau calculé mais non persisté est un
                # affichage (`feedback_controle_au_point_de_lecture`).
                sans_prov = [r["id"] for r in en_base
                             if not (r["content_structured"] or {}).get("ingredients")]
                sans_tier = [r["id"] for r in en_base if not r["reliability_tier"]]
                check("[4] chaque entry relue porte sa PROVENANCE concept par concept et un tier — "
                      "un nombre calculé sans ses ingrédients n'est pas contestable",
                      en_base and not sans_prov and not sans_tier,
                      f"→ sans provenance : {sans_prov}, sans tier : {sans_tier}")

                # L'AVEUGLEMENT, VÉRIFIÉ SUR CE QUI EST ÉCRIT (et non sur l'intention du code).
                fuites = [r["id"] for r in en_base
                          if any(j in (r["title"] + r["content"] + str(r["content_structured"]))
                                 for j in ("question_id", "ingredient_id", plan.framework_id))]
                check("[4bis] aucune entry ne nomme la question ni le framework : l'aveuglement du "
                      "collecteur (#58) tient sur le corpus, pas seulement dans les types",
                      not fuites, f"→ entries fautives : {fuites}")

                for r in en_base:
                    s = r["content_structured"] or {}
                    print(f"    #{r['id']} tier {r['reliability_tier']} "
                          f"({r['reliability_score']}) · nature={r['nature']} · "
                          f"{s.get('metric')} = {s.get('value')} {s.get('currency')} "
                          f"· {s.get('period')} · {len(s.get('ingredients') or [])} ingrédient(s) "
                          f"· statut={s.get('appariement_statut')} "
                          f"déterministe={s.get('deterministe')}")

                # ── [5] UN REFUS EST NOMMÉ, TOUJOURS ──────────────────────────────────────────────
                # Un refus n'est pas un échec de ce lot : « pas d'ancre commune » est une propriété
                # du dépôt. Ce qui serait un échec, c'est un refus MUET — il deviendrait un mandat
                # illisible, et l'analyste lirait « le dépôt ne porte pas ce nombre ».
                muets = [cle for cle, _it, _c, motif in refus
                         if not motif or len(motif) < 40]
                check("[5] tout refus porte un motif qui DIT ce qui manque (#25) : un refus muet "
                      "devient un mandat illisible, et se lit comme une absence au dépôt",
                      not muets, f"→ refus muets : {muets}")

                # ── [6] UNE SECONDE EXÉCUTION SUPERSÈDE, ELLE NE DOUBLE PAS ───────────────────────
                # L'identité du fait est son expression (#43). Sans elle, deux passages écriraient
                # deux entries actives et le corpus répondrait deux choses à la même question.
                if collectees:
                    cle, it, consigne, _ = collectees[0]
                    res2 = await collecter_un(
                        ligne_aveugle(it, plan.ticker_id), conn=conn, socle=socle,
                        carte_statut=(carte.statuts or {}).get(cle),
                        consigne=consigne, inventaire=carte.inventaire)
                    actives = await conn.fetchval(
                        "SELECT count(*) FROM knowledge_entries WHERE ticker_id = $1 "
                        "AND 'appariement' = ANY(tags) AND superseded_by IS NULL "
                        "AND content_structured->>'metric' = $2",
                        plan.ticker_id, consigne.expression)
                    check("[6] réexécuter la MÊME formule SUPERSÈDE l'entry au lieu de la doubler : "
                          "une seule reste active pour cette expression (#43)",
                          res2.entry_id is not None and actives == 1,
                          f"→ entry #{res2.entry_id}, {actives} active(s) pour "
                          f"« {consigne.expression} »")
                else:
                    check("[6] réexécuter la MÊME formule SUPERSÈDE l'entry au lieu de la doubler",
                          False, "→ aucune ligne collectée : critère NON MESURÉ (donc rouge, pas "
                                 "sauté — une mesure absente n'est pas un zéro)")
            finally:
                await tr.rollback()

            # ── [7] ZÉRO RÉSIDU — vérifié, pas promis ────────────────────────────────────────────
            apres = await conn.fetchval(
                "SELECT count(*) FROM knowledge_entries WHERE ticker_id = $1 "
                "AND 'appariement' = ANY(tags) AND superseded_by IS NULL", plan.ticker_id)
            check("[7] ROLLBACK effectif : la base est revenue à sa ligne de base. Des faits de "
                  "mesure laissés en base serviraient de « corpus réel » au lot suivant",
                  apres == avant, f"→ {avant} avant, {apres} après")
    finally:
        await close_pool()

    print(f"\n{'='*100}")
    print(f"BILAN acceptation appariement — {ok} critère(s) OK, {fail} échec(s)")
    return 1 if fail else 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
