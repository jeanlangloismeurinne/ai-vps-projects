"""
Job de synchronisation de la KB visuelle (sprint « Substrat », #1787600247611 / #1787600247612).

Réconciliation périodique = source de vérité du miroir, robuste aux écritures manquées (un
redéploiement pendant une mutation de carte ne perd rien : le run suivant rattrape l'état complet).
Les deux syncs sont indépendantes ; un échec de l'une ne doit pas empêcher l'autre.
"""
import logging

from app.services.kanban_vault import sync_kanban_vault
from app.services.kb_schema_notes import sync_schema_notes

logger = logging.getLogger(__name__)


async def run_kb_sync() -> None:
    try:
        await sync_kanban_vault()
    except Exception:
        logger.exception("kb_sync: miroir kanban → vault a échoué")
    try:
        await sync_schema_notes()
    except Exception:
        logger.exception("kb_sync: notes-schéma a échoué")
