"""Gestion des versions du prompt de résumé (éditable via le Hub, /newsletter/prompt).

Le prompt actif (= version is_active=True) est celui que le digest envoie à DeepInfra, relu
à chaque exécution — une édition au Hub s'applique donc sans redémarrage. Historique
append-only pour permettre de revenir à une version antérieure (menu déroulant).
"""
from __future__ import annotations

import logging

from sqlalchemy import select, update

from app.config import settings
from app.models import PromptVersion

logger = logging.getLogger(__name__)


async def get_active_html_prompt(db) -> str:
    """Version active du prompt HTML ; sinon retombe sur le défaut d'env."""
    res = await db.execute(
        select(PromptVersion).where(PromptVersion.is_active.is_(True)).order_by(PromptVersion.id.desc())
    )
    row = res.scalars().first()
    if row and row.prompt and row.prompt.strip():
        return row.prompt
    return settings.SUMMARIZE_HTML_PROMPT


async def list_versions(db) -> list[PromptVersion]:
    res = await db.execute(select(PromptVersion).order_by(PromptVersion.id.desc()))
    return list(res.scalars().all())


async def create_version(db, prompt: str, note: str = "") -> PromptVersion:
    """Enregistre une NOUVELLE version (append-only) et la rend active."""
    assert prompt and prompt.strip()
    await db.execute(update(PromptVersion).values(is_active=False))
    row = PromptVersion(prompt=prompt, note=note or "", is_active=True)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def activate_version(db, version_id: int) -> PromptVersion | None:
    """Rend active une version antérieure (sans créer de nouvelle version)."""
    res = await db.execute(select(PromptVersion).where(PromptVersion.id == version_id))
    row = res.scalar_one_or_none()
    if row is None:
        return None
    await db.execute(update(PromptVersion).values(is_active=False))
    row.is_active = True
    await db.commit()
    await db.refresh(row)
    return row


async def seed_default(db) -> None:
    """Au démarrage : crée une v1 depuis le défaut si aucune version n'existe.

    Sans ça, l'éditeur du Hub serait vide tant qu'aucune version n'a été enregistrée, alors
    que le service fonctionne déjà avec le défaut d'env.
    """
    res = await db.execute(select(PromptVersion))
    if res.scalars().first() is None:
        db.add(PromptVersion(
            prompt=settings.SUMMARIZE_HTML_PROMPT,
            note="Version initiale (défaut d'env)",
            is_active=True,
        ))
        await db.commit()
        logger.info("Prompt : version v1 seedée depuis le défaut d'env.")
