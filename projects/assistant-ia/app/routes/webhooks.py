import asyncio
import logging
from fastapi import APIRouter, BackgroundTasks, Request, Header
from fastapi.responses import JSONResponse

from app.config import settings
from app.handlers import bank_review as bank_review_handler
from app.handlers import feedback_deploy
from app.services import registry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/file-stored")
async def file_stored(request: Request, background_tasks: BackgroundTasks):
    """Reçoit la notification de tool-file-intake quand un fichier est stocké."""
    payload = await request.json()
    if payload.get("event") != "file_stored":
        return JSONResponse({"ok": True})
    background_tasks.add_task(bank_review_handler.handle_file_stored, payload)
    return JSONResponse({"ok": True})


@router.post("/webhook/deploy-complete")
async def deploy_complete(
    request: Request,
    background_tasks: BackgroundTasks,
    x_deploy_secret: str = Header(default=""),
):
    """
    Notifie un déploiement terminé et poste dans Slack le résumé des tickets implémentés.

    Appelé soit par Coolify (payload avec application_uuid),
    soit manuellement avec {"service": "bank-review"}.

    Sécurisé par X-Deploy-Secret si DEPLOY_WEBHOOK_SECRET est configuré.
    """
    if settings.DEPLOY_WEBHOOK_SECRET and x_deploy_secret != settings.DEPLOY_WEBHOOK_SECRET:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    payload = await request.json()

    # Résolution du service : par nom direct ou par UUID Coolify
    service_name: str | None = payload.get("service")
    if not service_name:
        coolify_uuid = payload.get("application_uuid") or payload.get("uuid")
        if coolify_uuid:
            svc = registry.by_coolify_uuid(coolify_uuid)
            service_name = svc["name"] if svc else None

    if not service_name:
        return JSONResponse({"error": "Service non identifié (fournir 'service' ou 'application_uuid')"}, status_code=400)

    if not registry.by_name(service_name):
        return JSONResponse({"error": f"Service '{service_name}' non enregistré"}, status_code=404)

    background_tasks.add_task(feedback_deploy.handle_deploy_complete, service_name)
    return JSONResponse({"ok": True, "service": service_name})
