"""Montre le SERVICE de l'architecture (§6.2) tel que le comité le voit — lecture seule.

  python tools/montrer_architecture.py TICKER

Rejoue `servir_architecture` contre la matière DU JOUR (à blanc, aucune écriture). Codes :
0 = servi (quel que soit l'état) · 2 = pas mesurable (titre inconnu, env absent).
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback

from app.db.database import close_pool, get_db_session, init_pool
from app.modele_entreprise.architecte import juger_architecture
from app.modele_entreprise.matiere import MatiereRefusee, charger_matiere
from app.modele_entreprise.referentiel import load_referentiel
from app.modele_entreprise.signature import lire_registre, servir_architecture


async def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ticker = sys.argv[1]
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquante.", file=sys.stderr)
        return 2
    await init_pool(url)
    try:
        ref = load_referentiel()
        async with get_db_session() as conn:
            if not await conn.fetchval("SELECT 1 FROM tickers WHERE id = $1", ticker):
                print(f"titre `{ticker}` inconnu.", file=sys.stderr)
                return 2
            versions, pv = await lire_registre(conn, ticker)
            try:
                matiere = await charger_matiere(conn, ticker, publier=False)

                def juger(arch):
                    return juger_architecture(arch, ref, matiere)
            except MatiereRefusee as e:
                motif = str(e)

                def juger(arch):
                    return False, f"matière indisponible : {motif}", ()

        s = servir_architecture(ticker, versions, pv, juger=juger,
                                interrupteur=ref.signature_de_l_architecture)
        print(f"Architecture de {ticker} — état : {s.etat}")
        print(f"Versions proposées : {s.versions_proposees}")
        if s.signee:
            print(f"Signée : v{s.signee.version.version} — {s.signee.etat} — {s.signee.motif_etat}")
            if s.signee.signaux_du_jour:
                print(f"  signaux du jour : {s.signee.signaux_du_jour}")
        if s.en_attente:
            print(f"En attente : v{s.en_attente.version.version} — signable={s.en_attente.signable} "
                 f"— {s.en_attente.motif_refus or 'OK'}")
        print(f"En vigueur : {s.en_vigueur.version.version if s.en_vigueur.version else 'AUCUNE'} "
             f"— {s.en_vigueur.motif}")
        print(f"PV ({len(s.proces_verbal)} décision(s)) :")
        for d in s.proces_verbal:
            print(f"  · v{d.version} {d.action} par {d.auteur} le {d.decide_le:%Y-%m-%d} — {d.motif}")
        return 0
    finally:
        await close_pool()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
