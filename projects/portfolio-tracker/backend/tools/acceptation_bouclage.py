"""Acceptation de bout en bout du BOUCLAGE comité → collecte (lot 5) — la boucle #71 fermée, mesurée
contre la VRAIE base, en transaction ROLLBACK (zéro résidu).

CE QUE ÇA MESURE, ET LA FRONTIÈRE HONNÊTE
-----------------------------------------
Le CŒUR neuf du lot est le WIRING DB : lire un renvoi ouvert (`read_open_mandates`), retrouver son
handle (`id_du_mandat_ouvert`), le SERVIR (`serve_mandate` : ouvert→servi, avant/après figés), et en
tirer la note honnête (`MandatBoucle`/`CompteRenduBouclage` + `classer_sort`). C'est ce chemin-là qui
n'avait aucun appelant de production le 2026-09-25. On le rejoue ICI de bout en bout contre
`db_portfolio`, dans une transaction annulée — comme l'acceptation T8 du manager (#77).

Ce que ce test NE rejoue PAS avec de vrais tokens : la re-collecte scopée (`executer_collecte_
framework(questions=…)`) et la re-analyse. Ces composants sont déjà prouvés (chaîne du 2026-09-25,
`check_bouclage §5` pour le scope du pont) ; les rejouer ici dépenserait du modèle ET écrirait en prod
(pas de rollback possible : ils ouvrent leurs propres sessions). La composition `boucler_renvois` est
gardée par `check_bouclage §4` (appelants comptés) — « exercé » au niveau code.

⚠️ Il RAPPORTE aussi l'état réel : combien de mandats manager/comité sont OUVERTS en base. S'il y en a,
le passage RÉEL complet (`bash tools/boucler_renvois.sh …`) peut tourner ; s'il n'y en a aucun, la
boucle live n'a rien à faire tant qu'aucun renvoi n'a été produit (les passages ont acquitté).

⚠️ Jamais dans `portfolio-backend`. Réseau `coolify` + vrai `.env` ; le web/modèle ne sont pas sollicités.
"""
from __future__ import annotations

import asyncio
import os
import sys

FW = "defendabilite"
Q = "mo_1"

crit_ok = crit_ko = 0


def crit(label, cond, detail=""):
    global crit_ok, crit_ko
    if cond:
        crit_ok += 1
        print(f"  OK  {label}")
    else:
        crit_ko += 1
        print(f"  KO  {label} {detail}")


def _bilan_et_sortie(code):
    print(f"\nBILAN acceptation bouclage — {crit_ok} critère(s) OK / {crit_ko} échec(s)")
    sys.exit(code)


_db_url = os.environ.get("DATABASE_URL", "") or os.environ.get("CHECK_DB_URL", "")
if not _db_url or "@" not in _db_url:
    print("  pas mesurable — DATABASE_URL absente ou factice")
    _bilan_et_sortie(2)

import asyncpg  # noqa: E402

from app.agents.v2.bouclage import classer_sort  # noqa: E402
from app.agents.v2.frameworks import load_frameworks  # noqa: E402
from app.agents.v2.manager_persist import (  # noqa: E402
    id_du_mandat_ouvert,
    persist_mandate,
    read_open_mandates,
    serve_mandate,
)
from app.contracts.bouclage_schema import (  # noqa: E402
    SORTS_BOUCLAGE,
    CompteRenduBouclage,
    MandatBoucle,
)
from app.contracts.framework_answer_schema import FrameworkMandate  # noqa: E402


