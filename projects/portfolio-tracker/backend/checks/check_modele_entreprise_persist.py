"""Vérification de l'ÉCRITURE des registres du classeur de l'entreprise contre la VRAIE base
(lot M1, migration 061). Tout se joue dans UNE transaction annulée à la fin : zéro résidu
(`feedback_fixture_pollue_le_reel`).

  • §1 PROPOSER : une architecture NVDA (fixture copiée du réel) s'inscrit, se relit IDENTIQUE.
  • §2 FOURCHETTE : une fourchette s'inscrit, rattachée à cette version.
  • §3 SCÉNARIO : un scénario nommé à deux déplacements s'inscrit dans une transaction explicite,
       et se relit avec ses déplacements ; `SCENARIO_CENTRAL` est refusé.
  • §4 APPEND-ONLY : le rôle applicatif ne modifie ni ne supprime, sur les quatre registres.

Tant que la migration 061 n'est PAS appliquée, ce check SORT EN ÉCHEC en le nommant, jamais en
sautant une section (`feedback_check_degrade_en_sortant_a_zero`).

Lancer : `bash checks/avec_base.sh check_modele_entreprise_persist`.
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

from app.contracts.modele_entreprise_schema import Architecture, Deplacement, Fourchette, Scenario, SCENARIO_CENTRAL  # noqa: E402
from app.modele_entreprise.referentiel import load_referentiel  # noqa: E402
from app.modele_entreprise.registre import (  # noqa: E402
    RegistreRefuse, inscrire_fourchette, inscrire_scenario, proposer_architecture)

FIXTURE_NVDA = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "modele_entreprise" / "NVDA.json").read_text(encoding="utf-8"))


async def compte(conn) -> int:
    return await conn.fetchval(
        "SELECT (SELECT count(*) FROM architectures_modele) + (SELECT count(*) FROM modele_fourchettes) + "
        "(SELECT count(*) FROM modele_scenarios) + (SELECT count(*) FROM modele_deplacements)")


async def main() -> None:
    conn = await asyncpg.connect(_db_url.replace("+asyncpg", ""))
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")

    if await table_absente(conn, "architectures_modele"):
        b.check(False, "§persistance non exécutée — migration 061 absente de cette base (table "
                       "`architectures_modele` absente). État attendu de cette session (§0 de la "
                       "spec M1 : Opus vérifie d'abord).")
        await conn.close()
        sys.exit(b.summary())

    ref = load_referentiel()
    arch = Architecture.model_validate(FIXTURE_NVDA)
    avant = await compte(conn)
    tr = conn.transaction()
    await tr.start()
    try:
        print("§1 proposer")
        architecture_id = await proposer_architecture(conn, arch, ref, auteur="agent architecte (test)")
        b.check(isinstance(architecture_id, int), f"l'architecture NVDA s'inscrit (#{architecture_id})")
        relue = await conn.fetchrow(
            "SELECT ticker_id, version, schema_version, version_referentiel, contenu "
            "FROM architectures_modele WHERE id = $1", architecture_id)
        b.check(relue["ticker_id"] == "NVDA" and relue["version"] == 1
                and Architecture.model_validate(relue["contenu"]) == arch,
                "relue du JSONB, l'architecture redonne EXACTEMENT ce qui a été proposé")
        try:
            await proposer_architecture(conn, arch, ref, auteur="agent architecte (test)")
            b.check(False, "une seconde proposition v1 pour NVDA : devait être refusée")
        except RegistreRefuse as e:
            b.check("v2" in str(e), f"une seconde proposition v1 pour NVDA est refusée (nommant la version "
                                    f"attendue) : {e}")

        print("§2 fourchette")
        fourchette = Fourchette.model_validate({
            "bloc": "unites_calcul_ia", "variable": "croissance_du_marche", "periode_debut": "FY2025",
            "periode_fin": "FY2027", "bas": 0.0, "haut": 0.30, "methode": "dispersion_observee",
            "origine_bas": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]},
            "origine_haut": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]}})
        fourchette_id = await inscrire_fourchette(conn, architecture_id, fourchette, auteur="analyste (test)")
        relue_f = await conn.fetchrow(
            "SELECT architecture_id, bloc, variable, bas, haut FROM modele_fourchettes WHERE id = $1",
            fourchette_id)
        b.check(relue_f["architecture_id"] == architecture_id and relue_f["bloc"] == "unites_calcul_ia"
                and relue_f["bas"] == 0.0 and relue_f["haut"] == 0.30,
                "la fourchette s'inscrit, rattachée à la version proposée, et se relit")

        print("§3 scénario et déplacements")
        deplacements = [
            Deplacement.model_validate({
                "bloc": "unites_calcul_ia", "variable": "croissance_du_marche", "periode_debut": "FY2025",
                "periode_fin": "FY2026", "cible": "borne_basse",
                "motif": "Un grand hébergeur internalise une partie de ses achats, motif testé ici."}),
            Deplacement.model_validate({
                "bloc": "charges_non_allouees", "variable": "couts_communs", "periode_debut": "FY2025",
                "periode_fin": "FY2026", "cible": "valeur_dite", "valeur_dite": 500.0,
                "motif": "Un programme d'économies annoncé relève les coûts communs, motif testé ici.",
                "source_entry_refs": [501]}),
        ]
        scenario = Scenario.model_validate({
            "nom": "scenario_test_m1", "recit": "Un grand hébergeur internalise une partie de ses achats.",
            "nature": "nomme", "deplacements": [d.model_dump(mode="json") for d in deplacements]})
        scenario_id = await inscrire_scenario(conn, architecture_id, scenario, auteur="constructeur (test)")
        relu_s = await conn.fetchrow(
            "SELECT architecture_id, nom, nature, probabilite FROM modele_scenarios WHERE id = $1", scenario_id)
        b.check(relu_s["architecture_id"] == architecture_id and relu_s["nom"] == "scenario_test_m1"
                and relu_s["nature"] == "nomme" and relu_s["probabilite"] is None,
                "le scénario s'inscrit, rattaché à la version proposée, sans probabilité (nommé)")
        relus_d = await conn.fetch(
            "SELECT bloc, variable, cible, valeur_dite FROM modele_deplacements WHERE scenario_id = $1 "
            "ORDER BY id", scenario_id)
        b.require(relus_d, 2, "les deux déplacements du scénario se relisent")
        b.check(relus_d[0]["cible"] == "borne_basse" and relus_d[0]["valeur_dite"] is None,
                "premier déplacement relu : borne basse, sans valeur dite")
        b.check(relus_d[1]["cible"] == "valeur_dite" and relus_d[1]["valeur_dite"] == 500.0,
                "second déplacement relu : valeur dite à 500.0")

        try:
            await inscrire_scenario(conn, architecture_id, SCENARIO_CENTRAL, auteur="constructeur (test)")
            b.check(False, "SCENARIO_CENTRAL inscrit : devait être refusé")
        except RegistreRefuse as e:
            b.check("jamais une ligne" in str(e), f"SCENARIO_CENTRAL est refusé à l'écriture : {e}")

        print("§4 registres append-only")
        for t in ("architectures_modele", "modele_fourchettes", "modele_scenarios", "modele_deplacements"):
            role = await conn.fetchval(
                "SELECT has_table_privilege(current_user, $1, 'UPDATE') OR "
                "has_table_privilege(current_user, $1, 'DELETE')", t)
            b.check(role is False, f"le rôle applicatif ne peut ni modifier ni supprimer `{t}`")
    finally:
        await tr.rollback()
    apres = await compte(conn)
    b.check(apres == avant, f"§fin zéro résidu en base après ROLLBACK ({avant} ligne(s) avant, {apres} après)")
    await conn.close()


asyncio.run(main())
sys.exit(b.summary())
