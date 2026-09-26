"""Vérification de l'ÉCRITURE et de la RELECTURE des notes flash contre la VRAIE base (lot 7, maillon 2,
migration 050). Tout se joue dans UNE transaction annulée à la fin : zéro résidu
(`feedback_fixture_pollue_le_reel` — une note fabriquée laissée en base requalifierait un vrai dépôt).

  • §1 ÉCRIRE : `persister_note` écrit la note telle que le pont l'a validée (types dérivés, éléments
       cités, documents lus, version du catalogue) ; les JSONB arrivent en objets, pas en chaînes.
  • §2 RELIRE : `qualifications_de_l_emetteur` rend, par dépôt, ce que le point de lecture retient —
       la note lisible avec son passage, la note illisible avec son motif ; rien pour un autre émetteur.
  • §3 LA VERSION DU JOUR L'EMPORTE : sur un même dépôt relu sous deux versions du catalogue, c'est la
       note de la version courante qui est servie, même plus ancienne.
  • §4 UNE FOIS PAR DÉPÔT : une seconde note du même dépôt sous la même version est refusée par la
       base, nommément.
  • §5 L'HORLOGE LIT LA NOTE : sur le flux RVMD réel, la note relue en base fait retomber qf_6 sur les
       résultats du 05/08 et laisse mo_1 sur l'approbation du 26/08.

Lancer : `bash checks/avec_base.sh check_note_flash_persist` (jamais dans `portfolio-backend`).
"""
import asyncio
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

from app.agents.v2.frameworks import load_frameworks, types_qui_rouvrent  # noqa: E402
from app.agents.v2.note_flash import (  # noqa: E402
    NoteRedigee, NoteValidee, persister_note, qualifications_de_l_emetteur)
from app.knowledge.evenements import A_QUALIFIER, ancre_de_la_question  # noqa: E402
from app.knowledge.material_events import MaterialEvent, MaterialEventLookup  # noqa: E402

fichier = load_frameworks()
VER = fichier.types_evenement_version
# CIK FICTIF : isole le check des notes RÉELLES déjà en base (un état qu'on ne suppose pas vide).
CIK = 999_000_001
PASSAGE = ("On August 26, 2026, the U.S. Food and Drug Administration approved RASONQUE™ "
           "(daraxonrasib) for the treatment of adult patients")
# Numéros de dépôt FICTIFS : l'unicité d'une note porte sur (dépôt, version du catalogue), et les vrais
# dépôts RVMD ont désormais leur note réelle — les réutiliser ferait heurter le check contre le réel.
FDA = MaterialEvent(form="8-K", event_date=date(2026, 8, 26), filing_date=date(2026, 8, 26),
                    items=("8.01",), accession="0000000000-26-000826")
AVRIL = MaterialEvent(form="8-K", event_date=date(2026, 4, 13), filing_date=date(2026, 4, 13),
                      items=("8.01",), accession="0000000000-26-000413")
FIN = MaterialEvent(form="8-K", event_date=date(2026, 8, 27), filing_date=date(2026, 9, 1),
                    items=("1.01", "2.03"), accession="0000000000-26-000827")
RES = MaterialEvent(form="8-K", event_date=date(2026, 8, 5), filing_date=date(2026, 8, 5),
                    items=("2.02", "9.01"), accession="0000000000-26-000805")
DOCS = [{"type": "8-K", "nom": "rvmd-20260826.htm", "taille": 3149, "tronque": False, "lu": 1500}]


def note(event, *, version=VER, lisible=True):
    if lisible:
        n = NoteValidee(lisible=True, types=("reglementaire_favorable",), motif=None,
                        elements=[{"type": "reglementaire_favorable", "passage": PASSAGE}])
    else:
        n = NoteValidee(lisible=False, types=(A_QUALIFIER,), elements=[],
                        motif="le dépôt ne contient que la page de signature")
    return NoteRedigee(ticker_id="RVMD", cik=CIK, event=event, catalogue_version=version, note=n,
                       documents=DOCS, modele="check-model")


async def ecrire(conn, redigee):
    """Écrit sous un savepoint : un refus de la base est un FAIL NOMMÉ, jamais la mort du script
    (sinon une note mal encodée tuerait le check avant son bilan — 2ᵉ faux vert)."""
    sp = conn.transaction()
    await sp.start()
    try:
        i = await persister_note(conn, redigee)
    except Exception as e:  # noqa: BLE001
        await sp.rollback()
        b.check(False, f"§1 la base accepte la note (éléments et documents en OBJETS JSON) — {e}")
        return None
    await sp.commit()
    return i


