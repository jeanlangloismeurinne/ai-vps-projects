"""Pages « Gmail » du Hub — pilotage des règles de transfert (service newsletter-summary, /api/gmail).

Le Hub ne détient aucune règle ni aucun secret de signature : il saisit, aperçoit, confirme et affiche.
Seule exception : le NOUVEAU secret d'une rotation, affiché une seule fois à l'écran pour être collé dans
le script Apps Script. Toute écriture porte un jeton anti-CSRF dérivé de la session.
"""
from __future__ import annotations

import hashlib
import hmac

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.newsletter import _CSS_ALIAS, _e, _fmt, _page

router = APIRouter(prefix="/newsletter/gmail")


class GmailError(Exception):
    def __init__(self, message: str, code: str = "", status: int = 0):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


async def _gapi(method: str, path: str, payload: dict | None = None):
    from app.main import settings
    base = (settings.NEWSLETTER_URL or "http://newsletter-summary:8000").rstrip("/")
    headers = {"x-hub-token": settings.NEWSLETTER_API_TOKEN} if settings.NEWSLETTER_API_TOKEN else {}
    try:
        async with httpx.AsyncClient(timeout=60.0) as c:   # le script Apps Script peut être lent
            r = await c.request(method, f"{base}/api/gmail{path}", json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise GmailError(f"Service newsletter injoignable : {type(exc).__name__}")
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except Exception:
            detail = None
        if isinstance(detail, dict):
            raise GmailError(str(detail.get("message") or detail.get("code")), str(detail.get("code") or ""), r.status_code)
        raise GmailError(f"Le service a répondu {r.status_code} : {detail if isinstance(detail, str) else r.text[:200]}",
                         status=r.status_code)
    return r.json()


# ── Anti-CSRF : jeton dérivé du cookie de session ───────────────────────────────────────────
def csrf_token(request: Request, secret: str) -> str:
    from app.auth import COOKIE_NAME
    return hmac.new(secret.encode(), ("gmail-csrf:" + request.cookies.get(COOKIE_NAME, "")).encode(), hashlib.sha256).hexdigest()[:32]


def _csrf_ok(request: Request, token: str) -> bool:
    from app.main import settings
    return bool(request.cookies.get("hub_session")) and hmac.compare_digest(csrf_token(request, settings.SESSION_SECRET), token or "")


def _guard(request: Request):
    """Authentification de session. Renvoie une réponse de refus, ou None."""
    from app.main import settings
    from app.roadmap import _require_auth
    return _require_auth(request, settings)


def _hidden(request: Request) -> str:
    from app.main import settings
    return f'<input type="hidden" name="csrf" value="{csrf_token(request, settings.SESSION_SECRET)}">'


def _to(path: str, **params) -> RedirectResponse:
    from urllib.parse import urlencode
    qs = urlencode({k: v for k, v in params.items() if v})
    return RedirectResponse(f"{path}?{qs}" if qs else path, status_code=303)


_CSS_GMAIL = _CSS_ALIAS + """
<style>
  .st-synced{color:#2da862}.st-pending{color:#f59e0b}.st-drift{color:#f59e0b}.st-error{color:#f87171}
  .rule{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:.9rem 1.1rem;margin-bottom:.7rem}
  .rule.off{opacity:.65}
  .rule-title{font-weight:600;font-size:.95rem;word-break:break-word}
  .rule-line{font-size:.8rem;color:#c8ccd6;margin-top:.35rem;word-break:break-word}
  .actions{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.7rem}
  .actions form{display:inline}
  .btn-danger{background:#3a1a1a;color:#f87171;border:1px solid #5a2a2a}
  .btn-sm{padding:.4rem .75rem;font-size:.8rem}
  .secret{font-family:ui-monospace,monospace;font-size:.82rem;background:#0f1117;border:1px solid #4f6ef7;border-radius:8px;
          padding:.7rem .9rem;word-break:break-all;user-select:all}
  .preview{background:#10161f;border:1px solid #4f6ef7;border-radius:10px;padding:.8rem 1rem;margin:.9rem 0;font-size:.88rem;line-height:1.6}
  ol.steps{padding-left:1.2rem;font-size:.84rem;line-height:1.7;color:#c8ccd6}
  @media(max-width:640px){.btn{padding:.6rem 1rem}.actions .btn{flex:1;justify-content:center}}
</style>
"""

_STATUS = {"synced": ("synchronisée", "synced"), "pending": ("en attente du script", "pending"),
           "drift": ("écart avec Gmail", "drift"), "error": ("refusée par le script", "error")}
_DRIFT = {"missing": "le filtre n'existe plus dans Gmail", "modified": "le filtre a été modifié à la main dans Gmail",
          "should_be_absent": "un filtre existe alors que la règle est désactivée",
          "unrecorded": "un filtre est présent mais n'est pas enregistré (remplacement interrompu)"}


def _nav(active: str) -> str:
    items = [("rules", "/newsletter/gmail", "Règles"), ("sync", "/newsletter/gmail/sync", "Synchronisation"),
             ("audit", "/newsletter/gmail/audit", "Journal"), ("secret", "/newsletter/gmail/secret", "Script & secret")]
    return ('<div class="tabs" style="flex-wrap:wrap">' + "".join(
        f'<a class="tab {"active" if k == active else ""}" href="{u}">{t}</a>' for k, u, t in items) + "</div>")


def _wrap(title: str, active: str, body: str) -> HTMLResponse:
    r = HTMLResponse(_page(title, _nav(active) + body, "", "gmail", extra_css=_CSS_GMAIL))
    r.headers["Cache-Control"] = "no-store"
    return r


def _flash(ok: str = "", error: str = "") -> str:
    out = f'<div class="alert alert-ok">{_e(ok)}</div>' if ok else ""
    return out + (f'<div class="alert alert-err">{_e(error)}</div>' if error else "")


def describe(f: dict) -> str:
    """Phrase en clair de ce que fera la règle — c'est ce que l'utilisateur confirme."""
    frm, sub, exc = f.get("from") or f.get("from_addr") or "", f.get("subject_contains") or "", f.get("exclude_words") or ""
    who = (f"tous les mails de <strong>{_e(frm[1:])}</strong>" if frm.startswith("@")
           else f"les mails de <strong>{_e(frm)}</strong>" if frm else "tous les mails, de n'importe quel expéditeur,")
    parts = [f"{who}"]
    if sub:
        parts.append(f"dont l'objet contient <strong>« {_e(sub)} »</strong>")
    if exc:
        parts.append(f"sans le mot <strong>« {_e(exc)} »</strong>")
    tail = f" seront transférés à <strong>{_e(f.get('destination') or '?')}</strong>"
    tail += (", <strong>et retirés de votre boîte de réception</strong>." if f.get("skip_inbox")
             else ", et restent dans votre boîte de réception.")
    return "Dès l'enregistrement, " + " ".join(parts) + tail


# ── Liste ───────────────────────────────────────────────────────────────────────────────────
def _page_rules(request: Request, rules: list, status: dict, flash: str = "") -> str:
    hid = _hidden(request)
    alerts = ""
    if not status.get("configured"):
        alerts += '<div class="alert alert-err">Le script Gmail n\'est pas configuré (GMAIL_SCRIPT_URL / GMAIL_SCRIPT_SECRET). Voir « Script & secret ».</div>'
    if status.get("secret_too_old"):
        alerts += f'<div class="alert alert-err">Le secret du script a {status["secret_age_days"]} jours : renouvelez-le (« Script & secret »).</div>'
    if status.get("auth_failures"):
        alerts += f'<div class="alert alert-err">{status["auth_failures"]} refus d\'authentification consécutif(s) : secrets désaccordés ?</div>'
    cards = ""
    for r in rules:
        label, cls = _STATUS.get(r["sync_status"], (r["sync_status"], ""))
        crit = (f'<strong>{_e(r["from"])}</strong>' if r["from"] else "<em>tout expéditeur</em>")
        if r["subject_contains"]:
            crit += f' · objet contient « {_e(r["subject_contains"])} »'
        if r["exclude_words"]:
            crit += f' · sans « {_e(r["exclude_words"])} »'
        extra = ""
        if r["sync_status"] == "drift" and r.get("drift_kind"):
            extra = f'<div class="warn">⚠ {_e(_DRIFT.get(r["drift_kind"], r["drift_kind"]))}</div>'
        if r.get("last_error") and r["sync_status"] in ("error", "pending"):
            extra += f'<div class="err" style="font-size:.78rem;margin-top:.3rem">{_e(r["last_error"])}</div>'
        rid = r["id"]
        btns = f'<a class="btn btn-secondary btn-sm" href="/newsletter/gmail/{rid}/edit">✏️ Modifier</a>'
        if r["sync_status"] in ("pending", "error") and r.get("pending_op"):
            btns += f'<form method="POST" action="/newsletter/gmail/{rid}/retry">{hid}<button class="btn btn-primary btn-sm">🔁 Réessayer</button></form>'
        if r["sync_status"] == "drift":
            btns += f'<form method="POST" action="/newsletter/gmail/{rid}/fix" onsubmit="return confirm(\'Réaligner Gmail sur cette règle ?\')">{hid}<button class="btn btn-primary btn-sm">🛠 Corriger</button></form>'
        btns += (f'<form method="POST" action="/newsletter/gmail/{rid}/toggle">{hid}<input type="hidden" name="enabled" value="{"0" if r["enabled"] else "1"}">'
                 f'<button class="btn btn-secondary btn-sm">{"⏸ Désactiver" if r["enabled"] else "▶ Réactiver"}</button></form>')
        btns += (f'<form method="POST" action="/newsletter/gmail/{rid}/delete" onsubmit="return confirm(\'Supprimer cette règle et son filtre Gmail ?\')">'
                 f'{hid}<button class="btn btn-danger btn-sm">🗑 Supprimer</button></form>')
        cards += f"""
<div class="rule{'' if r['enabled'] else ' off'}">
  <div class="rule-title">{_e(r["name"] or r["from"] or r["subject_contains"])} <span class="badge st-{cls}">{_e(label)}</span>{'' if r['enabled'] else ' <span class="badge" style="color:#6b7280">désactivée</span>'}</div>
  <div class="rule-line">{crit}</div>
  <div class="rule-line">→ {_e(r["destination"])}{' · retire de la boîte de réception' if r["skip_inbox"] else ''}</div>
  {extra}
  <div class="actions">{btns}</div>
</div>"""
    if not rules:
        cards = '<p class="empty">Aucune règle.</p>'
    body = f"""{flash}{alerts}
<div class="section">
  <div class="section-title">Règles de transfert Gmail — {status.get("active_rules", 0)}/{status.get("max_rules", 50)} actives</div>
  <div class="hint" style="margin:0 0 .9rem">Chaque règle crée un filtre dans le Gmail de l'utilisateur : les mails correspondants sont transférés à l'adresse choisie,
  qui est un alias du moteur de résumé. Rien n'est écrit dans Gmail sans votre confirmation.</div>
  {cards}
  <a class="btn btn-primary" href="/newsletter/gmail/new">➕ Nouvelle règle</a>
</div>"""
    return body


@router.get("", response_class=HTMLResponse)
async def rules_view(request: Request, ok: str = "", error: str = ""):
    if r := _guard(request):
        return r
    err, rules, status = error, [], {}
    try:
        status = await _gapi("GET", "/status")
        rules = (await _gapi("GET", "/rules"))["rules"]
    except GmailError as exc:
        err = err or exc.message
    return _wrap("Gmail", "rules", _page_rules(request, rules, status, _flash(ok, err)))


# ── Formulaire ──────────────────────────────────────────────────────────────────────────────
def _page_form(request: Request, rule: dict, addrs: list, *, error: str = "", warnings: list | None = None,
               preview: str = "", need_confirm: bool = False, rid: str = "") -> str:
    def opt(a):
        al = a.get("alias") or {}
        tag = (f' — alias « {al["local_part"]} », {al["frequency"]}' + ("" if al.get("enabled") else ", désactivé")) if al else " — sans alias dédié (alias par défaut)"
        dis = "" if a["selectable"] else " disabled"
        why = "" if a["selectable"] else (" [non validée par Gmail]" if a["status"] != "accepted" else " [domaine non autorisé]")
        sel = " selected" if a["email"] == rule.get("destination") else ""
        return f'<option value="{_e(a["email"])}"{sel}{dis}>{_e(a["email"])}{_e(tag)}{why}</option>'
    options = "".join(opt(a) for a in addrs) or '<option value="">(aucune adresse de transfert)</option>'
    warn = "".join(f'<div class="warn">⚠ {_e(w)}</div>' for w in (warnings or []))
    confirm = ('<label class="check"><input type="checkbox" name="confirm_broad" value="1"> '
               "Je comprends que cette règle est large (sans expéditeur) et je la confirme.</label>") if need_confirm else ""
    prev = f'<div class="preview">{preview}{warn}</div>' if preview else ""
    action = f"/newsletter/gmail/{rid}/preview" if rid else "/newsletter/gmail/preview"
    save = f"/newsletter/gmail/{rid}/save" if rid else "/newsletter/gmail/save"
    v = lambda k: _e(str(rule.get(k) or ""))   # noqa: E731
    confirm_btn = ""
    if preview:
        confirm_btn = f'<button type="submit" class="btn btn-primary" formaction="{save}">✅ Confirmer et enregistrer</button>'
    body = f"""{_flash(error=error)}
<div style="margin-bottom:1rem"><a class="btn btn-secondary" href="/newsletter/gmail">← Toutes les règles</a></div>
<form method="POST" action="{action}" class="section">
  {_hidden(request)}
  <div class="section-title">{'Modifier la règle' if rid else 'Nouvelle règle'}</div>
  <label>Nom (facultatif)</label><input type="text" name="name" value="{v('name')}" maxlength="80">
  <label style="margin-top:.8rem">Expéditeur</label>
  <input type="text" name="from" value="{v('from')}" placeholder="newsletter@exemple.com ou @exemple.com" autocomplete="off">
  <div class="hint">Une adresse, ou un domaine entier (<code>@exemple.com</code>). Pas de joker ; les domaines publics (<code>@co.uk</code>) et les domaines interdits sont refusés.</div>
  <label style="margin-top:.8rem">L'objet contient (facultatif)</label><input type="text" name="subject_contains" value="{v('subject_contains')}">
  <div class="hint">Sans expéditeur, 6 caractères au moins sont exigés et une confirmation sera demandée.</div>
  <label style="margin-top:.8rem">Sans le mot (facultatif)</label><input type="text" name="exclude_words" value="{v('exclude_words')}">
  <label style="margin-top:.8rem">Transférer à</label>
  <select name="destination" required>{options}</select>
  <div class="hint">Seules les adresses déjà validées par Gmail sont proposées. Le choix de l'adresse décide du rythme du résumé (matin, soir, ou chaque mail).</div>
  <label class="check" style="margin-top:.8rem"><input type="checkbox" name="skip_inbox" value="1"{' checked' if rule.get('skip_inbox') else ''}> Retirer de la boîte de réception (archiver)</label>
  {confirm}
  {prev}
  <div class="actions"><button type="submit" class="btn {'btn-secondary' if preview else 'btn-primary'}">👁 {'Revoir l\'aperçu' if preview else 'Aperçu avant enregistrement'}</button>{confirm_btn}</div>
</form>"""
    return body


def _form_values(name, from_, subject_contains, exclude_words, destination, skip_inbox, confirm_broad) -> dict:
    return {"name": name, "from": from_, "subject_contains": subject_contains, "exclude_words": exclude_words,
            "destination": destination, "skip_inbox": bool(skip_inbox), "confirm_broad": bool(confirm_broad)}


async def _addresses() -> list:
    try:
        return (await _gapi("GET", "/forwarding-addresses"))["addresses"]
    except GmailError:
        return []


@router.get("/new", response_class=HTMLResponse)
async def form_new(request: Request):
    if r := _guard(request):
        return r
    return _wrap("Nouvelle règle", "rules", _page_form(request, {"skip_inbox": False}, await _addresses()))


@router.get("/{rid}/edit", response_class=HTMLResponse)
async def form_edit(request: Request, rid: str):
    if r := _guard(request):
        return r
    try:
        rule = next((x for x in (await _gapi("GET", "/rules"))["rules"] if x["id"] == rid), None)
    except GmailError as exc:
        return _to("/newsletter/gmail", error=exc.message)
    if rule is None:
        return _to("/newsletter/gmail", error="Règle introuvable")
    return _wrap("Modifier la règle", "rules", _page_form(request, rule, await _addresses(), rid=rid))


async def _preview(request: Request, rid: str, data: dict):
    if not _csrf_ok(request, data.pop("csrf", "")):
        return _to("/newsletter/gmail", error="Session de formulaire expirée : rechargez la page.")
    addrs = await _addresses()
    try:
        res = await _gapi("POST", "/preview", {**data, "id": rid or None})
    except GmailError as exc:
        return _wrap("Règle", "rules", _page_form(request, data, addrs, error=exc.message, need_confirm=exc.code == "confirmation_required", rid=rid))
    return _wrap("Règle", "rules", _page_form(request, data, addrs, warnings=res.get("warnings"), preview=describe(data),
                                              need_confirm=False, rid=rid))


@router.post("/preview")
async def preview_new(request: Request, csrf: str = Form(""), name: str = Form(""), from_: str = Form("", alias="from"),
                      subject_contains: str = Form(""), exclude_words: str = Form(""), destination: str = Form(""),
                      skip_inbox: str = Form(""), confirm_broad: str = Form("")):
    if r := _guard(request):
        return r
    d = _form_values(name, from_, subject_contains, exclude_words, destination, skip_inbox, confirm_broad)
    return await _preview(request, "", {**d, "csrf": csrf})


@router.post("/{rid}/preview")
async def preview_edit(request: Request, rid: str, csrf: str = Form(""), name: str = Form(""), from_: str = Form("", alias="from"),
                       subject_contains: str = Form(""), exclude_words: str = Form(""), destination: str = Form(""),
                       skip_inbox: str = Form(""), confirm_broad: str = Form("")):
    if r := _guard(request):
        return r
    d = _form_values(name, from_, subject_contains, exclude_words, destination, skip_inbox, confirm_broad)
    return await _preview(request, rid, {**d, "csrf": csrf})


async def _save(request: Request, rid: str, csrf: str, d: dict):
    if not _csrf_ok(request, csrf):
        return _to("/newsletter/gmail", error="Session de formulaire expirée : rechargez la page.")
    try:
        res = await (_gapi("PUT", f"/rules/{rid}", d) if rid else _gapi("POST", "/rules", d))
    except GmailError as exc:
        return _wrap("Règle", "rules", _page_form(request, d, await _addresses(), error=exc.message,
                                                  need_confirm=exc.code == "confirmation_required", rid=rid))
    rule = res["rule"]
    label = _STATUS.get(rule["sync_status"], (rule["sync_status"],))[0]
    msg = "Règle enregistrée et synchronisée avec Gmail." if rule["sync_status"] == "synced" else \
        f"Règle enregistrée — état : {label}. {rule.get('last_error') or ''}".strip()
    return _to("/newsletter/gmail", ok=msg)


@router.post("/save")
async def save_new(request: Request, csrf: str = Form(""), name: str = Form(""), from_: str = Form("", alias="from"),
                   subject_contains: str = Form(""), exclude_words: str = Form(""), destination: str = Form(""),
                   skip_inbox: str = Form(""), confirm_broad: str = Form("")):
    if r := _guard(request):
        return r
    return await _save(request, "", csrf, _form_values(name, from_, subject_contains, exclude_words, destination, skip_inbox, confirm_broad))


@router.post("/{rid}/save")
async def save_edit(request: Request, rid: str, csrf: str = Form(""), name: str = Form(""), from_: str = Form("", alias="from"),
                    subject_contains: str = Form(""), exclude_words: str = Form(""), destination: str = Form(""),
                    skip_inbox: str = Form(""), confirm_broad: str = Form("")):
    if r := _guard(request):
        return r
    return await _save(request, rid, csrf, _form_values(name, from_, subject_contains, exclude_words, destination, skip_inbox, confirm_broad))


# ── Actions sur une règle ───────────────────────────────────────────────────────────────────
async def _act(request: Request, csrf: str, method: str, path: str, payload: dict | None, done: str, back="/newsletter/gmail"):
    if r := _guard(request):
        return r
    if not _csrf_ok(request, csrf):
        return _to(back, error="Session de formulaire expirée : rechargez la page.")
    try:
        res = await _gapi(method, path, payload)
    except GmailError as exc:
        return _to(back, error=exc.message)
    rule = res.get("rule") or {}
    if res.get("deleted") is False:
        return _to(back, error="Suppression non confirmée par le script : la règle est conservée, réessayez.")
    if rule.get("sync_status") in ("pending", "error"):
        return _to(back, error=f"{done} — mais Gmail n'a pas confirmé : {rule.get('last_error') or rule['sync_status']}")
    return _to(back, ok=done)


@router.post("/{rid}/toggle")
async def toggle(request: Request, rid: str, csrf: str = Form(""), enabled: str = Form("")):
    return await _act(request, csrf, "PATCH", f"/rules/{rid}/enabled", {"enabled": enabled == "1"},
                      "Règle réactivée." if enabled == "1" else "Règle désactivée.")


@router.post("/{rid}/delete")
async def delete(request: Request, rid: str, csrf: str = Form("")):
    return await _act(request, csrf, "DELETE", f"/rules/{rid}", None, "Règle supprimée.")


@router.post("/{rid}/retry")
async def retry(request: Request, rid: str, csrf: str = Form("")):
    return await _act(request, csrf, "POST", f"/rules/{rid}/retry", None, "Règle synchronisée.")


@router.post("/{rid}/fix")
async def fix(request: Request, rid: str, csrf: str = Form("")):
    return await _act(request, csrf, "POST", f"/rules/{rid}/fix", None, "Écart corrigé.")


# ── Synchronisation ─────────────────────────────────────────────────────────────────────────
def _page_sync(request: Request, rep: dict | None, status: dict, flash: str = "") -> str:
    hid = _hidden(request)
    last = status.get("last_sync")
    head = (f'<div class="hint">Dernière synchronisation : {_fmt(last.get("at"))}.</div>' if last else '<div class="hint">Jamais synchronisé.</div>')
    body = f"""{flash}
<div class="section">
  <div class="section-title">Comparer la base et Gmail</div>
  <div class="hint" style="margin:0 0 .8rem">La comparaison <strong>lit seulement</strong> : elle n'écrit rien dans Gmail. Chaque écart se corrige ensuite d'un clic, après lecture. Elle tourne aussi chaque matin à 6h30 (une alerte part si un écart nouveau apparaît).</div>
  {head}
  <form method="POST" action="/newsletter/gmail/sync" style="margin-top:.7rem">{hid}<button class="btn btn-primary">🔄 Synchroniser maintenant</button></form>
</div>"""
    if rep is None:
        return body
    drift = "".join(
        f'<div class="rule"><div class="rule-title">{_e(d["name"])}</div><div class="warn">⚠ {_e(_DRIFT.get(d["kind"], d["kind"]))}</div>'
        f'<div class="actions"><form method="POST" action="/newsletter/gmail/{d["rule_id"]}/fix" onsubmit="return confirm(\'Réaligner Gmail sur la règle de la base ?\')">{hid}<button class="btn btn-primary btn-sm">🛠 Corriger (Gmail = règle)</button></form>'
        f'<a class="btn btn-secondary btn-sm" href="/newsletter/gmail/{d["rule_id"]}/edit">✏️ Ouvrir la règle</a></div></div>'
        for d in rep.get("drift", [])) or '<p class="empty">Aucun écart : chaque règle correspond à son filtre.</p>'
    orphans = "".join(
        f'<div class="rule"><div class="rule-title">Filtre {_e(o["id"])}</div>'
        f'<div class="rule-line">{_e(_crit(o))}</div><div class="hint">Créé par le script, mais aucune règle de la base ne le revendique.</div>'
        f'<div class="actions"><form method="POST" action="/newsletter/gmail/orphans/{_e(o["id"])}/adopt">{hid}<button class="btn btn-primary btn-sm">📥 Adopter (créer la règle)</button></form>'
        f'<form method="POST" action="/newsletter/gmail/orphans/{_e(o["id"])}/delete" onsubmit="return confirm(\'Supprimer ce filtre de Gmail ?\')">{hid}<button class="btn btn-danger btn-sm">🗑 Supprimer le filtre</button></form></div></div>'
        for o in rep.get("orphans", [])) or '<p class="empty">Aucun filtre orphelin.</p>'
    foreign = "".join(f'<div class="rule-line">• {_e(f["id"])} — {_e(_crit(f))}</div>' for f in rep.get("foreign", [])) \
        or '<p class="empty">Aucun.</p>'
    return body + f"""
<div class="section"><div class="section-title">Écarts sur les règles</div>{drift}</div>
<div class="section"><div class="section-title">Filtres orphelins</div>{orphans}</div>
<div class="section"><div class="section-title">Filtres Gmail étrangers (lecture seule)</div>
  <div class="hint" style="margin:0 0 .6rem">Créés à la main : le script ne les modifie ni ne les supprime jamais.</div>{foreign}</div>"""


def _crit(f: dict) -> str:
    c = f.get("criteria") or {}
    a = f.get("action") or {}
    bits = [f"de {c['from']}" if c.get("from") else "", f"objet « {c['subject']} »" if c.get("subject") else "",
            f"→ {a['forward']}" if a.get("forward") else ""]
    return " ".join(b for b in bits if b) or "(critères non affichables)"


@router.get("/sync", response_class=HTMLResponse)
async def sync_view(request: Request, ok: str = "", error: str = ""):
    if r := _guard(request):
        return r
    status = {}
    try:
        status = await _gapi("GET", "/status")
    except GmailError as exc:
        error = error or exc.message
    return _wrap("Synchronisation", "sync", _page_sync(request, None, status, _flash(ok, error)))


@router.post("/sync", response_class=HTMLResponse)
async def sync_run(request: Request, csrf: str = Form("")):
    if r := _guard(request):
        return r
    if not _csrf_ok(request, csrf):
        return _to("/newsletter/gmail/sync", error="Session de formulaire expirée : rechargez la page.")
    try:
        rep = await _gapi("POST", "/sync")
        status = await _gapi("GET", "/status")
    except GmailError as exc:
        return _to("/newsletter/gmail/sync", error=exc.message)
    return _wrap("Synchronisation", "sync", _page_sync(request, rep, status))


@router.post("/orphans/{fid}/{what}")
async def orphan_act(request: Request, fid: str, what: str, csrf: str = Form("")):
    if what not in ("adopt", "delete"):
        return _to("/newsletter/gmail/sync", error="Action inconnue")
    return await _act(request, csrf, "POST", f"/orphans/{fid}/{what}", None,
                      "Filtre adopté." if what == "adopt" else "Filtre supprimé.", back="/newsletter/gmail/sync")


# ── Journal ─────────────────────────────────────────────────────────────────────────────────
@router.get("/audit", response_class=HTMLResponse)
async def audit_view(request: Request, action: str = "", only_errors: str = ""):
    if r := _guard(request):
        return r
    from urllib.parse import urlencode
    q = urlencode({k: v for k, v in (("action", action), ("ok", "false" if only_errors else "")) if v})
    err, rows = "", []
    try:
        rows = (await _gapi("GET", f"/audit?{q}"))["audit"]
    except GmailError as exc:
        err = exc.message
    trs = "".join(
        f'<tr><td>{_fmt(a["at"])}</td><td>{_e(a["actor"] or "")}</td><td>{_e(a["action"])}</td>'
        f'<td class="{"" if a["ok"] else "err"}">{"ok" if a["ok"] else _e(a["error_code"] or "échec")}</td><td>{_e(a["detail"] or "")}</td></tr>'
        for a in rows) or ""
    table = (f'<div class="tblwrap"><table class="mails"><tr><th>Quand</th><th>Qui</th><th>Action</th><th>Issue</th><th>Détail</th></tr>{trs}</table></div>'
             if trs else '<p class="empty">Aucune entrée.</p>')
    body = f"""{_flash(error=err)}
<div class="section"><div class="section-title">Journal des appels au script</div>
  <div class="hint" style="margin:0 0 .6rem">Chaque appel signé est tracé (qui, quoi, résultat, empreinte du contenu) — jamais le secret ni la signature. Conservé 12 mois.</div>
  <div class="actions" style="margin:0 0 .8rem"><a class="btn btn-secondary btn-sm" href="/newsletter/gmail/audit">Tout</a><a class="btn btn-secondary btn-sm" href="/newsletter/gmail/audit?only_errors=1">Échecs seulement</a></div>
  {table}
</div>"""
    return _wrap("Journal", "audit", body)


# ── Script & secret ─────────────────────────────────────────────────────────────────────────
def _page_secret(request: Request, status: dict, flash: str = "", new_secret: str = "", ping: dict | None = None) -> str:
    hid = _hidden(request)
    lp = ping or status.get("last_ping")
    ping_line = ""
    if lp:
        ping_line = (f'<div class="hint">Dernier test : {_fmt(lp.get("at"))} — ' + ("✓ le script répond" + (f" (version {_e(str(lp.get('version')))})" if lp.get("version") else "")
                     if lp.get("ok") else f'<span class="err">échec — {_e(str(lp.get("error") or ""))}</span>') + "</div>")
    age = status.get("secret_age_days")
    secret_box = ""
    if new_secret:
        secret_box = f"""
<div class="section"><div class="section-title">Nouveau secret — affiché une seule fois</div>
  <div class="secret">{_e(new_secret)}</div>
  <ol class="steps"><li>Dans le projet Apps Script : Paramètres du projet → Propriétés du script → <code>HMAC_SECRET</code> → collez cette valeur → enregistrez.</li>
  <li>Revenez ici et cliquez « Confirmer ». Le Hub teste le nouveau secret avant de l'adopter ; l'ancien reste actif tant que le test échoue.</li></ol>
  <div class="actions"><form method="POST" action="/newsletter/gmail/secret/confirm">{hid}<button class="btn btn-primary">✅ Confirmer la rotation</button></form>
  <form method="POST" action="/newsletter/gmail/secret/cancel">{hid}<button class="btn btn-secondary">Annuler</button></form></div></div>"""
    elif status.get("rotation_pending"):
        secret_box = f"""<div class="section"><div class="section-title">Rotation en cours</div>
  <div class="hint">Un nouveau secret a été généré mais pas confirmé. Pour le revoir, annulez puis recommencez.</div>
  <div class="actions"><form method="POST" action="/newsletter/gmail/secret/confirm">{hid}<button class="btn btn-primary">✅ Confirmer</button></form>
  <form method="POST" action="/newsletter/gmail/secret/cancel">{hid}<button class="btn btn-secondary">Annuler</button></form></div></div>"""
    return f"""{flash}
<div class="section"><div class="section-title">Connexion au script</div>
  <div class="hint" style="margin:0 0 .6rem">{'Configuré.' if status.get('configured') else '<span class="err">Non configuré : renseignez GMAIL_SCRIPT_URL et GMAIL_SCRIPT_SECRET dans l\'environnement du service.</span>'}
  Domaines de destination autorisés : {_e(", ".join(status.get("allowed_domains") or []) or "—")}. Domaines interdits comme expéditeur : {_e(", ".join(status.get("deny_from") or []) or "aucun")}.</div>
  {ping_line}
  <form method="POST" action="/newsletter/gmail/script/ping" style="margin-top:.7rem">{hid}<button class="btn btn-primary">📡 Tester la connexion</button></form>
</div>
<div class="section"><div class="section-title">Secret partagé</div>
  <div class="hint" style="margin:0 0 .6rem">{'Âge : ' + str(age) + ' jours' + (' — <span class="err">à renouveler</span>' if status.get('secret_too_old') else '') if age is not None else 'Âge inconnu.'} Rotation conseillée tous les 6 mois ; une alerte est envoyée au-delà.</div>
  <form method="POST" action="/newsletter/gmail/secret/rotate" onsubmit="return confirm('Générer un nouveau secret ?')">{hid}<button class="btn btn-secondary">🔑 Renouveler le secret</button></form>
</div>{secret_box}"""


@router.get("/secret", response_class=HTMLResponse)
async def secret_view(request: Request, ok: str = "", error: str = ""):
    if r := _guard(request):
        return r
    status = {}
    try:
        status = await _gapi("GET", "/status")
    except GmailError as exc:
        error = error or exc.message
    return _wrap("Script & secret", "secret", _page_secret(request, status, _flash(ok, error)))


@router.post("/script/ping", response_class=HTMLResponse)
async def ping(request: Request, csrf: str = Form("")):
    if r := _guard(request):
        return r
    if not _csrf_ok(request, csrf):
        return _to("/newsletter/gmail/secret", error="Session de formulaire expirée : rechargez la page.")
    try:
        res = await _gapi("POST", "/script/ping")
        status = await _gapi("GET", "/status")
    except GmailError as exc:
        return _to("/newsletter/gmail/secret", error=exc.message)
    return _wrap("Script & secret", "secret", _page_secret(request, status, ping=res if "ok" in res else None))


@router.post("/secret/rotate", response_class=HTMLResponse)
async def rotate(request: Request, csrf: str = Form("")):
    if r := _guard(request):
        return r
    if not _csrf_ok(request, csrf):
        return _to("/newsletter/gmail/secret", error="Session de formulaire expirée : rechargez la page.")
    try:
        nxt = (await _gapi("POST", "/secret/rotate"))["secret"]
        status = await _gapi("GET", "/status")
    except GmailError as exc:
        return _to("/newsletter/gmail/secret", error=exc.message)
    return _wrap("Script & secret", "secret", _page_secret(request, status, new_secret=nxt))


@router.post("/secret/{what}")
async def rotate_end(request: Request, what: str, csrf: str = Form("")):
    if what not in ("confirm", "cancel"):
        return _to("/newsletter/gmail/secret", error="Action inconnue")
    return await _act(request, csrf, "POST", f"/secret/{what}", None,
                      "Rotation confirmée : le nouveau secret est actif." if what == "confirm" else "Rotation annulée.",
                      back="/newsletter/gmail/secret")
