"""Persistance et LECTURE de la carte d'appariement (chantier v3, lot 3 maillon 4bis — étape 2b).

Migration 042 — table `appariement_cartes`, grain (ticker_id × framework_id × framework_version).

POURQUOI ON UPSERTE ET ON N'ACCUMULE PAS
-----------------------------------------
Une `FrameworkAnswer` est une DÉCISION humaine — append-only, avec lignée et supersedage. Une
`AppariementCarte` est une DÉRIVATION DÉTERMINISTE de l'inventaire déposé + du plan : mêmes
entrées → même sortie, donc l'historique n'a pas de valeur propre. Un nouveau dépôt produit un
UPSERT qui écrase l'ancienne carte ; lire la carte la plus récente sur `(ticker, framework, version)`
est alors une simple requête sans join sur l'historique.

LA REVÉRIFICATION À LA LECTURE (motif de #54, convention #67)
--------------------------------------------------------------
Un `indisponible` établi sur un inventaire de 269 concepts ne vaut rien contre un inventaire qui
en compte 272 : RVMD ne dépose pas encore `Revenues`, mais son approbation FDA d'août 2026 fera
apparaître ce concept au premier trimestre de commercialisation. La carte doit se relire comme
PÉRIMÉE dès que le dépôt courant est plus récent que `dernier_depot_vu`.

`lire_carte` compare donc `dernier_depot_vu` stocké à la date du dépôt courant (fournie par
l'appelant, qui détient l'inventaire). Si le dépôt courant est plus récent, la carte est traitée
comme ABSENTE — jamais comme valide. C'est ce mécanisme qui ferme la boucle de #54 pour
l'appariement : un verdict figé à l'écriture ne peut pas signaler qu'il a vieilli.

⚠️ L'APPELANT FOURNIT LA DATE DU DÉPÔT COURANT
La fonction de lecture reçoit `depot_courant` plutôt que d'aller lire l'inventaire elle-même, pour
deux raisons :
  · le pont appelle déjà `dernier_depot_vu(facts)` avant la dépense — on ne repaie pas l'inventaire
    une deuxième fois pour comparer une date ;
  · la logique de lecture reste pure (date en entrée → carte ou None), donc rejouable dans un test
    sans réseau, sans mock de `fetch_company_facts`.

⚠️ ATOMICITÉ
L'UPSERT est une seule instruction SQL (ON CONFLICT DO UPDATE) : elle est atomique par construction,
pas besoin d'une transaction enveloppante côté appelant.
"""
from __future__ import annotations

import json
from typing import Optional

import asyncpg

from app.contracts.appariement_schema import AppariementCarte, AppariementItem

__all__ = ["persister_carte", "lire_carte"]


async def persister_carte(conn: asyncpg.Connection, carte: AppariementCarte) -> int:
    """Écrit (ou écrase) la carte dans `appariement_cartes`. Rend l'`id` de la ligne upsertée.

    UPSERT sur la clef unique `(ticker_id, framework_id, framework_version)`. Une carte recalculée
    sur un inventaire plus récent remplace simplement l'ancienne — il n'y a pas d'historique à tenir
    pour une dérivation déterministe.
    """
    # On passe un dict Python — le codec JSONB enregistré sur la connexion (`init_pool` dans
    # `db/database.py`, ou `set_type_codec` dans les checks) se charge de la sérialisation.
    # On enveloppe la liste dans un dict car asyncpg n'infère pas jsonb depuis une liste nue.
    items_wrapped = {"items": [it.model_dump(mode="json") for it in carte.items]}
    row_id = await conn.fetchval(
        """
        INSERT INTO appariement_cartes
            (ticker_id, framework_id, framework_version, dernier_depot_vu, items)
        VALUES ($1, $2, $3, $4, ($5::jsonb)->'items')
        ON CONFLICT (ticker_id, framework_id, framework_version) DO UPDATE
            SET dernier_depot_vu = EXCLUDED.dernier_depot_vu,
                items             = EXCLUDED.items,
                updated_at        = now()
        RETURNING id
        """,
        carte.ticker_id,
        carte.framework_id,
        carte.framework_version,
        carte.dernier_depot_vu,
        items_wrapped,
    )
    return row_id


async def lire_carte(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    framework_id: str,
    framework_version: str,
    depot_courant: str,
) -> Optional[AppariementCarte]:
    """Lit la carte persistée et la REVÉRIFIE contre le dépôt courant.

    Rend `None` si :
      · aucune carte n'est persistée (cas initial) ;
      · la carte est PÉRIMÉE — `dernier_depot_vu` est strictement antérieur à `depot_courant`.

    Un `indisponible` établi sur un inventaire de 269 concepts ne vaut rien contre un inventaire
    qui en compte 272 : on traite la carte périmée exactement comme une carte absente, jamais
    comme une carte valide. C'est la revérification À LA LECTURE qui ferme la boucle de #54 :
    un verdict figé à l'écriture ne peut pas signaler qu'il a vieilli.

    ⚠️ La comparaison est STRICTEMENT INFÉRIEURE (`<`). Une carte calculée sur le même dépôt que
    le courant est VALIDE — on ne la recalcule pas inutilement. On ne recalcule que lorsqu'un
    dépôt PLUS RÉCENT est disponible.
    """
    row = await conn.fetchrow(
        """
        SELECT dernier_depot_vu, items
        FROM appariement_cartes
        WHERE ticker_id = $1 AND framework_id = $2 AND framework_version = $3
        """,
        ticker_id,
        framework_id,
        framework_version,
    )
    if row is None:
        return None

    # REVÉRIFICATION À LA LECTURE (#54) : un dépôt plus récent invalide la carte.
    if row["dernier_depot_vu"] < depot_courant:
        return None

    # Reconstituer l'objet depuis le JSONB persisté.
    try:
        items_data = row["items"]
        if isinstance(items_data, str):
            items_data = json.loads(items_data)
        items = [AppariementItem.model_validate(it) for it in items_data]
        return AppariementCarte(
            ticker_id=ticker_id,
            framework_id=framework_id,
            framework_version=framework_version,
            dernier_depot_vu=row["dernier_depot_vu"],
            items=items,
        )
    except Exception:
        # Une carte corrompue en base se traite comme absente : mieux vaut la recalculer que
        # servir un verdict faux. On ne lève pas — le caller recalculera.
        return None
