"""Écriture des registres du classeur de l'entreprise (migration 061, lot M1) — append-only,
même geste que `app/valorisation/signature.py` (#1 asyncpg, #35 transaction explicite).

`proposer_architecture` valide le PONT (`referentiel.valider_pont_architecture`) AVANT d'écrire —
le comité ne verra jamais, plus tard (M3), une proposition qui ne tiendrait déjà pas contre le
référentiel — et refuse une numérotation qui ne suit pas le registre (la version N+1 et aucune
autre), sous verrou du titre (comme `signature.proposer` : la contrainte UNIQUE (ticker_id,
version) de la migration 061 est le filet qui attrape une course entre deux propositions
concurrentes).

`inscrire_scenario` écrit le scénario ET ses déplacements dans une SEULE transaction explicite
(#35) — un scénario sans ses déplacements, ou l'inverse, ne serait rien — et refuse
`SCENARIO_CENTRAL` : il n'est jamais une ligne (09 §12.2), c'est la constante elle-même.

La SIGNATURE de l'architecture (M3, migration 062) n'est pas ici : ce module ne fait que PROPOSER,
jamais signer ou écarter.
"""
from __future__ import annotations

from app.contracts.modele_entreprise_schema import Architecture, Fourchette, Scenario
from app.modele_entreprise.referentiel import ReferentielModele, valider_pont_architecture

__all__ = [
    "RegistreRefuse", "prochaine_version", "proposer_architecture", "inscrire_fourchette",
    "inscrire_scenario",
]


class RegistreRefuse(ValueError):
    """Le geste n'est pas possible sur ce registre — même rôle que `valorisation.signature.ActeRefuse`."""


async def prochaine_version(conn, ticker_id: str) -> int:
    """La prochaine version d'architecture pour ce titre (dernière + 1, 1 si aucune) — lue hors
    transaction par `architecte.py` (M3) pour poser l'en-tête AVANT l'appel modèle, et revérifiée
    SOUS VERROU par `proposer_architecture` au moment d'écrire (#46 : la même requête, jamais
    recopiée — seule la portée transactionnelle diffère)."""
    derniere = await conn.fetchval(
        "SELECT coalesce(max(version), 0) FROM architectures_modele WHERE ticker_id = $1", ticker_id)
    return derniere + 1


async def proposer_architecture(conn, arch: Architecture, ref: ReferentielModele, *, auteur: str) -> int:
    """Inscrit une version PROPOSÉE d'architecture. Rend l'`id` de la ligne. Lève `RegistreRefuse`."""
    valider_pont_architecture(arch, ref)
    if not auteur.strip():
        raise RegistreRefuse("une architecture proposée dit qui la propose")
    async with conn.transaction():
        derniere = await conn.fetchval(
            "SELECT coalesce(max(version), 0) FROM architectures_modele WHERE ticker_id = $1",
            arch.ticker_id)
        if arch.version != derniere + 1:
            raise RegistreRefuse(
                f"la prochaine version de `{arch.ticker_id}` est la v{derniere + 1}, pas la v{arch.version}")
        row = await conn.fetchrow(
            "INSERT INTO architectures_modele (ticker_id, version, schema_version, version_referentiel, "
            "auteur, contenu) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
            arch.ticker_id, arch.version, arch.schema_version, arch.version_referentiel,
            auteur.strip(), arch.model_dump(mode="json"))
    return row["id"]


async def inscrire_fourchette(conn, architecture_id: int, fourchette: Fourchette, *, auteur: str) -> int:
    """Inscrit une fourchette, rattachée à une version d'architecture. Lève `RegistreRefuse`."""
    if not auteur.strip():
        raise RegistreRefuse("une fourchette inscrite dit qui l'inscrit")
    async with conn.transaction():
        row = await conn.fetchrow(
            "INSERT INTO modele_fourchettes (architecture_id, bloc, variable, periode_debut, "
            "periode_fin, bas, haut, methode, contenu, auteur) VALUES "
            "($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) RETURNING id",
            architecture_id, fourchette.bloc, fourchette.variable, fourchette.periode_debut,
            fourchette.periode_fin, fourchette.bas, fourchette.haut, fourchette.methode,
            fourchette.model_dump(mode="json"), auteur.strip())
    return row["id"]


async def inscrire_scenario(conn, architecture_id: int, scenario: Scenario, *, auteur: str) -> int:
    """Le scénario ET ses déplacements, dans une transaction EXPLICITE (#35). Refuse
    `SCENARIO_CENTRAL` : jamais une ligne. Lève `RegistreRefuse`."""
    if scenario.nature == "central":
        raise RegistreRefuse(
            "le scénario central n'est jamais une ligne — c'est la constante `SCENARIO_CENTRAL`, "
            "pas une écriture")
    if not auteur.strip():
        raise RegistreRefuse("un scénario inscrit dit qui l'inscrit")
    contenu_sans_deplacements = scenario.model_dump(mode="json", exclude={"deplacements"})
    async with conn.transaction():
        row = await conn.fetchrow(
            "INSERT INTO modele_scenarios (architecture_id, nom, nature, probabilite, contenu, auteur) "
            "VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
            architecture_id, scenario.nom, scenario.nature, scenario.probabilite,
            contenu_sans_deplacements, auteur.strip())
        scenario_id = row["id"]
        for d in scenario.deplacements:
            await conn.execute(
                "INSERT INTO modele_deplacements (scenario_id, bloc, variable, periode_debut, "
                "periode_fin, cible, valeur_dite, motif, source_entry_refs) VALUES "
                "($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                scenario_id, d.bloc, d.variable, d.periode_debut, d.periode_fin, d.cible,
                d.valeur_dite, d.motif, d.source_entry_refs)
    return scenario_id
