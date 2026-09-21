"""Vérification de la PERSISTANCE du MANDAT du manager (lot 4, migration 043 —
`app/agents/v2/manager_persist.py`).

Lit l'ÉTAT PERSISTABLE, pas seulement la règle : les fonctions écrivent vraiment, on relit, on
vérifie. Tout se passe dans une transaction ROLLBACK — **aucun résidu** en base
(`feedback_fixture_pollue_le_reel`).

Exige le réseau `coolify` + `CHECK_DB_URL` : sans elle, la moitié « état persisté » n'est pas
mesurée → SORT EN ÉCHEC, jamais un saut de section (`feedback_check_degrade_en_sortant_a_zero`).

  • §1 un mandat manager s'écrit 'ouvert', par-question (ingredient_id NULL), avec son mandat
       exécutable, son ticker, et une trace vide (entry_ids '{}', pas d'après/instant) ;
  • §2 `persist_review` est IDEMPOTENT par question : re-persister la même revue n'ajoute PAS un
       second mandat ouvert (une requête permanente, pas un fait daté comme le collecteur) ;
  • §3 `serve_mandate` fait 'ouvert' → 'servi' avec l'avant/après du statut et les entries produites
       (T8) ; un mandat déjà servi ne se re-sert pas ;
  • §4 `read_open_mandates` ne rend QUE les mandats manager/comité ouverts — pas ceux du collecteur,
       pas les servis ;
  • §5 DERNIER REMPART — la base REFUSE une FORME ou une TRACE interdite (les CHECK 043 redisent le
       contrat, éprouvés en négatif ici même), et ACCEPTE l'origine `comite` (§8.2).
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

from app.agents.v2.manager import Decision, ManagerReview  # noqa: E402
from app.agents.v2.manager_persist import (  # noqa: E402
    persist_mandate,
    persist_review,
    read_open_mandates,
    serve_mandate,
)
from app.contracts.framework_answer_schema import (  # noqa: E402
    ControlesManager,
    FrameworkMandate,
)

FW = "qualite_financiere"
FV = "v3.0.0"


def _mandat(ticker, question_id, origine="manager_renvoi", mandat="re-collecter de quoi lever"):
    return FrameworkMandate(
        framework_id=FW, question_id=question_id, ticker_id=ticker, origine=origine,
        motif=f"renvoi manager : test {question_id}", mandat=f"{question_id} : {mandat}",
        etat="ouvert")


def _review_avec(*mandats):
    """Une revue minimale dont `mandats()` rend exactement `mandats` (via `mandats_manquantes`)."""
    return ManagerReview(decisions={}, questions_manquantes=[m.question_id for m in mandats],
                         mandats_manquantes=list(mandats))


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
        print(f"  FAIL {label} → mauvaise exception {type(e).__name__}: {e}")
        return
    await sp.rollback()
    fail += 1
    print(f"  FAIL {label} → la base a ACCEPTÉ la ligne interdite")


async def _accepte(conn, label, sql, *args):
    """La base DOIT accepter (le cas licite — ici l'origine `comite`)."""
    global ok, fail
    sp = conn.transaction()
    await sp.start()
    try:
        await conn.execute(sql, *args)
    except Exception as e:  # noqa: BLE001
        await sp.rollback()
        fail += 1
        print(f"  FAIL {label} → la base a REFUSÉ une ligne licite : {type(e).__name__}: {e}")
        return
    await sp.rollback()
    ok += 1
    print(f"  ok   {label}")


async def run():
    conn = await asyncpg.connect(_db_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        ticker = (await conn.fetchval("SELECT id FROM tickers WHERE id = 'NVDA'")
                  or await conn.fetchval("SELECT id FROM tickers LIMIT 1"))
        if ticker is None:
            check("pré-requis présent (un ticker pour la FK ticker_id)", False, "→ base sans ticker")
            return

        tr = conn.transaction()
        await tr.start()
        try:
            # ── §1 un mandat manager s'écrit 'ouvert', par-question ────────────────────────────
            print("[1] un mandat manager s'écrit 'ouvert', par-question, avec sa trace vide")
            mid = await persist_mandate(conn, _mandat(ticker, "qf_1"), framework_version=FV)
            row = await conn.fetchrow(
                "SELECT question_id, ticker_id, ingredient_id, mandat, origine, statut, "
                "statut_avant, statut_apres, consomme_at, entry_ids_produits, framework_version "
                "FROM framework_mandates WHERE id = $1", mid)
            check("par-question : `ingredient_id` NULL, `mandat` et `ticker_id` renseignés",
                  row is not None and row["ingredient_id"] is None and row["mandat"]
                  and row["ticker_id"] == ticker,
                  f"→ {None if row is None else (row['ingredient_id'], row['mandat'], row['ticker_id'])}")
            check("l'état de vie est 'ouvert' et la version est écrite (écart V10 fermé)",
                  row is not None and row["statut"] == "ouvert" and row["framework_version"] == FV,
                  f"→ {None if row is None else (row['statut'], row['framework_version'])}")
            check("trace vide sur un 'ouvert' : pas d'après/instant, aucune entry produite",
                  row is not None and row["statut_apres"] is None and row["consomme_at"] is None
                  and list(row["entry_ids_produits"]) == [],
                  f"→ {None if row is None else (row['statut_apres'], row['entry_ids_produits'])}")

            # ── §2 persist_review IDEMPOTENT par question ──────────────────────────────────────
            print("\n[2] persist_review est idempotent par question (une requête permanente)")
            rev = _review_avec(_mandat(ticker, "qf_5"))
            r1 = await persist_review(conn, rev, framework_version=FV)
            r2 = await persist_review(conn, rev, framework_version=FV)
            n_ouverts_qf5 = await conn.fetchval(
                "SELECT count(*) FROM framework_mandates WHERE ticker_id = $1 AND framework_id = $2 "
                "AND framework_version = $3 AND question_id = 'qf_5' "
                "AND origine = 'manager_renvoi' AND statut = 'ouvert'", ticker, FW, FV)
            check("le 1er passage écrit, le 2e ne duplique pas",
                  r1["mandats_ecrits"] == 1 and r2["mandats_ecrits"] == 0
                  and r2["mandats_deja_ouverts"] == 1,
                  f"→ r1={r1} r2={r2}")
            check("un seul mandat ouvert sur qf_5 après deux revues identiques",
                  n_ouverts_qf5 == 1, f"→ {n_ouverts_qf5}")

            # ── §3 serve_mandate : 'ouvert' → 'servi' avec avant/après (T8) ────────────────────
            print("\n[3] serve_mandate consomme le mandat : 'ouvert' → 'servi' avec l'avant/après")
            bougé = await serve_mandate(conn, mid, statut_avant="non_fondable",
                                        statut_apres="repondu", entry_ids_produits=[101, 102])
            servi = await conn.fetchrow(
                "SELECT statut, statut_avant, statut_apres, consomme_at, entry_ids_produits "
                "FROM framework_mandates WHERE id = $1", mid)
            check("la consommation a bougé une ligne", bougé is True, f"→ {bougé}")
            check("le mandat est 'servi' et porte l'avant, l'après, l'instant et les entries",
                  servi is not None and servi["statut"] == "servi"
                  and servi["statut_avant"] == "non_fondable" and servi["statut_apres"] == "repondu"
                  and servi["consomme_at"] is not None
                  and list(servi["entry_ids_produits"]) == [101, 102],
                  f"→ {None if servi is None else tuple(servi)}")
            re_bougé = await serve_mandate(conn, mid, statut_avant="x", statut_apres="y",
                                           entry_ids_produits=[])
            check("un mandat déjà servi ne se re-sert pas", re_bougé is False, f"→ {re_bougé}")

            # ── §4 read_open_mandates : que les manager/comité ouverts ─────────────────────────
            print("\n[4] read_open_mandates ne rend que les mandats manager/comité OUVERTS")
            # un mandat COLLECTEUR (origine echec_collecte, par-ingrédient) sur le même ticker
            await conn.execute(
                "INSERT INTO framework_mandates "
                "(framework_id, framework_version, question_id, ingredient_id, motif, origine) "
                "VALUES ($1, $2, 'qf_9', 'ing_x', 'échec collecte', 'echec_collecte')", FW, FV)
            ouverts = await read_open_mandates(conn, ticker_id=ticker, framework_id=FW,
                                               framework_version=FV)
            qids = sorted(m.question_id for m in ouverts)
            check("seul le mandat manager ouvert (qf_5) est rendu : ni le servi (qf_1), ni le "
                  "collecteur (qf_9)", qids == ["qf_5"], f"→ {qids}")
            check("les objets rendus portent bien leur mandat exécutable et leur origine",
                  all(m.mandat and m.origine == "manager_renvoi" for m in ouverts),
                  f"→ {[(m.origine, bool(m.mandat)) for m in ouverts]}")

            # ── §5 DERNIER REMPART : les CHECK 043 redisent le contrat ─────────────────────────
            print("\n[5] la base REDIT le contrat — dernier rempart si une écriture le contournait")
            base_cols = ("framework_id, framework_version, question_id, motif, origine, statut")
            await _rejette(
                conn, "FORME : un mandat manager AVEC ingredient_id est REFUSÉ (un faux, #76)",
                f"INSERT INTO framework_mandates ({base_cols}, ticker_id, mandat, ingredient_id) "
                "VALUES ($1, $2, 'q', 'm', 'manager_renvoi', 'ouvert', $3, 'md', 'ing')", FW, FV, ticker)
            await _rejette(
                conn, "FORME : un mandat manager SANS mandat exécutable est REFUSÉ",
                f"INSERT INTO framework_mandates ({base_cols}, ticker_id) "
                "VALUES ($1, $2, 'q', 'm', 'manager_renvoi', 'ouvert', $3)", FW, FV, ticker)
            await _rejette(
                conn, "FORME : un mandat collecteur SANS ingredient_id est REFUSÉ",
                f"INSERT INTO framework_mandates ({base_cols}) "
                "VALUES ($1, $2, 'q', 'm', 'echec_collecte', 'ouvert')", FW, FV)
            await _rejette(
                conn, "TRACE : un 'servi' SANS statut_avant est REFUSÉ (T8)",
                f"INSERT INTO framework_mandates ({base_cols}, ticker_id, mandat, statut_apres, "
                "consomme_at) VALUES ($1, $2, 'q', 'm', 'manager_renvoi', 'servi', $3, 'md', "
                "'repondu', now())", FW, FV, ticker)
            await _rejette(
                conn, "TRACE : un 'ouvert' AVEC consomme_at est REFUSÉ",
                f"INSERT INTO framework_mandates ({base_cols}, ticker_id, mandat, consomme_at) "
                "VALUES ($1, $2, 'q', 'm', 'manager_renvoi', 'ouvert', $3, 'md', now())", FW, FV, ticker)
            await _rejette(
                conn, "ORIGINE : une origine hors vocabulaire fermé est REFUSÉE",
                f"INSERT INTO framework_mandates ({base_cols}, ticker_id, mandat) "
                "VALUES ($1, $2, 'q', 'm', 'inventee', 'ouvert', $3, 'md')", FW, FV, ticker)
            await _accepte(
                conn, "ORIGINE : `comite` est ACCEPTÉE (§8.2, un renvoi comité)",
                f"INSERT INTO framework_mandates ({base_cols}, ticker_id, mandat) "
                "VALUES ($1, $2, 'q', 'm', 'comite', 'ouvert', $3, 'md')", FW, FV, ticker)
        finally:
            await tr.rollback()  # AUCUN résidu : la vérification ne pollue pas le réel
    finally:
        await conn.close()


asyncio.run(run())
print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
