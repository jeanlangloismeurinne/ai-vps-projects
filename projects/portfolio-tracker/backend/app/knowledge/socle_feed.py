"""Publier le SOCLE DES COMPTES d'un émetteur au dossier — une pièce, versionnée à chaque nouveau dépôt.

Le socle (`socle_comptes.reconstituer`) est une fonction pure ; ce module en fait une PIÈCE du dossier,
comme le fait un fonds du modèle des comptes de l'analyste : un document unique, daté du dernier fait
qu'il constate, remplacé (jamais réécrit, A1) quand un nouveau dépôt l'enrichit. Toutes les questions
financières le lisent (jointure d'office, `preparation`), et l'encadré des chiffres clés en est tiré par
le code (`frameworks.completer_encadre`).

Coût : un appel public `companyfacts` (gratuit), aucun modèle. Idempotent : sur le même dépôt et le même
gabarit, la pièce en vigueur est rendue telle quelle (`a_jour`), rien n'est écrit.

Trois issues, jamais un silence (#25) : `publie` (version neuve), `a_jour` (rien à écrire), et une
exception NOMMÉE (`SocleIndisponible`) quand EDGAR est injoignable ou que l'émetteur ne dépose aucun
exercice — l'appelant le dit ; il ne publie jamais un socle vide.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, NamedTuple, Optional

from app.knowledge.datation import constatee
from app.knowledge.edgar_facts import EdgarUnavailable, fetch_company_facts
from app.knowledge.edgar_feed import EdgarFeedUnavailable, filing_url, identite_de_l_emetteur
from app.knowledge.service import ENTRIES_COURANTES, store_knowledge
from app.knowledge.socle_comptes import (
    METRIC,
    charger_gabarit,
    charger_reclassements,
    empreinte,
    reconstituer,
    rendre_socle,
    structure_du_socle,
)

logger = logging.getLogger(__name__)

SOURCE_TYPE = "edgar_official"
TAGS = ["financials", "edgar", METRIC]


class SocleIndisponible(Exception):
    """Le socle ne peut pas être reconstitué (EDGAR injoignable, émetteur sans exercice déposé)."""


class SoclePublie(NamedTuple):
    entry_id: int
    statut: str                          # "publie" | "a_jour"
    structure: dict[str, Any]
    remplace: tuple[int, ...] = ()


_SQL_COURANTS = f"""
    SELECT id, content_structured FROM knowledge_entries
     WHERE ticker_id = $1 AND {ENTRIES_COURANTES}
       AND content_structured->>'metric' = $2
     ORDER BY id DESC
"""


async def socle_en_vigueur(conn, ticker_id: str) -> Optional[dict[str, Any]]:
    """La pièce « socle des comptes » en vigueur pour ce titre : `{id, structure}`, ou None."""
    row = await conn.fetchrow(_SQL_COURANTS, ticker_id, METRIC)
    return None if row is None else {"id": row["id"], "structure": row["content_structured"]}


async def assurer_socle(conn, ticker_id: str) -> SoclePublie:
    """Reconstitue le socle depuis les dépôts et le publie s'il a changé. ÉCRIT (une transaction)."""
    try:
        ident = await identite_de_l_emetteur(conn, ticker_id)
        faits = await fetch_company_facts(ident.cik)
    except (EdgarFeedUnavailable, EdgarUnavailable) as e:
        raise SocleIndisponible(f"socle des comptes de {ticker_id} non reconstituable : {e}") from e
    return await publier_socle(conn, ticker_id, cik=ident.cik, raison_sociale=ident.raison_sociale,
                               faits=faits)


async def publier_socle(conn, ticker_id: str, *, cik: int, raison_sociale: str,
                        faits: dict[str, list[dict[str, Any]]], embed: bool = True) -> SoclePublie:
    """La moitié BASE de `assurer_socle` : un inventaire déjà lu → la pièce publiée (ou rendue telle
    quelle si rien n'a changé). Séparée pour s'éprouver sur un inventaire copié du réel, sans réseau."""
    gabarit = charger_gabarit()
    socle = reconstituer(faits, gabarit, reclassements=charger_reclassements(cik, gabarit))
    if not socle.periodes or socle.dernier_depot is None:
        raise SocleIndisponible(f"socle des comptes de {ticker_id} : {'; '.join(socle.refus) or 'aucune période'}")
    structure = structure_du_socle(socle)

    courants = await conn.fetch(_SQL_COURANTS, ticker_id, METRIC)
    if courants and empreinte(courants[0]["content_structured"] or {}) == empreinte(structure):
        return SoclePublie(courants[0]["id"], "a_jour", courants[0]["content_structured"])

    depot = socle.dernier_depot
    fin = date.fromisoformat(structure["period_end"])
    filed = date.fromisoformat(str(depot["filed"]))
    titre = (f"Socle des comptes — {raison_sociale} — {len(socle.periodes)} périodes jusqu'au "
             f"{structure['period_end']} (dernier dépôt {depot['form']} du {depot['filed']})")
    async with conn.transaction():
        stored = await store_knowledge(
            conn,
            ticker_id=ticker_id,
            entry_type="fact_financial",
            content=rendre_socle(structure, gabarit, raison_sociale=raison_sociale),
            source_type=SOURCE_TYPE,
            title=titre,
            content_structured=structure,
            tags=TAGS,
            lang="fr",
            source_url=filing_url(cik, depot.get("accn")),
            datation=constatee(date_du_fait=fin, date_du_document=filed),
            fiscal_period=f"AU {structure['period_end']}",
            supersedes_entry_id=courants[0]["id"] if courants else None,
            embed=embed,
        )
        autres = [r["id"] for r in courants[1:]]
        if autres:
            await conn.execute(
                "UPDATE knowledge_entries SET superseded_by = $1 WHERE id = ANY($2::int[])",
                stored["id"], autres)
    logger.info("socle des comptes %s publié (#%s), remplace %s", ticker_id, stored["id"],
                [r["id"] for r in courants])
    return SoclePublie(stored["id"], "publie", structure, tuple(r["id"] for r in courants))
