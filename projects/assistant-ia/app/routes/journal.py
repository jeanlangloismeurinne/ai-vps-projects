import logging
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.routes.auth import require_auth
from app.services import journal as journal_svc

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/journal", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def journal_page():
    entries = await journal_svc.get_all_entries()

    rows = ""
    for e in entries:
        dt = e["created_at"].strftime("%d/%m/%Y %H:%M")
        content = e["content"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows += f"""
        <article class="entry">
            <time>{dt}</time>
            <p>{content}</p>
        </article>"""

    if not rows:
        rows = '<p class="empty">Aucune entrée pour l\'instant.</p>'

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Journal d'apprentissage</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #f5f5f5; color: #333; padding: 1rem; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 1.5rem; color: #111; }}
  .entry {{ background: #fff; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  time {{ font-size: .8rem; color: #888; display: block; margin-bottom: .4rem; }}
  p {{ line-height: 1.5; white-space: pre-wrap; }}
  .empty {{ color: #999; font-style: italic; margin-top: 2rem; text-align: center; }}
  @media (min-width: 640px) {{ body {{ max-width: 700px; margin: 2rem auto; padding: 2rem; }} }}
</style>
</head>
<body>
<h1>💡 Journal d'apprentissage</h1>
{rows}
</body>
</html>"""
    return HTMLResponse(content=html)