async def run():
    fichier = load_frameworks()
    version = fichier.schema_version
    conn = await asyncpg.connect(_db_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        ticker = (await conn.fetchval("SELECT id FROM tickers WHERE id = 'RVMD'")
                  or await conn.fetchval("SELECT id FROM tickers LIMIT 1"))
        if ticker is None:
            crit("pré-requis présent (un ticker pour la FK)", False, "→ base sans ticker")
            _bilan_et_sortie(2)

        # ── ÉTAT RÉEL (informatif, hors transaction) : y a-t-il des renvois à boucler en vrai ? ──
        reels = await read_open_mandates(
            conn, ticker_id=ticker, framework_id=FW, framework_version=version)
        tous_reels = await conn.fetchval(
            "SELECT count(*) FROM framework_mandates "
            "WHERE origine IN ('manager_renvoi','comite') AND statut='ouvert'")
        print(f"  [état réel] mandats manager/comité OUVERTS en base : {tous_reels} "
              f"(dont {len(reels)} sur {ticker}/{FW}). "
              + ("→ un passage RÉEL complet est possible." if tous_reels
                 else "→ aucun renvoi ouvert : la boucle live n'a rien à faire pour l'instant."))
        avant_count = tous_reels

        # ── LE BOUT EN BOUT, EN ROLLBACK : un renvoi seedé, lu, servi, transformé en note ────────
        tr = conn.transaction()
        await tr.start()
        try:
            mandate = FrameworkMandate(
                framework_id=FW, question_id=Q, ticker_id=ticker, origine="manager_renvoi",
                motif="preuve de barrière insuffisante — barrière affirmée sans mécanisme cité",
                mandat="Chercher l'exclusivité réglementaire et le portefeuille de brevets de "
                       "l'émetteur, avec leur durée résiduelle, sources primaires.",
                etat="ouvert")
            mid = await persist_mandate(conn, mandate, framework_version=version)
            crit("[1] un renvoi manager est persisté OUVERT (persist_mandate)", isinstance(mid, int))

            ouverts = await read_open_mandates(
                conn, ticker_id=ticker, framework_id=FW, framework_version=version)
            le = next((m for m in ouverts if m.question_id == Q), None)
            crit("[2] read_open_mandates le rend (par-question, mandat exécutable, origine manager)",
                 le is not None and le.origine == "manager_renvoi" and bool(le.mandat),
                 f"→ {le}")

            handle = await id_du_mandat_ouvert(
                conn, ticker_id=ticker, framework_id=FW, framework_version=version, question_id=Q)
            crit("[3] id_du_mandat_ouvert retrouve le handle à servir (détenteur unique)",
                 handle == mid, f"→ {handle} vs {mid}")

            entries_produites = [900001]  # entries qu'une re-collecte aurait fondées (synthétiques)
            bouge = await serve_mandate(
                conn, handle, statut_avant="non_fondable", statut_apres="repondu",
                entry_ids_produits=entries_produites)
            row = await conn.fetchrow(
                "SELECT statut, statut_avant, statut_apres, consomme_at, entry_ids_produits "
                "FROM framework_mandates WHERE id=$1", mid)
            crit("[4] serve_mandate consomme : ouvert→servi, avant/après/instant figés",
                 bouge and row["statut"] == "servi" and row["statut_avant"] == "non_fondable"
                 and row["statut_apres"] == "repondu" and row["consomme_at"] is not None,
                 f"→ {None if row is None else dict(row)}")

            apres = await read_open_mandates(
                conn, ticker_id=ticker, framework_id=FW, framework_version=version)
            crit("[5] un mandat servi ne réapparaît PAS dans les ouverts (pas de re-service)",
                 all(m.question_id != Q for m in apres), f"→ {[m.question_id for m in apres]}")

            # La NOTE HONNÊTE assemblée depuis l'état servi — le sort DÉRIVÉ, jamais déclaré.
            sort = classer_sort("non_fondable", "repondu", a_tente_collecte=True, dispensee=False)
            note = CompteRenduBouclage(
                ticker_id=ticker, framework_id=FW, framework_version=version, mandats_lus=1,
                boucles=[MandatBoucle(
                    question_id=Q, mandat_id=mid, sort=sort,
                    statut_avant="non_fondable", statut_apres="repondu",
                    entry_ids_produits=list(row["entry_ids_produits"] or []),
                    motif="fondée par la re-collecte")])
            crit("[6] la note honnête classe ce renvoi `acquis` (statut passé au-dessus de non_fondable)",
                 sort == "acquis" and note.boucles[0].sort == "acquis")
            crit("[7] les quatre sorts de la note existent (vocabulaire fermé)",
                 set(SORTS_BOUCLAGE) == {"acquis", "collecte_insuffisante",
                                        "mandat_non_executable", "classe_sans_suite"})
        finally:
            await tr.rollback()

        # ── ZÉRO RÉSIDU : le rollback a tout annulé ──────────────────────────────────────────────
        apres_count = await conn.fetchval(
            "SELECT count(*) FROM framework_mandates "
            "WHERE origine IN ('manager_renvoi','comite') AND statut='ouvert'")
        crit("[0] ROLLBACK — aucun résidu (le compte de mandats ouverts est inchangé)",
             apres_count == avant_count, f"→ avant {avant_count}, après {apres_count}")
    finally:
        await conn.close()

    _bilan_et_sortie(1 if crit_ko else 0)


if __name__ == "__main__":
    asyncio.run(run())
