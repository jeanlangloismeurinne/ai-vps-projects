from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os

from app.routes.auth import is_authenticated
from app.services.file_parser import parse_upload
from app.services.claude_service import analyze_transactions

router = APIRouter()


class AnalyzeRequest(BaseModel):
    question: str | None = None


@router.post("/analyze")
async def analyze(request: Request, body: AnalyzeRequest = AnalyzeRequest()):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)

    file_path = request.session.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return JSONResponse({"error": "Aucun fichier chargé."}, status_code=400)

    ext = file_path.rsplit(".", 1)[-1]
    with open(file_path, "rb") as f:
        content = f.read()

    df, _ = parse_upload(f"file.{ext}", content)
    result = await analyze_transactions(df, body.question)
    return {"analysis": result}
