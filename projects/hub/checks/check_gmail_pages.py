#!/usr/bin/env python3
"""Pages Hub « Gmail » : contenu, échappement, anti-CSRF sur chaque écriture, aperçu avant enregistrement,
secret jamais affiché hors rotation, limitation des tentatives de login.

Lancer : docker run --rm -v $PWD:/w -w /w -e PYTHONDONTWRITEBYTECODE=1 -e WEB_USERNAME=u -e WEB_PASSWORD=p -e SESSION_SECRET=s hub-homepage:latest python checks/check_gmail_pages.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx  # noqa: E402
from app import gmail as gm  # noqa: E402
import app.main as hubmain  # noqa: E402
import app.roadmap as roadmap  # noqa: E402
from app.auth import COOKIE_NAME, make_cookie_value  # noqa: E402

XSS = "<script>alert(1)</script>"
DEST = "veille@oozeenaru.resend.app"
RULES = [
    {"id": "r1", "name": f"Les Echos {XSS}", "enabled": True, "from": "news@lesechos.fr", "subject_contains": "", "exclude_words": "",
     "skip_inbox": True, "destination": DEST, "gmail_filter_id": "F1", "sync_status": "synced", "drift_kind": None, "pending_op": None, "last_error": None},
    {"id": "r2", "name": "", "enabled": True, "from": "", "subject_contains": f"Brief {XSS}", "exclude_words": "pub",
     "skip_inbox": False, "destination": DEST, "gmail_filter_id": None, "sync_status": "error", "drift_kind": None, "pending_op": "create",
     "last_error": f"destination_not_verified {XSS}"},
    {"id": "r3", "name": "Manuel", "enabled": False, "from": "@vieux.fr", "subject_contains": "", "exclude_words": "", "skip_inbox": False,
     "destination": DEST, "gmail_filter_id": None, "sync_status": "drift", "drift_kind": "missing", "pending_op": None, "last_error": None},
]
STATUS = {"configured": True, "active_rules": 2, "max_rules": 50, "secret_too_old": True, "secret_age_days": 200, "auth_failures": 0,
          "last_sync": {"at": "2026-10-31T06:30:00"}, "last_ping": {"ok": True, "at": "2026-10-31T10:00:00", "version": "1.1.0"},
          "rotation_pending": False, "allowed_domains": ["oozeenaru.resend.app"], "deny_from": ["banque.fr"]}
ADDRS = [{"email": DEST, "status": "accepted", "selectable": True, "alias": {"local_part": "veille", "frequency": "morning", "enabled": True}},
         {"email": "attente@oozeenaru.resend.app", "status": "pending", "selectable": False, "alias": None}]

calls = []
fail_next = {}


async def fake_gapi(method, path, payload=None):
    calls.append((method, path, payload))
    if (method, path) in fail_next:
        raise gm.GmailError(*fail_next.pop((method, path)))
    if path == "/status":
        return STATUS
    if path == "/rules" and method == "GET":
        return {"rules": RULES}
    if path == "/forwarding-addresses":
        return {"addresses": ADDRS, "stale": False}
    if path == "/preview":
        return {"ok": True, "warnings": ["l'expéditeur n'est pas dans la liste blanche de l'alias"]}
    if path == "/sync":
        return {"drift": [{"rule_id": "r3", "name": "Manuel", "kind": "missing"}],
                "orphans": [{"id": "F9", "criteria": {"from": f"x@y.fr{XSS}"}, "action": {"forward": DEST}}],
                "foreign": [{"id": "F7", "criteria": {"from": "ami@z.fr"}, "action": {"forward": "ami@z.fr"}}]}
    if path.startswith("/audit"):
        return {"audit": [{"id": 1, "at": "2026-10-31T10:00:00", "actor": "hub", "action": "create_rule", "ok": False,
                           "error_code": f"rate_limited{XSS}", "detail": XSS}]}
    if path == "/secret/rotate":
        return {"secret": "N" * 64}
    if path == "/script/ping":
        return {"ok": True, "at": "2026-10-31T10:05:00", "version": "1.1.0"}
    return {"rule": {**RULES[0], "sync_status": "synced"}, "warnings": []}


gm._gapi = fake_gapi
_real_auth = roadmap._require_auth
roadmap._require_auth = lambda request, settings: None


async def main():
    transport = httpx.ASGITransport(app=hubmain.app)
    cookie = make_cookie_value("u", hubmain.settings.SESSION_SECRET)
    async with httpx.AsyncClient(transport=transport, base_url="http://t", cookies={COOKIE_NAME: cookie}) as c:
        r = await c.get("/newsletter/gmail")
        h = r.text
        assert r.status_code == 200 and XSS not in h and "&lt;script&gt;" in h, "H1 : liste — contenu externe non échappé"
        assert "synchronisée" in h and "refusée par le script" in h and "écart avec Gmail" in h, "H1 : les 3 états doivent être lisibles"
        assert "le filtre n'existe plus dans Gmail" in h, "H1 : la nature de l'écart doit être nommée"
        assert "destination_not_verified" in h, "H1 : l'erreur du script doit être visible"
        assert "à renouveler" in h or "200 jours" in h, "H1 : secret trop vieux signalé"
        assert "désactivée" in h and "▶ Réactiver" in h and "⏸ Désactiver" in h, "H1 : activation/désactivation"
        assert r.headers["cache-control"] == "no-store", "H1 : pages sans cache"
        token = re.search(r'name="csrf" value="([0-9a-f]{32})"', h).group(1)
        assert h.count('name="csrf"') >= 8, "H1 : chaque formulaire d'écriture doit porter le jeton anti-CSRF"
        assert "/newsletter/gmail/r2/retry" in h and "/newsletter/gmail/r3/fix" in h, "H1 : réessayer sur l'erreur, corriger sur l'écart"
        assert "/newsletter/gmail/r1/retry" not in h, "H1 : pas de « réessayer » sur une règle synchronisée"

        # Formulaire : destinations croisées avec les alias, non validée non sélectionnable
        h = (await c.get("/newsletter/gmail/new")).text
        assert 'alias « veille », morning' in h and "[non validée par Gmail]" in h, "H2 : menu de destination croisé avec les alias"
        assert re.search(r'<option value="attente@oozeenaru.resend.app"[^>]* disabled', h), "H2 : adresse non validée non sélectionnable"
        assert "co.uk" in h, "H2 : l'aide nomme les suffixes publics refusés"

        # CSRF : refusé sans jeton ou avec un faux jeton, sans appel au service
        calls.clear()
        for path, data in [("/newsletter/gmail/save", {"from": "a@b.fr", "destination": DEST}),
                           ("/newsletter/gmail/r1/delete", {}), ("/newsletter/gmail/r1/toggle", {"enabled": "0"}),
                           ("/newsletter/gmail/sync", {}), ("/newsletter/gmail/secret/rotate", {}), ("/newsletter/gmail/script/ping", {}),
                           ("/newsletter/gmail/orphans/F9/delete", {}), ("/newsletter/gmail/secret/confirm", {})]:
            for csrf in (None, "0" * 32):
                r = await c.post(path, data={**data, **({"csrf": csrf} if csrf else {})}, follow_redirects=False)
                assert r.status_code == 303 and "expir" in r.headers["location"], \
                    f"H3 : {path} sans jeton valide aurait dû être refusée ({r.status_code} {r.headers.get('location')})"
        assert not [x for x in calls if x[0] != "GET"], f"H3 : une écriture a atteint le service malgré le CSRF : {calls}"
        # CSRF d'une autre session refusé
        other = make_cookie_value("u", "autre-secret")
        async with httpx.AsyncClient(transport=transport, base_url="http://t", cookies={COOKIE_NAME: other}) as c2:
            r = await c2.post("/newsletter/gmail/r1/delete", data={"csrf": token}, follow_redirects=False)
            assert r.status_code == 303 and "expir" in r.headers.get("location", ""), "H3 : jeton d'une autre session"
        assert not [x for x in calls if x[0] != "GET"], "H3 : jeton d'une autre session accepté"

        # Aperçu avant enregistrement : en clair, avertissements du moteur, bouton de confirmation
        calls.clear()
        form = {"csrf": token, "name": "n", "from": "@lesechos.fr", "subject_contains": "Brief", "exclude_words": "", "destination": DEST, "skip_inbox": "1"}
        r = await c.post("/newsletter/gmail/preview", data=form)
        h = r.text
        assert "Dès l'enregistrement" in h and "lesechos.fr" in h and "retirés de votre boîte de réception" in h, "H4 : aperçu en clair"
        assert "liste blanche de l'alias" in h, "H4 : avertissement du moteur affiché"
        assert "Confirmer et enregistrer" in h, "H4 : l'enregistrement passe par la confirmation"
        assert [x[:2] for x in calls if x[0] != "GET"] == [("POST", "/preview")], f"H4 : l'aperçu ne doit RIEN écrire : {calls}"
        # Règle large : le service demande confirmation → case à cocher réaffichée
        fail_next[("POST", "/preview")] = ("règle large", "confirmation_required", 400)
        h = (await c.post("/newsletter/gmail/preview", data={**form, "from": "", "subject_contains": "Brief du jour"})).text
        assert 'name="confirm_broad"' in h and "règle large" in h, "H5 : règle large → confirmation explicite"
        # Refus de validation : message du service, formulaire conservé
        fail_next[("POST", "/preview")] = ("expéditeur : le joker * est refusé", "criteria_too_broad", 400)
        h = (await c.post("/newsletter/gmail/preview", data={**form, "from": "*"})).text
        assert "joker" in h and 'value="*"' in h and "Confirmer et enregistrer" not in h, "H5 : refus affiché, saisie conservée, pas de confirmation"

        # Enregistrement : charge utile complète, booléens
        calls.clear()
        r = await c.post("/newsletter/gmail/save", data=form, follow_redirects=False)
        assert r.status_code == 303 and "synchronis" in r.headers["location"], r.headers
        m, p, body = calls[0]
        assert (m, p) == ("POST", "/rules") and body["from"] == "@lesechos.fr" and body["skip_inbox"] is True and body["confirm_broad"] is False, calls
        calls.clear()
        await c.post("/newsletter/gmail/r1/save", data=form, follow_redirects=False)
        assert calls[0][:2] == ("PUT", "/rules/r1"), "H5 : modification → PUT sur CETTE règle"

        # Synchronisation : écarts, orphelins (échappés), étrangers en lecture seule
        calls.clear()
        r = await c.post("/newsletter/gmail/sync", data={"csrf": token})
        h = r.text
        assert XSS not in h and "Corriger (Gmail = règle)" in h and "Adopter" in h and "ami@z.fr" in h and "lecture seule" in h, "H6 : page de synchronisation"
        assert 'action="/newsletter/gmail/orphans/F7' not in h, "H6 : aucune action sur un filtre étranger"
        # Journal
        h = (await c.get("/newsletter/gmail/audit")).text
        assert XSS not in h and "create_rule" in h, "H7 : journal échappé"
        # Rotation : le secret n'apparaît QUE sur la page de rotation, une fois
        h = (await c.post("/newsletter/gmail/secret/rotate", data={"csrf": token})).text
        assert "N" * 64 in h and "Confirmer la rotation" in h, "H8 : nouveau secret affiché à la rotation"
        for path in ("/newsletter/gmail", "/newsletter/gmail/secret", "/newsletter/gmail/sync", "/newsletter/gmail/audit"):
            assert "N" * 64 not in (await c.get(path)).text, f"H8 : le secret fuit sur {path}"

        # Non authentifié : redirigé vers le login
        roadmap._require_auth = _real_auth
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as anon:
            for path in ("/newsletter/gmail", "/newsletter/gmail/new", "/newsletter/gmail/audit"):
                r = await anon.get(path, follow_redirects=False)
                assert r.status_code == 302 and "/login" in r.headers["location"], f"H9 : {path} accessible sans session"
            r = await anon.post("/newsletter/gmail/r1/delete", data={"csrf": token}, follow_redirects=False)
            assert r.status_code == 302 and "/login" in r.headers["location"], "H9 : écriture sans session"
        assert not [x for x in calls if x[0] == "DELETE"], "H9 : une suppression a atteint le service sans session"

        # Limitation des tentatives de login
        hubmain._LOGIN_FAILS.clear()
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as lg:
            codes = [(await lg.post("/login", data={"username": "u", "password": "faux"}, headers={"x-forwarded-for": "9.9.9.9"})).status_code for _ in range(7)]
            assert codes[:5] == [401] * 5 and codes[5:] == [429, 429], f"H10 : verrou après 5 échecs : {codes}"
            r = await lg.post("/login", data={"username": "u", "password": hubmain.settings.WEB_PASSWORD}, headers={"x-forwarded-for": "9.9.9.9"})
            assert r.status_code == 429, "H10 : même le bon mot de passe est refusé pendant le verrou"
            r = await lg.post("/login", data={"username": "u", "password": hubmain.settings.WEB_PASSWORD}, headers={"x-forwarded-for": "8.8.8.8"}, follow_redirects=False)
            assert r.status_code == 302, "H10 : le verrou est par adresse, pas global"
            ip7 = {"x-forwarded-for": "7.7.7.7"}
            for _ in range(4):
                await lg.post("/login", data={"username": "u", "password": "faux"}, headers=ip7)
            await lg.post("/login", data={"username": "u", "password": hubmain.settings.WEB_PASSWORD}, headers=ip7)
            codes = [(await lg.post("/login", data={"username": "u", "password": "faux"}, headers=ip7)).status_code for _ in range(4)]
            assert codes == [401] * 4, f"H10 : un succès remet le compteur à zéro : {codes}"
    print("OK — pages Gmail : états, échappement, CSRF sur 8 écritures, aperçu sans écriture, secret une seule fois, login verrouillé")


asyncio.run(main())
