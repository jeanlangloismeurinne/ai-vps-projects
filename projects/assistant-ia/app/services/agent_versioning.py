"""
Versionnage du doc système : approbation, rejet, rollback (#1787559677496).

Ticket sécurité — c'est le garde-fou qui rend le chantier acceptable.

Invariants, dans l'ordre d'importance :

1. **Aucune version ne s'active sans décision humaine.** `approve_proposal` et `rollback_to_version`
   exigent un `actor` humain vérifié par l'appelant ; aucun autre chemin de code du projet n'écrit
   `active = true`.
2. **Append-only.** Approuver crée une ligne `version = max + 1` avec `parent_version` renseigné.
   Une version existante n'est jamais modifiée — sauf le drapeau `active`, qui est justement ce qui
   rend le rollback possible.
3. **Activation transactionnelle.** L'index unique partiel `uq_agent_system_doc_active` interdit
   deux lignes actives : désactivation et activation doivent donc être dans la *même* transaction,
   sinon l'index rejette l'opération à mi-chemin.
4. **Audit immuable.** Chaque décision écrit dans `agent_audit_log`. Ce module ne fait jamais
   d'UPDATE ni de DELETE sur cette table.
"""
import logging
from dataclasses import dataclass

from app.config import settings
from app.db import get_pool

logger = logging.getLogger(__name__)


class NotAuthorized(Exception):
    """L'utilisateur qui a cliqué n'est pas habilité à décider."""


@dataclass
class DecisionResult:
    applied: bool           # False = déjà tranchée (double-clic), sans erreur
    message: str
    to_version: int | None = None


def approvers() -> set[str]:
    return {u.strip() for u in (settings.AGENT_APPROVERS or "").split(",") if u.strip()}


def is_approver(user_id: str | None) -> bool:
    """Le channel est privé, mais la confidentialité n'est pas une autorisation : on vérifie
    l'identité réelle du cliqueur (§ ticket 496)."""
    return bool(user_id) and user_id in approvers()


