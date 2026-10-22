"""Vérification de l'ÉCRITURE de l'architecture et de sa SIGNATURE contre la VRAIE base (lot M3,
migrations 061 déjà en place / 062 ÉCRITE MAIS NON APPLIQUÉE — §0 de la spec M3 : Opus applique 062
après vérification). Tout se joue dans UNE transaction annulée à la fin : zéro résidu
(`feedback_fixture_pollue_le_reel`).

  • §1 PROPOSER : une architecture NVDA (fixture copiée du réel) s'inscrit dans `architectures_modele`
       (061, déjà en place), se relit IDENTIQUE ; une seconde v1 est refusée (`RegistreRefuse`).
  • §2 APPEND-ONLY (061) : le rôle applicatif ne modifie ni ne supprime `architectures_modele`.
  • §3 SIGNATURE (062) : SI la table `architectures_modele_decisions` existe (après qu'Opus l'aura
       appliquée), signer → seconde décision refusée (409 côté service / UNIQUE côté base) → écarter
       sur une autre version → version remplacée non décidable → append-only. TANT QU'ELLE N'EXISTE
       PAS, cette section est nommée NON EXÉCUTÉE (pas sautée en silence,
       `feedback_check_degrade_en_sortant_a_zero`) : c'est l'état ATTENDU de cette session.

Lancer : `bash checks/avec_base.sh check_architecture_persist`.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, table_absente  # noqa: E402

b = Bilan()
_db_url = os.environ.get("CHECK_DB_URL", "")
if not _db_url or "@" not in _db_url:
    b.check(False, "§persistance non exécutée — CHECK_DB_URL absente ou factice ; l'état persisté "
                   "n'a PAS été mesuré")
    sys.exit(b.summary())

import asyncpg  # noqa: E402

from app.contracts.architecture_signature_schema import DemandeDecisionArchitecture  # noqa: E402
from app.contracts.modele_entreprise_schema import Architecture  # noqa: E402
from app.modele_entreprise.referentiel import load_referentiel  # noqa: E402
from app.modele_entreprise.registre import RegistreRefuse, proposer_architecture  # noqa: E402
from app.modele_entreprise.signature import ActeRefuse, ecarter, signer  # noqa: E402

FIXTURE_NVDA = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "modele_entreprise" / "NVDA.json").read_text(encoding="utf-8"))


async def main() -> None:
    conn = await asyncpg.connect(_db_url.replace("+asyncpg", ""))
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")

    if await table_absente(conn, "architectures_modele"):
        b.check(False, "§persistance non exécutée — migration 061 absente de cette base.")
        await conn.close()
        sys.exit(b.summary())

    ref = load_referentiel()
    arch1 = Architecture.model_validate(FIXTURE_NVDA)
    arch2 = Architecture.model_validate({**FIXTURE_NVDA, "version": 2})

    tr = conn.transaction()
    await tr.start()
    try:
        print("§1 proposer")
        id1 = await proposer_architecture(conn, arch1, ref, auteur="architecte (test)")
        b.check(isinstance(id1, int), f"l'architecture NVDA v1 s'inscrit (#{id1})")
        relue = await conn.fetchrow(
            "SELECT ticker_id, version, contenu FROM architectures_modele WHERE id = $1", id1)
        b.check(relue["ticker_id"] == "NVDA" and relue["version"] == 1
                and Architecture.model_validate(relue["contenu"]) == arch1,
                "relue du JSONB, l'architecture redonne EXACTEMENT ce qui a été proposé")
        try:
            await proposer_architecture(conn, arch1, ref, auteur="architecte (test)")
            b.check(False, "une seconde proposition v1 pour NVDA : devait être refusée")
        except RegistreRefuse as e:
            b.check("v2" in str(e), f"une seconde proposition v1 est refusée (nomme la version "
                                    f"attendue) : {e}")

        print("§2 append-only (061)")
        role = await conn.fetchval(
            "SELECT has_table_privilege(current_user, 'architectures_modele', 'UPDATE') OR "
            "has_table_privilege(current_user, 'architectures_modele', 'DELETE')")
        b.check(role is False, "le rôle applicatif ne peut ni modifier ni supprimer `architectures_modele`")

        print("§3 signature (062)")
        if await table_absente(conn, "architectures_modele_decisions"):
            b.check(False, "§3 signature NON EXÉCUTÉE — migration 062 absente de cette base "
                           "(écrite, non appliquée : état ATTENDU de la session M3, §0 de la spec).")
        else:
            # v2 REMPLACE v1 (jamais décidée) avant toute signature — le cas « version remplacée ».
            id2 = await proposer_architecture(conn, arch2, ref, auteur="architecte (test)")
            demande = DemandeDecisionArchitecture(
                auteur="comité (test)", motif="Motif de signature pour ce test, assez long.")

            def juger_tient(_a):
                return True, "", ("[S3b] signal de test",)

            try:
                await signer(conn, ticker_id="NVDA", version=1, demande=demande, juger=juger_tient)
                b.check(False, "signer v1 alors que v2 l'a REMPLACÉE (jamais décidée) : devait être refusé")
            except ActeRefuse as e:
                b.check("remplacée" in str(e), f"v1 remplacée par v2, non décidable, refusée nommément : {e}")

            decision = await signer(conn, ticker_id="NVDA", version=2, demande=demande, juger=juger_tient)
            b.check(decision.action == "signer" and decision.signaux == ["[S3b] signal de test"],
                    "la v2 (en attente) se signe, avec ses signaux du jour au PV")
            try:
                await signer(conn, ticker_id="NVDA", version=2, demande=demande, juger=juger_tient)
                b.check(False, "une seconde décision sur la v2 (déjà signée) : devait être refusée")
            except ActeRefuse as e:
                b.check("déjà" in str(e), f"seconde décision sur v2 refusée côté SERVICE (409) : {e}")
            try:
                # Point de sauvegarde : le refus attendu de la base n'avorte que lui, pas la transaction
                # englobante (sans lui, la v3 ci-dessous tombait en InFailedSQLTransactionError).
                async with conn.transaction():
                    await conn.execute(
                        "INSERT INTO architectures_modele_decisions (architecture_id, action, auteur, motif, signaux) "
                        "VALUES ($1, 'signer', 'x', 'Motif suffisant pour ce test de doublon.', '[]')", id2)
                b.check(False, "une seconde ligne de décision pour la MÊME architecture_id : devait être refusée")
            except asyncpg.PostgresError as e:
                b.check("architectures_modele_decisions_unique" in str(e),
                        f"seconde décision refusée côté BASE (contrainte UNIQUE) : {e}")

            # v3 attend, et s'écarte.
            arch3 = Architecture.model_validate({**FIXTURE_NVDA, "version": 3})
            await proposer_architecture(conn, arch3, ref, auteur="architecte (test)")
            demande_ecart = DemandeDecisionArchitecture(
                auteur="comité (test)", motif="Motif d'écart pour ce test, assez long aussi.")
            decision2 = await ecarter(conn, ticker_id="NVDA", version=3, demande=demande_ecart)
            b.check(decision2.action == "ecarter", "la v3 (en attente) s'écarte")

            role2 = await conn.fetchval(
                "SELECT has_table_privilege(current_user, 'architectures_modele_decisions', 'UPDATE') OR "
                "has_table_privilege(current_user, 'architectures_modele_decisions', 'DELETE')")
            b.check(role2 is False, "le rôle applicatif ne peut ni modifier ni supprimer "
                                    "`architectures_modele_decisions`")
    finally:
        await tr.rollback()
    await conn.close()


asyncio.run(main())
sys.exit(b.summary())
