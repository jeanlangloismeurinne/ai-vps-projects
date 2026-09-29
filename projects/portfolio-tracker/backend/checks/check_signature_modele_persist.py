"""Vérification de l'ÉCRITURE des registres du modèle de valorisation contre la VRAIE base (capacité
4 bis, migration 051). Tout se joue dans UNE transaction annulée à la fin : zéro résidu
(`feedback_fixture_pollue_le_reel` — jamais une signature fabriquée laissée en base : un PV
append-only la garderait pour toujours).

  • §1 PROPOSER : la version s'inscrit, se relit IDENTIQUE (le contenu JSONB redonne le même modèle) ;
       refus nommés : numérotation qui ne suit pas le registre, modèle d'un autre titre, modèle qui ne
       tient pas contre le dossier.
  • §2 SIGNER / ÉCARTER : la signature inscrit la fourchette que le comité voit ; refus nommés : version
       déjà décidée, version remplacée par une plus récente, version inconnue, dossier du jour qui ne
       tient plus ; écarter une version en attente laisse la signée en référence.
  • §3 LA LECTURE : `lire_atelier` + `servir_atelier` sur ce qui vient d'être écrit.
  • §4 LE DOSSIER RÉEL : `charger_dossier_valorisation` rend, pour RVMD, des réponses acquittées qui
       sont des réponses COURANTES du titre, et des pièces courantes du titre.
  • §5 LES REGISTRES NE SE RÉÉCRIVENT PAS : le rôle applicatif ne modifie ni ne supprime.

Le dossier des §1-§3 est INJECTÉ (celui des modèles fictifs) : on éprouve l'écriture, pas le pont,
déjà prouvé hors ligne. Lancer : `bash checks/avec_base.sh check_signature_modele_persist`.
"""
import asyncio
import copy
import json
import os
import sys
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

from _modeles_fictifs import ARBRE, DOSSIER_RVMD  # noqa: E402
from app.contracts.modele_valorisation_schema import ModeleValorisation  # noqa: E402
from app.contracts.signature_modele_schema import DemandeDecisionModele  # noqa: E402
from app.valorisation.signature import (  # noqa: E402
    ActeRefuse, DossierValorisation, charger_dossier_valorisation, ecarter, lire_atelier, proposer,
    servir_atelier, signer)

DOSSIER = DossierValorisation(ticker_id="RVMD", reponses_acquittees=DOSSIER_RVMD["reponses_acquittees"],
                              pieces_du_dossier=frozenset(DOSSIER_RVMD["pieces_du_dossier"]),
                              questions_sans_objet=DOSSIER_RVMD["questions_sans_objet"],
                              reprises_admises=DOSSIER_RVMD["reprises_admises"])
SANS_PIECE = DossierValorisation(ticker_id="RVMD", reponses_acquittees=DOSSIER_RVMD["reponses_acquittees"],
                                 pieces_du_dossier=frozenset({501, 502, 503}),
                                 questions_sans_objet=DOSSIER_RVMD["questions_sans_objet"],
                                 reprises_admises=DOSSIER_RVMD["reprises_admises"])
DEMANDE = DemandeDecisionModele(auteur="membre du comité", motif="hypothèses relues en séance, ancrées")


def modele(v: int, **surcharges) -> ModeleValorisation:
    m = copy.deepcopy(ARBRE)
    m["version"] = v
    m.update(surcharges)
    return ModeleValorisation.model_validate(m)


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


async def compte(conn) -> int:
    return await conn.fetchval(
        "SELECT (SELECT count(*) FROM modeles_valorisation) + (SELECT count(*) FROM modeles_valorisation_decisions)")


