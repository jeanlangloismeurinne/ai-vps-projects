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
  • §6 RÉINITIALISER (#137, migration 058) : le PV relève la réponse courante mise de côté et arrête la
       recherche en cours ; LU PAR LE DOSSIER (`charger_etat_dossier`), la question est rouverte et la
       relance la refait ; une réponse écrite APRÈS la referme ; le chapitre = une ligne par question ;
       un chapitre vide est refusé.

Lancer : `bash checks/avec_base.sh check_comite_persist` (jamais dans `portfolio-backend`).
"""
import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, colonne_absente  # noqa: E402

b = Bilan()
_db_url = os.environ.get("CHECK_DB_URL", "")
if not _db_url or "@" not in _db_url:
    b.check(False, "§persistance non exécutée — CHECK_DB_URL absente ou factice ; l'état persisté "
                   "n'a PAS été mesuré")
    sys.exit(b.summary())

import asyncpg  # noqa: E402

from app.agents.v2.comite import (  # noqa: E402
    DecisionRefusee, acquitter, lire_registre, position_du_comite, reinitialiser,
    reinitialiser_chapitre, renvoyer, retablir)
from app.agents.v2.frameworks import load_frameworks  # noqa: E402
from app.agents.v2.manager_persist import (  # noqa: E402
    id_du_mandat_ouvert, persist_mandate, read_open_mandates)
from app.agents.v2.parcours import (  # noqa: E402
    ReferenceInconnue, _lignes, charger_etat_dossier, questions_a_relancer)
from app.contracts.comite_schema import (  # noqa: E402
    DemandeAcquittement, DemandeReinitialisation, DemandeRenvoi, DemandeRetablissement)
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
    # Le décodage JSON du pool applicatif (`db/database.py`) : §6 lit le dossier par son vrai chargeur.
    for t in ("jsonb", "json"):
        await conn.set_type_codec(t, encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    # PRÉREQUIS DE SCHÉMA (point 13, migration 060) — `_inscrire`/`lire_registre` portent désormais
    # `retablie_depuis_id` sur TOUT geste (acquitter/renvoyer/reinitialiser/retablir : une colonne
    # partagée, comme 059 l'a fait pour `ticker_archetypes`). Tant que la 060 n'est pas appliquée
    # (interdit de CETTE session), §1-§7 entiers ne peuvent pas tourner contre la VRAIE base — un
    # échec NOMMÉ ici, jamais une trace Python qui tue le script avant son bilan
    # (`feedback_check_degrade_en_sortant_a_zero`). Prouvé PAR AILLEURS : `negatif_060.sh` (copie de
    # la base, migration appliquée, 15/0) et un diagnostic `BEGIN … ROLLBACK` en rôle admin sur la
    # VRAIE base, migration appliquée SEULEMENT pour la durée de la transaction (jamais committée).
    if await colonne_absente(conn, "comite_decisions", "retablie_depuis_id"):
        b.check(False, "§1-§7 non exécutées — la migration 060 n'est PAS appliquée à cette base "
                       "(colonne `retablie_depuis_id` absente de `comite_decisions`) : "
                       "`_inscrire`/`lire_registre` sont des chemins PARTAGÉS par les 4 gestes, donc "
                       "CHAQUE écriture/lecture du comité (pas seulement `retablir`) en dépend "
                       "désormais. C'est l'état attendu de cette session (interdit d'appliquer la "
                       "060 à la vraie base) — voir `negatif_060.sh` et le rapport pour la preuve "
                       "par ailleurs")
        await conn.close()
        sys.exit(b.summary())
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

        # ══ §6 RÉINITIALISER ═══════════════════════════════════════════════════════════════════
        print("[6] réinitialiser — écrit au PV, lu par le dossier, refermé par une réponse postérieure")
        # Une question APPLICABLE à l'émetteur, avec une réponse courante, autre que celle des §1-§4 :
        # choisie dans le dossier réel (une question hors sujet ne s'ouvre ni ne se ferme).
        etat0 = await charger_etat_dossier(conn, tk)
        candidates = [r for r in etat0.reponses
                      if r.servie.question_id != qid and r.answer_id != aid
                      and r.servie.question_id in (etat0.applicables.get(r.servie.framework_id) or ())]
        b.check(bool(candidates), f"§6 fixture : {tk} a une réponse courante sur une question applicable")
        if not candidates:
            return
        q2, a2, fw2 = (candidates[0].servie.question_id, candidates[0].answer_id,
                       candidates[0].servie.framework_id)
        a2 = await conn.fetchval(
            "SELECT max(id) FROM framework_answers WHERE ticker_id = $1 AND framework = $2 "
            "AND framework_version = $3 AND question_id = $4 AND superseded_by IS NULL",
            tk, fw2, VER, q2)
        cle2 = dict(ticker_id=tk, framework_id=fw2, question_id=q2)
        print(f"  (question réinitialisée : {tk} · {fw2} · {q2}, réponse courante #{a2})")
        m2 = await persist_mandate(conn, FrameworkMandate(
            framework_id=fw2, question_id=q2, ticker_id=tk, origine="manager_renvoi",
            motif="renvoi manager (check)", mandat="re-collecter (check)", etat="ouvert"),
            framework_version=VER)
        d6 = await reinitialiser(conn, **cle2, ancre=INJOIGNABLE, demande=DemandeReinitialisation(
            auteur="gérant (check)", motif="reconstruction du test (#127)"))
        st6 = await conn.fetchval("SELECT statut FROM framework_mandates WHERE id = $1", m2)
        b.check((d6.action, d6.answer_id, d6.mandat_id) == ("reinitialiser", a2, None),
                f"§6 le PV relève la réponse COURANTE mise de côté (#{a2}) et n'ouvre aucun mandat — "
                f"obtenu {d6.action}/#{d6.answer_id}/{d6.mandat_id}")
        b.check(st6 == "abandonne" and d6.mandat_remplace_id == m2,
                f"§6 la recherche en cours est ARRÊTÉE (mandat #{m2} → {st6})")
        b.check(d6.ancre_etat == "unavailable",
                "§6 EDGAR illisible n'empêche pas de réinitialiser (rien ne doit tomber ensuite)")

        etat = await charger_etat_dossier(conn, tk)
        f2 = next(f for f in etat.fichier.frameworks if f.id == fw2)
        ligne = next(lq for lq in _lignes(etat, f2) if lq.question_id == q2)
        b.check(ligne.applicable is True, f"§6 fixture : {tk} · {q2} est applicable — obtenu {ligne.applicable}")
        b.check(ligne.manque is not None and (ligne.manque.nature, ligne.manque.cause)
                == ("rouverte_comite", "reinitialisation"),
                f"§6 LU PAR LE DOSSIER, la question est rouverte — obtenu "
                f"{ligne.manque and (ligne.manque.nature, ligne.manque.cause)}")
        b.check(q2 in questions_a_relancer(etat, fw2).ouvertes,
                "§6 la relance du chapitre REFAIT la question réinitialisée")

        # L'analyse est refaite APRÈS le geste (une transaction plus tard, en réel : ici l'instant est
        # posé explicitement, `now()` étant figé pour toute la transaction).
        apres = await conn.fetchval(
            "INSERT INTO framework_answers (framework, framework_version, question_id, ticker_id, "
            "analyste, statut, answer_json, cited_entry_ids, rang_degrade, methode_approximation, "
            "ingredients, motif, created_at) SELECT framework, framework_version, question_id, "
            "ticker_id, analyste, statut, answer_json, cited_entry_ids, rang_degrade, "
            "methode_approximation, ingredients, motif, now() + interval '1 minute' "
            "FROM framework_answers WHERE id = $1 RETURNING id", a2)
        await conn.execute("UPDATE framework_answers SET superseded_by = $2 WHERE id = $1", a2, apres)
        etat2 = await charger_etat_dossier(conn, tk)
        ligne2 = next(lq for lq in _lignes(etat2, f2) if lq.question_id == q2)
        b.check(ligne2.manque is None or ligne2.manque.nature != "rouverte_comite",
                f"§6 une réponse écrite APRÈS la réinitialisation la consomme — obtenu "
                f"{ligne2.manque and (ligne2.manque.nature, ligne2.manque.cause)}")

        await refus(conn, "§6 un chapitre SANS question applicable est refusé", "rien à réinitialiser",
                    DecisionRefusee, reinitialiser_chapitre(
                        conn, ticker_id=tk, framework_id=fw2, questions=[], ancre=ANCRE,
                        demande=DemandeReinitialisation(auteur="gérant (check)", motif="x")))
        qs = [q.id for q in f2.questions][:2]
        dch = await reinitialiser_chapitre(
            conn, ticker_id=tk, framework_id=fw2, questions=qs, ancre=ANCRE,
            demande=DemandeReinitialisation(auteur="gérant (check)", motif="chapitre (check)"))
        b.check([d.question_id for d in dch] == qs and all(d.action == "reinitialiser" for d in dch),
                f"§6 le chapitre inscrit UNE ligne par question — obtenu {[d.question_id for d in dch]}")

        # ══ §7 RÉTABLIR (point 13, migration 060) ═══════════════════════════════════════════════
        print("[7] rétablir — la baisse RÉELLE de NVDA ma_1 (#1475 repondu → #1499 non_fondable)")
        # Fixture copiée du réel (mesurée le 2026-10-18, 07 §3.13) : la SEULE baisse en vigueur
        # aujourd'hui dans tout le corpus. Les quatre refus (a)-(d) n'écrivent RIEN dans
        # `comite_decisions` — ils s'arrêtent à la validation, avant `_inscrire` — et tournent donc
        # contre le schéma RÉEL, migration 060 appliquée ou non. Seul l'EFFET (e) insère au PV et
        # exige la colonne `retablie_depuis_id` : gardé explicitement, jamais un saut muet
        # (`feedback_check_degrade_en_sortant_a_zero`).
        row_cour = await conn.fetchrow(
            "SELECT id, ticker_id, framework, framework_version, question_id, statut, superseded_by "
            "FROM framework_answers WHERE id = 1499")
        row_prec = await conn.fetchrow(
            "SELECT id, ticker_id, framework, framework_version, question_id, statut, superseded_by "
            "FROM framework_answers WHERE id = 1475")
        if row_cour is None or row_prec is None or row_cour["superseded_by"] is not None \
                or row_prec["superseded_by"] != 1499 or row_cour["statut"] != "non_fondable" \
                or row_prec["statut"] != "repondu":
            b.check(False, "§7 fixture : NVDA #1475→#1499 (ma_1) n'est plus la baisse attendue — "
                           "le réel a changé depuis le diagnostic du 2026-10-18, section non mesurée")
        else:
            tk7, fw7, qid7, ver7 = (row_cour["ticker_id"], row_cour["framework"],
                                    row_cour["question_id"], row_cour["framework_version"])
            cle7 = dict(ticker_id=tk7, framework_id=fw7, question_id=qid7)
            print(f"  (fixture confirmée : {tk7} · {fw7} · {qid7}, #{row_prec['id']} → #{row_cour['id']})")

            # (a) la réponse désignée n'est pas de CE dossier (ticker/framework/version/question).
            autre_tuple = await conn.fetchval(
                "SELECT id FROM framework_answers WHERE ticker_id != $1 LIMIT 1", tk7)
            await refus(conn, "§7(a) rétablir une réponse d'un AUTRE dossier est refusé",
                       "n'est pas une réponse de", DecisionRefusee,
                       retablir(conn, **cle7, ancre=ANCRE, demande=DemandeRetablissement(
                           answer_id=autre_tuple, auteur="comité", motif="x")))

            # (b) la réponse désignée est DU dossier, mais n'est pas la précédente IMMÉDIATE (ici :
            # la courante elle-même, dont `superseded_by` n'est PAS 1499).
            await refus(conn, "§7(b) désigner une réponse qui n'est pas la précédente IMMÉDIATE "
                              "est refusé", "PRÉCÉDENTE IMMÉDIATE", DecisionRefusee,
                       retablir(conn, **cle7, ancre=ANCRE, demande=DemandeRetablissement(
                           answer_id=row_cour["id"], auteur="comité", motif="x")))

            # (c) une lignée réelle qui N'EST PAS une baisse : NVDA qf_7, #1197 (repondu) → #1214
            # (repondu), fondement ÉGAL — une précédente IMMÉDIATE réelle, mais pas une dégradation.
            # (qf_7, pas qf_1/qf_2 : §3 et §6 supersèdent déjà la réponse éprouvée et celle du
            # chapitre réinitialisé — reprendre l'une d'elles lirait une lignée que CE check a
            # lui-même mutée, pas le réel.)
            row_c197 = await conn.fetchrow(
                "SELECT id, statut, superseded_by FROM framework_answers WHERE id = 1197")
            row_c214 = await conn.fetchrow(
                "SELECT id, ticker_id, framework, framework_version, question_id, statut, "
                "superseded_by FROM framework_answers WHERE id = 1214")
            if row_c197 is None or row_c214 is None or row_c197["superseded_by"] != 1214 \
                    or row_c214["superseded_by"] is not None or row_c197["statut"] != "repondu" \
                    or row_c214["statut"] != "repondu":
                b.check(False, "§7(c) fixture : NVDA qf_7 #1197→#1214 n'est plus un couple à "
                               "fondement ÉGAL — section non mesurée")
            else:
                cle7c = dict(ticker_id=row_c214["ticker_id"], framework_id=row_c214["framework"],
                            question_id=row_c214["question_id"])
                await refus(conn, "§7(c) rétablir sur une question qui N'EST PAS une baisse (ÉGAL) "
                                  "est refusé", "n'est pas une baisse à lire", DecisionRefusee,
                           retablir(conn, **cle7c, ancre=ANCRE, demande=DemandeRetablissement(
                               answer_id=row_c197["id"], auteur="comité", motif="x")))

            # (d) la précédente désignée ne valide plus contre le contrat EN VIGUEUR — une lignée
            # SYNTHÉTIQUE, isolée (analyste dédié, ET tuple DISTINCT de ma_1 pour ne pas perturber
            # §7(e) : `max(id)` n'a rien à départager entre questions différentes), fabriquée DANS
            # la transaction (jamais écrite pour de vrai) sur la MÊME question que §7(c) (NVDA
            # qf_7) : une précédente au JSON tronqué (contrat antérieur), supersédée par une
            # courante VALIDE dont le fondement a réellement baissé (`non_fondable` sous `repondu`).
            tk_d, fw_d, qid_d, ver_d = (row_c214["ticker_id"], row_c214["framework"],
                                        row_c214["question_id"], row_c214["framework_version"])
            cle7d = dict(ticker_id=tk_d, framework_id=fw_d, question_id=qid_d)
            # Objet PYTHON natif, jamais pré-sérialisé : le codec jsonb de CETTE connexion encode
            # déjà (`json.dumps`) — lui donner une chaîne double-encoderait (bug observé : la
            # colonne aurait porté une STRING jsonb, pas un OBJET, et `model_validate` l'aurait vu
            # comme `input_type=str`).
            cour_json_d = {
                "schema_version": "v3.0.0", "framework_id": fw_d, "framework_version": ver_d,
                "question_id": qid_d, "ticker_id": tk_d, "analyste": "analyste_test_060",
                "statut": "non_fondable",
                "gap": {"dimension": "d", "champs_cibles": [qid_d], "manque": "m",
                       "priorite": "haute", "coverage_actuelle": "0/1"}}
            prec_cassee = await conn.fetchval(
                "INSERT INTO framework_answers (framework, framework_version, question_id, "
                "ticker_id, analyste, statut, answer_json) VALUES ($1, $2, $3, $4, "
                "'analyste_test_060', 'repondu', '{\"statut\": \"repondu\"}'::jsonb) RETURNING id",
                fw_d, ver_d, qid_d, tk_d)
            cour_synthetique = await conn.fetchval(
                "INSERT INTO framework_answers (framework, framework_version, question_id, "
                "ticker_id, analyste, statut, answer_json) VALUES ($1, $2, $3, $4, "
                "'analyste_test_060', 'non_fondable', $5) RETURNING id",
                fw_d, ver_d, qid_d, tk_d, cour_json_d)
            await conn.execute("UPDATE framework_answers SET superseded_by = $2 WHERE id = $1",
                              prec_cassee, cour_synthetique)
            await refus(conn, "§7(d) une précédente écrite sous un contrat ANTÉRIEUR est refusée "
                              "(réinitialiser plutôt)", "contrat antérieur", DecisionRefusee,
                       retablir(conn, **cle7d, ancre=ANCRE, demande=DemandeRetablissement(
                           answer_id=prec_cassee, auteur="comité", motif="x")))

            # (e) L'EFFET — le garde-fou de tête (`colonne_absente`) a déjà arrêté le script si la
            # colonne manquait : ici, elle existe forcément.
            if True:
                mandat7 = await persist_mandate(conn, FrameworkMandate(
                    framework_id=fw7, question_id=qid7, ticker_id=tk7, origine="manager_renvoi",
                    motif="renvoi manager (check)", mandat="re-collecter (check)", etat="ouvert"),
                    framework_version=ver7)
                d7 = await retablir(conn, **cle7, ancre=ANCRE, demande=DemandeRetablissement(
                    answer_id=row_prec["id"], auteur="comité (check)",
                    motif="rétablissement point 13 (check)"))
                b.check(d7.action == "retablir" and d7.retablie_depuis_id == row_prec["id"]
                        and d7.answer_id != row_prec["id"] and d7.mandat_id is None,
                        f"§7(e) le PV porte les DEUX ids (copie + précédente rétablie) — obtenu "
                        f"action={d7.action}/answer_id={d7.answer_id}/retablie_depuis_id="
                        f"{d7.retablie_depuis_id}")
                superseded = await conn.fetchval(
                    "SELECT superseded_by FROM framework_answers WHERE id = $1", row_cour["id"])
                b.check(superseded == d7.answer_id,
                        f"§7(e) la COURANTE dégradée est SUPERSÉDÉE par la copie — obtenu {superseded}")
                statut_servi = await conn.fetchval(
                    "SELECT statut FROM framework_mandates WHERE id = $1", mandat7)
                b.check(statut_servi == "servi",
                        f"§7(e) un mandat ouvert est SERVI comme effet de l'écriture (§14) — "
                        f"obtenu {statut_servi}")
                copie_statut = await conn.fetchval(
                    "SELECT statut FROM framework_answers WHERE id = $1", d7.answer_id)
                b.check(copie_statut == row_prec["statut"],
                        f"§7(e) la copie porte le STATUT de la PRÉCÉDENTE (`repondu`), jamais celui "
                        f"de la courante dégradée — obtenu {copie_statut}")
    finally:
        await tr.rollback()
        reste = await conn.fetchval("SELECT count(*) FROM comite_decisions WHERE auteur LIKE "
                                    "'membre du comité%' OR auteur IN ('m', 'gérant (check)')")
        b.check(reste == 0, f"§fin zéro résidu en base après ROLLBACK — {reste} ligne(s)")
        await conn.close()


asyncio.run(main())
sys.exit(b.summary())
