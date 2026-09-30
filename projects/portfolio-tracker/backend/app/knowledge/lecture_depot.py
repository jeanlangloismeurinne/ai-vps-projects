"""La LECTURE d'un dépôt postérieur aux comptes, classée au dossier comme une pièce (#106).

Comme un vrai fonds : quand l'émetteur publie après ses derniers comptes un fait qui rouvre une
question (les baux du nouveau siège de RVMD, 8-K du 27/08), l'analyste LIT le dépôt et le range au
dossier ; sa note dit ensuite l'effet du fait (#103). Jusqu'ici personne ne lisait un dépôt que sa
FORME qualifiait (1.01 + 2.03 = financement) : la note flash ne lit que les `a_qualifier` (#90). La
seule pièce tirée du 8-K des baux était une pièce d'héritage (#296) qui mêlait les chiffres du 30/06
et un résumé du 8-K — dès qu'une pièce mieux datée est passée devant elle (#104), l'analyste n'a plus
rien eu à lire et sa réponse est née périmée (réponse #976, 2026-09-30).

La pièce est le texte DÉPOSÉ, tel quel : aucun modèle, aucun résumé, aucune traduction — un
résumé serait une lecture de plus entre le dépôt et le comité. Elle est datée par le dépôt même
(`constatee` : le fait à `reportDate`, le document à `filingDate`, #79), adressée dans le dossier
EDGAR du dépôt (c'est ce qui la fait reconnaître comme « tirée du dépôt », `provient_du_depot`),
et marquée d'une étiquette propre pour être jointe au dossier des questions que le dépôt rouvre.

Un dépôt se lit UNE fois (idempotent par étiquette + accession). Un échec de téléchargement n'écrit
rien et est RENDU nommé : le fait reste non montré et la réponse reste périmée — ce qui est vrai.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from app.agents.v2.note_flash import (
    DocumentDepot, NoteFlashImpossible, extraire_documents, telecharger_soumission,
)
from app.knowledge.datation import constatee
from app.knowledge.material_events import MaterialEvent
from app.knowledge.service import store_knowledge

logger = logging.getLogger(__name__)

ETIQUETTE = "lecture_du_depot"


@dataclass(frozen=True)
class Lecture:
    """Ce qu'un dépôt a donné : une pièce au dossier (`entry_id`) OU un motif — jamais aucun (#25)."""
    accession: str
    entry_id: Optional[int] = None
    ecrite: bool = False          # vrai si ce passage l'a écrite (faux : déjà lue)
    motif: Optional[str] = None


def adresse_du_depot(event: MaterialEvent, cik: int) -> str:
    """L'adresse de la pièce : le document principal si le flux le donne DANS le dossier du dépôt,
    sinon l'index du dépôt. Toujours sous `/Archives/edgar/data/<cik>/<accession sans tirets>/`."""
    acc = event.accession or ""
    dossier = acc.replace("-", "")
    if event.url and dossier and dossier in event.url:
        return event.url
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{dossier}/{acc}-index.htm"


def type_de_piece(event: MaterialEvent) -> str:
    """`fact_financial` si le dépôt porte un item de la section 2 du formulaire 8-K (« Financial
    Information » dans la nomenclature de la SEC : résultats, obligation financière, dépréciation…),
    sinon `fact_qualitative`. C'est la classification de la SEC elle-même, pas un jugement."""
    return "fact_financial" if any(str(i).startswith("2.") for i in event.items) else "fact_qualitative"


def construire_contenu(event: MaterialEvent, documents: list[DocumentDepot]) -> str:
    """Le texte de la pièce : l'identité du dépôt, puis ses documents TELS QU'EXTRAITS (troncature dite)."""
    entete = (f"Dépôt EDGAR {event.form} du {event.event_date.isoformat()} "
              f"(déposé le {event.filing_date.isoformat()}, accession {event.accession})"
              + (f", items {', '.join(event.items)}" if event.items else "")
              + " — texte tel que déposé, sans résumé ni traduction.")
    blocs = [f"[{d.type} — {d.nom}{' — TRONQUÉ à la lecture' if d.tronque else ''}]\n{d.texte}"
             for d in documents]
    return "\n\n".join([entete, *blocs])


async def _deja_lu(conn, ticker_id: str, accession: str) -> Optional[int]:
    return await conn.fetchval(
        """SELECT id FROM knowledge_entries
            WHERE ticker_id = $1 AND superseded_by IS NULL
              AND $2 = ANY(tags) AND $3 = ANY(tags)
            ORDER BY id DESC LIMIT 1""",
        ticker_id, ETIQUETTE, accession)


async def assurer_lectures(conn, ticker_id: str, cik: Optional[int],
                           events: Iterable[MaterialEvent]) -> list[Lecture]:
    """Chaque dépôt de `events` a sa pièce de lecture au dossier. Écrit ce qui manque, rend tout.

    `cik` absent (titre hors EDGAR) : rien n'est lu, chaque dépôt est rendu avec son motif."""
    vus: dict[str, MaterialEvent] = {}
    for e in events:
        if e.accession and e.accession not in vus:
            vus[e.accession] = e
    lectures: list[Lecture] = []
    for acc, event in vus.items():
        existant = await _deja_lu(conn, ticker_id, acc)
        if existant is not None:
            lectures.append(Lecture(accession=acc, entry_id=int(existant)))
            continue
        if cik is None:
            lectures.append(Lecture(accession=acc, motif="émetteur sans CIK : le dépôt ne se télécharge pas"))
            continue
        try:
            documents = extraire_documents(await telecharger_soumission(cik, acc))
        except NoteFlashImpossible as e:
            lectures.append(Lecture(accession=acc, motif=str(e)))
            continue
        if not documents:
            lectures.append(Lecture(accession=acc, motif="la soumission ne contient aucun document lisible"))
            continue
        ligne = await store_knowledge(
            conn,
            ticker_id=ticker_id,
            entry_type=type_de_piece(event),
            content=construire_contenu(event, documents),
            source_type="edgar_official",
            title=f"Lecture du dépôt {event.form} du {event.event_date.isoformat()} ({ticker_id}) — {acc}",
            tags=[ETIQUETTE, acc, event.form],
            lang="en",
            source_url=adresse_du_depot(event, cik),
            datation=constatee(date_du_fait=event.event_date, date_du_document=event.filing_date),
        )
        lectures.append(Lecture(accession=acc, entry_id=int(ligne["id"]), ecrite=True))
        logger.info("lecture_depot: %s %s → entry #%s", ticker_id, acc, ligne["id"])
    return lectures


def ids_des_lectures(lectures: Iterable[Lecture]) -> list[int]:
    return [x.entry_id for x in lectures if x.entry_id is not None]


def resume_des_lectures(lectures: list[Lecture]) -> list[str]:
    out: list[str] = []
    for x in lectures:
        if x.entry_id is not None:
            out.append(f"  lecture du dépôt {x.accession} → pièce #{x.entry_id}"
                       f"{' (écrite)' if x.ecrite else ' (déjà au dossier)'}")
        else:
            out.append(f"  ⚠️ dépôt {x.accession} NON lu : {x.motif}")
    return out


__all__: list[Any] = ["ETIQUETTE", "Lecture", "adresse_du_depot", "assurer_lectures", "construire_contenu",
                      "ids_des_lectures", "resume_des_lectures", "type_de_piece"]
