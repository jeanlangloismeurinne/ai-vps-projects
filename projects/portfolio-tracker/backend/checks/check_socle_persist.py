"""Vérification de la PUBLICATION du socle des comptes contre la VRAIE base (`socle_feed.publier_socle`).

Tout se joue dans UNE transaction annulée à la fin : zéro résidu (`feedback_fixture_pollue_le_reel`).
L'inventaire est celui de RVMD copié du réel (`fixtures/socle_comptes/RVMD.json`) — aucun réseau.

  §1 PUBLIER : une pièce, tier A, `mesure`, datée de la dernière clôture (fait) et du dépôt (document) ;
     la structure relue en base rend les mêmes chiffres que la fonction pure ;
  §2 IDEMPOTENCE : le même dépôt ne crée pas de version (`a_jour`, même pièce) ;
  §3 UN DÉPÔT NOUVEAU REMPLACE : une nouvelle version, l'ancienne supersédée, UNE pièce courante ;
  §4 LE DOSSIER LA PORTE : jointe d'office, reconnue par `socle_au_dossier`, structure comprise.

Lancer : `bash checks/avec_base.sh check_socle_persist` (jamais dans `portfolio-backend`).
"""
import asyncio
import copy
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan  # noqa: E402

b = Bilan()
_db_url = os.environ.get("CHECK_DB_URL", "")
if not _db_url or "@" not in _db_url:
    b.check(False, "§persistance non exécutée — CHECK_DB_URL absente ou factice ; l'état persisté "
                   "n'a PAS été mesuré")
    sys.exit(b.summary())

import asyncpg  # noqa: E402

from app.agents.v2.dossier import charger_dossier  # noqa: E402
from app.agents.v2.frameworks import socle_au_dossier  # noqa: E402
from app.knowledge.socle_comptes import METRIC, valeur_du_socle  # noqa: E402
from app.knowledge.socle_feed import publier_socle  # noqa: E402

FIX = json.loads((Path(__file__).resolve().parent / "fixtures" / "socle_comptes" / "RVMD.json").read_text())
TICKER = "RVMD"
M = 1e6
DETTE = "dette_financiere_courante + dette_financiere_non_courante + financement_adosse_aux_redevances"


async def courants(conn):
    return await conn.fetch(
        "SELECT id, nature, reliability_tier, source_date, date_du_fait, date_du_document, portee_temporelle, "
        "content_structured, superseded_by FROM knowledge_entries "
        "WHERE ticker_id = $1 AND superseded_by IS NULL AND content_structured->>'metric' = $2",
        TICKER, METRIC)


async def main():
    conn = await asyncpg.connect(_db_url.replace("postgresql+asyncpg://", "postgresql://"))
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    tr = conn.transaction()
    await tr.start()
    try:
        avant = await courants(conn)
        # §1 ─────────────────────────────────────────────────────────────────────────────────────
        p1 = await publier_socle(conn, TICKER, cik=FIX["cik"], raison_sociale="Revolution Medicines, Inc.",
                                 faits=FIX["faits"], embed=False)
        rows = await courants(conn)
        b.require(rows, 1, "§1 une seule pièce « socle des comptes » courante pour le titre")
        r = rows[0] if rows else {}
        b.check(p1.statut == ("a_jour" if avant else "publie"), f"§1 statut {p1.statut}")
        b.check(r.get("reliability_tier") == "A" and r.get("nature") == "mesure",
                f"§1 tier A et nature `mesure` dérivés au guichet ({r.get('reliability_tier')}, {r.get('nature')})")
        b.check(r.get("portee_temporelle") == "constatee" and r.get("date_du_fait") == date(2026, 6, 30)
                and r.get("date_du_document") == date(2026, 8, 5),
                f"§1 datée du dernier fait (30/06) et du dépôt (05/08) ({r.get('date_du_fait')}, "
                f"{r.get('date_du_document')})")
        st = r.get("content_structured") or {}
        b.check(isinstance(st, dict) and st.get("metric") == METRIC, "§1 la structure revient en OBJET (JSONB)")
        v, _ = valeur_du_socle(st, DETTE, "dernier_bilan") if isinstance(st, dict) else (None, "")
        b.check(v is not None and abs(v - 1035.976 * M) < 1000, f"§1 relue en base, la dette brute vaut 1 035,976 M$ ({v})")

        # §2 ─────────────────────────────────────────────────────────────────────────────────────
        p2 = await publier_socle(conn, TICKER, cik=FIX["cik"], raison_sociale="Revolution Medicines, Inc.",
                                 faits=FIX["faits"], embed=False)
        b.check(p2.statut == "a_jour" and p2.entry_id == p1.entry_id,
                f"§2 le même dépôt ne crée pas de version ({p2.statut}, #{p2.entry_id} vs #{p1.entry_id})")
        b.require(await courants(conn), 1, "§2 toujours UNE pièce courante")

        # §3 ─────────────────────────────────────────────────────────────────────────────────────
        f3 = copy.deepcopy(FIX["faits"])
        f3["AccruedRoyaltiesCurrentAndNoncurrent"] = [
            {**p, "val": p["val"] + 1_000_000} if p.get("end") == "2026-06-30" else p
            for p in f3["AccruedRoyaltiesCurrentAndNoncurrent"]]
        p3 = await publier_socle(conn, TICKER, cik=FIX["cik"], raison_sociale="Revolution Medicines, Inc.",
                                 faits=f3, embed=False)
        rows3 = await courants(conn)
        b.check(p3.statut == "publie" and p3.entry_id != p1.entry_id and p1.entry_id in p3.remplace,
                f"§3 un dépôt qui change un chiffre publie une version neuve qui remplace l'ancienne ({p3})")
        b.require(rows3, 1, "§3 après remplacement, UNE pièce courante (#43 : combien de lignes actives ?)")
        ancienne = await conn.fetchval("SELECT superseded_by FROM knowledge_entries WHERE id = $1", p1.entry_id)
        b.check(ancienne == p3.entry_id, f"§3 l'ancienne pointe la nouvelle (A1) ({ancienne})")

        # §4 ─────────────────────────────────────────────────────────────────────────────────────
        d = await charger_dossier(conn, ticker_id=TICKER, framework_id="qualite_financiere",
                                  framework_version="v3.0.0", plafond=60, joindre=[p3.entry_id])
        trouve = socle_au_dossier(d.entries)
        b.check(p3.entry_id in d.jointes and trouve is not None and trouve[0] == p3.entry_id,
                f"§4 le dossier porte le socle joint d'office et le reconnaît ({d.jointes}, {trouve and trouve[0]})")
        b.check(trouve is not None and isinstance(trouve[1], dict) and trouve[1].get("cellules"),
                "§4 … avec sa structure (le code relit l'encadré dans la pièce même)")
    finally:
        await tr.rollback()   # AUCUN résidu
        await conn.close()


asyncio.run(main())
sys.exit(b.summary())
