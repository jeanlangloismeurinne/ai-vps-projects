"""
Page web d'édition du doc système de l'agent (#1787559677497).

Cible du bouton *Éditer* du message d'approbation Slack. Cette page modifie le prompt système de
l'agent : elle est derrière `require_auth` au niveau du routeur, jamais publique.

Elle n'a **aucun** chemin d'écriture propre : édition et rollback passent par `agent_versioning`,
c'est-à-dire la même couche append-only + audit que l'approbation Slack. Les bornes §5.4
s'appliquent donc aussi à une édition humaine.
"""
import difflib
import html
import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.routes.auth import require_auth
from app.services import agent_versioning

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_auth)])

_CSS = """
:root{--bg:#0f1117;--card:#1a1d27;--border:#1e2130;--text:#e8e8ea;--muted:#888;
      --accent:#4f6ef7;--danger:#e05252;--success:#2da862;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);
     min-height:100vh;}
header{padding:1rem 2rem;border-bottom:1px solid var(--border);display:flex;gap:1.5rem;
       align-items:center;}
header h1{font-size:1.1rem;font-weight:600;}
header a{color:var(--muted);text-decoration:none;font-size:.9rem;}
main{max-width:900px;margin:0 auto;padding:2rem;}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1.25rem;
      margin-bottom:1.25rem;}
h2{font-size:1rem;margin-bottom:.75rem;}
textarea{width:100%;min-height:320px;background:#0b0d13;color:var(--text);border:1px solid
         var(--border);border-radius:8px;padding:.9rem;font-family:ui-monospace,monospace;
         font-size:.85rem;line-height:1.5;resize:vertical;}
button,.btn{background:var(--accent);color:#fff;border:0;border-radius:7px;padding:.55rem 1.1rem;
            font-size:.9rem;cursor:pointer;text-decoration:none;display:inline-block;}
.btn-sec{background:transparent;border:1px solid var(--border);color:var(--muted);}
table{width:100%;border-collapse:collapse;font-size:.85rem;}
th,td{text-align:left;padding:.5rem .6rem;border-bottom:1px solid var(--border);}
th{color:var(--muted);font-weight:500;}
.tag{background:var(--success);color:#fff;border-radius:4px;padding:.1rem .45rem;font-size:.72rem;}
pre{background:#0b0d13;border:1px solid var(--border);border-radius:8px;padding:.9rem;
    overflow-x:auto;font-size:.8rem;line-height:1.45;}
.err{background:#3a1c1c;border:1px solid var(--danger);color:#ffb4b4;border-radius:8px;
     padding:.75rem 1rem;margin-bottom:1.25rem;font-size:.9rem;}
.okmsg{background:#12301f;border:1px solid var(--success);color:#9fe0bb;border-radius:8px;
       padding:.75rem 1rem;margin-bottom:1.25rem;font-size:.9rem;}
.muted{color:var(--muted);font-size:.85rem;}
"""


def _page(body: str) -> str:
    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Document système — assistant</title><style>{_CSS}</style></head><body>
