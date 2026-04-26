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

    Accepte deux formats :
    - {"service": "bank-review"}  — appel direct par nom de service
    - {"application_uuid": "..."}  — payload Coolify (un UUID peut couvrir plusieurs services)

    Sécurisé par X-Deploy-Secret si DEPLOY_WEBHOOK_SECRET est configuré.
    """
    if settings.DEPLOY_WEBHOOK_SECRET and x_deploy_secret != settings.DEPLOY_WEBHOOK_SECRET:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    payload = await request.json()
    service_name: str | None = payload.get("service")

    if service_name:
        # Appel direct par nom
        if not registry.by_name(service_name):
            return JSONResponse({"error": f"Service '{service_name}' non enregistré"}, status_code=404)
        background_tasks.add_task(feedback_deploy.handle_deploy_complete, service_name)
        return JSONResponse({"ok": True, "services": [service_name]})

    # Résolution par UUID Coolify (peut retourner plusieurs services)
    coolify_uuid = payload.get("application_uuid") or payload.get("uuid")
    if not coolify_uuid:
        return JSONResponse(
            {"error": "Fournir 'service' ou 'application_uuid'"},
            status_code=400,
        )

    services = registry.by_coolify_uuid(coolify_uuid)
    if not services:
        return JSONResponse(
            {"error": f"Aucun service pour l'UUID '{coolify_uuid}'"},
            status_code=404,
        )

    notified = []
    for svc in services:
        background_tasks.add_task(feedback_deploy.handle_deploy_complete, svc["name"])
        notified.append(svc["name"])

    return JSONResponse({"ok": True, "services": notified})