async def main() -> None:
    conn = await asyncpg.connect(_db_url.replace("+asyncpg", ""))
    # Le codec JSONB du POOL (`init_pool`), rejoué à l'identique (convention #1).
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    avant = await compte(conn)
    tr = conn.transaction()
    await tr.start()
    try:
        print("§1 proposer")
        await refus(conn, "une v2 proposée sur un registre vide", "la prochaine version de `RVMD` est la v1",
                    ActeRefuse, proposer(conn, modele(2), auteur="agent", dossier=DOSSIER))
        await refus(conn, "un modèle NVDA proposé au dossier RVMD", "proposé au dossier de `RVMD`",
                    ActeRefuse, proposer(conn, modele(1, ticker_id="NVDA"), auteur="agent", dossier=DOSSIER))
        await refus(conn, "un modèle qui ne tient pas contre le dossier", "504",
                    ActeRefuse, proposer(conn, modele(1), auteur="agent", dossier=SANS_PIECE))
        v1 = await proposer(conn, modele(1), auteur="agent de valorisation", dossier=DOSSIER)
        b.check(v1.version == 1 and v1.modele == modele(1),
                "v1 inscrite, et relue du JSONB elle redonne EXACTEMENT le modèle proposé")

        print("§2 signer / écarter")
        s1 = await signer(conn, ticker_id="RVMD", version=1, demande=DEMANDE, dossier=DOSSIER)
        attendu = servir_atelier([v1], [], DOSSIER).en_attente.fourchette
        b.check(s1.action == "signer" and s1.fourchette == attendu,
                f"la signature inscrit au PV la fourchette que le comité voyait ({s1.fourchette})")
        b.check(set(s1.fourchette.par_evenement) == {"succes_a", "succes_b"},
                "le détail par événement est au PV et se relit (JSONB → paires)")
        await refus(conn, "signer une seconde fois la v1", "a déjà été signée", ActeRefuse,
                    signer(conn, ticker_id="RVMD", version=1, demande=DEMANDE, dossier=DOSSIER))
        await refus(conn, "écarter une v1 déjà signée", "a déjà été signée", ActeRefuse,
                    ecarter(conn, ticker_id="RVMD", version=1, demande=DEMANDE))
        await refus(conn, "signer une version jamais proposée", "aucune version 9", LookupError,
                    signer(conn, ticker_id="RVMD", version=9, demande=DEMANDE, dossier=DOSSIER))
        v2 = await proposer(conn, modele(2), auteur="agent de valorisation", dossier=DOSSIER)
        v3 = await proposer(conn, modele(3), auteur="membre du comité", dossier=DOSSIER)
        await refus(conn, "signer la v2 remplacée par la v3", "a été remplacée", ActeRefuse,
                    signer(conn, ticker_id="RVMD", version=2, demande=DEMANDE, dossier=DOSSIER))
        await refus(conn, "signer la v3 alors qu'une pièce a été remplacée", "ne tient plus", ActeRefuse,
                    signer(conn, ticker_id="RVMD", version=3, demande=DEMANDE, dossier=SANS_PIECE))
        x3 = await ecarter(conn, ticker_id="RVMD", version=3, demande=DEMANDE)
        b.check(x3.action == "ecarter" and x3.fourchette is None, "la v3 est écartée, sans fourchette adoptée")

        print("§3 lecture")
        versions, pv = await lire_atelier(conn, "RVMD")
        b.check([v.version for v in versions] == [1, 2, 3] and [v.id for v in versions] == [v1.id, v2.id, v3.id],
                "le registre rend les trois versions dans l'ordre")
        b.check([d.id for d in pv] == [x3.id, s1.id], "le PV se relit le plus récent d'abord")
        a = servir_atelier(versions, pv, DOSSIER)
        b.check(a.etat == "signe" and a.signee.version.version == 1 and a.signee.etat == "tient",
                f"après l'écart de la v3, la v1 signée est la référence et tient (servi : {a.etat})")
        a = servir_atelier(versions, pv, SANS_PIECE)
        b.check(a.signee.etat == "a_revoir" and a.signee.signature.fourchette == s1.fourchette,
                "relue contre un dossier où une pièce est remplacée, la v1 est « à revoir », fourchette signée gardée")

        print("§4 le dossier réel")
        from app.agents.v2.parcours import charger_etat_dossier, dresser_niveau1
        from app.agents.v2.projection_memo import memo_de_l_etat
        reel = await charger_dossier_valorisation(conn, "RVMD")
        etat = await charger_etat_dossier(conn, "RVMD")
        alerte = dresser_niveau1(etat, memo_de_l_etat(etat)).peut_on_decider
        en_manque = {m.question_id for m in alerte.manques}
        acquittees = {r.answer_id: r.servie.question_id for r in etat.reponses if r.verdict == "acquitte"}
        print(f"  mesuré : RVMD — {len(acquittees)} réponse(s) acquittée(s) par le contrôle, dont "
              f"{len(reel.reponses_acquittees)} reprenable(s) {sorted({r.question_id for r in reel.reponses_acquittees.values()})} ; "
              f"alerte : {sorted(en_manque)} ; {len(reel.pieces_du_dossier)} pièce(s) courante(s)")
        courantes = {r["id"]: r["question_id"] for r in await conn.fetch(
            "SELECT id, question_id FROM framework_answers WHERE ticker_id = 'RVMD' AND superseded_by IS NULL")}
        # Non vide AVANT le `all(...)` : vert sur zéro élément, il ne prouverait rien (5ᵉ faux vert).
        b.check(len(reel.reponses_acquittees) > 0,
                "au moins une réponse de RVMD est reprenable — sinon le §4 ne discrimine rien")
        b.check(all(courantes.get(i) == r.question_id for i, r in reel.reponses_acquittees.items()),
                "les réponses reprenables sont des réponses COURANTES de RVMD, à leur question")
        # PAS DE DETTE (arbitrage du 2026-09-29) : une réponse reprenable porte l'ENCADRÉ que sa question
        # déclare — les réponses d'avant l'encadré ont été réémises sur les mêmes pièces. Lu sur l'état
        # réel : c'est lui, pas une fixture, que la valorisation reprendra.
        from app.agents.v2.frameworks import question_profiles
        profils = question_profiles(etat.fichier)
        sans_encadre = sorted(f"{r.question_id} (#{a}) : rend {sorted(r.chiffres)}, déclare "
                              f"{sorted(c.id for c in profils[r.question_id]['chiffres_cles'])}"
                              for a, r in reel.reponses_acquittees.items()
                              if set(r.chiffres) != {c.id for c in profils[r.question_id]["chiffres_cles"]})
        print(f"  mesuré : RVMD — encadrés repris : "
              f"{ {r.question_id: dict(r.chiffres) for r in reel.reponses_acquittees.values()} }")
        b.check(not sans_encadre,
                f"toute réponse reprenable de RVMD porte l'encadré que sa question déclare — sinon : {sans_encadre}")
        # L'autre point de lecture : l'alerte « peut-on décider ? ». Une réponse dont la question y est
        # un manque (périmée par l'approbation FDA, renvoyée…) ne peut pas donner un chiffre à la valorisation.
        repris_en_manque = sorted(r.question_id for r in reel.reponses_acquittees.values()
                                  if r.question_id in en_manque)
        b.check(not repris_en_manque,
                f"aucune réponse reprenable ne porte sur une question que l'alerte dit manquante ({repris_en_manque})")
        b.check(len(en_manque & set(acquittees.values())) > 0,
                "le dossier réel a des réponses acquittées mais périmées — le cas que la règle écarte est présent")
        # Option (c), #99 : sur RVMD (biotech sans chiffre d'affaires), qf_1 est sans objet — le modèle
        # portera son propre coût du capital ; qf_6, qui tient, doit être repris, jamais remplacé.
        print(f"  mesuré : RVMD — sans objet : {sorted(reel.questions_sans_objet)}")
        b.check("qf_1" in reel.questions_sans_objet and "qf_1" in reel.reprises_admises,
                "RVMD : qf_1 est sans objet et reprise par la valorisation — le cas de l'option (c) est réel")
        b.check(not ({r.question_id for r in reel.reponses_acquittees.values()} & reel.questions_sans_objet),
                "aucune question n'est à la fois reprenable et sans objet")
        n_pieces = await conn.fetchval(
            "SELECT count(*) FROM knowledge_entries WHERE ticker_id = 'RVMD' AND superseded_by IS NULL")
        b.check(len(reel.pieces_du_dossier) == n_pieces and n_pieces > 0,
                f"les pièces du dossier sont les {n_pieces} pièces courantes de RVMD (rendues : {len(reel.pieces_du_dossier)})")
        autre = await conn.fetchval(
            "SELECT count(*) FROM knowledge_entries WHERE id = ANY($1::int[]) AND ticker_id <> 'RVMD'",
            sorted(reel.pieces_du_dossier))
        b.check(autre == 0, f"aucune pièce d'un autre titre dans le dossier RVMD ({autre})")

        print("§5 registres append-only")
        for t in ("modeles_valorisation", "modeles_valorisation_decisions"):
            role = await conn.fetchval(
                "SELECT has_table_privilege(current_user, $1, 'UPDATE') OR has_table_privilege(current_user, $1, 'DELETE')", t)
            b.check(role is False, f"le rôle applicatif ne peut ni modifier ni supprimer `{t}`")
    finally:
        await tr.rollback()
    apres = await compte(conn)
    b.check(apres == avant, f"§fin zéro résidu en base après ROLLBACK ({avant} ligne(s) avant, {apres} après)")
    await conn.close()


asyncio.run(main())
sys.exit(b.summary())