async def main() -> None:
    conn = await asyncpg.connect(_db_url.replace("+asyncpg", ""))
    # Le codec JSONB du POOL (`init_pool`) ne s'applique qu'aux connexions du pool : on le rejoue ici
    # à l'identique, puisque `persister_note` écrit des objets Python (convention #1).
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    tr = conn.transaction()
    await tr.start()
    total_avant = -1
    try:
        total_avant = await conn.fetchval("SELECT count(*) FROM notes_flash")
        avant = await conn.fetchval(
            "SELECT count(*) FROM notes_flash WHERE cik = $1 OR accession LIKE '0000000000-%'", CIK)
        b.check(avant == 0, f"§0 le CIK et les dépôts fictifs du check n'ont aucune note en base — {avant}")

        print("§1 écrire")
        id_fda = await ecrire(conn, note(FDA))
        await ecrire(conn, note(AVRIL, lisible=False))
        row = await conn.fetchrow("SELECT * FROM notes_flash WHERE id = $1", id_fda) or {
            "types": None, "lisible": None, "catalogue_version": None, "modele": None,
            "elements": None, "documents": None, "items": [], "event_date": None}
        b.check(row["types"] == ["reglementaire_favorable"] and row["lisible"]
                and row["catalogue_version"] == VER and row["modele"] == "check-model",
                f"la note est écrite telle que validée → {row['types']}")
        b.check(isinstance(row["elements"], list) and bool(row["elements"])
                and row["elements"][0]["passage"] == PASSAGE,
                "les éléments cités arrivent en OBJETS (pas en chaîne JSON)")
        b.check(isinstance(row["documents"], list) and bool(row["documents"])
                and row["documents"][0]["type"] == "8-K",
                "les documents lus sont notés")
        b.check(list(row["items"]) == ["8.01"] and row["event_date"] == date(2026, 8, 26),
                "la forme et la date du dépôt sont notées")

        print("§2 relire")
        lues = await qualifications_de_l_emetteur(conn, CIK, fichier)
        b.require(lues, 2, "deux dépôts lus pour l'émetteur du check")
        q_fda, q_avr = lues.get(FDA.accession), lues.get(AVRIL.accession)
        b.check(q_fda is not None and q_fda.types == frozenset({"reglementaire_favorable"})
                and "RASONQUE" in q_fda.resume, f"la note lisible se relit avec son passage → {q_fda}")
        b.check(q_avr is not None and q_avr.types == frozenset({A_QUALIFIER})
                and "page de signature" in q_avr.resume,
                f"la note illisible se relit `a_qualifier`, motif à l'appui → {q_avr}")
        b.check(await qualifications_de_l_emetteur(conn, 999_000_002, fichier) == {},
                "aucune note n'est prêtée à un autre émetteur")
        b.check(await qualifications_de_l_emetteur(conn, None, fichier) == {},
                "une ancre sans CIK (indisponible) ne relit rien")

        print("§3 la version du jour l'emporte")
        autre = note(FDA, version="0.9.0-ancienne")
        autre.note = NoteValidee(lisible=True, types=("routine",), motif=None,
                                 elements=[{"type": "routine", "passage": PASSAGE}])
        await ecrire(conn, autre)   # écrite APRÈS, sous une autre version
        lues2 = await qualifications_de_l_emetteur(conn, CIK, fichier)
        b.check(FDA.accession in lues2 and not lues2[FDA.accession].a_relire,
                "la note servie, de la version du jour, n'est pas à relire")
        b.check(FDA.accession in lues2 and lues2[FDA.accession].types == frozenset({"reglementaire_favorable"}),
                "la note de la version COURANTE est servie, même plus ancienne → "
                f"{lues2.get(FDA.accession)}")

        print("§4 une fois par dépôt")
        sp = conn.transaction()
        await sp.start()
        try:
            await persister_note(conn, note(FDA))
            b.check(False, "une seconde note du même dépôt sous la même version — ACCEPTÉE")
        except Exception as e:  # noqa: BLE001 — un refus par une AUTRE règle est un FAIL nommé
            b.check("notes_flash_une_lecture" in str(e),
                    f"une seconde note du même dépôt est refusée par SA contrainte → {e}")
        finally:
            await sp.rollback()

        print("§5 l'horloge lit la note relue en base")
        flux = MaterialEventLookup(status="found", event=FIN, cik=CIK, recents=(FIN, FDA, RES))
        a_qf6 = ancre_de_la_question(flux, rouvrent=types_qui_rouvrent(fichier, "qf_6"),
                                     qualifications=lues)
        a_mo1 = ancre_de_la_question(flux, rouvrent=types_qui_rouvrent(fichier, "mo_1"),
                                     qualifications=lues)
        b.check(a_qf6.event is not None and a_qf6.event.event_date == date(2026, 8, 5),
                f"qf_6 retombe sur les résultats du 05/08 → {getattr(a_qf6.event, 'event_date', None)}")
        b.check(a_mo1.event is not None and a_mo1.event.event_date == date(2026, 8, 26)
                and "note flash" in a_mo1.event.resume(),
                f"mo_1 reste sur l'approbation, motif lu → {a_mo1.event.resume() if a_mo1.event else None}")
    finally:
        await tr.rollback()
        reste = await conn.fetchval("SELECT count(*) FROM notes_flash WHERE cik = $1", CIK)
        total = await conn.fetchval("SELECT count(*) FROM notes_flash")
        b.check(reste == 0 and total == total_avant,
                f"zéro résidu après ROLLBACK — {reste} sur le CIK du check, {total} vs {total_avant} au total")
        await conn.close()


asyncio.run(main())
sys.exit(b.summary())
