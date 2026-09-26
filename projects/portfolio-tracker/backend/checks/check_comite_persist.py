"""Vérification de l'ÉCRITURE du procès-verbal du comité contre la VRAIE base (lot 6 maillon 3,
migration 048). Tout se joue dans UNE transaction annulée à la fin : zéro résidu
(`feedback_fixture_pollue_le_reel` — jamais un renvoi fabriqué laissé en base pour verdir le bouclage).

  • §1 ACQUITTER : le PV porte qui / quand / quelle réponse / pourquoi / le fait connu ; la recherche
       en cours sur la question est ARRÊTÉE (mandat `abandonne`, jamais supprimé) et le PV garde son id.
  • §2 RENVOYER : un mandat `comite` OUVERT par le canal du manager, que le bouclage lit
       (`read_open_mandates`) avec la consigne du comité TELLE QUELLE ; un second renvoi REMPLACE le
       premier (jamais deux mandats ouverts sur une question) ; EDGAR illisible n'empêche pas de renvoyer.
  • §3 LES REFUS NOMMÉS : réponse remplacée depuis, réponse d'une autre question, réponse inconnue,
       faits illisibles pour une acceptation, question hors référentiel.
  • §4 LA LECTURE : `lire_registre` rend le PV le plus récent d'abord, et une acceptation sur une
       réponse remplacée depuis TOMBE à la lecture.
  • §5 LE PV NE SE RÉÉCRIT PAS : le rôle applicatif ne peut ni modifier ni supprimer une décision.

Lancer : `bash checks/avec_base.sh check_comite_persist` (jamais dans `portfolio-backend`).
"""
import asyncio
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

from app.agents.v2.comite import (  # noqa: E402
    DecisionRefusee, acquitter, lire_registre, position_du_comite, renvoyer)
from app.agents.v2.frameworks import load_frameworks  # noqa: E402
from app.agents.v2.manager_persist import (  # noqa: E402
    id_du_mandat_ouvert, persist_mandate, read_open_mandates)
from app.agents.v2.parcours import ReferenceInconnue  # noqa: E402
from app.contracts.comite_schema import DemandeAcquittement, DemandeRenvoi  # noqa: E402
from app.contracts.framework_answer_schema import FrameworkMandate  # noqa: E402
from app.knowledge.material_events import MaterialEvent, MaterialEventLookup  # noqa: E402

VER = load_frameworks().schema_version
# L'approbation FDA de RVMD, forme réelle du flux EDGAR (8-K 8.01 du 2026-08-26).
FDA = MaterialEvent(form="8-K", event_date=date(2026, 8, 26), filing_date=date(2026, 8, 26),
                    items=("8.01",), accession="0001193125-26-366931")
ANCRE = MaterialEventLookup(status="found", event=FDA, cik=1628171, recents=(FDA,))
INJOIGNABLE = MaterialEventLookup(status="unavailable", raison="EDGAR 503")


async def refus(conn, label, attendu, exc, coro):
    """Le refus doit être le BON (classe + motif), et ne rien laisser derrière lui (savepoint)."""
    sp = conn.transaction()
    await sp.start()
    try:
        await coro
    except exc as e:
        b.check(attendu in str(e), f"{label} — refusé, mais pas pour la bonne raison : {e}")
    except Exception as e:  # noqa: BLE001
        b.check(False, f"{label} — refusé par autre chose : {type(e).__name__}: {e}")
    else:
        b.check(False, f"{label} — ACCEPTÉ")
    finally:
        await sp.rollback()


