"""Gestion des versions du prompt de résumé (éditable via le Hub, `/newsletter/aliases/…`).

Chaque alias a SON prompt : une version active PAR alias. Le prompt actif est celui que le moteur
envoie à DeepInfra, relu à chaque exécution — une édition au Hub s'applique donc sans redémarrage.
Historique append-only pour permettre de revenir à une version antérieure (menu déroulant).

⚠️ Portée : chaque lecture ET chaque `UPDATE is_active=false` est filtré sur l'alias. Sans ce
filtre, enregistrer un prompt pour un alias désactiverait silencieusement celui des autres (la
newsletter retomberait sur le défaut d'env sans aucun symptôme).
"""
from __future__ import annotations

import logging

from sqlalchemy import select, update

from app.config import settings
from app.models import Alias, PromptVersion

logger = logging.getLogger(__name__)


async def default_alias_id(db) -> int | None:
    """Id de l'alias par défaut (la newsletter). `alias_id=None` désigne toujours celui-là."""
    res = await db.execute(select(Alias.id).where(Alias.is_default.is_(True)))
    return res.scalars().first()


async def _resolve(db, alias_id: int | None) -> int | None:
    return alias_id if alias_id is not None else await default_alias_id(db)


def _scope(alias_id: int | None):
    return PromptVersion.alias_id == alias_id if alias_id is not None else PromptVersion.alias_id.is_(None)


async def get_active_html_prompt(db, alias_id: int | None = None) -> str:
    """Version active du prompt HTML de l'alias ; sinon retombe sur le défaut d'env."""
    scope = _scope(await _resolve(db, alias_id))
    res = await db.execute(
        select(PromptVersion).where(PromptVersion.is_active.is_(True), scope).order_by(PromptVersion.id.desc())
    )
    row = res.scalars().first()
    if row and row.prompt and row.prompt.strip():
        return row.prompt
    return settings.SUMMARIZE_HTML_PROMPT


async def list_versions(db, alias_id: int | None = None) -> list[PromptVersion]:
    scope = _scope(await _resolve(db, alias_id))
    res = await db.execute(select(PromptVersion).where(scope).order_by(PromptVersion.id.desc()))
    return list(res.scalars().all())


async def create_version(db, prompt: str, note: str = "", alias_id: int | None = None) -> PromptVersion:
    """Enregistre une NOUVELLE version (append-only) de CET alias et la rend active."""
    assert prompt and prompt.strip()
    alias_id = await _resolve(db, alias_id)
    await db.execute(update(PromptVersion).where(_scope(alias_id)).values(is_active=False))
    row = PromptVersion(prompt=prompt, note=note or "", is_active=True, alias_id=alias_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def activate_version(db, version_id: int, alias_id: int | None = None) -> PromptVersion | None:
    """Rend active une version antérieure DE CET ALIAS (sans créer de nouvelle version)."""
    alias_id = await _resolve(db, alias_id)
    res = await db.execute(select(PromptVersion).where(PromptVersion.id == version_id, _scope(alias_id)))
    row = res.scalar_one_or_none()
    if row is None:
        return None
    await db.execute(update(PromptVersion).where(_scope(alias_id)).values(is_active=False))
    row.is_active = True
    await db.commit()
    await db.refresh(row)
    return row


async def seed_default(db) -> None:
    """Au démarrage : crée une v1 depuis le défaut d'env si l'alias par défaut n'a aucune version.

    Sans ça, l'éditeur du Hub serait vide tant qu'aucune version n'a été enregistrée, alors
    que le service fonctionne déjà avec le défaut d'env.
    """
    alias_id = await default_alias_id(db)
    res = await db.execute(select(PromptVersion).where(_scope(alias_id)))
    if res.scalars().first() is None:
        db.add(PromptVersion(
            prompt=settings.SUMMARIZE_HTML_PROMPT,
            note="Version initiale (défaut d'env)",
            is_active=True,
            alias_id=alias_id,
        ))
        await db.commit()
        logger.info("Prompt : version v1 seedée depuis le défaut d'env.")
