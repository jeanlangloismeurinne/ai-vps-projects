"""Vérification de la PERSISTANCE de la RÉPONSE et de la DISPENSE (lot 3 maillon 2, migration 040
— `app/agents/v2/framework_persist.py`).

Lit l'ÉTAT PERSISTABLE, pas seulement la règle : les fonctions écrivent vraiment, on relit, on
vérifie. Tout se passe dans une transaction ROLLBACK — **aucun résidu** en base
(`feedback_fixture_pollue_le_reel`).

Exige le réseau `coolify` + `CHECK_DB_URL` : sans elle, la moitié « état persisté » n'est pas
mesurée → SORT EN ÉCHEC, jamais un saut de section (`feedback_check_degrade_en_sortant_a_zero`).

  • §1 une réponse `repondu` s'écrit avec ses colonnes dénormalisées ET son `answer_json` complet ;
  • §2 une correction du MÊME analyste SUPERSÈDE la ligne courante de sa lignée ;
  • §2bis un autre analyste sur la MÊME question ne supersède PERSONNE (§3.4, N ≥ 1) ;
  • §3 une dispense s'écrit, et se redéclarer met à jour son motif SANS dupliquer la ligne ;
  • §4 un `non_fondable` porte son `gap` dans `answer_json`, ses colonnes dénormalisées de
       `sans_objet`/`approximation` restent NULL — aucun bloc étranger ne fuit dans une colonne ;
  • §5 DERNIER REMPART — la base REFUSE un statut hors vocabulaire fermé : le CHECK SQL redit le
       contrat, éprouvé en négatif ici même.
  • §6 POINT 14 (séance du 2026-10-18) — une réponse ÉCRITE sert le mandat manager/comité OUVERT de
       SA question (`persist_answer_detail`, trace correcte avant/après/entries) ; un mandat d'une
       AUTRE question, d'un AUTRE ticker, ou d'origine COLLECTEUR n'est PAS touché.
  • §7 après cette fermeture, un NOUVEAU renvoi (`persist_review`) sur la MÊME question crée un
       mandat NEUF (id différent, SON PROPRE motif) — l'ancien, servi, garde son motif périmé intact ;
       jamais une vieille demande n'absorbe un motif neuf.
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

from app.agents.v2.framework_persist import (  # noqa: E402
    persist_answer,
    persist_answer_detail,
    persist_dispense,
)
from app.agents.v2.manager import ManagerReview  # noqa: E402
from app.agents.v2.manager_persist import persist_mandate, persist_review  # noqa: E402
from app.contracts.framework_answer_schema import (  # noqa: E402
    Fondation,
    FrameworkAnswer,
    FrameworkMandate,
    Reponse,
)
from app.contracts.readiness_report_schema import GapItem  # noqa: E402

FV = "v3.0.0"


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
    # Connexion NUE, hors du pool applicatif : le codec jsonb enregistré dans `db/database.py`
    # (`init_pool`) ne s'applique qu'aux connexions du pool. `persist_answer` écrit un dict Python
    # tel quel (contrat de la fonction, cf. sa docstring), donc on le rejoue ici à l'identique.
    import json as _json
    await conn.set_type_codec("jsonb", encoder=_json.dumps, decoder=_json.loads, schema="pg_catalog")
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
            # ── §1 une réponse `repondu` s'écrit ────────────────────────────────────────────────
            print("[1] une réponse `repondu` s'écrit avec ses colonnes dénormalisées")
            rep1 = FrameworkAnswer(
                framework_id="qualite_financiere", framework_version=FV, question_id="qf_1",
                ticker_id=ticker, analyste="analyste_1", statut="repondu",
                reponse=Reponse(verbatim="ROIC de 18%", chiffres_cles=[{"id": "rendement_du_capital_employe", "unite": "%", "valeur": 18.0, "date_ou_periode": "moyenne 2020-2024"}]),
                fondation=Fondation(cited_entry_ids=[entry_id], rang_derive="A",
                                    nature_effective="mesure"))
            id1 = await persist_answer(conn, rep1)
            row1 = await conn.fetchrow(
                "SELECT framework, framework_version, question_id, ticker_id, analyste, statut, "
                "cited_entry_ids, rang_degrade, superseded_by, answer_json "
                "FROM framework_answers WHERE id = $1", id1)
            check("les colonnes dénormalisées portent les bonnes valeurs",
                  row1 is not None and (row1["framework"], row1["framework_version"],
                                        row1["question_id"], row1["ticker_id"], row1["analyste"],
                                        row1["statut"]) ==
                  ("qualite_financiere", FV, "qf_1", ticker, "analyste_1", "repondu"),
                  f"→ {None if row1 is None else tuple(row1)[:6]}")
            check("`cited_entry_ids` et `rang_degrade` sont dénormalisés",
                  row1 is not None and row1["cited_entry_ids"] == [entry_id]
                  and row1["rang_degrade"] == "A",
                  f"→ {None if row1 is None else (row1['cited_entry_ids'], row1['rang_degrade'])}")
            check("`answer_json` porte le contrat complet (le bloc `reponse`)",
                  row1 is not None
                  and (row1["answer_json"].get("reponse") or {}).get("verbatim") == "ROIC de 18%",
                  f"→ {None if row1 is None else row1['answer_json'].get('reponse')}")
            check("une ligne neuve n'a pas de `superseded_by`", row1 is not None
                  and row1["superseded_by"] is None, f"→ {None if row1 is None else row1['superseded_by']}")

            # ── §2 une correction du MÊME analyste supersède ────────────────────────────────────
            print("\n[2] une correction du MÊME analyste supersède la ligne courante de sa lignée")
            rep2 = rep1.model_copy(update={
                "reponse": Reponse(verbatim="ROIC de 19%", chiffres_cles=[{"id": "rendement_du_capital_employe", "unite": "%", "valeur": 19.0, "date_ou_periode": "moyenne 2021-2025"}])})
            id2 = await persist_answer(conn, rep2)
            superseded_by = await conn.fetchval(
                "SELECT superseded_by FROM framework_answers WHERE id = $1", id1)
            check("l'ancienne ligne pointe la nouvelle via `superseded_by`",
                  superseded_by == id2, f"→ {superseded_by} attendu {id2}")
            n_courantes = await conn.fetchval(
                "SELECT count(*) FROM framework_answers WHERE ticker_id = $1 AND framework = $2 "
                "AND framework_version = $3 AND question_id = $4 AND analyste = $5 "
                "AND superseded_by IS NULL",
                ticker, "qualite_financiere", FV, "qf_1", "analyste_1")
            check("une seule ligne courante reste sur la lignée `analyste_1`", n_courantes == 1,
                  f"→ {n_courantes}")

            # ── §2bis un AUTRE analyste ne supersède personne (§3.4, N ≥ 1) ────────────────────
            print("\n[2bis] un autre analyste sur la même question ne supersède PERSONNE (§3.4)")
            rep3 = rep1.model_copy(update={"analyste": "analyste_2"})
            id3 = await persist_answer(conn, rep3)
            sup3 = await conn.fetchval(
                "SELECT superseded_by FROM framework_answers WHERE id = $1", id3)
            sup2 = await conn.fetchval(
                "SELECT superseded_by FROM framework_answers WHERE id = $1", id2)
            check("`analyste_2` n'est pas superseded, `analyste_1` (la ligne courante) non plus",
                  sup3 is None and sup2 is None, f"→ sup3={sup3} sup2={sup2}")
            n_courantes_totales = await conn.fetchval(
                "SELECT count(*) FROM framework_answers WHERE ticker_id = $1 AND framework = $2 "
                "AND framework_version = $3 AND question_id = $4 AND superseded_by IS NULL "
                # Les seules lignées de CE test : NVDA porte depuis le 2026-10-12 une vraie réponse qf_1
                # (`passage_manuel_v3`, #1190), qui faisait compter 3 — l'assert lisait la prod, pas sa fixture.
                "AND analyste IN ('analyste_1', 'analyste_2')",
                ticker, "qualite_financiere", FV, "qf_1")
            check("deux lignes courantes coexistent (une par analyste)", n_courantes_totales == 2,
                  f"→ {n_courantes_totales}")

            # ── §3 une dispense s'écrit, se redéclarer met à jour SANS dupliquer ────────────────
            print("\n[3] une dispense s'écrit, se redéclarer met à jour le motif sans dupliquer")
            await persist_dispense(conn, ticker_id=ticker, framework_id="qualite_financiere",
                                    framework_version=FV, question_id="qf_7",
                                    motif="pré-revenus, ROIC sans objet")
            await persist_dispense(conn, ticker_id=ticker, framework_id="qualite_financiere",
                                    framework_version=FV, question_id="qf_7",
                                    motif="motif corrigé")
            n_disp = await conn.fetchval(
                "SELECT count(*) FROM framework_dispenses WHERE ticker_id = $1 AND framework_id = $2 "
                "AND framework_version = $3 AND question_id = $4",
                ticker, "qualite_financiere", FV, "qf_7")
            motif_disp = await conn.fetchval(
                "SELECT motif FROM framework_dispenses WHERE ticker_id = $1 AND framework_id = $2 "
                "AND framework_version = $3 AND question_id = $4",
                ticker, "qualite_financiere", FV, "qf_7")
            check("une seule ligne de dispense (idempotence)", n_disp == 1, f"→ {n_disp}")
            check("le motif a été mis à jour, pas ignoré", motif_disp == "motif corrigé",
                  f"→ {motif_disp}")

            # ── §4 un `non_fondable` ne fait fuiter aucun bloc étranger ─────────────────────────
            print("\n[4] un `non_fondable` porte son gap en JSON, aucune colonne étrangère ne fuit")
            nf = FrameworkAnswer(
                framework_id="qualite_financiere", framework_version=FV, question_id="qf_9",
                ticker_id=ticker, analyste="analyste_1", statut="non_fondable",
                gap=GapItem(dimension="qualite_financiere", champs_cibles=["qf_9"],
                            manque="aucune entry ne fonde qf_9", coverage_actuelle="aucune",
                            priorite="haute"))
            id4 = await persist_answer(conn, nf)
            row4 = await conn.fetchrow(
                "SELECT statut, rang_degrade, methode_approximation, ingredients, motif, "
                "answer_json FROM framework_answers WHERE id = $1", id4)
            check("`rang_degrade`/`methode_approximation`/`ingredients`/`motif` restent NULL",
                  row4 is not None and row4["rang_degrade"] is None
                  and row4["methode_approximation"] is None and row4["ingredients"] is None
                  and row4["motif"] is None,
                  f"→ {None if row4 is None else tuple(row4)[1:5]}")
            check("`answer_json` porte le `gap` complet",
                  row4 is not None
                  and (row4["answer_json"].get("gap") or {}).get("champs_cibles") == ["qf_9"],
                  f"→ {None if row4 is None else row4['answer_json'].get('gap')}")

            # ── §5 dernier rempart : le CHECK de statut ─────────────────────────────────────────
            print("\n[5] la base REDIT le contrat — dernier rempart si une écriture le contournait")
            await _rejette(
                conn, "un statut hors vocabulaire fermé est REFUSÉ (CHECK statut)",
                "INSERT INTO framework_answers "
                "(framework, framework_version, question_id, ticker_id, analyste, statut, "
                " answer_json) VALUES ('f', $1, 'q', $2, 'a', 'invalide', '{}'::jsonb)",
                FV, ticker)

            # ── §6 POINT 14 : une réponse écrite SERT le mandat ouvert de SA question ───────────
            print("\n[6] `persist_answer` ferme le mandat manager/comité ouvert de SA question (point 14)")
            mandat_qf2 = await persist_mandate(
                conn, FrameworkMandate(
                    framework_id="qualite_financiere", question_id="qf_2", ticker_id=ticker,
                    origine="manager_renvoi", motif="renvoi manager : test §6",
                    mandat="qf_2 : re-collecter", etat="ouvert"),
                framework_version=FV)
            # Un mandat sur une AUTRE question (même ticker) — ne doit PAS être touché.
            mandat_qf3 = await persist_mandate(
                conn, FrameworkMandate(
                    framework_id="qualite_financiere", question_id="qf_3", ticker_id=ticker,
                    origine="manager_renvoi", motif="renvoi manager : test §6 (autre question)",
                    mandat="qf_3 : re-collecter", etat="ouvert"),
                framework_version=FV)
            # Un mandat sur la MÊME question mais un AUTRE ticker — ne doit pas être touché non plus.
            ticker2 = await conn.fetchval("SELECT id FROM tickers WHERE id <> $1 LIMIT 1", ticker)
            mandat_qf2_autre_ticker = None
            if ticker2 is not None:
                mandat_qf2_autre_ticker = await persist_mandate(
                    conn, FrameworkMandate(
                        framework_id="qualite_financiere", question_id="qf_2", ticker_id=ticker2,
                        origine="manager_renvoi", motif="renvoi manager : test §6 (autre ticker)",
                        mandat="qf_2 : re-collecter", etat="ouvert"),
                    framework_version=FV)
            # Un mandat COLLECTEUR, MÊME question/ticker, mais hors du canal manager/comité — exclu
            # par construction (`id_du_mandat_ouvert` ne lit QUE `manager_renvoi`/`comite`).
            await conn.execute(
                "INSERT INTO framework_mandates (framework_id, framework_version, question_id, "
                "ticker_id, ingredient_id, motif, origine, cause) "
                "VALUES ($1, $2, 'qf_2', $3, 'ing_test_6', 'échec collecte test §6', "
                "'echec_collecte', 'recherche_epuisee')",
                "qualite_financiere", FV, ticker)

            rep6 = FrameworkAnswer(
                framework_id="qualite_financiere", framework_version=FV, question_id="qf_2",
                ticker_id=ticker, analyste="analyste_6", statut="repondu",
                reponse=Reponse(verbatim="marge de 22%", chiffres_cles=[]),
                fondation=Fondation(cited_entry_ids=[entry_id], rang_derive="A",
                                    nature_effective="mesure"))
            persiste6 = await persist_answer_detail(conn, rep6)
            check("la réponse écrite sur qf_2 SERT le mandat qf_2 (`mandat_servi_id` rendu)",
                  persiste6.mandat_servi_id == mandat_qf2,
                  f"→ {persiste6.mandat_servi_id} attendu {mandat_qf2}")
            row_mandat_qf2 = await conn.fetchrow(
                "SELECT statut, statut_avant, statut_apres, consomme_at, entry_ids_produits "
                "FROM framework_mandates WHERE id = $1", mandat_qf2)
            check("trace correcte : avant=non_fondable (rien avant), après=repondu, instant posé, "
                  "entries = cited_entry_ids de la réponse",
                  row_mandat_qf2 is not None and row_mandat_qf2["statut"] == "servi"
                  and row_mandat_qf2["statut_avant"] == "non_fondable"
                  and row_mandat_qf2["statut_apres"] == "repondu"
                  and row_mandat_qf2["consomme_at"] is not None
                  and list(row_mandat_qf2["entry_ids_produits"]) == [entry_id],
                  f"→ {None if row_mandat_qf2 is None else tuple(row_mandat_qf2)}")

            statut_qf3 = await conn.fetchval(
                "SELECT statut FROM framework_mandates WHERE id = $1", mandat_qf3)
            check("un mandat d'une AUTRE question n'est pas touché", statut_qf3 == "ouvert",
                  f"→ {statut_qf3}")
            if mandat_qf2_autre_ticker is not None:
                statut_autre_ticker = await conn.fetchval(
                    "SELECT statut FROM framework_mandates WHERE id = $1", mandat_qf2_autre_ticker)
                check("un mandat de la MÊME question mais un AUTRE ticker n'est pas touché",
                      statut_autre_ticker == "ouvert", f"→ {statut_autre_ticker}")
            statut_collecteur = await conn.fetchval(
                "SELECT statut FROM framework_mandates WHERE origine = 'echec_collecte' "
                "AND question_id = 'qf_2' AND ticker_id = $1 ORDER BY id DESC LIMIT 1", ticker)
            check("un mandat COLLECTEUR (même question/ticker, autre origine) n'est pas touché",
                  statut_collecteur == "ouvert", f"→ {statut_collecteur}")

            # ── §7 un NOUVEAU renvoi sur la MÊME question crée un mandat NEUF ───────────────────
            print("\n[7] après la fermeture, un NOUVEAU renvoi sur la MÊME question ouvre un mandat NEUF")
            mandat_neuf_obj = FrameworkMandate(
                framework_id="qualite_financiere", question_id="qf_2", ticker_id=ticker,
                origine="manager_renvoi", motif="renvoi manager : motif NEUF test §7",
                mandat="qf_2 : re-collecter (second renvoi)", etat="ouvert")
            review_neuve = ManagerReview(decisions={}, questions_manquantes=["qf_2"],
                                        mandats_manquantes=[mandat_neuf_obj])
            bilan7 = await persist_review(conn, review_neuve, framework_version=FV)
            check("le second renvoi ÉCRIT (l'ancien mandat est SERVI, pas 'ouvert' : pas d'idempotence)",
                  bilan7["mandats_ecrits"] == 1 and bilan7["mandats_deja_ouverts"] == 0,
                  f"→ {bilan7}")
            mandat_qf2_neuf = bilan7["ids"][0]
            check("le mandat NEUF a un id DIFFÉRENT de l'ancien (servi)",
                  mandat_qf2_neuf != mandat_qf2, f"→ neuf={mandat_qf2_neuf} ancien={mandat_qf2}")
            motif_neuf = await conn.fetchval(
                "SELECT motif FROM framework_mandates WHERE id = $1", mandat_qf2_neuf)
            check("le mandat NEUF porte SON PROPRE motif, jamais celui de l'ancien",
                  motif_neuf == "renvoi manager : motif NEUF test §7", f"→ {motif_neuf}")
            ancien_motif_toujours = await conn.fetchval(
                "SELECT motif FROM framework_mandates WHERE id = $1", mandat_qf2)
            check("l'ANCIEN mandat (servi) garde intact son motif périmé — jamais réécrit, "
                  "jamais absorbé par le neuf",
                  ancien_motif_toujours == "renvoi manager : test §6", f"→ {ancien_motif_toujours}")
        finally:
            await tr.rollback()  # AUCUN résidu : la vérification ne pollue pas le réel
    finally:
        await conn.close()


asyncio.run(run())
print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