<header><h1>Document système de l'agent</h1>
<a href="/">← Accueil</a><a href="/agent/system-doc">Versions</a></header>
<main>{body}</main></body></html>"""


def _esc(text) -> str:
    return html.escape(str(text if text is not None else ""))


def _diff_html(previous: str, current: str, from_v, to_v) -> str:
    diff = "\n".join(difflib.unified_diff(
        (previous or "").splitlines(), (current or "").splitlines(),
        fromfile=f"v{from_v}", tofile=f"v{to_v}", lineterm="",
    ))
    return f"<pre>{_esc(diff)}</pre>" if diff else "<p class='muted'>Aucune différence.</p>"


@router.get("/agent/system-doc", response_class=HTMLResponse)
async def system_doc_index(request: Request):
    versions = await agent_versioning.list_versions()
    audit = await agent_versioning.list_audit(limit=25)
    msg = request.query_params.get("msg", "")
    err = request.query_params.get("err", "")

    banner = ""
    if msg:
        banner += f"<div class='okmsg'>{_esc(msg)}</div>"
    if err:
        banner += f"<div class='err'>{_esc(err)}</div>"

    by_version = {v["version"]: v["content"] for v in versions}
    rows = []
    for v in versions:
        active = "<span class='tag'>active</span>" if v["active"] else ""
        actions = f"<a class='btn btn-sec' href='/agent/system-doc/edit/{v['version']}'>Éditer</a>"
        if not v["active"]:
            actions += (
                f" <form method='post' action='/agent/system-doc/rollback' "
                f"style='display:inline'><input type='hidden' name='version' "
                f"value='{v['version']}'><button class='btn-sec'>Réactiver</button></form>"
            )
        rows.append(
            f"<tr><td>v{v['version']} {active}</td><td>{_esc(v['created_by'])}</td>"
            f"<td class='muted'>{v['created_at']:%Y-%m-%d %H:%M}</td><td>{actions}</td></tr>"
        )

    audit_rows = "".join(
        f"<tr><td>{_esc(a['event'])}</td><td>{_esc(a['actor'])}</td>"
        f"<td>{_esc(a['from_version'])} → {_esc(a['to_version'])}</td>"
        f"<td class='muted'>{a['created_at']:%Y-%m-%d %H:%M}</td></tr>"
        for a in audit
    ) or "<tr><td colspan='4' class='muted'>Aucune entrée.</td></tr>"

    active_doc = next((v for v in versions if v["active"]), None)
    diff_block = ""
    if active_doc and active_doc["parent_version"] in by_version:
        diff_block = (
            "<div class='card'><h2>Diff avec la version précédente</h2>"
            + _diff_html(by_version[active_doc["parent_version"]], active_doc["content"],
                         active_doc["parent_version"], active_doc["version"])
            + "</div>"
        )

    active_html = (
        f"<pre>{_esc(active_doc['content'])}</pre>" if active_doc
        else "<p class='muted'>Aucune version active.</p>"
    )

    return HTMLResponse(_page(f"""{banner}
<div class="card"><h2>Version active</h2>{active_html}
<p style="margin-top:.9rem">
<a class="btn" href="/agent/system-doc/edit/{active_doc['version'] if active_doc else 1}">Éditer</a>
</p></div>
{diff_block}
<div class="card"><h2>Historique des versions</h2>
<table><tr><th>Version</th><th>Auteur</th><th>Date</th><th></th></tr>{''.join(rows)}</table></div>
<div class="card"><h2>Journal d'audit</h2>
<table><tr><th>Événement</th><th>Acteur</th><th>Versions</th><th>Date</th></tr>
{audit_rows}</table></div>"""))


@router.get("/agent/system-doc/edit/{version}", response_class=HTMLResponse)
async def system_doc_edit(version: int, request: Request):
    versions = await agent_versioning.list_versions()
    target = next((v for v in versions if v["version"] == version), None)
    if not target:
        return RedirectResponse("/agent/system-doc?err=Version+introuvable", status_code=303)

    err = request.query_params.get("err", "")
    banner = f"<div class='err'>{_esc(err)}</div>" if err else ""

    return HTMLResponse(_page(f"""{banner}
<div class="card"><h2>Éditer à partir de la v{version}</h2>
<p class="muted" style="margin-bottom:.9rem">L'enregistrement crée une <strong>nouvelle</strong>
version active. La v{version} est conservée : rien n'est écrasé.</p>
<form method="post" action="/agent/system-doc">
<textarea name="content" spellcheck="false">{_esc(target['content'])}</textarea>
<p style="margin-top:.9rem"><button type="submit">Enregistrer comme nouvelle version</button>
<a class="btn btn-sec" href="/agent/system-doc">Annuler</a></p>
</form></div>"""))


@router.post("/agent/system-doc")
async def system_doc_save(content: str = Form(...)):
    # L'identité vient de la session (routeur sous `require_auth`) ; l'acteur est tracé comme tel
    # dans l'audit pour le distinguer d'une approbation Slack.
    result = await agent_versioning.create_manual_version(content, actor="web")
    if not result.applied:
        # Retour sur l'édition de la version *active*, pas d'un numéro figé : le refus laisse le
        # document inchangé, donc c'est bien elle qui reste la base de la prochaine tentative.
        versions = await agent_versioning.list_versions()
        active = next((v["version"] for v in versions if v["active"]), 1)
        return RedirectResponse(
            f"/agent/system-doc/edit/{active}?err={quote(result.message)}", status_code=303
        )
    return RedirectResponse(f"/agent/system-doc?msg={quote(result.message)}", status_code=303)


@router.post("/agent/system-doc/rollback")
async def system_doc_rollback(version: int = Form(...)):
    result = await agent_versioning.rollback_to_version(version, actor="web", preauthorized=True)
    key = "msg" if result.applied else "err"
    return RedirectResponse(f"/agent/system-doc?{key}={quote(result.message)}", status_code=303)