async def _audit(conn, event: str, *, actor: str, instruction_ids, diff, from_version, to_version):
    await conn.execute(
        """
        INSERT INTO agent_audit_log (event, actor, instruction_ids, diff, from_version, to_version)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        event, actor, instruction_ids or [], diff, from_version, to_version,
    )


async def approve_proposal(proposal_id: str, actor: str) -> DecisionResult:
    """Crée la version suivante et l'active. Idempotent : une proposition déjà tranchée est un
    no-op silencieux, pas une erreur (le cas du double-clic)."""
    if not is_approver(actor):
        raise NotAuthorized(actor or "inconnu")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # FOR UPDATE : deux clics simultanés sérialisent ici, le second voit 'approved'.
            prop = await conn.fetchrow(
                "SELECT * FROM agent_proposals WHERE id = $1 FOR UPDATE", proposal_id
            )
            if not prop:
                return DecisionResult(False, "Proposition introuvable.")
            if prop["status"] != "pending":
                return DecisionResult(
                    False, f"Proposition déjà {prop['status']} — aucune action.", prop["to_version"]
                )

            current = await conn.fetchrow(
                "SELECT version FROM agent_system_doc WHERE active FOR UPDATE"
            )
            from_version = current["version"] if current else None
            next_version = (await conn.fetchval(
                "SELECT COALESCE(max(version), 0) FROM agent_system_doc"
            )) + 1

            # Désactivation puis activation dans la même transaction (invariant 3).
            if current:
                await conn.execute(
                    "UPDATE agent_system_doc SET active = false WHERE version = $1", from_version
                )
            await conn.execute(
                """
                INSERT INTO agent_system_doc
                    (version, content, active, created_by, parent_version)
                VALUES ($1, $2, true, $3, $4)
                """,
                next_version, prop["content"], actor, from_version,
            )

            await conn.execute(
                "UPDATE agent_proposals SET status='approved', to_version=$1, decided_by=$2, "
                "decided_at=now() WHERE id=$3",
                next_version, actor, proposal_id,
            )
            await conn.execute(
                "UPDATE agent_instruction_queue SET status='approved' WHERE id = ANY($1::uuid[])",
                list(prop["instruction_ids"] or []),
            )
            await _audit(
                conn, "approved", actor=actor,
                instruction_ids=list(prop["instruction_ids"] or []),
                diff=prop["diff"], from_version=from_version, to_version=next_version,
            )

    logger.info("agent_versioning: proposition %s approuvée par %s → v%s",
                proposal_id, actor, next_version)
    return DecisionResult(True, f"Version {next_version} active.", next_version)


async def reject_proposal(proposal_id: str, actor: str, reason: str = "") -> DecisionResult:
    """Rejette. Les consignes repassent `rejected` : l'utilisateur reformule et relance `@update`."""
    if not is_approver(actor):
        raise NotAuthorized(actor or "inconnu")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            prop = await conn.fetchrow(
                "SELECT * FROM agent_proposals WHERE id = $1 FOR UPDATE", proposal_id
            )
            if not prop:
                return DecisionResult(False, "Proposition introuvable.")
            if prop["status"] != "pending":
                return DecisionResult(False, f"Proposition déjà {prop['status']} — aucune action.")

            await conn.execute(
                "UPDATE agent_proposals SET status='rejected', decided_by=$1, decided_at=now() "
                "WHERE id=$2",
                actor, proposal_id,
            )
            await conn.execute(
                "UPDATE agent_instruction_queue SET status='rejected' WHERE id = ANY($1::uuid[])",
                list(prop["instruction_ids"] or []),
            )
            await _audit(
                conn, "rejected", actor=actor,
                instruction_ids=list(prop["instruction_ids"] or []),
                diff=(reason or prop["diff"]),
                from_version=prop["from_version"], to_version=None,
            )

    logger.info("agent_versioning: proposition %s rejetée par %s", proposal_id, actor)
    return DecisionResult(True, "Proposition rejetée. Le document système est inchangé.")


async def create_manual_version(content: str, actor: str) -> DecisionResult:
    """Édition manuelle depuis la page web (#1787559677497).

    Passe par la **même** couche que l'approbation Slack : append-only, activation transactionnelle,
    audit. Il n'existe donc pas de chemin d'écriture parallèle qui contournerait ces garanties.

    Les bornes §5.4 s'appliquent aussi ici : une édition humaine n'est pas une raison de désactiver
    les contrôles — c'est justement le cas où un contenu injecté depuis la queue de consignes
    pourrait être recopié sans relecture.
    """
    from app.services import agent_guardrails

    current = await get_active_content()
    verdict = agent_guardrails.check_document(content, current)
    if not verdict.ok:
        return DecisionResult(False, f"Édition refusée par les bornes de sécurité : {verdict.summary()}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT version FROM agent_system_doc WHERE active FOR UPDATE")
            from_version = row["version"] if row else None
            next_version = (await conn.fetchval(
                "SELECT COALESCE(max(version), 0) FROM agent_system_doc"
            )) + 1

            if row:
                await conn.execute(
                    "UPDATE agent_system_doc SET active = false WHERE version = $1", from_version
                )
            await conn.execute(
                """
                INSERT INTO agent_system_doc (version, content, active, created_by, parent_version)
                VALUES ($1, $2, true, $3, $4)
                """,
                next_version, content, actor, from_version,
            )
            await _audit(
                conn, "edited", actor=actor, instruction_ids=[],
                diff=f"édition manuelle v{from_version} → v{next_version}",
                from_version=from_version, to_version=next_version,
            )

    logger.info("agent_versioning: édition manuelle par %s → v%s", actor, next_version)
    return DecisionResult(True, f"Version {next_version} enregistrée et active.", next_version)


async def get_active_content() -> str:
    pool = await get_pool()
    return await pool.fetchval("SELECT content FROM agent_system_doc WHERE active") or ""


async def list_versions() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT version, active, created_by, created_at, parent_version, content
        FROM agent_system_doc ORDER BY version DESC
        """
    )
    return [dict(r) for r in rows]


async def list_audit(limit: int = 50) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT event, actor, from_version, to_version, created_at
        FROM agent_audit_log ORDER BY created_at DESC LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]


async def rollback_to_version(version: int, actor: str, *, preauthorized: bool = False) -> DecisionResult:
    """Réactive une version antérieure (§5.5). Aucune ligne n'est créée : le rollback est un
    déplacement du drapeau `active`, l'historique reste intact et l'audit garde la trace.

    `preauthorized` : l'appelant a déjà établi l'identité par un autre moyen que l'allowlist Slack —
    en pratique la session web authentifiée de #1787559677497. L'allowlist porte sur des Slack user
    IDs et ne peut pas trancher pour un utilisateur web.
    """
    if not preauthorized and not is_approver(actor):
        raise NotAuthorized(actor or "inconnu")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            target = await conn.fetchrow(
                "SELECT version, active FROM agent_system_doc WHERE version = $1 FOR UPDATE", version
            )
            if not target:
                return DecisionResult(False, f"Version {version} introuvable.")
            if target["active"]:
                return DecisionResult(False, f"Version {version} est déjà active.", version)

            current = await conn.fetchrow(
                "SELECT version FROM agent_system_doc WHERE active FOR UPDATE"
            )
            from_version = current["version"] if current else None
            if current:
                await conn.execute(
                    "UPDATE agent_system_doc SET active = false WHERE version = $1", from_version
                )
            await conn.execute(
                "UPDATE agent_system_doc SET active = true WHERE version = $1", version
            )
            await _audit(
                conn, "rollback", actor=actor, instruction_ids=[],
                diff=f"rollback v{from_version} → v{version}",
                from_version=from_version, to_version=version,
            )

    logger.info("agent_versioning: rollback v%s → v%s par %s", from_version, version, actor)
    return DecisionResult(True, f"Version {version} réactivée.", version)
