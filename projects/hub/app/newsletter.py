"""Pages « Newsletter » du Hub — KB des résumés + éditeur de prompt versionné.

Le Hub (portail + auth) rend ces pages en appelant le service `newsletter-summary` sur le
réseau Docker (même réseau `coolify`) : `/api/kb` (résumés, enveloppes KNOWLEDGE §3) et
`/api/prompt*` (éditeur de prompt avec historique).

Les données restent dans le service (PostgreSQL) ; seule une clé partagée
`NEWSLETTER_API_TOKEN` (= `HUB_API_TOKEN` côté service) sécurise ces appels. L'auth du Hub
(session cookie) protège les pages.
"""
from __future__ import annotations

import re
from datetime import datetime

import httpx
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(prefix="/newsletter")


class ApiError(Exception):
    pass


async def _api(method: str, path: str, payload: dict | None = None) -> dict:
    """Appelle le service newsletter-summary avec le header d'auth partagé."""
    from app.main import settings
    base = (settings.NEWSLETTER_URL or "http://newsletter-summary:8000").rstrip("/")
    headers = {}
    if settings.NEWSLETTER_API_TOKEN:
        headers["x-hub-token"] = settings.NEWSLETTER_API_TOKEN
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.request(method, f"{base}{path}", json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise ApiError(f"Service newsletter injoignable : {type(exc).__name__}")
    if r.status_code >= 400:
        try:   # FastAPI renvoie {"detail": "…"} : on montre le message, pas le JSON brut
            detail = r.json().get("detail")
        except Exception:
            detail = None
        raise ApiError(f"Le service a répondu {r.status_code} : {detail if isinstance(detail, str) else r.text[:200]}")
    return r.json()


def _e(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _fmt(dt) -> str:
    if not dt:
        return "?"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return dt
    try:
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(dt)


# ── Rendu Markdown minimal (même philosophie que nuit.py : ne perd aucune ligne) ──
def _md(raw: str) -> str:
    out, in_code = [], False
    for line in _e(raw).split("\n"):
        if line.startswith("```"):
            in_code = not in_code
            out.append('<div class="code">' if in_code else "</div>")
            continue
        if in_code:
            out.append(line if line.strip() else "&nbsp;")
            continue
        line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", line)
        line = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", line)
        if m := re.match(r"^(#{1,4})\s+(.*)$", line):
            lvl = len(m.group(1))
            size = {1: "1.02rem", 2: ".94rem", 3: ".88rem", 4: ".84rem"}[lvl]
            color = "#e8e8ea" if lvl <= 2 else "#a5b4fc"
            out.append(f'<div style="font-size:{size};font-weight:700;color:{color};margin:1rem 0 .4rem">{m.group(2)}</div>')
        elif re.match(r"^[-*]\s+", line):
            out.append(f'<div class="li">{line[2:]}</div>')
        elif re.match(r"^\d+\.\s+", line):
            out.append(f'<div class="li">{line.split(".", 1)[1].strip()}</div>')
        elif not line.strip():
            out.append('<div style="height:.5rem"></div>')
        else:
            out.append(f"<div>{line}</div>")
    if in_code:
        out.append("</div>")
    return "\n".join(out)


_CSS = """
<style>
  .tabs{display:flex;gap:.5rem;margin-bottom:1.4rem}
  .tab{padding:.45rem .95rem;border-radius:20px;font-size:.82rem;border:1px solid #2a2d3a;
       background:#1a1d27;color:#888;cursor:pointer;text-decoration:none}
  .tab.active{background:#4f6ef7;color:#fff;border-color:#4f6ef7}
  .kb-card{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:1rem 1.2rem;margin-bottom:.8rem}
  .kb-head{display:flex;justify-content:space-between;gap:.6rem;flex-wrap:wrap;margin-bottom:.3rem}
  .kb-from{font-size:.72rem;color:#6b7280}
  .kb-title{font-size:.95rem;font-weight:600}
  .kb-date{font-size:.72rem;color:#555;white-space:nowrap}
  .doc{font-size:.84rem;line-height:1.6;color:#c8ccd6;margin-top:.6rem}
  .doc code{background:#0f1117;border:1px solid #2a2d3a;border-radius:4px;padding:.05rem .3rem;
       font-family:ui-monospace,monospace;font-size:.92em;color:#a5b4fc}
  .doc .code{background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;padding:.6rem .8rem;
       margin:.4rem 0;font-family:ui-monospace,monospace;font-size:.78rem;white-space:pre-wrap;color:#9aa2b1}
  .doc .li{padding-left:1.1rem;text-indent:-.7rem}
  .alert{padding:.7rem 1rem;border-radius:8px;margin-bottom:1rem;font-size:.85rem}
  .alert-ok{background:rgba(45,168,98,.12);border:1px solid rgba(45,168,98,.3);color:#2da862}
  .alert-err{background:rgba(220,38,38,.12);border:1px solid rgba(220,38,38,.3);color:#f87171}
  label{display:block;font-size:.75rem;color:#888;margin-bottom:.35rem;text-transform:uppercase;letter-spacing:.04em}
  textarea,input[type=text],select{width:100%;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;
    padding:.65rem .9rem;color:#e8e8ea;font-size:.9rem;outline:none;font-family:inherit}
  textarea:focus,select:focus,input:focus{border-color:#4f6ef7}
  select option{background:#1a1d27}
  textarea{resize:vertical;font-family:ui-monospace,monospace;font-size:.82rem;line-height:1.6}
  .section{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:1.2rem;margin-bottom:1.1rem}
  .section-title{font-size:.78rem;font-weight:600;color:#888;margin-bottom:.9rem;text-transform:uppercase;letter-spacing:.06em}
  .btn{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1rem;border-radius:8px;border:none;
       cursor:pointer;font-size:.85rem;font-weight:500;transition:opacity .15s;text-decoration:none;white-space:nowrap}
  .btn:hover{opacity:.85}
  .btn-primary{background:#4f6ef7;color:#fff}
  .btn-secondary{background:#1e2130;color:#e8e8ea;border:1px solid #2a2d3a}
  .v-active{color:#2da862;font-weight:600}
  .hint{font-size:.78rem;color:#555;margin-top:.4rem}
  .empty{color:#555;font-size:.82rem;font-style:italic}
  .v-row{display:flex;gap:.6rem;align-items:center;padding:.5rem .2rem;border-bottom:1px solid #1e2130}
</style>
"""


def _page(title: str, body: str, tabs: str, active, extra_css: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Hub</title>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,-apple-system,sans-serif;background:#0f1117;color:#e8e8ea;min-height:100vh;font-size:14px}}
  a{{color:inherit;text-decoration:none}}
  header{{padding:1rem 1.5rem;border-bottom:1px solid #1e2130}}
  .logo{{color:#888;font-size:.9rem}}
  .logo a:hover{{color:#e8e8ea}}
  .sep{{color:#444}}
  .container{{max-width:860px;margin:0 auto;padding:2rem 1.5rem}}
  .page-title{{font-size:1.2rem;font-weight:700;margin-bottom:1.2rem}}
</style>
{_CSS}{extra_css}
</head>
<body>
<header><div class="logo"><a href="/">JLM VPS</a> <span class="sep">/</span> <span class="logo">Newsletter</span></div></header>
<div class="container">
  <div class="page-title">📬 Newsletter Summary</div>
  <div class="tabs">
    <a class="tab {'active' if active=='kb' else ''}" href="/newsletter">📚 Résumés (KB)</a>
    <a class="tab {'active' if active=='prompt' else ''}" href="/newsletter/prompt">✏️ Prompt de résumé</a>
    <a class="tab {'active' if active=='aliases' else ''}" href="/newsletter/aliases">📮 Alias</a>
  </div>
  {body}
</div>
</body></html>"""


# ── Page KB ────────────────────────────────────────────────────────────────────

def _page_kb(docs: list[dict], error: str = "") -> str:
    if error:
        banner = f'<div class="alert alert-err">{_e(error)}</div>'
    elif not docs:
        banner = '<p class="empty">Aucun résumé enregistré pour l\'instant. Le premier digest va remplir cette base.</p>'
    else:
        banner = f'<div class="alert alert-ok">{len(docs)} résumé(s) enregistré(s) dans la base de connaissance (enveloppe KNOWLEDGE §3).</div>'

    cards = ""
    for d in docs:
        body_md = _md(d.get("body") or "")
        tags = "".join(
            f'<span class="tag" style="background:#0f1117;border:1px solid #2a2d3a;color:#9ca3af;'
            f'border-radius:20px;padding:.15rem .5rem;font-size:.7rem;margin-right:.3rem">{_e(t)}</span>'
            for t in (d.get("tags") or [])
        )
        cards += f"""
<div class="kb-card">
  <div class="kb-head">
    <div class="kb-title">{_e(d.get("title") or "(sans objet)")}</div>
    <div class="kb-date">{_fmt(d.get("created_at"))}</div>
  </div>
  <div class="kb-from">{_e(d.get("metadata", {}).get("from_addr", d.get("uri", "")))}</div>
  <div style="display:flex;gap:.5rem;margin-top:.4rem;flex-wrap:wrap">{tags}</div>
  <div class="doc">{body_md}</div>
</div>"""
    body = f"""{banner}
{cards}"""
    return _page("Résumés", body, "", "kb")


# ── Page éditeur de prompt ─────────────────────────────────────────────────────

def _prompt_editor(data: dict, save_action: str, activate_action: str) -> str:
    """Éditeur de prompt versionné : formulaire d'enregistrement + historique (menu « Restaurer »).

    Partagé par la page newsletter (`/newsletter/prompt`, HTML inchangé) et les pages d'alias.
    """
    active_id = data.get("active_id")
    active_prompt = data.get("active_prompt", "")
    versions = data.get("versions", [])

    # Menu déroulant des versions (plus récente d'abord, données triées par le service).
    v_opts = ""
    for v in versions:
        label = f"v{v.get('id')} — {_fmt(_dt(v.get('created_at')))} — {(len(v.get('note',''))>24 and v.get('note','')[:24]+'…' or v.get('note')) or (v.get('prompt','') or '')[:24]}"
        if v.get("is_active"):
            label += "  (active)"
            v_opts = f'<option value="{v.get("id")}" selected>{_e(label)}</option>' + v_opts
        else:
            v_opts += f'<option value="{v.get("id")}">{_e(label)}</option>'

    active_note = ""
    for v in versions:
        if v.get("id") == active_id:
            active_note = f"v{v.get('id')} rédigée le {_fmt(_dt(v.get('created_at')))} — {_e(v.get('note') or '')}"
            break
    active_html = f'<div class="hint" style="margin-bottom:1rem">Actuellement active : <span class="v-active">{_e(active_note)}</span></div>' if active_note else ""

    return f"""{active_html}
<form method="POST" action="{save_action}">
  <div class="section">
    <div class="section-title">Prompt envoyé à DeepInfra (rédaction du résumé en HTML)</div>
    <label>Prompt</label>
    <textarea name="prompt" rows="16">{_e(active_prompt)}</textarea>
    <div class="hint">Ce prompt est celui qui produit le résumé de chaque newsletter (un appel par mail). Le système ajoute
    toujours côté code les exigences « en français » et « exclure les publicités », qui restent donc garanties même ici.</div>
    <label>Note (optionnel)</label>
    <input type="text" name="note" placeholder="ex : v2 — titres plus courts">
    <button type="submit" class="btn btn-primary" style="margin-top:.8rem">💾 Enregistrer comme nouvelle version</button>
  </div>
</form>

<div class="section">
  <div class="section-title">Historique des versions — revenir à une version antérieure</div>
  <form method="POST" action="{activate_action}" style="display:flex;gap:.5rem;align-items:flex-end;flex-wrap:wrap">
    <div style="flex:1;min-width:220px">
      <label>Version</label>
      <select name="version_id">{v_opts}</select>
    </div>
    <button type="submit" class="btn btn-secondary">↩ Restaurer cette version</button>
  </form>
  {"" if versions else '<p class="empty" style="margin-top:.6rem">Aucune version enregistrée.</p>'}
</div>"""


def _page_prompt(data: dict, flash: str = "", error: str = "") -> str:
    flash_html = ""
    if flash == "saved":
        flash_html = '<div class="alert alert-ok">✓ Nouvelle version enregistrée et activée.</div>'
    elif flash == "activated":
        flash_html = '<div class="alert alert-ok">✓ Version restaurée et activée.</div>'
    if error:
        flash_html += f'<div class="alert alert-err">{_e(error)}</div>'

    body = f"{flash_html}\n" + _prompt_editor(data, "/newsletter/prompt/save", "/newsletter/prompt/activate")
    return _page("Éditeur de prompt", body, "", "prompt")


def _dt(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except Exception:
        return None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def kb_view(request: Request):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    try:
        data = await _api("GET", "/api/kb")
        docs, error = data.get("documents", []), ""
    except ApiError as exc:
        docs, error = [], str(exc)
    return HTMLResponse(_page_kb(docs, error))


@router.get("/prompt", response_class=HTMLResponse)
async def prompt_view(request: Request, saved: str = "", activated: str = "", error: str = ""):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    flash = "saved" if saved else ("activated" if activated else "")
    error = error or ""
    data = {}
    try:
        data = await _api("GET", "/api/prompt")
    except ApiError as exc:
        error = error or str(exc)
    return HTMLResponse(_page_prompt(data, flash=flash, error=error))


@router.post("/prompt/save")
async def prompt_save(request: Request, prompt: str = Form(""), note: str = Form("")):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    from urllib.parse import quote
    if not prompt.strip():
        return RedirectResponse("/newsletter/prompt?error=Le+prompt+ne+peut+pas+%C3%AAtre+vide", status_code=303)
    try:
        await _api("POST", "/api/prompt/versions", {"prompt": prompt, "note": note})
    except ApiError as exc:
        return RedirectResponse(f"/newsletter/prompt?error={quote(str(exc))}", status_code=303)
    return RedirectResponse("/newsletter/prompt?saved=1", status_code=303)


@router.post("/prompt/activate")
async def prompt_activate(request: Request, version_id: str = Form("")):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    from urllib.parse import quote
    try:
        await _api("POST", "/api/prompt/activate", {"version_id": int(version_id)})
    except (ApiError, ValueError) as exc:
        return RedirectResponse(f"/newsletter/prompt?error={quote(str(exc))}", status_code=303)
    return RedirectResponse("/newsletter/prompt?activated=1", status_code=303)


# ══ Alias ══════════════════════════════════════════════════════════════════════════════════════════
# Un alias = une adresse de réception + sa politique : fréquence, expéditeurs autorisés, prompt.
# Le service (newsletter-summary) est seul détenteur des règles ; le Hub ne fait que les saisir et
# les afficher — toute valeur invalide (nom, adresse d'expéditeur) revient du service en erreur
# lisible, jamais ignorée en silence.

_FREQ_LABELS = {
    "morning": "Matin à 8h — un lot par destinataire",
    "evening": "Soir à 18h — un lot par destinataire",
    "minute": "Chaque minute — un e-mail par mail reçu",
}
_STATUS_LABELS = {
    "new": ("en attente", "#f59e0b"), "processing": ("en cours", "#f59e0b"),
    "summarized": ("envoyé", "#2da862"), "failed": ("échec", "#f87171"), "rejected": ("rejeté", "#6b7280"),
    "ignored": ("ignoré", "#6b7280"),
}

_CSS_ALIAS = """
<style>
  .badge{display:inline-block;border-radius:20px;padding:.1rem .55rem;font-size:.7rem;font-weight:600;
         border:1px solid currentColor;white-space:nowrap}
  .al-card{display:block;background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:.9rem 1.1rem;
           margin-bottom:.7rem}
  .al-card:hover{border-color:#4f6ef7}
  .al-addr{font-weight:600;font-size:.95rem;word-break:break-all}
  .al-meta{font-size:.76rem;color:#888;margin-top:.3rem;display:flex;gap:.9rem;flex-wrap:wrap}
  .check{display:flex;gap:.5rem;align-items:center;margin:.5rem 0;font-size:.85rem;text-transform:none;letter-spacing:0;color:#c8ccd6}
  .check input{width:auto}
  .warn{font-size:.78rem;color:#f59e0b;margin-top:.3rem}
  table.mails{width:100%;border-collapse:collapse;font-size:.78rem}
  table.mails th{text-align:left;color:#888;font-weight:600;padding:.35rem .4rem;border-bottom:1px solid #2a2d3a}
  table.mails td{padding:.4rem;border-bottom:1px solid #1e2130;vertical-align:top;word-break:break-word}
  .err{color:#f87171}
  .tblwrap{overflow-x:auto}
  .row2{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
  @media(max-width:640px){.row2{grid-template-columns:1fr}}
</style>
"""


def _badge(status: str) -> str:
    label, color = _STATUS_LABELS.get(status, (status, "#888"))
    return f'<span class="badge" style="color:{color}">{_e(label)}</span>'


def _counts_html(counts: dict) -> str:
    """Décompte lisible par statut : ce qui attend ou a échoué ne doit jamais rester invisible."""
    pending = counts.get("new", 0) + counts.get("processing", 0)
    parts = [f"{pending} en attente"]
    for key, word in (("failed", "échec(s)"), ("rejected", "rejeté(s)"), ("summarized", "envoyé(s)")):
        if counts.get(key):
            color = "#f87171" if key == "failed" else "inherit"
            parts.append(f'<span style="color:{color}">{counts[key]} {word}</span>')
    return " · ".join(parts)


def _senders_label(a: dict) -> str:
    if a.get("open_senders"):
        return "tous les expéditeurs"
    n = len(a.get("allowed_senders") or [])
    return f"{n} expéditeur(s) autorisé(s)" if n else '<span style="color:#f87171">aucun expéditeur autorisé</span>'


def _flash(saved: str = "", created: str = "", activated: str = "", prompt_saved: str = "", error: str = "") -> str:
    out = ""
    for cond, msg in ((saved, "✓ Réglages enregistrés."), (created, "✓ Alias créé — ajoutez maintenant les expéditeurs autorisés."),
                      (prompt_saved, "✓ Nouvelle version du prompt enregistrée et activée."), (activated, "✓ Version restaurée et activée.")):
        if cond:
            out += f'<div class="alert alert-ok">{msg}</div>'
    if error:
        out += f'<div class="alert alert-err">{_e(error)}</div>'
    return out


def _page_aliases(data: dict, flash_html: str = "", error: str = "") -> str:
    aliases = data.get("aliases", [])
    domain = data.get("domain", "")
    banner = f'<div class="alert alert-err">{_e(error)}</div>' if error else ""
    cards = ""
    for a in aliases:
        state = "" if a.get("enabled") else ' <span class="badge" style="color:#6b7280">désactivé</span>'
        default = ' <span class="badge" style="color:#4f6ef7">par défaut</span>' if a.get("is_default") else ""
        dest = f'envoi à {_e(a["recipient"])}' if a.get("recipient") else "réponse à l'expéditeur"
        cards += f"""
<a class="al-card" href="/newsletter/aliases/{a['id']}">
  <div class="al-addr">{_e(a['address'])}{default}{state}</div>
  <div class="al-meta"><span>{_e(_FREQ_LABELS.get(a['frequency'], a['frequency']))}</span><span>{_senders_label(a)}</span><span>{_e(dest)}</span></div>
  <div class="al-meta">{_counts_html(a.get('counts') or {})}</div>
</a>"""
    if not aliases and not error:
        cards = '<p class="empty">Aucun alias.</p>'
    freq_opts = "".join(f'<option value="{k}"{" selected" if k == "minute" else ""}>{_e(v)}</option>' for k, v in _FREQ_LABELS.items())
    body = f"""{flash_html}{banner}
<div class="section">
  <div class="section-title">Alias de réception</div>
  <div class="hint" style="margin:0 0 .9rem">Un mail envoyé à l'adresse d'un alias est résumé, et le résumé revient à l'expéditeur s'il est autorisé.
  Tant que le gateway est en mode développement, tous les envois sont redirigés vers l'adresse du compte Resend.</div>
  {cards}
</div>
<form method="POST" action="/newsletter/aliases/create">
  <div class="section">
    <div class="section-title">Créer un alias</div>
    <label>Adresse</label>
    <div style="display:flex;gap:.5rem;align-items:center;flex-wrap:wrap">
      <input type="text" name="local_part" placeholder="summary ou aaa+bbb" required style="flex:1;min-width:160px" autocomplete="off">
      <span class="hint" style="margin:0">@{_e(domain)}</span>
    </div>
    <div class="hint">Lettres, chiffres et _ + - ; le point n'est admis qu'entre deux segments. <code>aaa+bbb</code> est une adresse à part entière (pas de repli sur <code>aaa</code>).</div>
    <div class="row2" style="margin-top:.8rem">
      <div><label>Fréquence</label><select name="frequency">{freq_opts}</select></div>
      <div><label>Expéditeurs autorisés (un par ligne)</label><textarea name="allowed_senders" rows="3" placeholder="vous@exemple.fr"></textarea></div>
    </div>
    <div class="hint">Sans expéditeur autorisé, personne ne peut utiliser l'alias. Le prompt de départ est une copie de celui de la newsletter.</div>
    <button type="submit" class="btn btn-primary" style="margin-top:.8rem">➕ Créer l'alias</button>
  </div>
</form>"""
    return _page("Alias", body, "", "aliases", extra_css=_CSS_ALIAS)


def _page_alias(alias: dict, prompt_data: dict, mails: list, flash_html: str = "", error: str = "") -> str:
    aid = alias["id"]
    banner = f'<div class="alert alert-err">{_e(error)}</div>' if error else ""
    freq_opts = "".join(f'<option value="{k}"{" selected" if k == alias["frequency"] else ""}>{_e(v)}</option>' for k, v in _FREQ_LABELS.items())
    senders = "\n".join(alias.get("allowed_senders") or [])
    enabled_box = "" if alias.get("is_default") else (
        '<input type="hidden" name="enabled_present" value="1">'
        f'<label class="check"><input type="checkbox" name="enabled"{" checked" if alias.get("enabled") else ""}> Alias actif</label>'
        '<div class="hint" style="margin-top:-.2rem">Désactivé : les mails reçus sont rejetés (conservés, sans réponse).</div>'
    )
    dest = (f"Le digest est envoyé à <strong>{_e(alias['recipient'])}</strong>." if alias.get("recipient")
            else "La réponse est envoyée à <strong>l'expéditeur</strong> du mail.")
    rows = ""
    for m in mails:
        err = f'<div class="err">{_e(m["last_error"])}</div>' if m.get("last_error") else ""
        tries = f' ({m["attempts"]} essai(s))' if m.get("attempts") else ""
        rows += (f'<tr><td>{_fmt(m.get("received_at"))}</td><td>{_e(m.get("from_addr") or "")}</td>'
                 f'<td>{_e(m.get("subject") or "(sans objet)")}{err}</td><td>{_badge(m.get("status", ""))}{_e(tries)}</td></tr>')
    table = (f'<div class="tblwrap"><table class="mails"><tr><th>Reçu</th><th>Expéditeur</th><th>Objet</th><th>Statut</th></tr>{rows}</table></div>'
             if rows else '<p class="empty">Aucun mail reçu sur cet alias.</p>')
    editor = _prompt_editor(prompt_data, f"/newsletter/aliases/{aid}/prompt/save", f"/newsletter/aliases/{aid}/prompt/activate")
    body = f"""{flash_html}{banner}
<div style="margin-bottom:1rem"><a class="btn btn-secondary" href="/newsletter/aliases">← Tous les alias</a></div>
<div class="page-title" style="font-size:1.05rem;word-break:break-all">{_e(alias['address'])}</div>
<form method="POST" action="/newsletter/aliases/{aid}/save">
  <div class="section">
    <div class="section-title">Réglages</div>
    <label>Fréquence du résumé</label>
    <select name="frequency">{freq_opts}</select>
    <div class="hint">« Chaque minute » : le système vérifie chaque minute et vous renvoie <strong>un e-mail par mail reçu</strong> (jamais de regroupement).
    Matin/soir : un seul e-mail regroupant tous les mails reçus depuis le dernier envoi.</div>
    <label style="margin-top:.9rem">Expéditeurs autorisés (un par ligne)</label>
    <textarea name="allowed_senders" rows="4" placeholder="vous@exemple.fr">{_e(senders)}</textarea>
    <div class="hint">Les mails d'une autre adresse sont rejetés sans réponse. {dest}</div>
    <label class="check" style="margin-top:.7rem"><input type="checkbox" name="open_senders"{" checked" if alias.get("open_senders") else ""}> Accepter tous les expéditeurs</label>
    <div class="warn">⚠ À éviter sur un alias qui répond à l'expéditeur : l'adresse d'un expéditeur est facile à usurper.</div>
    {enabled_box}
    <button type="submit" class="btn btn-primary" style="margin-top:.8rem">💾 Enregistrer les réglages</button>
  </div>
</form>
{editor}
<div class="section">
  <div class="section-title">Derniers mails</div>
  <div class="hint" style="margin:0 0 .6rem">{_counts_html(alias.get('counts') or {})}</div>
  {table}
</div>"""
    return _page(alias["address"], body, "", "aliases", extra_css=_CSS_ALIAS)


async def _alias_by_id(aid: int) -> dict | None:
    data = await _api("GET", "/api/aliases")
    return next((a for a in data.get("aliases", []) if a["id"] == aid), None)


def _to(path: str, **params) -> RedirectResponse:
    from urllib.parse import urlencode
    qs = urlencode({k: v for k, v in params.items() if v})
    return RedirectResponse(f"{path}?{qs}" if qs else path, status_code=303)


@router.get("/aliases", response_class=HTMLResponse)
async def aliases_view(request: Request, error: str = "", created: str = "", saved: str = ""):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    data, err = {}, error
    try:
        data = await _api("GET", "/api/aliases")
    except ApiError as exc:
        err = err or str(exc)
    return HTMLResponse(_page_aliases(data, flash_html=_flash(saved=saved, created=created), error=err))


@router.post("/aliases/create")
async def alias_create(request: Request, local_part: str = Form(""), frequency: str = Form("minute"),
                       allowed_senders: str = Form("")):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    try:
        res = await _api("POST", "/api/aliases", {"local_part": local_part, "frequency": frequency,
                                                   "allowed_senders": allowed_senders})
    except ApiError as exc:
        return _to("/newsletter/aliases", error=str(exc))
    return _to(f"/newsletter/aliases/{res['id']}", created="1")


@router.get("/aliases/{aid}", response_class=HTMLResponse)
async def alias_view(request: Request, aid: int, saved: str = "", created: str = "", prompt_saved: str = "",
                     activated: str = "", error: str = ""):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    try:
        alias = await _alias_by_id(aid)
        if alias is None:
            return _to("/newsletter/aliases", error="Alias introuvable")
        prompt_data = await _api("GET", f"/api/prompt?alias_id={aid}")
        mails = (await _api("GET", f"/api/aliases/{aid}/mails?limit=20")).get("mails", [])
    except ApiError as exc:
        return _to("/newsletter/aliases", error=str(exc))
    flash = _flash(saved=saved, created=created, prompt_saved=prompt_saved, activated=activated)
    return HTMLResponse(_page_alias(alias, prompt_data, mails, flash_html=flash, error=error))


@router.post("/aliases/{aid}/save")
async def alias_save(request: Request, aid: int, frequency: str = Form(""), allowed_senders: str = Form(""),
                     open_senders: str = Form(""), enabled: str = Form(""), enabled_present: str = Form("")):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    payload = {"frequency": frequency, "allowed_senders": allowed_senders, "open_senders": bool(open_senders)}
    if enabled_present:   # absent pour l'alias par défaut : la case n'est pas affichée, on ne le désactive jamais par oubli
        payload["enabled"] = bool(enabled)
    try:
        await _api("PUT", f"/api/aliases/{aid}", payload)
    except ApiError as exc:
        return _to(f"/newsletter/aliases/{aid}", error=str(exc))
    return _to(f"/newsletter/aliases/{aid}", saved="1")


@router.post("/aliases/{aid}/prompt/save")
async def alias_prompt_save(request: Request, aid: int, prompt: str = Form(""), note: str = Form("")):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    if not prompt.strip():
        return _to(f"/newsletter/aliases/{aid}", error="Le prompt ne peut pas être vide")
    try:
        await _api("POST", "/api/prompt/versions", {"prompt": prompt, "note": note, "alias_id": aid})
    except ApiError as exc:
        return _to(f"/newsletter/aliases/{aid}", error=str(exc))
    return _to(f"/newsletter/aliases/{aid}", prompt_saved="1")


@router.post("/aliases/{aid}/prompt/activate")
async def alias_prompt_activate(request: Request, aid: int, version_id: str = Form("")):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    try:
        await _api("POST", "/api/prompt/activate", {"version_id": int(version_id), "alias_id": aid})
    except (ApiError, ValueError) as exc:
        return _to(f"/newsletter/aliases/{aid}", error=str(exc))
    return _to(f"/newsletter/aliases/{aid}", activated="1")
