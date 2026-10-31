#!/usr/bin/env python3
"""Mutations des gardes des pages Gmail du Hub (même protocole que newsletter-summary/checks/mutations.py).
Lancer : python3 projects/hub/checks/mutations_gmail.py   → BILAN mutations : N/N rouges pour la bonne raison"""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
G, M = "app/gmail.py", "app/main.py"
MUT = [
    ("CSRF non vérifié", G, "return bool(request.cookies.get(\"hub_session\")) and hmac.compare_digest(csrf_token(request, settings.SESSION_SECRET), token or \"\")", "return True", "H3"),
    ("jeton indépendant de la session", G, '("gmail-csrf:" + request.cookies.get(COOKIE_NAME, ""))', '("gmail-csrf:")', "H3 : jeton d'une autre session"),
    ("session non exigée", G, "    return _require_auth(request, settings)", "    return None", "H9"),
    ("liste non échappée", G, '<div class="rule-title">{_e(r["name"] or r["from"] or r["subject_contains"])}', '<div class="rule-title">{(r["name"] or r["from"] or r["subject_contains"])}', "H1"),
    ("erreur du script non échappée", G, '<div class="err" style="font-size:.78rem;margin-top:.3rem">{_e(r["last_error"])}</div>', '<div class="err" style="font-size:.78rem;margin-top:.3rem">{r["last_error"]}</div>', "H1"),
    ("orphelins non échappés", G, "f'<div class=\"rule-line\">{_e(_crit(o))}</div>", "f'<div class=\"rule-line\">{_crit(o)}</div>", "H6"),
    ("journal non échappé", G, "<td>{_e(a[\"detail\"] or \"\")}</td>", "<td>{(a[\"detail\"] or \"\")}</td>", "H7"),
    ("adresse non validée sélectionnable", G, 'dis = "" if a["selectable"] else " disabled"', 'dis = ""', "H2"),
    ("aperçu écrit", G, 'res = await _gapi("POST", "/preview", {**data, "id": rid or None})', 'res = await _gapi("POST", "/rules", {**data, "id": rid or None})', "H4"),
    ("confirmation large perdue", G, "need_confirm=exc.code == \"confirmation_required\", rid=rid))\n    return _wrap(\"Règle\", \"rules\", _page_form(request, data, addrs, warnings", "need_confirm=False, rid=rid))\n    return _wrap(\"Règle\", \"rules\", _page_form(request, data, addrs, warnings", "H5"),
    ("modification en création", G, 'await (_gapi("PUT", f"/rules/{rid}", d) if rid else _gapi("POST", "/rules", d))', 'await _gapi("POST", "/rules", d)', "H5"),
    ("action sur filtre étranger", G, "f'<div class=\"rule-line\">• {_e(f[\"id\"])}", "f'<div class=\"rule-line\"><form method=\"POST\" action=\"/newsletter/gmail/orphans/{_e(f[\"id\"])}/delete\"></form>• {_e(f[\"id\"])}", "H6"),
    ("secret affiché hors rotation", G, '</div>{secret_box}"""', '</div>{secret_box}<div class="hint">{_e("N" * 64)}</div>"""', "H8"),
    ("login sans verrou", M, "    if _login_blocked(ip):", "    if False:", "H10"),
    ("verrou global au lieu de par adresse", M, 'return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")) or "?"', 'return "global"', "H10"),
    ("compteur jamais purgé après succès", M, "    _LOGIN_FAILS.pop(ip, None)\n", "", "H10"),
]
def run():
    p = subprocess.run(["docker", "run", "--rm", "-v", f"{ROOT}:/w", "-w", "/w", "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "WEB_USERNAME=u", "-e", "WEB_PASSWORD=p",
                        "-e", "SESSION_SECRET=s", "hub-homepage:latest", "python", "checks/check_gmail_pages.py"], capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout + p.stderr
ok = 0
for name, rel, old, new, expect in MUT:
    path = ROOT / rel; orig = path.read_text()
    assert orig.count(old) == 1, f"« {name} » : motif trouvé {orig.count(old)}× dans {rel}"
    try:
        path.write_text(orig.replace(old, new)); code, out = run()
    finally:
        path.write_text(orig)
    if code == 0: v = "FAUX-VERT"
    elif expect in out: v, ok = "ROUGE-OK", ok + 1
    else: v = f"MAUVAIS-ROUGE (attendu « {expect} »)"
    last = next((l for l in reversed(out.splitlines()) if "Error" in l), "")[:110]
    print(f"{v:10s} | {name:40s} | {last}", flush=True)
print(f"BILAN mutations : {ok}/{len(MUT)} rouges pour la bonne raison")
sys.exit(0 if ok == len(MUT) else 1)
