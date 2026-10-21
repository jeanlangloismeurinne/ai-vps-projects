"""Vérification de la PUBLICATION de la ventilation publiée contre la VRAIE base
(`ventilation_feed.publier_ventilation`) — lot M2, calqué sur `check_socle_persist.py`.

Tout se joue dans UNE transaction annulée à la fin : zéro résidu (`feedback_fixture_pollue_le_reel`).
Les dépôts sont ceux des fixtures copiées du réel (`checks/fixtures/ventilation/*.xml.gz`) — aucun
réseau.

  §1 PUBLIER (NVDA, `ventilee`) : une pièce courante, tier A, `mesure`, datée du dernier fait/dépôt ;
  §2 IDEMPOTENCE : le même dépôt ne crée pas de version (`a_jour`, même pièce) ;
  §3 UNE CELLULE CHANGÉE : une nouvelle version, l'ancienne `superseded_by` ;
  §4 `secteur_unique` (RVMD) : aucune ligne écrite — le constat est recalculable (#77) ;
  §5 famille bancaire (JPM) : refus NOMMÉ, aucune ligne écrite.

Lancer : `bash checks/avec_base.sh check_ventilation_persist` (jamais dans `portfolio-backend`).
"""
import asyncio
import copy
import gzip
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

from app.knowledge import ventilation as vt  # noqa: E402
from app.knowledge import ventilation_xbrl as vx  # noqa: E402
from app.knowledge.socle_comptes import charger_gabarit, charger_reclassements, reconstituer, structure_du_socle  # noqa: E402
from app.knowledge.ventilation_feed import METRIC, publier_ventilation  # noqa: E402

GAB = charger_gabarit()
REF = vt.charger_referentiel()
FIX = Path(__file__).resolve().parent / "fixtures" / "ventilation"
SOCLE_FIX = Path(__file__).resolve().parent / "fixtures" / "socle_comptes"
M = 1e6


def charger_depot(ticker: str, accn: str) -> vt.Depot:
    manifeste = json.loads((FIX / f"{ticker}_{accn}.json").read_text(encoding="utf-8"))
    inst = gzip.decompress((FIX / f"{ticker}_{accn}_inst.xml.gz").read_bytes())
    lab = gzip.decompress((FIX / f"{ticker}_{accn}_lab.xml.gz").read_bytes())
    defx = gzip.decompress((FIX / f"{ticker}_{accn}_def.xml.gz").read_bytes())
    faits = tuple(vx.lire_instance(inst))
    etiquettes = vx.lire_etiquettes(lab)
    hierarchie, conflits = vx.lire_hierarchie(defx)
    return vt.Depot(accn=accn, form=manifeste["form"], filed=manifeste["filed"], faits=faits,
                    etiquettes=etiquettes, hierarchie=hierarchie, conflits=conflits)


def socle_de(ticker: str, *, reclasse: bool = False):
    d = json.loads((SOCLE_FIX / f"{ticker}.json").read_text(encoding="utf-8"))
    reclassements = charger_reclassements(d["cik"], GAB) if reclasse else ()
    return d["cik"], structure_du_socle(reconstituer(d["faits"], GAB, reclassements=reclassements))


NVDA_10K = charger_depot("NVDA", "0001045810-26-000021")
NVDA_10Q = charger_depot("NVDA", "0001045810-26-000075")
RVMD_10K = charger_depot("RVMD", "0001193125-26-071563")
JPM_10K = charger_depot("JPM", "0001628280-26-008131")
CIK_NVDA, SOCLE_NVDA = socle_de("NVDA", reclasse=True)
CIK_RVMD, SOCLE_RVMD = socle_de("RVMD")
CIK_JPM, SOCLE_JPM = socle_de("JPM")

TICKER = "NVDA"


async def courants(conn, ticker: str):
    return await conn.fetch(
        "SELECT id, nature, reliability_tier, source_date, content_structured, superseded_by "
        "FROM knowledge_entries WHERE ticker_id = $1 AND superseded_by IS NULL "
        "AND content_structured->>'metric' = $2",
        ticker, METRIC)


