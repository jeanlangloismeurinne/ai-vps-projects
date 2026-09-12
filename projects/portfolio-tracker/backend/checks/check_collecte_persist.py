"""Vérification de la PERSISTANCE de la chaîne de collecte (lot 2c, migration 039 —
`app/agents/v2/collecte_persist.py`).

Lit l'ÉTAT PERSISTABLE, pas seulement la règle : les fonctions écrivent vraiment, on relit, on
vérifie. Tout se passe dans une transaction ROLLBACK — **aucun résidu** en base (une fixture de
rejeu qui polluerait le réel est un mode de panne connu, `feedback_fixture_pollue_le_reel`).

Exige le réseau `coolify` + `CHECK_DB_URL` : sans elle, la moitié « état persisté » n'est pas
mesurée → SORT EN ÉCHEC, jamais un saut de section (`feedback_check_degrade_en_sortant_a_zero`).

  • §1 le PLAN s'écrit avec ses lignes, et le CHECK de base tient la charge du statut ;
  • §2 l'aiguillage écrit ses LIENS (question_coverage) ET ses MANDATS (framework_mandates) ;
  • §3 DERNIER REMPART — la base REFUSE une ligne `traduit` sans métrique, et un mandat d'origine
       inconnue : le CHECK SQL redit le contrat, éprouvé en négatif ici même.
"""
import asyncio
import os
import sys

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


_db_url = os.environ.get("CHECK_DB_URL", "")
if not _db_url or "@" not in _db_url:
    print("  FAIL §persistance non exécutée — CHECK_DB_URL absente ou factice ; l'état persisté "
          "n'a PAS été mesuré")
    print("\n=== 0 ok / 1 FAIL ===\n0 vérifications OK, 1 échec(s)")
    sys.exit(1)

import asyncpg  # noqa: E402

from app.agents.v2.collecte_persist import persist_aiguillage, persist_plan  # noqa: E402
from app.agents.v2.collecteur import (  # noqa: E402
    LienCouverture,
    MandatCollecte,
    ResultatAiguillage,
)
from app.contracts.collection_plan_schema import CollectionPlan, CollectionPlanItem  # noqa: E402


async def _rejette(conn, label, sql, *args):
    """La base DOIT refuser (CheckViolation). Savepoint : l'échec n'abîme pas la transaction outer."""
    global ok, fail
    sp = conn.transaction()
    await sp.start()
    try:
        await conn.execute(sql, *args)
    except asyncpg.exceptions.CheckViolationError:
        await sp.rollback()
        ok += 1
        print(f"  ok   {label}")
        return
    except Exception as e:  # noqa: BLE001
        await sp.rollback()
        fail += 1
        print(f"  FAIL {label} → mauvaise exception {type(e).__name__}")
        return
    await sp.rollback()
    fail += 1
    print(f"  FAIL {label} → la base a ACCEPTÉ la ligne interdite")


