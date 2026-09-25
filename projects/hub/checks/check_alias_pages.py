#!/usr/bin/env python3
"""Pages Hub « Alias » : contenu attendu, échappement, et piège « désactiver la newsletter par oubli ».

Les données d'entrée ont la forme réelle des réponses de `GET /api/aliases`, `/api/prompt?alias_id=`
et `/api/aliases/{id}/mails` (cf. newsletter-summary/app/main.py). Deux risques précis :
  - un objet de mail ou un message d'erreur du service arrive du DEHORS : il doit être échappé ;
  - le formulaire de l'alias par défaut n'affiche pas la case « actif » : le POST ne doit alors pas
    envoyer `enabled` (sinon un enregistrement de réglages couperait la newsletter sans un mot).

Lancer : docker run --rm -v $PWD:/w -w /w -e PYTHONDONTWRITEBYTECODE=1 hub-homepage:latest python checks/check_alias_pages.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import newsletter as nl  # noqa: E402

XSS = '<script>alert(1)</script>'
LIST = {"domain": "oozeenaru.resend.app", "aliases": [
    {"id": 1, "local_part": "newsletter", "address": "newsletter@oozeenaru.resend.app", "enabled": True, "frequency": "morning",
     "is_default": True, "recipient": "jean@mailbox.org", "open_senders": True, "allowed_senders": [], "counts": {"summarized": 115, "ignored": 4}},
    {"id": 2, "local_part": "summary", "address": "summary@oozeenaru.resend.app", "enabled": True, "frequency": "minute",
     "is_default": False, "recipient": None, "open_senders": False, "allowed_senders": ["jean@exemple.fr"], "counts": {"new": 1, "failed": 2, "rejected": 3}},
    {"id": 3, "local_part": "vide", "address": "vide@oozeenaru.resend.app", "enabled": False, "frequency": "evening",
     "is_default": False, "recipient": None, "open_senders": False, "allowed_senders": [], "counts": {}},
]}
PROMPT = {"active_id": 5, "active_prompt": "Résume {email}", "versions": [{"id": 5, "created_at": "2026-09-25T08:00:00", "note": "copie", "prompt": "p", "is_active": True}]}
MAILS = [{"id": 9, "received_at": "2026-09-25T08:10:00", "from_addr": f"x@y.fr{XSS}", "subject": f"Objet {XSS}", "status": "failed",
          "attempts": 3, "last_error": f"page bloquée (403) {XSS}", "summarized_at": None}]

lst = nl._page_aliases(LIST, error=f"Le service a répondu 400 : {XSS}")
assert XSS not in lst and "&lt;script&gt;" in lst, "liste : erreur du service NON échappée"
assert "newsletter@oozeenaru.resend.app" in lst and "par défaut" in lst and "désactivé" in lst, "liste : adresse / badges"
assert "aucun expéditeur autorisé" in lst, "liste : un alias sans expéditeur doit le dire (sinon « personne » passe inaperçu)"
assert "2 échec(s)" in lst and "3 rejeté(s)" in lst and "1 en attente" in lst, "liste : les échecs/rejets doivent être VISIBLES"
assert all(f'<option value="{k}"' in lst for k in ("morning", "evening", "minute")), "création : les trois fréquences"
assert 'action="/newsletter/aliases/create"' in lst and "@oozeenaru.resend.app" in lst

det = nl._page_alias(LIST["aliases"][1], PROMPT, MAILS, error=XSS)
assert XSS not in det, "détail : sortie non échappée (objet, expéditeur, erreur ou message)"
assert 'action="/newsletter/aliases/2/save"' in det and 'action="/newsletter/aliases/2/prompt/save"' in det \
    and 'action="/newsletter/aliases/2/prompt/activate"' in det, "détail : les 3 formulaires doivent cibler CET alias"
assert re.search(r'<option value="minute" selected>', det) and "jean@exemple.fr" in det, "détail : réglages courants préremplis"
assert 'name="enabled_present"' in det and 'name="enabled"' in det, "détail : case « actif » attendue sur un alias non défaut"
assert "3 essai(s)" in det and "page bloquée (403)" in det, "détail : statut, essais et erreur nommée visibles"

dft = nl._page_alias(LIST["aliases"][0], PROMPT, [])
assert 'name="enabled"' not in dft and 'name="enabled_present"' not in dft, "alias par défaut : pas de case « actif » (foot-gun)"
assert "jean@mailbox.org" in dft and "checked" in dft.split('name="open_senders"')[1][:20], "alias par défaut : destinataire fixe + tous expéditeurs"

# Le POST de l'alias par défaut ne doit jamais envoyer `enabled`.
import asyncio, inspect  # noqa: E402
sent = {}
async def fake_api(method, path, payload=None):
    sent.update(method=method, path=path, payload=payload); return {"ok": True}
nl._api = fake_api
class Req:  # `_require_auth` n'est pas testé ici : on le neutralise
    pass
import app.roadmap as roadmap  # noqa: E402
import app.main as hubmain  # noqa: E402
roadmap._require_auth = lambda request, settings: None
asyncio.run(nl.alias_save(Req(), 1, frequency="morning", allowed_senders="", open_senders="on", enabled="", enabled_present=""))
assert "enabled" not in sent["payload"], f"un enregistrement de l'alias par défaut a envoyé enabled={sent['payload']}"
asyncio.run(nl.alias_save(Req(), 2, frequency="minute", allowed_senders="a@b.fr", open_senders="", enabled="", enabled_present="1"))
assert sent["payload"]["enabled"] is False and sent["payload"]["open_senders"] is False, sent
print("OK — pages Alias : contenu, échappement (3 sources), formulaires ciblés, alias par défaut protégé")