async def main():
    conn = await asyncpg.connect(_db_url.replace("postgresql+asyncpg://", "postgresql://"))
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    tr = conn.transaction()
    await tr.start()
    try:
        # §1 ─────────────────────────────────────────────────────────────────────────────────────
        p1 = await publier_ventilation(
            conn, TICKER, cik=CIK_NVDA, raison_sociale="NVIDIA Corporation",
            famille=("industrielle", "socle_comptes.yaml"), depots=[NVDA_10K, NVDA_10Q],
            socle=SOCLE_NVDA, embed=False)
        rows = await courants(conn, TICKER)
        b.require(rows, 1, "§1 une seule pièce « ventilation publiée » courante pour NVDA")
        r = rows[0] if rows else {}
        b.check(p1.statut == "publie", f"§1 statut `publie` (première publication) ({p1.statut})")
        b.check(r.get("reliability_tier") == "A" and r.get("nature") == "mesure",
                f"§1 tier A et nature `mesure` dérivés au guichet ({r.get('reliability_tier')}, {r.get('nature')})")
        st = r.get("content_structured") or {}
        b.check(isinstance(st, dict) and st.get("metric") == METRIC and st.get("statut") == "ventilee",
                f"§1 la structure revient en OBJET, statut `ventilee` ({st.get('statut')})")
        b.check(any(c["membre"] == "nvda:DataCenterMember" and abs(c["v"] - 193737 * M) < 1
                   for c in st.get("cellules") or []),
                "§1 relue en base, la cellule Data Center FY2026 vaut 193 737 M$")

        # §2 ─────────────────────────────────────────────────────────────────────────────────────
        p2 = await publier_ventilation(
            conn, TICKER, cik=CIK_NVDA, raison_sociale="NVIDIA Corporation",
            famille=("industrielle", "socle_comptes.yaml"), depots=[NVDA_10K, NVDA_10Q],
            socle=SOCLE_NVDA, embed=False)
        b.check(p2.statut == "a_jour" and p2.entry_id == p1.entry_id,
                f"§2 le même dépôt ne crée pas de version ({p2.statut}, #{p2.entry_id} vs #{p1.entry_id})")
        b.require(await courants(conn, TICKER), 1, "§2 toujours UNE pièce courante")

        # §3 ─────────────────────────────────────────────────────────────────────────────────────
        faits3 = tuple(
            vx.FaitDimensionne(f.concept, f.debut, f.fin, f.instant, f.membres, f.unite, f.valeur + 1_000_000, f.decimales)
            if f.concept == "us-gaap:Revenues" and f.fin == "2026-01-25" and f.membres == (
                ("srt:ProductOrServiceAxis", "nvda:DataCenterMember"),) else f
            for f in NVDA_10K.faits)
        nvda_10k_3 = vt.Depot(accn=NVDA_10K.accn, form=NVDA_10K.form, filed=NVDA_10K.filed, faits=faits3,
                              etiquettes=NVDA_10K.etiquettes, hierarchie=NVDA_10K.hierarchie,
                              conflits=NVDA_10K.conflits)
        p3 = await publier_ventilation(
            conn, TICKER, cik=CIK_NVDA, raison_sociale="NVIDIA Corporation",
            famille=("industrielle", "socle_comptes.yaml"), depots=[nvda_10k_3, NVDA_10Q],
            socle=SOCLE_NVDA, embed=False)
        rows3 = await courants(conn, TICKER)
        b.check(p3.statut == "publie" and p3.entry_id != p1.entry_id and p1.entry_id in p3.remplace,
                f"§3 une cellule changée publie une version neuve qui remplace l'ancienne ({p3.statut}, #{p3.entry_id})")
        b.require(rows3, 1, "§3 après remplacement, UNE pièce courante (#43)")
        ancienne = await conn.fetchval("SELECT superseded_by FROM knowledge_entries WHERE id = $1", p1.entry_id)
        b.check(ancienne == p3.entry_id, f"§3 l'ancienne pointe la nouvelle (A1) ({ancienne})")

        # §4 ─────────────────────────────────────────────────────────────────────────────────────
        p4 = await publier_ventilation(
            conn, "RVMD", cik=CIK_RVMD, raison_sociale="Revolution Medicines, Inc.",
            famille=("industrielle", "socle_comptes.yaml"), depots=[RVMD_10K], socle=SOCLE_RVMD, embed=False)
        b.check(p4.statut == "secteur_unique" and p4.entry_id is None, f"§4 RVMD : constat rendu, RIEN écrit ({p4.statut})")
        b.require(await courants(conn, "RVMD"), 0, "§4 aucune pièce écrite pour RVMD")

        # §5 ─────────────────────────────────────────────────────────────────────────────────────
        # Point de sauvegarde : si le refus bancaire est retiré, JPM (statut `ventilee`) tenterait
        # un INSERT réel — « JPM » n'est pas un ticker connu de la base (contrainte étrangère), donc
        # un refus manquant lèverait une exception SQL brute plutôt qu'un simple mauvais statut. Le
        # SAVEPOINT isole ce risque : l'échec devient un FAIL nommé, jamais un script mort avant son
        # bilan (2ᵉ faux vert, `feedback_check_degrade_en_sortant_a_zero`).
        p5 = None
        try:
            async with conn.transaction():
                p5 = await publier_ventilation(
                    conn, "JPM", cik=CIK_JPM, raison_sociale="JPMorgan Chase & Co.", famille=("bancaire", None),
                    depots=[JPM_10K], socle=SOCLE_JPM, embed=False)
        except Exception as e:
            p5 = e
        refus_ok = (not isinstance(p5, Exception) and p5.statut == "refus_famille"
                   and p5.entry_id is None and p5.motif and "bancaire" in p5.motif)
        b.check(refus_ok, f"§5 JPM : refus NOMMÉ (famille bancaire), RIEN écrit ({p5})")
        b.require(await courants(conn, "JPM"), 0, "§5 aucune pièce écrite pour JPM")
    finally:
        await tr.rollback()   # AUCUN résidu
        await conn.close()


asyncio.run(main())
sys.exit(b.summary())