async def run():
    conn = await asyncpg.connect(_db_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        entry_id = await conn.fetchval("SELECT id FROM knowledge_entries ORDER BY id LIMIT 1")
        ticker = (await conn.fetchval("SELECT id FROM tickers WHERE id = 'NVDA'")
                  or await conn.fetchval("SELECT id FROM tickers LIMIT 1"))
        if entry_id is None or ticker is None:
            check("pré-requis présents (une entry, un ticker pour les FK)", False,
                  "→ base sans entry ou sans ticker")
            return

        tr = conn.transaction()
        await tr.start()
        try:
            # ── §1 le plan ──────────────────────────────────────────────────────────────────────
            print("[1] le plan s'écrit avec ses lignes")
            plan = CollectionPlan(
                ticker_id=ticker, framework_id="qualite_financiere", framework_version="v3.0.0",
                archetype="rentable",
                items=[
                    CollectionPlanItem(question_id="qf_1",
                                       ingredient_id="resultat_operationnel_apres_impot",
                                       statut="traduit", metrique="résultat d'exploitation après impôt",
                                       source_pressentie="10-K", ancre="clôture de l'exercice"),
                    CollectionPlanItem(question_id="qf_1", ingredient_id="cout_du_capital",
                                       statut="inobtenable",
                                       motif="aucun poste EDGAR ne produit le coût du capital"),
                ])
            plan_id = await persist_plan(conn, plan)
            row = await conn.fetchrow(
                "SELECT ticker_id, framework_id, framework_version, archetype "
                "FROM collection_plans WHERE id = $1", plan_id)
            check("le plan porte ses colonnes",
                  tuple(row) == (ticker, "qualite_financiere", "v3.0.0", "rentable"), f"→ {tuple(row)}")
            n_items = await conn.fetchval(
                "SELECT count(*) FROM collection_plan_items WHERE plan_id = $1", plan_id)
            check("les deux lignes sont écrites", n_items == 2, f"→ {n_items}")
            trad = await conn.fetchrow(
                "SELECT metrique, motif FROM collection_plan_items "
                "WHERE plan_id = $1 AND statut = 'traduit'", plan_id)
            check("la ligne traduite porte sa métrique, pas de motif",
                  trad is not None and trad["metrique"] is not None and trad["motif"] is None,
                  "→ ligne traduite absente" if trad is None else "")
            inob = await conn.fetchrow(
                "SELECT metrique, motif FROM collection_plan_items "
                "WHERE plan_id = $1 AND statut = 'inobtenable'", plan_id)
            check("la ligne inobtenable porte son motif, pas de métrique",
                  inob is not None and inob["motif"] is not None and inob["metrique"] is None,
                  "→ ligne inobtenable absente" if inob is None else "")

            # ── §2 l'aiguillage : liens + mandats ───────────────────────────────────────────────
            print("\n[2] l'aiguillage écrit ses liens de couverture ET ses mandats")
            res = ResultatAiguillage(
                liens=[LienCouverture(
                    framework_id="qualite_financiere", framework_version="v3.0.0",
                    question_id="qf_1", ingredient_id="resultat_operationnel_apres_impot",
                    entry_id=entry_id)],
                mandats=[MandatCollecte(
                    framework_id="qualite_financiere", framework_version="v3.0.0",
                    question_id="qf_1", ingredient_id="cout_du_capital",
                    motif="aucune source EDGAR", origine="inobtenable")],
                lignes_vues=2)
            await persist_aiguillage(conn, res, plan_id=plan_id)
            n_cov = await conn.fetchval(
                "SELECT count(*) FROM question_coverage WHERE entry_id = $1 "
                "AND question_id = 'qf_1' AND ingredient_id = 'resultat_operationnel_apres_impot'",
                entry_id)
            check("le lien est écrit dans question_coverage", n_cov >= 1, f"→ {n_cov}")
            n_mand = await conn.fetchval(
                "SELECT count(*) FROM framework_mandates WHERE plan_id = $1 AND origine = 'inobtenable'",
                plan_id)
            check("le mandat est écrit dans framework_mandates", n_mand == 1, f"→ {n_mand}")

            # ── §3 dernier rempart : les CHECK de base ──────────────────────────────────────────
            print("\n[3] la base REDIT le contrat — dernier rempart si une écriture le contournait")
            await _rejette(
                conn, "une ligne `traduit` sans métrique est REFUSÉE (CHECK charge)",
                "INSERT INTO collection_plan_items "
                "(plan_id, question_id, ingredient_id, statut, metrique, source_pressentie, ancre) "
                "VALUES ($1, 'qf_9', 'x', 'traduit', NULL, 's', 'a')", plan_id)
            await _rejette(
                conn, "un mandat d'origine inconnue est REFUSÉ (CHECK origine)",
                "INSERT INTO framework_mandates "
                "(framework_id, framework_version, question_id, ingredient_id, motif, origine) "
                "VALUES ('f', 'v', 'qf_1', 'x', 'm', 'autre')")
        finally:
            await tr.rollback()  # AUCUN résidu : la vérification ne pollue pas le réel
    finally:
        await conn.close()


asyncio.run(run())
print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