async def main() -> None:
    conn = await asyncpg.connect(_db_url.replace("+asyncpg", ""))
    tr = conn.transaction()
    await tr.start()
    try:
        # Une réponse COURANTE réelle, et une réponse d'une AUTRE question du même émetteur.
        rows = await conn.fetch(
            "SELECT id, ticker_id, framework, question_id FROM framework_answers "
            "WHERE superseded_by IS NULL AND framework_version = $1 ORDER BY id", VER)
        b.check(len(rows) >= 2, f"§0 au moins deux réponses courantes réelles en base (fixture = "
                                f"le réel) — obtenu {len(rows)}")
        if len(rows) < 2:
            return
        r0 = rows[0]
        autre = next((r for r in rows if r["ticker_id"] == r0["ticker_id"]
                      and r["question_id"] != r0["question_id"]), None)
        b.check(autre is not None, "§0 une réponse d'une autre question du même émetteur existe")
        tk, fw, qid, aid = r0["ticker_id"], r0["framework"], r0["question_id"], r0["id"]
        cle = dict(ticker_id=tk, framework_id=fw, question_id=qid)
        print(f"  (réponse éprouvée : #{aid} · {tk} · {fw} · {qid})")

        # ══ §1 ACQUITTER ═══════════════════════════════════════════════════════════════════════
        print("[1] acquitter")
        m0 = await persist_mandate(conn, FrameworkMandate(
            framework_id=fw, question_id=qid, ticker_id=tk, origine="manager_renvoi",
            motif="renvoi manager (check)", mandat="re-collecter (check)", etat="ouvert"),
            framework_version=VER)
        d1 = await acquitter(conn, **cle, ancre=ANCRE, demande=DemandeAcquittement(
            answer_id=aid, auteur="  membre du comité ", motif=" on décide sans la marge des pairs "))
        b.check((d1.action, d1.answer_id, d1.auteur, d1.motif) ==
                ("acquitter", aid, "membre du comité", "on décide sans la marge des pairs"),
                f"§1 le PV porte qui, quelle réponse, pourquoi — obtenu {d1.action}/{d1.answer_id}/"
                f"{d1.auteur!r}/{d1.motif!r}")
        b.check(d1.framework_version == VER and d1.decide_le is not None,
                "§1 le PV porte la VERSION des frameworks et l'INSTANT (version du dossier lue)")
        b.check(d1.ancre_etat == "found" and d1.fait_connu is not None
                and d1.fait_connu.accession == FDA.accession,
                "§1 le PV note le dernier fait important CONNU (ce qui rendra « nouveau » un fait futur)")
        st0 = await conn.fetchval("SELECT statut FROM framework_mandates WHERE id = $1", m0)
        b.check(st0 == "abandonne" and d1.mandat_remplace_id == m0,
                f"§1 la recherche en cours est ARRÊTÉE (mandat #{m0} → {st0}) et le PV garde son id")

        # ══ §2 RENVOYER ════════════════════════════════════════════════════════════════════════
        print("[2] renvoyer")
        d2 = await renvoyer(conn, **cle, ancre=ANCRE, demande=DemandeRenvoi(
            auteur="membre du comité", motif="la marge citée date de 2024",
            mandat="retrouver la marge brute publiée au 10-Q du T2 2026", answer_id=aid))
        ouverts = await read_open_mandates(conn, ticker_id=tk, framework_id=fw, framework_version=VER)
        du_comite = [m for m in ouverts if m.question_id == qid and m.origine == "comite"]
        b.require(du_comite, 1, "§2 le renvoi OUVRE exactement un mandat `comite`, lu par le bouclage")
        b.check(bool(du_comite) and du_comite[0].mandat ==
                "retrouver la marge brute publiée au 10-Q du T2 2026",
                "§2 la consigne du comité atteint le collecteur TELLE QUELLE")
        b.check(d2.mandat_id == await id_du_mandat_ouvert(conn, **cle, framework_version=VER),
                "§2 le PV pointe le mandat réellement ouvert")
        b.check(d2.mandat_remplace_id is None,
                "§2 aucune recherche en cours à remplacer (l'acceptation l'avait arrêtée)")
        d3 = await renvoyer(conn, **cle, ancre=INJOIGNABLE, demande=DemandeRenvoi(
            auteur="membre du comité", motif="précision", mandat="chercher aussi au 8-K du 2026-08-26"))
        n_ouv = await conn.fetchval(
            "SELECT count(*) FROM framework_mandates WHERE ticker_id = $1 AND framework_id = $2 "
            "AND framework_version = $3 AND question_id = $4 AND statut = 'ouvert' "
            "AND origine IN ('manager_renvoi', 'comite')", tk, fw, VER, qid)
        st2 = await conn.fetchval("SELECT statut FROM framework_mandates WHERE id = $1", d2.mandat_id)
        b.check(n_ouv == 1 and st2 == "abandonne" and d3.mandat_remplace_id == d2.mandat_id,
                f"§2 un second renvoi REMPLACE le premier — ouverts={n_ouv}, ancien={st2}")
        b.check(d3.ancre_etat == "unavailable" and d3.fait_connu is None,
                "§2 EDGAR illisible n'empêche pas de RENVOYER, et le PV le dit (#49)")

        # ══ §3 LES REFUS ═══════════════════════════════════════════════════════════════════════
        print("[3] les refus nommés")
        if autre is not None:
            await refus(conn, "§3 accepter la réponse d'une AUTRE question est refusé",
                        "n'est pas une réponse de", DecisionRefusee,
                        acquitter(conn, **cle, ancre=ANCRE, demande=DemandeAcquittement(
                            answer_id=autre["id"], auteur="m", motif="x")))
        await refus(conn, "§3 accepter une réponse INCONNUE est refusé", "introuvable",
                    DecisionRefusee, acquitter(conn, **cle, ancre=ANCRE, demande=DemandeAcquittement(
                        answer_id=-1, auteur="m", motif="x")))
        await refus(conn, "§3 accepter sur des faits ILLISIBLES est refusé", "illisibles",
                    DecisionRefusee, acquitter(conn, **cle, ancre=INJOIGNABLE,
                                               demande=DemandeAcquittement(answer_id=aid, auteur="m",
                                                                           motif="x")))
        await refus(conn, "§3 une question hors référentiel est refusée", "inconnue",
                    ReferenceInconnue, acquitter(conn, ticker_id=tk, framework_id=fw,
                                                 question_id="q_fictive", ancre=ANCRE,
                                                 demande=DemandeAcquittement(answer_id=aid,
                                                                             auteur="m", motif="x")))
        # L'analyse est refaite : une copie de la réponse la remplace (dans la transaction annulée).
        neuve = await conn.fetchval(
            "INSERT INTO framework_answers (framework, framework_version, question_id, ticker_id, "
            "analyste, statut, answer_json, cited_entry_ids, rang_degrade, methode_approximation, "
            "ingredients, motif) SELECT framework, framework_version, question_id, ticker_id, "
            "analyste, statut, answer_json, cited_entry_ids, rang_degrade, methode_approximation, "
            "ingredients, motif FROM framework_answers WHERE id = $1 RETURNING id", aid)
        await conn.execute("UPDATE framework_answers SET superseded_by = $2 WHERE id = $1", aid, neuve)
        await refus(conn, "§3 accepter une réponse REMPLACÉE depuis est refusé (lire la courante)",
                    "a été remplacée", DecisionRefusee,
                    acquitter(conn, **cle, ancre=ANCRE, demande=DemandeAcquittement(
                        answer_id=aid, auteur="m", motif="x")))

        # ══ §4 LA LECTURE ══════════════════════════════════════════════════════════════════════
        print("[4] la lecture du registre")
        reg = (await lire_registre(conn, ticker_id=tk, framework_version=VER)).get((fw, qid), [])
        b.check([d.id for d in reg] == [d3.id, d2.id, d1.id],
                f"§4 le PV se relit ENTIER, le plus récent d'abord — obtenu {[d.id for d in reg]}")
        pos = position_du_comite([d1], reponses_courantes=frozenset({neuve}), ancre=ANCRE)
        b.check(pos is not None and pos.acceptation.etat == "tombee_reponse_remplacee",
                "§4 une acceptation sur une réponse REMPLACÉE depuis tombe à la lecture")

        # ══ §5 LE PV NE SE RÉÉCRIT PAS ═════════════════════════════════════════════════════════
        print("[5] le procès-verbal ne se réécrit pas")
        for sql, label in (("UPDATE comite_decisions SET motif = 'réécrit' WHERE id = $1", "MODIFIE"),
                           ("DELETE FROM comite_decisions WHERE id = $1", "SUPPRIME")):
            sp = conn.transaction()
            await sp.start()
            try:
                await conn.execute(sql, d1.id)
                b.check(False, f"§5 le rôle applicatif {label} une décision du PV")
            except asyncpg.InsufficientPrivilegeError:
                b.check(True, f"§5 le rôle applicatif ne {label} pas une décision (droit refusé)")
            except Exception as e:  # noqa: BLE001
                b.check(False, f"§5 {label} refusé par autre chose que le droit : {e}")
            finally:
                await sp.rollback()
    finally:
        await tr.rollback()
        reste = await conn.fetchval("SELECT count(*) FROM comite_decisions WHERE auteur LIKE "
                                    "'membre du comité%' OR auteur = 'm'")
        b.check(reste == 0, f"§fin zéro résidu en base après ROLLBACK — {reste} ligne(s)")
        await conn.close()


asyncio.run(main())
sys.exit(b.summary())
