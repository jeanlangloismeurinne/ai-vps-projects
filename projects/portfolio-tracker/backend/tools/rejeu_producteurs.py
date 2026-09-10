"""Rejeu des PRODUCTEURS DÉTERMINISTES après la 036 — reconstitue le socle, à coût modèle NUL.

POURQUOI CE FICHIER EXISTE
---------------------------
La 036 archive les 15 tables V2 par `SET SCHEMA` et recrée `public.knowledge_entries` VIDE. Deux
checks portent un plancher sur le corpus courant — `check_edgar_feed` §12bis (≥ 50 lignes du socle)
et `check_entry_nature` §7 (13 entries déterministes sur RVMD). Sur une base vide, ils rougissent.

La tentation est d'abaisser le plancher « le temps de la migration ». C'est le mode de panne de
`feedback_optional_schema_gate` : un desserrage posé à chaud ne se resserre jamais, et un plancher
abaissé rend le check vrai sur un corpus qu'il ne mesure plus. Le corpus se **reconstruit** — les
producteurs concernés sont déterministes (dépôt XBRL EDGAR, fournisseur de marché, corpus de taux
de base) : les rejouer coûte des appels réseau, **zéro token**.

CE QUI EST REJOUÉ, ET CE QUI NE L'EST PAS
------------------------------------------
Rejoué  : `edgar-refresh` (le socle, 8 postes), puis `financials-refresh` (ratios DÉRIVÉS du socle,
          donc jamais avant lui), `valuation-refresh`, `base-rate-anchor`.
NON rejoué : `synthesize` — un tour LLM. Les `agent_synthesis` et `analysis` du corpus d'avant ne
          se reconstituent pas gratuitement ; elles restent lisibles dans `archive_v2` et seront
          reproduites par les flux d'analyse, pas par ce script. Ne pas les compter comme perdues.

LES TICKERS SE LISENT DANS L'ARCHIVE, ILS NE SE RETAPENT PAS. Une liste en dur ici divergerait du
corpus réellement archivé au premier ticker ajouté, et le rejeu paraîtrait complet en ayant sauté
quelqu'un. C'est le corpus d'avant qui dit qui avait un socle.

⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code DÉPLOYÉ, qui peut précéder
celui qu'on rejoue. Lanceur : `tools/rejeu_producteurs.sh`.

Sortie : un bilan reconnaissable À SA FORME (`feedback_bilan_par_sa_forme`), jamais un `tail -1`.
Codes : 0 = rejoué et les planchers sont tenus · 1 = un plancher n'est PAS tenu · 2 = pas mesurable.
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback

from app.db.database import close_pool, get_db_session, init_pool
from app.knowledge.base_rate_corpus import BaseRateUnavailable, run_base_rate_anchor
from app.knowledge.edgar_feed import EdgarFeedUnavailable, run_edgar_feed
from app.knowledge.financials_feed import FinancialsUnavailable, run_financials_feed
from app.knowledge.valuation_feed import ValuationUnavailable, run_valuation_feed

# ⚠️ L'ORDRE EST LOAD-BEARING : `financials-refresh` CALCULE ses ratios depuis les faits EDGAR déjà
# en base. Lancé avant `edgar-refresh` sur une base vide, il lève `FinancialsUnavailable` — et un
# rejeu qui aurait « juste sauté les ratios » laisserait la dimension `financials` non fondable
# sans que rien ne le dise.
ETAPES: list[tuple[str, object, type[Exception]]] = [
    ("edgar",      run_edgar_feed,      EdgarFeedUnavailable),
    ("financials", run_financials_feed, FinancialsUnavailable),
    ("valuation",  run_valuation_feed,  ValuationUnavailable),
    ("base_rate",  run_base_rate_anchor, BaseRateUnavailable),
]

# Les deux planchers que le rejeu doit restaurer, chacun avec le check qui le porte — pour que le
# message dise QUOI relancer, pas seulement qu'un nombre est trop petit.
PLANCHERS = [
    ("socle EDGAR (check_edgar_feed §12bis)", 50,
     "SELECT count(*) FROM knowledge_entries "
     " WHERE entry_type = 'fact_financial' AND source_type = 'edgar_official'"),
    ("RVMD déterministes actives (check_entry_nature §7)", 13,
     "SELECT count(*) FROM knowledge_entries "
     " WHERE ticker_id = 'RVMD' AND superseded_by IS NULL "
     "   AND entry_type IN ('fact_financial', 'fact_statistical')"),
]


async def _tickers_du_corpus_archive(conn) -> list[str]:
    """Qui avait un socle déterministe AVANT la 036. Lu, jamais retapé."""
    lignes = await conn.fetch(
        "SELECT DISTINCT ticker_id FROM archive_v2.knowledge_entries "
        " WHERE ticker_id IS NOT NULL AND source_type IN ('edgar_official', 'yfinance') "
        "   AND entry_type = 'fact_financial' ORDER BY 1")
    return [r["ticker_id"] for r in lignes]


async def main() -> int:
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquante — le rejeu ÉCRIT dans le corpus réel, il ne se simule pas.",
              file=sys.stderr)
        return 2

    await init_pool(url)
    try:
        async with get_db_session() as conn:
            tickers = await _tickers_du_corpus_archive(conn)
        if not tickers:
            # Zéro ticker rendrait tout « rejoué » sur zéro ligne — le 1ᵉʳ faux vert.
            print("archive_v2 ne porte aucun socle déterministe : rien à rejouer, et un bilan vert "
                  "ici serait vrai sur zéro ligne.", file=sys.stderr)
            return 2

        print(f"Rejeu des producteurs déterministes sur {len(tickers)} ticker(s) : "
              f"{', '.join(tickers)}\n")

        echecs: list[str] = []
        for ticker in tickers:
            for nom, fonction, indisponible in ETAPES:
                try:
                    res = await fonction(ticker, persist=True)  # type: ignore[operator]
                    ecrites = res.get("persisted", res.get("entries_created", "?")) \
                        if isinstance(res, dict) else "?"
                    print(f"  ok   {ticker:<6} {nom:<11} → {ecrites}")
                except indisponible as e:  # type: ignore[misc]
                    # 422 métier : le producteur DIT qu'il ne peut pas fonder. Ce n'est pas une
                    # panne, mais ce n'est pas un succès non plus — on le compte comme tel.
                    print(f"  --   {ticker:<6} {nom:<11} indisponible : {e}")
                except Exception as e:  # noqa: BLE001
                    echecs.append(f"{ticker}/{nom} : {type(e).__name__} {e}")
                    print(f"  FAIL {ticker:<6} {nom:<11} {type(e).__name__} : {e}")

        # ── Les planchers, relus LÀ OÙ LES CHECKS LES LISENT : la colonne ─────────────────────
        print("\nPlanchers après rejeu :")
        manques = 0
        async with get_db_session() as conn:
            for libelle, plancher, sql in PLANCHERS:
                n = await conn.fetchval(sql)
                if n >= plancher:
                    print(f"  ok   {libelle:<52} {n} ≥ {plancher}")
                else:
                    manques += 1
                    print(f"  FAIL {libelle:<52} {n} < {plancher}")

        print("\n============================================================")
        print(f"rejeu : {len(tickers)} ticker(s) · {len(echecs)} erreur(s) · "
              f"{manques} plancher(s) non tenu(s)")
        return 1 if (manques or echecs) else 0
    finally:
        await close_pool()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)   # « pas mesurable » — jamais confondu avec « mesuré et rouge » (#44/#54)
